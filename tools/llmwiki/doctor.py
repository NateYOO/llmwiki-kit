"""환경 점검: 학생이 막히는 지점을 PASS/WARN/FAIL로 보여 준다."""
from __future__ import annotations

import importlib
import locale
import os
import platform
import shutil
import sys
from pathlib import Path

from .util import Workspace, http_get


def run(ws: Workspace | None, offline: bool = False, as_json: bool = False) -> int:
    rows: list[tuple[str, str, str]] = []
    ok = lambda name, msg="": rows.append(("PASS", name, msg))
    warn = lambda name, msg: rows.append(("WARN", name, msg))
    fail = lambda name, msg: rows.append(("FAIL", name, msg))

    v = sys.version_info
    (ok if v >= (3, 10) else fail)("Python", f"{platform.python_version()} ({sys.executable})" + ("" if v >= (3, 10) else " → 3.10 이상 필요"))
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    (ok if in_venv else warn)("가상환경", sys.prefix if in_venv else "가상환경 밖에서 실행 중 — ./llmwiki 또는 .\\llmwiki.cmd 로 실행하세요")
    for mod, pkg, required in (("pymupdf", "pymupdf", True), ("yaml", "pyyaml", True), ("pyzotero", "pyzotero", False)):
        try:
            m = importlib.import_module(mod)
            ver = getattr(m, "__version__", getattr(m, "VersionBind", ""))
            if not ver:
                try:
                    import importlib.metadata as md
                    ver = md.version(pkg)
                except Exception:  # noqa: BLE001
                    ver = ""
            ok(pkg, ver)
        except Exception as e:  # noqa: BLE001
            (fail if required else warn)(pkg, f"import 실패: {e} → setup 스크립트를 다시 실행" + ("" if required else " (없어도 Zotero는 표준 HTTP로 조회)"))
    enc = (sys.stdout.encoding or "").lower()
    (ok if "utf" in enc else warn)("콘솔 인코딩", f"stdout={enc}, locale={locale.getpreferredencoding(False)}, PYTHONUTF8={os.environ.get('PYTHONUTF8', '')}")

    if ws is None:
        fail("작업 폴더", "AGENTS.md + wiki/ 가 있는 폴더를 찾지 못함")
    else:
        ok("작업 폴더", str(ws.root))
        for rel in ("AGENTS.md", "wiki/index.md", "wiki/log.md", ".agents/skills/wiki-ingest/SKILL.md",
                    ".agents/skills/wiki-query/SKILL.md", ".agents/skills/wiki-synthesize/SKILL.md"):
            (ok if (ws.root / rel).exists() else fail)(rel, "" if (ws.root / rel).exists() else "없음 → 키트를 다시 복사(llmwiki init)")
        agents = ws.root / "AGENTS.md"
        if (ws.root / "AGENTS.llmwiki.md").exists() and agents.exists() and "llmwiki" not in agents.read_text(encoding="utf-8", errors="ignore"):
            warn("키트 규칙(AGENTS)", "이 폴더에 원래 AGENTS.md가 있어서 키트 안내는 AGENTS.llmwiki.md에 두었어요. Codex는 AGENTS.md만 읽으니, 키트 규칙을 쓰게 하려면 AGENTS.llmwiki.md 내용을 원래 AGENTS.md 끝에 붙여 넣으세요(스킬 3개는 지금도 쓸 수 있어요).")
        if agents.exists():
            size = agents.stat().st_size
            (ok if size < 32 * 1024 else warn)("AGENTS.md 크기", f"{size} bytes" + ("" if size < 32 * 1024 else " — Codex 기본 상한 32KiB 초과"))
        try:
            probe = ws.wiki / ".llmwiki_write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            ok("쓰기 권한", "wiki/ 쓰기 가능")
        except OSError as e:
            fail("쓰기 권한", str(e))
        (ok if (ws.root / ".git").exists() else warn)("git", "git 저장소" if (ws.root / ".git").exists() else "git init 권장(선택): Codex가 프로젝트 루트를 확실히 인식")
        cfg = ws.config
        ext = cfg.get("zotero", {}).get("external_cli", {})
        if any(ext.values()):
            ok("Zotero 외부 CLI", "설정됨: " + ", ".join(k for k, v in ext.items() if v))

    # Zotero — 실습 컬렉션은 zotero next와 같은 규칙(resolve_collection)으로 정한다 (QA H45②)
    coll_todo = ""
    try:
        from .zotero import LocalApiBackend, SqliteBackend, default_data_dirs
        zcfg = (ws.config if ws else {}).get("zotero", {}) or {}
        base = zcfg.get("local_api_url", "http://127.0.0.1:23119/api")
        be = None
        # 실제 로컬 API 엔드포인트(/api/users/0/items/top)를 조회한다. /connector/ping만으로는
        # '로컬 API 허용' 설정이 꺼진 경우를 구분할 수 없어서, ping은 원인 안내에만 쓴다(QA 반영).
        try:
            api = LocalApiBackend(base, timeout=2)
            msg = api.status()
            ok("Zotero 로컬 API", f"{base}/users/0/items/top → {msg}")
            be = api
        except Exception as e:  # noqa: BLE001
            ping_ok = False
            try:
                st, _, _ = http_get(base.rsplit("/api", 1)[0] + "/connector/ping", timeout=2, headers={"Zotero-Allowed-Request": "1"})
                ping_ok = st == 200
            except Exception:  # noqa: BLE001
                pass
            if ping_ok:
                warn("Zotero 로컬 API", "Zotero는 실행 중이지만 로컬 API가 응답하지 않음 → "
                     "Zotero 설정(윈도우: 편집 → 설정, 맥: Zotero → 설정) → 고급 → 기타 → 'Allow other applications on this computer to communicate with Zotero' 체크")
            else:
                warn("Zotero 로컬 API", f"{str(e)[:120]} (Zotero 실행 + Zotero 설정(윈도우: 편집 → 설정, 맥: Zotero → 설정) → 고급 → 기타 → 'Allow other applications on this computer to communicate with Zotero' 체크)")
        # 데이터 폴더: llmwiki.yaml의 zotero.data_dir 먼저, 없으면 기본 위치 (QA H45①)
        conf_dir = str(zcfg.get("data_dir") or "").strip()
        cands = ([Path(conf_dir).expanduser()] if conf_dir else []) + default_data_dirs()
        dirs = [d for d in cands if (d / "zotero.sqlite").exists()]
        if dirs:
            ok("Zotero 데이터 폴더", str(dirs[0]) + (" (llmwiki.yaml data_dir)" if conf_dir and dirs[0] == Path(conf_dir).expanduser() else ""))
        elif conf_dir:
            warn("Zotero 데이터 폴더", f"llmwiki.yaml data_dir '{conf_dir}'에 zotero.sqlite 없음 → Zotero 설정→고급→파일 및 폴더의 '데이터 디렉터리 위치'로 고치기")
        else:
            warn("Zotero 데이터 폴더", "zotero.sqlite 못 찾음 (로컬 API가 되면 무시해도 됨)")
        if be is None and dirs and ws is not None:  # 로컬 API가 안 되면 sqlite 사본으로 컬렉션 점검을 대신함
            try:
                be = SqliteBackend(str(dirs[0]))
            except Exception:  # noqa: BLE001
                be = None
        if be is not None and ws is not None:
            coll_todo = _check_collection(be, ws.config, ok, warn)
    except Exception as e:  # noqa: BLE001
        warn("Zotero", str(e))

    if not offline:
        for name, url in (("arXiv API", "https://export.arxiv.org/api/query?id_list=1706.03762"), ("Crossref", "https://api.crossref.org/works/10.1038/nature14539")):
            try:
                st, _, _ = http_get(url, timeout=8)
                (ok if st == 200 else warn)(name, f"HTTP {st}")
            except Exception as e:  # noqa: BLE001
                warn(name, f"연결 실패({type(e).__name__}) — 메타데이터 보강 없이도 추출은 됩니다")
    if ws is not None:  # 위키 화면(선택) — 기본은 site/index.html을 파일로 열기, 주소 서버(serve)는 선택. WARN까지만, FAIL 없음
        try:
            from . import serve
            idx = ws.root / "site" / "index.html"
            if not idx.exists():
                rows.append(("INFO", "위키 화면", "아직 만들지 않음(설치 중이면 다음 단계에서 만듦) → 나중에는 Codex에게 「위키 화면 열어 줘」"))
            else:
                reviews = list(ws.papers.glob("*/review.md")) if ws.papers.exists() else []
                newest = max((r.stat().st_mtime for r in reviews), default=0)
                cur = serve.running(ws.root)
                st = serve.read_state(ws.root)
                if newest > idx.stat().st_mtime + 1:
                    warn("위키 화면", "위키보다 화면이 오래됐어요(선택) → Codex에게 「위키 화면 새로 만들어 줘」")
                elif st and not cur:
                    warn("위키 화면", "주소 서버가 꺼졌어요(선택) → 「이 폴더에서 위키 화면 다시 켜 줘」 · 파일로 보기는 그대로 됩니다")
                else:
                    ok("위키 화면", "site/index.html" + (f" · 주소 {cur['url']}" if cur else ""))
        except Exception as e:  # noqa: BLE001
            warn("위키 화면", f"확인 실패(선택): {str(e)[:80]}")
    codex = shutil.which("codex")
    rows.append(("INFO", "codex CLI", codex or "없음(데스크톱 앱만 써도 됨)"))

    fails = sum(1 for r in rows if r[0] == "FAIL")
    warns = sum(1 for r in rows if r[0] == "WARN")
    if as_json:
        import json
        print(json.dumps({"fail": fails, "warn": warns, "checks": [{"level": l, "name": n, "message": m} for l, n, m in rows],
                          "summary": summary_line(rows, coll_todo)}, ensure_ascii=True, indent=1))  # ASCII: 콘솔 코드페이지와 무관하게 파싱
        return 1 if fails else 0
    import unicodedata
    dw = lambda s: sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in s)
    width = max(dw(r[1]) for r in rows)
    for lvl, name, msg in rows:
        print(f"[{lvl}] {name}{' ' * (width - dw(name))}  {msg}")
    print(f"\n결과: FAIL {fails} · WARN {warns} — " + ("준비 완료!" if not fails else "FAIL 항목을 먼저 해결하세요."))
    print(summary_line(rows, coll_todo))
    return 1 if fails else 0


def _check_collection(be, cfg: dict, ok, warn) -> str:
    """zotero next와 같은 규칙으로 실습 컬렉션을 정하고 PDF 수를 센다. 돌려주는 값 = 요약 줄의 '남은 일'(없으면 "")."""
    from .zotero import ZoteroUnavailable, resolve_collection
    name = "실습 컬렉션"
    try:
        ckey, note = resolve_collection(be, cfg, "")
    except ZoteroUnavailable as e:
        first = str(e).splitlines()[0]
        if "여러 개" in first:
            warn(name, str(e).replace("\n", " "))
            return "llmwiki.yaml의 practice_collection을 쓸 컬렉션 이름으로 바꾸기(또는 Zotero에 'llmwiki-practice' 만들기)"
        want = (cfg.get("zotero", {}) or {}).get("practice_collection") or "llmwiki-practice"
        warn(name, f"컬렉션이 없음 → Zotero에서 새 컬렉션 '{want}'을 만들고 논문 PDF 1편 이상(1편 필수, 2편째 선택)을 넣으세요")
        return f"Zotero에 '{want}' 컬렉션 만들고 논문 PDF 1편 넣기"
    except Exception as e:  # noqa: BLE001
        warn(name, f"확인 실패: {str(e)[:100]}")
        return ""
    cname = next((c["name"] for c in be.collections() if c["key"] == ckey), ckey)
    try:
        items = be.search("", ckey, "", 50, with_pdf=True)
    except Exception as e:  # noqa: BLE001
        warn(name, f"'{cname}' 항목 확인 실패: {str(e)[:100]}")
        return ""
    with_pdf = sum(1 for i in items if i.get("pdf"))
    alone = sum(1 for i in items if i.get("standalone_pdf"))
    msg = (f"'{cname}': 논문 {len(items)}편" + (f"(단독 PDF {alone}개 포함 — 서지는 넣을 때 PDF에서 찾음)" if alone else "")
           + f", 로컬 PDF {with_pdf}편" + (f" · {note} (zotero next도 이 컬렉션을 씀)" if note else ""))
    if with_pdf:
        ok(name, msg)
        return ""
    warn(name, msg + " → 논문 PDF 1편을 이 컬렉션에 끌어다 넣기(PDF가 Zotero에 로컬 저장돼 있어야 함)")
    return f"Zotero의 '{cname}' 컬렉션에 논문 PDF 1편 넣기"


def summary_line(rows: list[tuple[str, str, str]], coll_todo: str = "") -> str:
    """사람이 읽는 한 줄 요약. 예: '설치 완료 ✅ / 남은 일: Zotero 설정 1개'"""
    fails = [n for l, n, _ in rows if l == "FAIL"]
    if fails:
        return f"설치 미완료 ❌ / 해결할 것: {', '.join(fails[:4])}"
    todo = []
    zot = [n for l, n, _ in rows if l == "WARN" and n.startswith("Zotero")]
    if any(n == "Zotero 로컬 API" for n in zot):
        todo.append("Zotero 설정 1개 (Zotero 실행 + Zotero 설정(윈도우: 편집 → 설정, 맥: Zotero → 설정) → 고급 → 기타 → 'Allow other applications on this computer to communicate with Zotero' 체크)")
    elif coll_todo:
        todo.append(coll_todo)
    net = [n for l, n, _ in rows if l == "WARN" and n in ("arXiv API", "Crossref")]
    if net:
        todo.append("인터넷 확인(선택: 서지 자동 보강용)")
    return "설치 완료 ✅ / 남은 일: " + (" · ".join(todo) if todo else "없음")
