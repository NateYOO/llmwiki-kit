"""메타데이터: DOI·arXiv ID 찾기와 키 없는 보강(arXiv API, Crossref, OpenAlex DOI 단건 조회).

모든 네트워크 호출은 실패해도 추출을 멈추지 않는다(오프라인 강의실 대비).
"""
from __future__ import annotations

import json
import os
import random
import re
import time
import urllib.error
import xml.etree.ElementTree as ET
from typing import Any

from .util import http_get, q, title_similarity

# 강의실(같은 IP 20–30명 동시) 대비: 짧은 타임아웃 + 짧은 재시도 + 논문당 전체 시간 상한.
REQ_TIMEOUT = 6.0        # 요청 1번의 최대 대기(초)
RETRIES = 2              # 429·5xx·타임아웃·연결 오류일 때 다시 시도하는 횟수(총 3번)
BACKOFF = 0.8            # 재시도 대기 기본값(초): 0.8 → 1.6 (+ 0–0.5초 무작위)
RETRY_AFTER_CAP = 3.0    # Retry-After가 이보다 크면 이 값까지만 기다림
BUDGET = 18.0            # 논문 1편의 외부 서지 조회 전체 시간 상한(초)
# 테스트용(인터넷 없이 가짜 서버로): LLMWIKI_ARXIV_BASE · LLMWIKI_CROSSREF_BASE · LLMWIKI_OPENALEX_BASE
ARXIV_BASE = os.environ.get("LLMWIKI_ARXIV_BASE", "https://export.arxiv.org").rstrip("/")
CROSSREF_BASE = os.environ.get("LLMWIKI_CROSSREF_BASE", "https://api.crossref.org").rstrip("/")
OPENALEX_BASE = os.environ.get("LLMWIKI_OPENALEX_BASE", "https://api.openalex.org").rstrip("/")


class Busy(RuntimeError):
    """서지 사이트가 바쁨(429·5xx·타임아웃·연결 오류) — 재시도 뒤에도 실패."""


class Budget:
    def __init__(self, seconds: float = BUDGET):
        self.end = time.monotonic() + seconds

    def left(self) -> float:
        return self.end - time.monotonic()


def _retry_after(headers: dict) -> float | None:
    for k, v in (headers or {}).items():
        if k.lower() == "retry-after":
            try:
                return max(0.0, float(str(v).strip()))
            except ValueError:
                return None
    return None


def get_with_retry(url: str, budget: Budget | None = None, timeout: float = REQ_TIMEOUT) -> bytes:
    """GET → 200이면 본문. 429·5xx·타임아웃·연결 오류는 짧게 재시도(지터 포함), 전체 시간은 budget 안에서만.
    그래도 안 되면 Busy, 그 밖의 HTTP 오류(404 등)는 RuntimeError."""
    budget = budget or Budget()
    last = ""
    for attempt in range(RETRIES + 1):
        t = min(timeout, budget.left())
        if t < 0.5:
            raise Busy(f"시간 상한 도달 ({last or '시도 전'})")
        try:
            status, body, headers = http_get(url, timeout=t)
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            status, body, headers, last = 0, b"", {}, f"연결/타임아웃: {type(e).__name__}"
        if status == 200:
            return body
        if status and status != 429 and status < 500:
            raise RuntimeError(f"HTTP {status}")
        if status:
            last = f"HTTP {status}"
        if attempt == RETRIES:
            break
        ra = _retry_after(headers) if status == 429 else None
        wait = min(ra, RETRY_AFTER_CAP) if ra is not None else BACKOFF * (2 ** attempt)
        wait += random.uniform(0, 0.5)
        if budget.left() - wait < 1.0:
            break
        time.sleep(wait)
    raise Busy(last or "응답 없음")


def _get_json(url: str, budget: Budget | None, timeout: float) -> Any:
    return json.loads(get_with_retry(url, budget, min(timeout, REQ_TIMEOUT)).decode("utf-8"))

DOI_RE = re.compile(r"\b(10\.\d{4,9}/[^\s\"<>{}|\\^`\[\]]+)", re.I)
ARXIV_RE = re.compile(r"arXiv:\s*(\d{4}\.\d{4,5})(v\d+)?", re.I)
ARXIV_FILE_RE = re.compile(r"(?<!\d)(\d{4}\.\d{4,5})(v\d+)?(?!\d)")


def clean_doi(doi: str) -> str:
    doi = doi.strip().rstrip(".,;)")
    doi = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", doi, flags=re.I)
    return doi


def find_doi(text: str) -> str:
    m = DOI_RE.search(text or "")
    if not m:
        return ""
    doi = clean_doi(m.group(1))
    # arXiv가 부여한 DOI(10.48550/arXiv.xxxx)는 그대로 둬도 되지만 저널 DOI가 우선
    return doi


def find_arxiv(text: str, filename: str = "") -> str:
    m = ARXIV_RE.search(text or "")
    if m:
        return m.group(1)
    m = ARXIV_FILE_RE.search(filename or "")
    if m:
        return m.group(1)
    return ""


def arxiv_lookup(arxiv_id: str, timeout: float = REQ_TIMEOUT, budget: Budget | None = None) -> dict[str, Any]:
    body = get_with_retry(f"{ARXIV_BASE}/api/query?id_list={q(arxiv_id)}", budget, min(timeout, REQ_TIMEOUT))
    ns = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    root = ET.fromstring(body)
    entry = root.find("a:entry", ns)
    if entry is None or entry.find("a:title", ns) is None:
        raise RuntimeError("arXiv 결과 없음")
    title = " ".join((entry.findtext("a:title", "", ns) or "").split())
    if not title or title.lower() == "error":
        raise RuntimeError("arXiv 결과 없음")
    out = {
        "title": title,
        "authors": [n for n in (" ".join((a.findtext("a:name", "", ns) or "").split()) for a in entry.findall("a:author", ns)) if n],
        "date": (entry.findtext("a:published", "", ns) or "")[:10],
        "abstract": " ".join((entry.findtext("a:summary", "", ns) or "").split()),
        "url": f"https://arxiv.org/abs/{arxiv_id}",
        "arxiv": arxiv_id,
    }
    doi = entry.findtext("arxiv:doi", "", ns)
    if doi:
        out["doi"] = clean_doi(doi)
    jr = entry.findtext("arxiv:journal_ref", "", ns)
    if jr:
        out["venue"] = " ".join(jr.split())
    return out


def _crossref_item(item: dict) -> dict[str, Any]:
    authors = []
    for a in item.get("author", []) or []:
        name = " ".join(x for x in [a.get("given", ""), a.get("family", "")] if x).strip()
        if name:
            authors.append(name)
    parts = (item.get("issued", {}) or {}).get("date-parts", [[None]])[0]
    date = "-".join(f"{p:02d}" if i else str(p) for i, p in enumerate(parts) if p) if parts and parts[0] else ""
    abstract = re.sub(r"<[^>]+>", " ", item.get("abstract", "") or "")
    return {
        "title": " ".join((item.get("title") or [""])[0].split()),
        "authors": authors,
        "date": date,
        "doi": clean_doi(item.get("DOI", "")),
        "venue": (item.get("container-title") or [""])[0],
        "abstract": " ".join(abstract.split()),
        "url": item.get("URL", ""),
    }


def crossref_by_doi(doi: str, timeout: float = REQ_TIMEOUT, mailto: str = "", budget: Budget | None = None) -> dict[str, Any]:
    url = f"{CROSSREF_BASE}/works/{q(doi)}" + (f"?mailto={q(mailto)}" if mailto else "")
    return _crossref_item(_get_json(url, budget, timeout)["message"])


def crossref_by_title(title: str, first_author: str = "", year: str = "", timeout: float = REQ_TIMEOUT, mailto: str = "", budget: Budget | None = None) -> dict[str, Any] | None:
    """제목 검색은 엉뚱한 결과가 1위로 오는 일이 있어(sources.md §4.4) 제목 유사도로 반드시 검증한다."""
    query = title + (" " + first_author if first_author else "")
    url = f"{CROSSREF_BASE}/works?rows=5&query.bibliographic={q(query)}" + (f"&mailto={q(mailto)}" if mailto else "")
    items = _get_json(url, budget, timeout)["message"].get("items", [])
    best, best_s = None, 0.0
    for it in items:
        cand = _crossref_item(it)
        s = title_similarity(title, cand["title"])
        if year and cand["date"][:4] and abs(int(cand["date"][:4]) - int(str(year)[:4])) > 2:
            s -= 0.3
        if s > best_s:
            best, best_s = cand, s
    if best and best_s >= 0.8:
        best["match_score"] = round(best_s, 2)
        return best
    return None


def openalex_by_doi(doi: str, timeout: float = REQ_TIMEOUT, budget: Budget | None = None) -> dict[str, Any]:
    """OpenAlex는 2026-02부터 키 없는 '검색'이 매우 제한적이지만 DOI 단건 조회는 비용 0(sources.md §4.4)."""
    data = _get_json(f"{OPENALEX_BASE}/works/doi:{q(doi)}", budget, timeout)
    return {
        "openalex": data.get("id", ""),
        "cited_by_count": data.get("cited_by_count"),
        "concepts": [c.get("display_name") for c in (data.get("concepts") or [])[:5]],
    }


BIB_KEYS = ("title", "authors", "date", "year", "doi", "venue", "abstract", "url", "arxiv")


def zotero_complete(meta: dict[str, Any]) -> bool:
    """Zotero에서 온 항목이고 제목·저자·연도가 다 있으면 True(외부 서지 조회를 하지 않는다)."""
    return bool(meta.get("zotero_key") and meta.get("title") and [a for a in (meta.get("authors") or []) if str(a).strip()]
                and (meta.get("year") or re.search(r"\d{4}", str(meta.get("date") or ""))))


def enrich(meta: dict[str, Any], *, network: bool = True, timeout: float = REQ_TIMEOUT, mailto: str = "",
           budget_s: float = BUDGET) -> dict[str, Any]:
    """빈칸만 채운다. 이미 있는 값(Zotero 등)은 절대 덮어쓰거나 비우지 않는다. 출처는 meta['sources']에 남긴다.
    우선순위: Zotero(시드) → (이미 있던 meta.json, ingest에서 합침) → arXiv → Crossref → OpenAlex → PDF 정보·첫 페이지(ingest).
    서지 사이트가 바빴으면(재시도 뒤에도 429·5xx·타임아웃) meta['_busy']=True (meta.json에는 저장하지 않음)."""
    sources = meta.setdefault("sources", [])
    notes = meta.setdefault("enrich_notes", [])
    if meta.get("zotero_key") and "zotero" not in sources:
        sources.append("zotero")
    if not network:
        notes.append("network disabled")
        return meta
    if zotero_complete(meta):
        notes.append("Zotero 서지(제목·저자·연도)가 있어 외부 서지 조회 생략")
        return meta
    budget = Budget(budget_s)
    timeout = min(float(timeout or REQ_TIMEOUT), REQ_TIMEOUT)

    weak = meta.get("_weak") or set()  # PDF 정보에서 추정한 값(예: 제목) — 서지 사이트 값이 오면 바꾼다

    def fill(new: dict, tag: str) -> None:
        for k, v in new.items():
            if isinstance(v, list):
                v = [x for x in v if str(x).strip()]
            if v and (not meta.get(k) or k in weak):
                meta[k] = v
                weak.discard(k)
        sources.append(tag)

    def attempt(tag: str, fn) -> Any:
        if budget.left() < 1.5:
            notes.append(f"{tag}: 시간 상한으로 건너뜀")
            meta["_busy"] = True
            return None
        try:
            return fn()
        except Busy as e:
            notes.append(f"{tag}: 바쁨({e})")
            meta["_busy"] = True
        except Exception as e:  # noqa: BLE001
            notes.append(f"{tag}: {e}")
        return None

    if meta.get("arxiv"):
        r = attempt("arxiv", lambda: arxiv_lookup(meta["arxiv"], timeout, budget))
        if r:
            fill(r, "arxiv")
    if meta.get("doi") and not str(meta["doi"]).lower().startswith("10.48550/"):
        r = attempt("crossref", lambda: crossref_by_doi(meta["doi"], timeout, mailto, budget))
        if r:
            fill(r, "crossref")
    elif not meta.get("doi") and meta.get("title"):
        hit = attempt("crossref-title", lambda: crossref_by_title(meta["title"], (meta.get("authors") or [""])[0],
                                                                 str(meta.get("date", ""))[:4], timeout, mailto, budget) or "")
        if hit:
            # 검증된 제목 일치일 때만 DOI·학술지를 받는다
            for k in ("doi", "venue"):
                if hit.get(k) and not meta.get(k):
                    meta[k] = hit[k]
                    if k == "doi":
                        meta["doi_source"] = f"crossref title match {hit['match_score']} (다른 판본 DOI일 수 있음 — 확인)"
            sources.append(f"crossref-title({hit['match_score']})")
        elif hit == "":
            notes.append("crossref-title: no verified match")
    if meta.get("doi"):
        r = attempt("openalex", lambda: openalex_by_doi(meta["doi"], timeout, budget))
        if r:
            fill(r, "openalex")
    return meta
