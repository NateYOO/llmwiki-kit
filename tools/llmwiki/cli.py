"""llmwiki 명령줄 진입점. 하위 명령 모듈은 필요할 때만 import한다(init은 표준 라이브러리만으로 동작)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__

HELP_EPILOG = """자주 쓰는 순서:
  llmwiki doctor                          환경 점검
  llmwiki zotero search "키워드" --collection llmwiki-practice
  llmwiki zotero import <KEY>             (또는) llmwiki extract "논문.pdf"
  → 에이전트가 review.md 작성 →
  llmwiki related --write && llmwiki index && llmwiki log ingest "제목" && llmwiki lint
"""


def _print(obj, as_json: bool = True) -> None:
    if as_json:
        print(json.dumps(obj, ensure_ascii=False, indent=2))
    else:
        print(obj)


def _ws(args):
    from .util import find_workspace
    return find_workspace(args.root)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="llmwiki", description="LLM 위키 하네스 CLI (Zotero → 마크다운 논문 위키)",
                                epilog=HELP_EPILOG, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", help="작업 폴더 경로(기본: 현재 폴더에서 위로 AGENTS.md+wiki/ 탐색)")
    p.add_argument("--version", action="version", version=f"llmwiki {__version__}")
    sub = p.add_subparsers(dest="cmd", metavar="<명령>")

    s = sub.add_parser("doctor", help="환경 점검 (Python·패키지·폴더·Zotero·네트워크)")
    s.add_argument("--offline", action="store_true", help="네트워크 점검 생략")
    s.add_argument("--json", action="store_true", help="기계용 JSON 출력 (설치 스크립트가 사용)")

    s = sub.add_parser("init", help="기존 연구 폴더에 키트 설치 (기존 파일은 절대 덮어쓰지 않음)")
    s.add_argument("folder", help="설치할 폴더 (없으면 만듦)")
    s.add_argument("--append-agents", action="store_true", help="기존 AGENTS.md가 있으면 끝에 'AGENTS.llmwiki.md를 따르라' 안내 블록만 덧붙임")
    s.add_argument("--no-sample", action="store_true", help="examples/sample-wiki 복사 생략")

    s = sub.add_parser("sample", help="복구용 샘플 위키(3편)를 wiki/에 복사 (같은 이름은 건너뜀)")
    s.add_argument("--overwrite", action="store_true", help="같은 slug가 있어도 덮어씀")

    z = sub.add_parser("zotero", help="Zotero 검색·가져오기 (로컬 API → sqlite 사본 → 외부 CLI)")
    zs = z.add_subparsers(dest="zcmd", metavar="<하위명령>")
    for name, hlp in (("status", "어떤 백엔드로 연결되는지 확인"), ("collections", "컬렉션 목록")):
        x = zs.add_parser(name, help=hlp)
        x.add_argument("--backend", default="auto", choices=["auto", "local_api", "sqlite", "external"])
    x = zs.add_parser("search", help="키워드/컬렉션/태그로 항목 찾기 (PDF 경로 포함)")
    x.add_argument("query", nargs="?", default="", help="제목·저자·연도 키워드, 영어로 (생략 가능)")
    x.add_argument("--collection", default="", help="컬렉션 이름 또는 키 (예: llmwiki-practice)")
    x.add_argument("--tag", default="")
    x.add_argument("--limit", type=int, default=20)
    x.add_argument("--no-pdf", action="store_true", help="PDF 경로 조회 생략(빠름)")
    x.add_argument("--everything", action="store_true", help="제목·저자·연도뿐 아니라 초록·메모·전문 색인까지 검색 (qmode=everything)")
    x.add_argument("--backend", default="auto", choices=["auto", "local_api", "sqlite", "external"])
    x = zs.add_parser("get", help="항목 하나의 서지·PDF 경로")
    x.add_argument("key")
    x.add_argument("--backend", default="auto", choices=["auto", "local_api", "sqlite", "external"])
    x = zs.add_parser("import", help="Zotero 항목의 PDF를 추출해 위키에 넣을 준비 (= extract + Zotero 서지)")
    x.add_argument("key")
    x.add_argument("--slug")
    x.add_argument("--force", action="store_true")
    x.add_argument("--offline", action="store_true", help="Crossref/arXiv/OpenAlex 보강 생략")
    x.add_argument("--backend", default="auto", choices=["auto", "local_api", "sqlite", "external"])

    s = sub.add_parser("extract", help="PDF → wiki/papers/<slug>/ (source.md, meta.json, figures/, tables/, review.md 뼈대)")
    s.add_argument("pdf", help="PDF 경로 (Zotero 없이 직접 지정)")
    s.add_argument("--slug", help="폴더 이름 직접 지정")
    s.add_argument("--force", action="store_true", help="이미 있는 논문도 다시 추출(review.md는 보존)")
    s.add_argument("--offline", action="store_true", help="메타데이터 보강(네트워크) 생략")

    s = sub.add_parser("related", help="관련 논문 계산 (TF-IDF + BM25 → RRF, 저자·연도 규칙)")
    s.add_argument("--write", action="store_true", help="각 review.md의 '## Related Papers' 자동 블록 갱신")
    s.add_argument("--top", type=int, help="논문당 후보 수 (기본 5)")
    s.add_argument("--slug", help="이 논문 결과만 출력/갱신")
    s.add_argument("target", nargs="?", help="slug를 주면 그 논문의 이웃(관계·링크·주제·공저자)을 보여 줌: llmwiki related <slug>")
    s.add_argument("--json", action="store_true")

    s = sub.add_parser("search", help="위키 BM25 검색 (인용 꼬리표 포함)")
    s.add_argument("query")
    s.add_argument("--scope", default="wiki", choices=["wiki", "source", "figures", "drafts", "all"],
                   help="wiki=리뷰·주제, source=추출 원문(페이지), figures=그림·표 캡션, drafts=초안")
    s.add_argument("--top", type=int, default=8)
    s.add_argument("--json", action="store_true")

    s = sub.add_parser("find", help="정확한 문구 찾기 (대소문자·줄바꿈 무시, 페이지 표시)")
    s.add_argument("phrase")
    s.add_argument("--scope", default="all", choices=["all", "source", "wiki", "drafts"])
    s.add_argument("--json", action="store_true")

    s = sub.add_parser("figures", help="그림·표 찾기 (= search --scope figures)")
    s.add_argument("query")
    s.add_argument("--top", type=int, default=8)
    s.add_argument("--json", action="store_true")

    s = sub.add_parser("lint", help="기계 검사: 스키마·헤딩·깨진 링크·고아·중복 DOI·관련 링크 대칭·그림")
    s.add_argument("--json", action="store_true")
    s.add_argument("--fix", action="store_true", help="안전한 자동 수정: related --write + index 재생성 후 다시 검사")

    s = sub.add_parser("hubs", help="링크가 가장 많은 허브 논문 + 연결 덩어리(네트워크를 질문거리로)")
    s.add_argument("--top", type=int, default=10)
    s.add_argument("--json", action="store_true")

    s = sub.add_parser("clusters", help="주제 탐색용 군집(TF-IDF 평균연결) + 대표 단어 + 군집 간 유사도·링크 수")
    s.add_argument("--threshold", type=float, help="병합 기준 코사인(기본: 자동)")
    s.add_argument("--json", action="store_true")

    s = sub.add_parser("sections", help="여러 리뷰에서 같은 섹션만 모으기 (예: --name limitation,gap)")
    s.add_argument("--name", required=True, help="쉼표로 구분: essence,motivation,known,gap,why,approach,achievement,how,originality,limitation,evaluation,verdict,related")
    s.add_argument("--slugs", default="", help="쉼표로 구분한 slug만 (기본: 전체)")
    s.add_argument("--category", default="", help="category에 이 글자가 들어간 논문만")
    s.add_argument("--out", help="drafts/ 안에 markdown으로 저장 (예: drafts/limitations-raw.md)")
    s.add_argument("--force", action="store_true", help="--out 파일이 있어도 덮어씀")
    s.add_argument("--json", action="store_true")

    sub.add_parser("index", help="wiki/index.md 자동 블록 재생성 (카테고리별)")

    s = sub.add_parser("log", help="wiki/log.md에 한 줄 추가: ## [날짜] 종류 | 제목")
    s.add_argument("op", choices=["ingest", "query", "lint", "draft", "synthesize", "related", "setup", "fix"])
    s.add_argument("title")
    s.add_argument("--note", action="append", default=[], help="세부 bullet (여러 번 가능)")
    return p


def _print_results(rows, as_json):
    if as_json:
        _print(rows)
        return
    if not rows:
        print("결과 없음. 다른 단어(영어 원어/한국어)로 다시 찾거나 --scope all 을 써 보세요.")
    for r in rows:
        meta = f"  ({r['kind']}, score {r['score']})" if "score" in r else ""
        print(f"- {r.get('cite', '')}{meta}  {r['path']}")
        if r.get("image"):
            print(f"    이미지: {r['image']}" + (f" | 표 markdown: {r['markdown']}" if r.get("markdown") else ""))
        print(f"    {r.get('snippet') or r.get('context', '')}")


def main(argv: list[str] | None = None) -> int:
    from .console import setup_console
    setup_console()
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.cmd:
        parser.print_help()
        return 0

    if args.cmd == "init":
        from .scaffold import init
        res = init(Path(args.folder), append_agents=args.append_agents, with_sample=not args.no_sample)
        notes = res.pop("notes", [])
        _print(res)
        for n in notes:
            print("\n[안내] " + n)
        return 0

    if args.cmd == "doctor":
        from .doctor import run
        try:
            ws = _ws(args)
        except SystemExit:
            ws = None
        return run(ws, offline=args.offline, as_json=args.json)

    ws = _ws(args)

    if args.cmd == "sample":
        from .scaffold import restore_sample
        from .wikiops import append_log, write_index
        res = restore_sample(ws.root, overwrite=args.overwrite)
        if res["copied"]:
            from . import related
            related.write(ws, related.compute(ws))  # 내 논문과 샘플 논문 사이 관련 링크도 다시 계산
        write_index(ws)
        if res["copied"]:
            append_log(ws, "setup", "샘플 위키 복원", [f"복사: {', '.join(res['copied'])}"])
        _print(res)
        return 0

    if args.cmd == "zotero":
        from .zotero import ZoteroUnavailable, open_backend
        if not args.zcmd:
            parser.parse_args(["zotero", "--help"])
        try:
            backend, tried = open_backend(ws.config, args.backend)
        except ZoteroUnavailable as e:
            print(str(e), file=sys.stderr)
            return 2
        if args.zcmd == "status":
            _print({"backend": backend.name, "status": backend.status(), "fallback_log": tried})
        elif args.zcmd == "collections":
            _print(backend.collections())
        elif args.zcmd == "search":
            from .zotero import normalize_item
            rows = [normalize_item(r) for r in backend.search(args.query, args.collection, args.tag, args.limit,
                                                              with_pdf=not args.no_pdf, everything=args.everything)]
            for r in rows:
                r["abstract"] = (r.get("abstract") or "")[:300]
            out = {"backend": backend.name, "count": len(rows), "items": rows}
            if not rows and args.query:
                import re as _re
                hint = "0건입니다. Zotero 검색은 글자를 그대로 비교합니다."
                if _re.search(r"[\uac00-\ud7a3]", args.query):
                    hint += " 한국어 키워드로는 영어 논문이 나오지 않습니다 → 영어 단어로 바꿔 다시 검색하세요(예: 튜터링 → tutoring)."
                if not args.everything:
                    hint += " 초록·메모까지 찾으려면 --everything 을 붙이세요."
                out["hint"] = hint
            _print(out)
        elif args.zcmd == "get":
            from .zotero import normalize_item
            _print(normalize_item(backend.get(args.key)))
        elif args.zcmd == "import":
            from .ingest import extract_to_wiki
            from .zotero import normalize_item
            item = normalize_item(backend.get(args.key))
            if not item.get("pdf"):
                print(f"이 항목에 로컬 PDF가 없습니다(키 {args.key}). Zotero에서 PDF를 첨부하거나 `llmwiki extract <PDF>`를 쓰세요.", file=sys.stderr)
                return 2
            res = extract_to_wiki(ws, Path(item["pdf"]), seed=item, slug=args.slug, force=args.force,
                                  network=False if args.offline else None)
            res["zotero_backend"] = backend.name
            _print(res)
        return 0

    if args.cmd == "extract":
        from .ingest import extract_to_wiki
        res = extract_to_wiki(ws, Path(args.pdf), slug=args.slug, force=args.force, network=False if args.offline else None)
        _print(res)
        return 0 if res["status"] in ("ok", "duplicate") else 1

    if args.cmd == "related" and args.target and not args.write:
        from .network import neighbors
        res = neighbors(ws, args.target)
        if args.json:
            _print(res)
        else:
            print(f"{res['slug']} — {res['title']}\n이웃 {len(res['neighbors'])}편:")
            for r in res["neighbors"]:
                extra = " · ".join(x for x in [
                    f"관계 {r['relation']}" if r["relation"] else "",
                    ("링크 " + ",".join(r["links"])) if r["links"] else "링크 없음(후보만)",
                    ("주제 " + ",".join(r["shared_topics"])) if r["shared_topics"] else "",
                    ("공저자 " + ",".join(r["shared_authors"])) if r["shared_authors"] else "",
                    r["auto_reason"]] if x)
                print(f"  - {r['slug']} ({r['year']}) {extra}  {r['cite']}")
            print("\n" + res["hint"])
        return 0

    if args.cmd == "related":
        from . import related
        if args.target and not args.slug:
            args.slug = args.target
        res = related.compute(ws, top_k=args.top)
        if args.slug:
            res_view = {args.slug: res.get(args.slug, [])}
        else:
            res_view = res
        if args.write:
            changed = related.write(ws, res, only=args.slug)
            print(f"갱신한 review.md: {len(changed)}개 {changed}  (wiki/related.json 저장)")
        if args.json or not args.write:
            if args.json:
                _print(res_view)
            else:
                for slug, rows in res_view.items():
                    print(f"\n{slug}")
                    for r in rows:
                        print(f"  - [{r['relation']}] {r['slug']} — {r['reason']}")
        return 0

    if args.cmd in ("search", "figures"):
        from .search import search
        scope = "figures" if args.cmd == "figures" else args.scope
        _print_results(search(ws, args.query, scope=scope, top=args.top), args.json)
        return 0

    if args.cmd == "find":
        from .search import find_phrase
        _print_results(find_phrase(ws, args.phrase, scope=args.scope), args.json)
        return 0

    if args.cmd == "hubs":
        from .network import hubs
        res = hubs(ws, args.top)
        if args.json:
            _print(res)
        else:
            print(f"허브 논문 (연결된 논문 수 순, 전체 링크 {res['edges']}개)")
            for i, r in enumerate(res["hubs"], 1):
                print(f"  {i}. {r['slug']} ({r['year']}) — 연결 {r['degree']}편 · 근거 링크 {r['agent_links']} · 들어옴 {r['in']}/나감 {r['out']}"
                      + (f" · 주제 {','.join(r['topics'])}" if r["topics"] else "") + f"  {r['cite']}")
            print(f"\n연결 덩어리 {len(res['components'])}개:")
            for i, c in enumerate(res["components"], 1):
                print(f"  덩어리 {i} ({len(c)}편): {', '.join(c)}")
            print("\n" + res["hint"])
        return 0

    if args.cmd == "clusters":
        from . import related
        from .network import links_between
        res = related.clusters(ws, args.threshold)
        lb = links_between(ws, [[p["slug"] for p in c["papers"]] for c in res["clusters"]])
        for x in res["cross_links"]:
            m = next((y for y in lb if {y["a"], y["b"]} == {x["a"], x["b"]}), None)
            x["links"] = m["links"] if m else 0
            x["agent_links"] = m["agent_links"] if m else 0
        if args.json:
            _print(res)
        else:
            print(f"군집 기준 코사인: {res['threshold']}")
            for c in res["clusters"]:
                print(f"\n[군집 {c['cluster']}] {c['size']}편 · 대표 단어: {', '.join(c['top_terms'])} · category: {', '.join(c['categories'])}")
                for p in c["papers"]:
                    print(f"  - {p['slug']} ({p['year']})")
            if res["cross_links"]:
                print("\n군집 간 유사도·링크 수 (유사도 낮고 링크 0 = 아직 함께 연구되지 않은 조합 후보):")
                for x in res["cross_links"]:
                    print(f"  군집 {x['a']} × 군집 {x['b']}: 유사도 {x['similarity']} · 링크 {x['links']} (근거 링크 {x['agent_links']})")
        return 0

    if args.cmd == "sections":
        from . import sections
        names = [n.strip().lower() for n in args.name.split(",") if n.strip()]
        slugs = [x.strip() for x in args.slugs.split(",") if x.strip()] or None
        rows = sections.extract(ws, names, slugs, args.category)
        if args.json:
            _print(rows)
            return 0
        md = sections.to_markdown(rows, names)
        if args.out:
            print(f"저장: {sections.write_out(ws, args.out, md, args.force)} ({len(rows)}편)")
        else:
            print(md)
        return 0

    if args.cmd == "index":
        from .wikiops import write_index
        print(f"갱신: {ws.rel(write_index(ws))}")
        return 0

    if args.cmd == "log":
        from .wikiops import append_log
        print(append_log(ws, args.op, args.title, args.note))
        return 0

    if args.cmd == "lint":
        from . import lint
        if args.fix:
            from . import related
            from .wikiops import write_index
            related.write(ws, related.compute(ws))
            write_index(ws)
        issues = lint.run(ws)
        summ = lint.summarize(issues)
        if args.json:
            _print({"summary": summ, "issues": [i.as_dict() for i in issues]})
        else:
            for i in sorted(issues, key=lambda i: ({"ERROR": 0, "WARN": 1}.get(i.level, 2), i.path)):
                print(f"[{i.level}] {i.code:<14} {i.path}  {i.msg}")
            print(f"\n요약: ERROR {summ['errors']} · WARN {summ['warnings']}" + ("  ✅ 기계 검사 통과" if not summ["errors"] else ""))
        return 1 if summ["errors"] else 0

    parser.print_help()
    return 0
