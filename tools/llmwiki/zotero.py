"""Zotero 접근 어댑터 (읽기 전용).

우선순위(DESIGN.md·sources.md §8):
  1) local_api : Zotero 7+ 로컬 API (http://127.0.0.1:23119/api, 키 불필요, Zotero 실행 + 설정 허용 필요)
                 pyzotero(local=True)가 설치돼 있으면 그것으로 조회하고, 실패하면 표준 라이브러리 HTTP로 다시 시도한다.
                 어느 쪽이든 'Zotero-Allowed-Request: 1' 헤더를 붙인다.
  2) sqlite    : zotero.sqlite(+ -wal, -shm)를 임시 폴더로 복사해 읽기 전용으로 연다 (원본 DB에는 절대 쓰지 않음)
  3) external  : 외부 Zotero CLI를 꽂아 쓰는 자리 (llmwiki.yaml의 zotero.external_cli 명령 템플릿)
  (+ PDF 직접 경로는 `llmwiki extract <pdf>`가 처리)

모든 백엔드는 같은 형태의 dict를 돌려준다:
  {"key", "title", "authors": [..], "date", "year", "doi", "url", "abstract", "venue",
   "item_type", "collections": [..], "tags": [..], "pdf": "<로컬 경로 또는 ''>", "backend"}
"""
from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from .util import USER_AGENT, http_get, q


class ZoteroUnavailable(RuntimeError):
    pass


def collection_not_found(name: str, cols: list[dict[str, Any]]) -> ZoteroUnavailable:
    """없는 컬렉션 이름 → 지금 있는 컬렉션 목록과 다음 행동을 담은 한 덩어리 안내 (QA H38)."""
    names = [c["name"] for c in cols][:12]
    have = ", ".join(f"'{n}'" for n in names) if names else "(컬렉션이 하나도 없음)"
    first = names[0] if names else "컬렉션 이름"
    return ZoteroUnavailable(
        f"컬렉션 '{name}'을(를) 찾지 못했습니다.\n"
        f"  지금 있는 컬렉션: {have}\n"
        f"  해결: ① Zotero에서 'llmwiki-practice' 컬렉션을 만들고 논문 PDF 1편 이상을 넣거나\n"
        f"        ② 있는 이름으로 다시 찾기: llmwiki zotero search \"<영어 키워드>\" --collection \"{first}\"\n"
        f"        (전체 목록: llmwiki zotero collections)")


def pick_collection(name_or_key: str, cols: list[dict[str, Any]]) -> dict[str, Any]:
    """키 → 이름(대소문자 무시) → 이름 일부 순으로 찾는다. 일부 일치가 여럿이면 목록을 보여 주고 멈춘다."""
    for c in cols:
        if c["key"] == name_or_key:
            return c
    low = _nfc(name_or_key).lower()
    exact = [c for c in cols if _nfc(c["name"]).lower() == low]
    if exact:
        return exact[0]
    part = [c for c in cols if low and low in _nfc(c["name"]).lower()]
    if len(part) == 1:
        return part[0]
    if len(part) > 1:
        raise ZoteroUnavailable(f"'{name_or_key}'이(가) 들어간 컬렉션이 여러 개입니다:\n" + numbered_collections(part)
                                + "\n  해결: 정확한 이름으로 다시: --collection \"<이름>\"")
    raise collection_not_found(name_or_key, cols)


def numbered_collections(cols: list[dict[str, Any]]) -> str:
    return "\n".join(f"  {i}. {_nfc(c['name'])}" for i, c in enumerate(cols[:20], 1))


def resolve_collection(backend: Any, cfg: dict, explicit: str = "") -> tuple[str, str]:
    """(컬렉션 키, 안내) — QA H41.
    명시한 이름 > llmwiki.yaml의 zotero.practice_collection > 컬렉션이 하나뿐이면 그것 > 여럿이면 번호 목록과 함께 멈춤."""
    cols = backend.collections()
    if explicit:
        return pick_collection(explicit, cols)["key"], ""
    want = (cfg.get("zotero", {}) or {}).get("practice_collection") or ""
    if want:
        low = _nfc(want).lower()
        for c in cols:
            if c["key"] == want or _nfc(c["name"]).lower() == low:
                return c["key"], ""
    top = [c for c in cols if not c.get("parent")] or cols
    if len(top) == 1:
        note = (f"설정의 '{want}' 컬렉션이 없어 하나뿐인 컬렉션 '{_nfc(top[0]['name'])}'을(를) 씁니다."
                if want else f"컬렉션 '{_nfc(top[0]['name'])}'을(를) 씁니다.")
        return top[0]["key"], note
    if not top:
        raise ZoteroUnavailable(
            f"Zotero에 컬렉션이 없습니다.\n  해결: Zotero 왼쪽 'My Library' 우클릭 → 새 컬렉션 '{want or 'llmwiki-practice'}' → 논문 PDF 1편 이상 끌어다 넣기")
    raise ZoteroUnavailable(
        f"설정의 실습 컬렉션 '{want}'이(가) 없고 컬렉션이 여러 개입니다. 어느 것을 쓸지 번호를 골라 주세요:\n"
        + numbered_collections(top)
        + "\n  해결: 고른 이름으로 다시: --collection \"<이름>\"  (늘 같은 것을 쓰려면 llmwiki.yaml의 practice_collection을 그 이름으로)")


def _arxiv_from(text: str) -> str:
    m = re.search(r"(?:arxiv[:./\s]*|abs/)(\d{4}\.\d{4,5})", text or "", re.I)
    return m.group(1) if m else ""


def _year(date: str) -> str:
    m = re.search(r"(\d{4})", date or "")
    return m.group(1) if m else ""


# =========================================================== 1) local API
class LocalApiBackend:
    name = "local_api"

    HEADERS = {"Zotero-Allowed-Request": "1", "Accept": "application/json"}

    def __init__(self, base: str = "http://127.0.0.1:23119/api", timeout: float = 5):
        self.base = base.rstrip("/")
        self.timeout = timeout
        self._pz_obj: Any = None
        self.transport = "urllib"

    def _pz(self):
        """pyzotero 로컬 클라이언트 (없거나 만들 수 없으면 None)."""
        if self._pz_obj is None:
            self._pz_obj = False
            if os.environ.get("LLMWIKI_NO_PYZOTERO") != "1":
                try:
                    from pyzotero import zotero as pz  # type: ignore
                    try:
                        import httpx2 as hx  # type: ignore  # pyzotero 1.15+
                    except ImportError:
                        import httpx as hx  # type: ignore
                    client = hx.Client(headers=self.HEADERS, follow_redirects=True, timeout=self.timeout)
                    z = pz.Zotero(0, "user", local=True, client=client)
                    z.endpoint = self.base
                    self._pz_obj = z
                except Exception:
                    self._pz_obj = False
        return self._pz_obj or None

    def _call(self, method: str, args: tuple, params: dict, path: str) -> Any:
        """pyzotero로 먼저, 실패하면 urllib으로 같은 엔드포인트를 조회."""
        z = self._pz()
        if z is not None:
            try:
                res = getattr(z, method)(*args, **{k: v for k, v in params.items() if v not in (None, "") and k != "format"})
                self.transport = "pyzotero"
                return res
            except Exception:
                pass  # 아래 urllib 경로가 더 자세한 오류 메시지를 준다
        self.transport = "urllib"
        return self._get(path, params)

    def _get(self, path: str, params: dict | None = None) -> Any:
        url = f"{self.base}/users/0{path}"
        if params:
            url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v not in (None, "")})
        # 'Zotero-Allowed-Request: 1' + 비브라우저 UA → 브라우저 요청 차단 규칙 회피(sources.md §8.2)
        try:
            status, body, _ = http_get(url, timeout=self.timeout, headers=self.HEADERS)
        except Exception as e:  # 연결 거부 등
            raise ZoteroUnavailable(f"로컬 API 연결 실패({self.base}): Zotero가 실행 중인지 확인하세요. ({e})") from e
        if status == 403:
            raise ZoteroUnavailable("로컬 API 403: Zotero 설정 → 고급 → '이 컴퓨터의 다른 응용 프로그램이 Zotero와 통신하도록 허용'을 켜세요.")
        if status == 404 and path.startswith("/items/"):
            raise ZoteroUnavailable(f"Zotero 항목을 찾지 못했습니다(키 {path.rsplit('/', 1)[-1]}). "
                                    "키는 `llmwiki zotero search \"<영어 키워드>\"` 결과의 key 값(영문 대문자·숫자 8자)입니다.")
        if status != 200:
            raise ZoteroUnavailable(f"로컬 API HTTP {status}: {url}")
        text = body.decode("utf-8", errors="replace")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text

    def status(self) -> str:
        data = self._call("top", (), {"limit": 1, "format": "json"}, "/items/top")
        return f"OK (항목 응답 {len(data) if isinstance(data, list) else '?'}개, {self.transport})"

    def _item(self, raw: dict, with_pdf: bool = True) -> dict[str, Any]:
        d = raw.get("data", raw)
        authors = []
        for c in d.get("creators", []) or []:
            name = c.get("name") or " ".join(x for x in [c.get("firstName", ""), c.get("lastName", "")] if x)
            if name.strip():
                authors.append(name.strip())
        item = {
            "key": d.get("key") or raw.get("key", ""),
            "title": d.get("title", ""),
            "authors": authors,
            "date": d.get("date", ""),
            "year": _year(d.get("date", "")),
            "doi": d.get("DOI", "") or _doi_from_extra(d.get("extra", "")),
            "url": d.get("url", ""),
            "abstract": d.get("abstractNote", ""),
            "venue": d.get("publicationTitle") or d.get("proceedingsTitle") or d.get("conferenceName") or "",
            "item_type": d.get("itemType", ""),
            "collections": d.get("collections", []),
            "tags": [t.get("tag", "") for t in d.get("tags", []) or []],
            "citekey": d.get("citationKey", ""),
            "arxiv": _arxiv_from(" ".join(str(d.get(k, "")) for k in ("extra", "url", "DOI"))),
            "date_added": d.get("dateAdded", ""),
            "pdf": "",
            "backend": self.name,
        }
        if with_pdf:
            item["pdf"] = self.pdf_path(item["key"])
        return item

    def pdf_path(self, key: str) -> str:
        try:
            children = self._call("children", (key,), {"format": "json"}, f"/items/{key}/children")
        except ZoteroUnavailable:
            return ""
        for ch in children if isinstance(children, list) else []:
            d = ch.get("data", {})
            if d.get("contentType") == "application/pdf":
                try:
                    url = self._get(f"/items/{d.get('key')}/file/view/url")
                except ZoteroUnavailable:
                    continue
                if isinstance(url, str) and url.startswith("file:"):
                    return file_url_to_path(url.strip())
        return ""

    def collections(self) -> list[dict[str, Any]]:
        data = self._call("collections", (), {"format": "json", "limit": 100}, "/collections")
        return [{"key": c["data"]["key"], "name": c["data"]["name"], "parent": c["data"].get("parentCollection") or ""} for c in data]

    def search(self, query: str = "", collection: str = "", tag: str = "", limit: int = 20, with_pdf: bool = True,
               everything: bool = False, sort: str = "") -> list[dict[str, Any]]:
        # 서버의 itemType 부정 조합('-attachment || note')은 기대대로 걸러지지 않아(QA H06),
        # '-attachment'만 서버에 맡기고 노트·주석은 여기서 거른 뒤, limit을 채울 때까지 start로 페이지를 넘긴다.
        ckey = self._collection_key(collection) if collection else ""
        out: list[dict[str, Any]] = []
        start, page = 0, max(25, min(100, limit * 2))
        for _ in range(20):  # 최대 2000건 훑기
            params = {"q": query, "qmode": "everything" if everything else "titleCreatorYear", "tag": tag,
                      "limit": page, "start": start, "format": "json", "itemType": "-attachment"}
            if sort:  # 'dateAdded' → 최근 추가 순 (QA 23129에서 sort/direction 동작 확인)
                params.update({"sort": sort, "direction": "desc"})
            if ckey:
                data = self._call("collection_items_top", (ckey,), params, f"/collections/{ckey}/items/top")
            else:
                data = self._call("top", (), params, "/items/top")
            data = data if isinstance(data, list) else []
            for r in data:
                if r.get("data", {}).get("itemType") in ("attachment", "note", "annotation"):
                    continue
                out.append(r)
                if len(out) >= limit:
                    break
            if len(out) >= limit or len(data) < page:
                break
            start += len(data)
        return [self._item(r, with_pdf) for r in out[:limit]]

    def get(self, key: str) -> dict[str, Any]:
        return self._item(self._call("item", (key,), {"format": "json"}, f"/items/{key}"))

    def _collection_key(self, name_or_key: str) -> str:
        return pick_collection(name_or_key, self.collections())["key"]


def _nfc(text: str) -> str:
    """macOS가 돌려주는 NFD(자모 분리) 한글을 NFC로 (QA H13)."""
    return unicodedata.normalize("NFC", text or "")


def existing_path(path: str) -> str:
    """경로를 NFC로 맞추되, 실제 파일이 NFD 이름이면 그 이름을 그대로 돌려준다."""
    if not path:
        return ""
    for cand in (path, unicodedata.normalize("NFC", path), unicodedata.normalize("NFD", path)):
        if os.path.exists(cand):
            return cand
    return path


def file_url_to_path(url: str) -> str:
    p = urllib.parse.urlparse(url)
    path = urllib.request.url2pathname(p.path)  # %xx 해제와 Windows 드라이브 문자 처리 포함
    if os.name == "nt" and p.netloc:  # UNC
        path = f"\\\\{p.netloc}{path}"
    return existing_path(path)


def _doi_from_extra(extra: str) -> str:
    m = re.search(r"^DOI:\s*(\S+)", extra or "", re.M | re.I)
    return m.group(1) if m else ""


# =========================================================== 2) sqlite copy
def default_data_dirs() -> list[Path]:
    home = Path.home()
    cands = [home / "Zotero"]
    if os.name == "nt" and os.environ.get("USERPROFILE"):
        cands.append(Path(os.environ["USERPROFILE"]) / "Zotero")
    # 프로필 prefs.js 의 사용자 지정 데이터 폴더(extensions.zotero.dataDir)
    prof_roots = [
        home / "Library/Application Support/Zotero/Profiles",  # macOS
        Path(os.environ.get("APPDATA", home / "AppData/Roaming")) / "Zotero/Zotero/Profiles",  # Windows
        home / ".zotero/zotero",  # Linux
    ]
    for root in prof_roots:
        if root.exists():
            for prefs in root.glob("*/prefs.js"):
                m = re.search(r'user_pref\("extensions\.zotero\.dataDir",\s*"(.+?)"\);', prefs.read_text(encoding="utf-8", errors="ignore"))
                if m:
                    cands.insert(0, Path(m.group(1).encode().decode("unicode_escape")))
    out, seen = [], set()
    for c in cands:
        if str(c) not in seen:
            seen.add(str(c))
            out.append(c)
    return out


def _base_attachment_dir() -> str:
    home = Path.home()
    for root in [home / "Library/Application Support/Zotero/Profiles", Path(os.environ.get("APPDATA", home / "AppData/Roaming")) / "Zotero/Zotero/Profiles", home / ".zotero/zotero"]:
        if root.exists():
            for prefs in root.glob("*/prefs.js"):
                m = re.search(r'user_pref\("extensions\.zotero\.baseAttachmentPath",\s*"(.+?)"\);', prefs.read_text(encoding="utf-8", errors="ignore"))
                if m:
                    return m.group(1).encode().decode("unicode_escape")
    return ""


class SqliteBackend:
    name = "sqlite"

    def __init__(self, data_dir: str = ""):
        dirs = [Path(data_dir).expanduser()] if data_dir else default_data_dirs()
        self.data_dir = next((d for d in dirs if (d / "zotero.sqlite").exists()), None)
        if self.data_dir is None:
            raise ZoteroUnavailable("zotero.sqlite를 찾지 못했습니다. llmwiki.yaml의 zotero.data_dir에 Zotero 데이터 폴더를 적어 주세요. 확인한 곳: " + ", ".join(map(str, dirs)))
        self._tmp: str | None = None
        self.conn = self._open()

    def _open(self) -> sqlite3.Connection:
        """원본은 건드리지 않고 sqlite + -wal + -shm 사본을 임시 폴더에서 읽는다.
        Zotero가 실행 중이면 최근 변경이 -wal에만 있을 수 있어 함께 복사한다(QA 반영)."""
        self._tmp = tempfile.mkdtemp(prefix="llmwiki-zotero-")
        src = self.data_dir / "zotero.sqlite"
        dst = Path(self._tmp) / "zotero.sqlite"
        try:
            shutil.copy2(src, dst)
            for suffix in ("-wal", "-shm"):
                side = self.data_dir / f"zotero.sqlite{suffix}"
                if side.exists():
                    shutil.copy2(side, Path(self._tmp) / f"zotero.sqlite{suffix}")
        except OSError as e:  # Windows에서 Zotero가 파일을 잠근 경우 등
            raise ZoteroUnavailable(f"zotero.sqlite 복사 실패({e}). Zotero를 켜고 로컬 API를 쓰거나, Zotero를 종료한 뒤 다시 시도하세요.") from e
        conn = sqlite3.connect(f"file:{dst.as_posix()}?mode=rw", uri=True)  # 사본이므로 WAL 반영을 위해 rw 허용
        conn.row_factory = sqlite3.Row
        return conn

    def close(self) -> None:
        try:
            self.conn.close()
        finally:
            if self._tmp:
                shutil.rmtree(self._tmp, ignore_errors=True)

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def status(self) -> str:
        n = self.conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        return f"OK ({self.data_dir}, items {n}개, 사본으로 읽음)"

    def _fields(self, item_id: int) -> dict[str, str]:
        rows = self.conn.execute(
            "SELECT f.fieldName, v.value FROM itemData d JOIN fields f ON f.fieldID=d.fieldID "
            "JOIN itemDataValues v ON v.valueID=d.valueID WHERE d.itemID=?", (item_id,)).fetchall()
        return {r["fieldName"]: r["value"] for r in rows}

    def _authors(self, item_id: int) -> list[str]:
        rows = self.conn.execute(
            "SELECT c.firstName, c.lastName FROM itemCreators ic JOIN creators c ON c.creatorID=ic.creatorID "
            "WHERE ic.itemID=? ORDER BY ic.orderIndex", (item_id,)).fetchall()
        return [" ".join(x for x in [r["firstName"], r["lastName"]] if x).strip() for r in rows]

    def _pdf(self, item_id: int) -> str:
        rows = self.conn.execute(
            "SELECT i.key, a.path FROM itemAttachments a JOIN items i ON i.itemID=a.itemID "
            "WHERE a.parentItemID=? AND a.contentType='application/pdf' "
            "AND a.itemID NOT IN (SELECT itemID FROM deletedItems)", (item_id,)).fetchall()
        for r in rows:
            path = r["path"] or ""
            if path.startswith("storage:"):
                cand = self.data_dir / "storage" / r["key"] / path[len("storage:"):]
            elif path.startswith("attachments:"):
                base = _base_attachment_dir()
                cand = Path(base) / path[len("attachments:"):] if base else Path(path)
            else:
                cand = Path(path)
            found = existing_path(str(cand))
            if os.path.exists(found):
                return found
        return ""

    def _row_to_item(self, row: sqlite3.Row, with_pdf: bool = True) -> dict[str, Any]:
        f = self._fields(row["itemID"])
        cols = [r[0] for r in self.conn.execute(
            "SELECT c.collectionName FROM collectionItems ci JOIN collections c ON c.collectionID=ci.collectionID WHERE ci.itemID=?", (row["itemID"],))]
        tags = [r[0] for r in self.conn.execute(
            "SELECT t.name FROM itemTags it JOIN tags t ON t.tagID=it.tagID WHERE it.itemID=?", (row["itemID"],))]
        return {
            "key": row["key"], "title": f.get("title", ""), "authors": self._authors(row["itemID"]),
            "date": f.get("date", "")[:10], "year": _year(f.get("date", "")),
            "doi": f.get("DOI", "") or _doi_from_extra(f.get("extra", "")), "url": f.get("url", ""),
            "abstract": f.get("abstractNote", ""),
            "venue": f.get("publicationTitle") or f.get("proceedingsTitle") or f.get("conferenceName") or "",
            "item_type": row["typeName"], "collections": cols, "tags": tags,
            "citekey": f.get("citationKey", ""),
            "arxiv": _arxiv_from(" ".join([f.get("extra", ""), f.get("url", ""), f.get("DOI", "")])),
            "date_added": row["dateAdded"] if "dateAdded" in row.keys() else "",
            "pdf": self._pdf(row["itemID"]) if with_pdf else "", "backend": self.name,
        }

    _BASE = ("SELECT i.itemID, i.key, i.dateAdded, t.typeName FROM items i JOIN itemTypes t ON t.itemTypeID=i.itemTypeID "
             "WHERE t.typeName NOT IN ('attachment','note','annotation') AND i.itemID NOT IN (SELECT itemID FROM deletedItems)")

    def collections(self) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT c.key, c.collectionName, p.key AS pkey FROM collections c LEFT JOIN collections p ON p.collectionID=c.parentCollectionID").fetchall()
        return [{"key": r["key"], "name": r["collectionName"], "parent": r["pkey"] or ""} for r in rows]

    def search(self, query: str = "", collection: str = "", tag: str = "", limit: int = 20, with_pdf: bool = True,
               everything: bool = False, sort: str = "") -> list[dict[str, Any]]:
        sql, args = self._BASE, []
        if collection:
            cols = self.collections()
            collection = pick_collection(collection, cols)["key"]
        fields = "'title','date','DOI','publicationTitle'" + (",'abstractNote','extra'" if everything else "")
        if collection:
            sql += (" AND i.itemID IN (SELECT ci.itemID FROM collectionItems ci JOIN collections c ON c.collectionID=ci.collectionID "
                    "WHERE c.key=?)")
            args += [collection]
        if tag:
            sql += " AND i.itemID IN (SELECT it.itemID FROM itemTags it JOIN tags tg ON tg.tagID=it.tagID WHERE lower(tg.name)=?)"
            args.append(tag.lower())
        if query:
            for word in query.split():
                like = f"%{word.lower()}%"
                sql += (" AND (i.itemID IN (SELECT d.itemID FROM itemData d JOIN fields f ON f.fieldID=d.fieldID JOIN itemDataValues v ON v.valueID=d.valueID "
                        f"WHERE f.fieldName IN ({fields}) AND lower(v.value) LIKE ?) "
                        "OR i.itemID IN (SELECT ic.itemID FROM itemCreators ic JOIN creators c ON c.creatorID=ic.creatorID WHERE lower(c.lastName) LIKE ? OR lower(c.firstName) LIKE ?))")
                args += [like, like, like]
        sql += (" ORDER BY i.dateAdded DESC" if sort == "dateAdded" else " ORDER BY i.dateModified DESC") + " LIMIT ?"
        args.append(limit)
        return [self._row_to_item(r, with_pdf) for r in self.conn.execute(sql, args).fetchall()]

    def get(self, key: str) -> dict[str, Any]:
        row = self.conn.execute(self._BASE + " AND i.key=?", (key,)).fetchone()
        if not row:
            raise ZoteroUnavailable(f"Zotero 항목을 찾지 못했습니다(키 {key}). "
                                    "키는 `llmwiki zotero search \"<영어 키워드>\"` 결과의 key 값(영문 대문자·숫자 8자)입니다.")
        return self._row_to_item(row)


# =========================================================== 3) external CLI slot
class ExternalCliBackend:
    """외부 Zotero CLI를 꽂는 자리. llmwiki.yaml 예:

    zotero:
      external_cli:
        search: "zotero-cli search {query} --json"      # {query} {collection} {tag} {limit} 치환
        get: "zotero-cli get {key} --json"
        collections: "zotero-cli collections --json"

    명령은 표준출력으로 JSON(목록 또는 객체)을 내야 한다. 필드 이름이 달라도
    title/authors(creators)/date/DOI/key/pdf(file, path, attachment) 등을 최대한 맞춰 읽는다.
    """
    name = "external"

    def __init__(self, cfg: dict):
        self.cfg = cfg or {}
        if not any(self.cfg.get(k) for k in ("search", "get", "collections")):
            raise ZoteroUnavailable("외부 Zotero CLI가 설정되지 않았습니다(llmwiki.yaml → zotero.external_cli). 선택 사항입니다.")

    def _run(self, tmpl: str, **kw) -> Any:
        if not tmpl:
            raise ZoteroUnavailable("이 동작에 대한 external_cli 명령이 비어 있습니다.")
        args = [a.format(**{k: str(v) for k, v in kw.items()}) for a in shlex.split(tmpl, posix=(os.name != "nt"))]
        exe = shutil.which(args[0])
        if not exe:
            raise ZoteroUnavailable(f"외부 CLI '{args[0]}'를 PATH에서 찾지 못했습니다.")
        r = subprocess.run([exe, *args[1:]], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        if r.returncode != 0:
            raise ZoteroUnavailable(f"외부 CLI 실패({r.returncode}): {r.stderr.strip()[:300]}")
        try:
            return json.loads(r.stdout)
        except json.JSONDecodeError as e:
            raise ZoteroUnavailable(f"외부 CLI 출력이 JSON이 아닙니다: {e}") from e

    @staticmethod
    def _norm(d: dict) -> dict[str, Any]:
        d = d.get("data", d)
        authors = d.get("authors") or [
            c.get("name") or " ".join(x for x in [c.get("firstName", ""), c.get("lastName", "")] if x) for c in d.get("creators", []) or []
        ]
        date = str(d.get("date") or d.get("year") or "")
        return {
            "key": d.get("key") or d.get("id") or "", "title": d.get("title", ""), "authors": [a for a in authors if a],
            "date": date, "year": _year(date), "doi": d.get("doi") or d.get("DOI") or "", "url": d.get("url", ""),
            "abstract": d.get("abstract") or d.get("abstractNote") or "", "venue": d.get("venue") or d.get("publicationTitle") or "",
            "item_type": d.get("itemType", ""), "collections": d.get("collections", []), "tags": d.get("tags", []),
            "citekey": d.get("citekey") or d.get("citationKey") or "",
            "pdf": d.get("pdf") or d.get("file") or d.get("path") or d.get("attachment") or "", "backend": "external",
        }

    def status(self) -> str:
        return "설정됨: " + ", ".join(k for k in ("search", "get", "collections") if self.cfg.get(k))

    def collections(self) -> list[dict[str, Any]]:
        data = self._run(self.cfg.get("collections", ""))
        return [{"key": c.get("key", ""), "name": c.get("name", ""), "parent": c.get("parent", "")} for c in (data or [])]

    def search(self, query: str = "", collection: str = "", tag: str = "", limit: int = 20, with_pdf: bool = True,
               everything: bool = False, sort: str = "") -> list[dict[str, Any]]:
        data = self._run(self.cfg.get("search", ""), query=query, collection=collection, tag=tag, limit=limit)
        if isinstance(data, dict):
            data = data.get("items") or data.get("results") or [data]
        return [self._norm(d) for d in data][:limit]

    def get(self, key: str) -> dict[str, Any]:
        return self._norm(self._run(self.cfg.get("get", ""), key=key))


def normalize_item(item: dict[str, Any]) -> dict[str, Any]:
    """문자열 필드를 NFC로 (macOS NFD 한글 대비)."""
    for k in ("title", "abstract", "venue", "pdf"):
        if k == "pdf":
            continue
        if isinstance(item.get(k), str):
            item[k] = _nfc(item[k])
    item["authors"] = [_nfc(a) for a in item.get("authors", []) if isinstance(a, str)]
    item["tags"] = [_nfc(t) for t in item.get("tags", []) if isinstance(t, str)]
    return item


# =========================================================== chooser
def open_backend(cfg: dict, prefer: str = "auto"):
    """설정 순서대로 시도해 처음 되는 백엔드를 돌려준다. (backend, 시도 기록)"""
    zcfg = cfg.get("zotero", {})
    order = [prefer] if prefer and prefer != "auto" else zcfg.get("order", ["local_api", "sqlite", "external"])
    tried = []
    for name in order:
        try:
            if name == "local_api":
                b = LocalApiBackend(zcfg.get("local_api_url", "http://127.0.0.1:23119/api"))
                b.status()
            elif name == "sqlite":
                b = SqliteBackend(zcfg.get("data_dir", ""))
            elif name == "external":
                b = ExternalCliBackend(zcfg.get("external_cli", {}))
            else:
                tried.append(f"{name}: 알 수 없는 백엔드")
                continue
            return b, tried
        except ZoteroUnavailable as e:
            tried.append(f"{name}: {e}")
        except Exception as e:  # noqa: BLE001
            tried.append(f"{name}: {type(e).__name__}: {e}")
    raise ZoteroUnavailable("사용 가능한 Zotero 백엔드가 없습니다.\n  - " + "\n  - ".join(tried) + "\n  → PDF 경로를 직접 주세요: llmwiki extract <PDF 경로>")
