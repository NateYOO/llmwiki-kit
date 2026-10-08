"""`llmwiki zotero next` — 컬렉션에서 '최근에 넣은' 논문 1편을 골라 바로 넣는다 (QA H39·H41·H42).

순서: 컬렉션 정하기(설정 기본값) → dateAdded 내림차순으로 받기 → 로컬 PDF 없음·이미 위키에 있음 건너뛰기
→ N번째 후보(기본 1)를 import → 고른 논문 + 다음 후보 2편을 함께 보고.
상위 항목 없는 단독 PDF(Zotero 메타데이터 검색 실패)도 후보다: 서지는 PDF에서 찾는다(QA H43).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .metadata import find_arxiv
from .util import Workspace
from .zotero import ingest_seed, normalize_item, resolve_collection


def _seed_meta(item: dict[str, Any]) -> dict[str, Any]:
    arx = item.get("arxiv") or find_arxiv(" ".join(str(item.get(k, "")) for k in ("doi", "url", "extra")))
    return {"doi": item.get("doi", ""), "arxiv": arx, "zotero_key": item.get("key", ""), "title": item.get("title", "")}


def _brief(item: dict[str, Any]) -> dict[str, Any]:
    authors = item.get("authors") or []
    out = {"key": item.get("key", ""), "title": item.get("title", ""), "year": item.get("year", ""),
           "first_author": authors[0] if authors else "", "date_added": item.get("date_added", "")}
    if item.get("standalone_pdf"):
        out["standalone_pdf"] = True  # 제목은 Zotero 첨부 이름. 넣을 때 PDF에서 서지를 다시 찾음
    return out


NONE_NO_PDF = "'{c}'에 넣을 수 있는 논문 PDF가 없어요. Zotero에서 논문 PDF 1편을 이 컬렉션에 끌어다 넣고 다시 말해 주세요."
NONE_ALL_IN_WIKI = "'{c}'의 PDF 논문은 모두 이미 위키에 있어요({n}편). 새 논문 PDF를 이 컬렉션에 끌어다 넣고 다시 말해 주세요."


def _none_message(cname: str, pick: int, n_eligible: int, skipped: dict[str, list[str]]) -> tuple[str, str]:
    """(none_reason, message). 첫 줄은 고정 문구 두 가지 중 하나(강의자료가 인용, T-NONE), 이어지는 '참고:' 줄은 상황별."""
    if pick > 1 and n_eligible:
        return "pick_out_of_range", f"{pick}번째 후보가 없습니다(넣을 수 있는 논문 {n_eligible}편). `llmwiki zotero next`(1번째)로 넣으세요."
    if skipped["in_wiki"]:
        reason, head = "all_in_wiki", NONE_ALL_IN_WIKI.format(c=cname, n=len(skipped["in_wiki"]))
    else:
        reason, head = "no_pdf", NONE_NO_PDF.format(c=cname)
    notes = []
    if skipped["no_pdf"]:
        notes.append(f"  참고: PDF가 붙지 않은 항목 {len(skipped['no_pdf'])}개 → Zotero에서 그 항목 오른쪽 클릭 → 첨부 파일 추가(PDF)")
    if skipped["pdf_missing"]:
        notes.append(f"  참고: PDF 파일이 이 컴퓨터에 없는 항목 {len(skipped['pdf_missing'])}개 → Zotero에서 PDF를 내려받기(동기화)")
    notes.append("  (Zotero 밖 PDF는 `$wiki-ingest raw/<파일>.pdf`)")
    return reason, "\n".join([head] + notes)


def run(ws: Workspace, backend: Any, *, collection: str = "", pick: int = 1, offline: bool = False,
        dry_run: bool = False, scan: int = 50) -> dict[str, Any]:
    from .ingest import extract_to_wiki, find_duplicate

    ckey, note = resolve_collection(backend, ws.config, collection)
    cname = next((c["name"] for c in backend.collections() if c["key"] == ckey), ckey)
    items = [normalize_item(i) for i in backend.search("", ckey, "", scan, with_pdf=False, sort="dateAdded")]
    skipped: dict[str, list[str]] = {"in_wiki": [], "no_pdf": [], "pdf_missing": []}
    eligible: list[dict[str, Any]] = []
    for it in items:
        dup = find_duplicate(ws, _seed_meta(it))
        if dup:
            skipped["in_wiki"].append(f"{it.get('title', '')[:60]} → {dup}")
            continue
        if len(eligible) >= pick + 6:  # 고를 것 + 다른 후보 2편 + 여유(PDF 내용으로 중복 판정될 때) — PDF 확인 호출 줄이기
            break
        pdf = it.get("pdf") or normalize_item(backend.get(it["key"])).get("pdf", "")
        if not pdf:
            skipped["no_pdf"].append(it.get("title", "")[:60])
            continue
        if not Path(pdf).exists():
            skipped["pdf_missing"].append(f"{it.get('title', '')[:60]} ({pdf})")
            continue
        it["pdf"] = pdf
        eligible.append(it)

    def summary(status: str, **extra: Any) -> dict[str, Any]:
        out: dict[str, Any] = {"status": status, "collection": cname, "collection_note": note,
                               "order": "dateAdded desc (Zotero에 추가한 날짜)",
                               "skipped": {k: len(v) for k, v in skipped.items()},
                               "skipped_detail": {k: v[:5] for k, v in skipped.items() if v},
                               "standalone_pdf_seen": sum(1 for x in items if x.get("standalone_pdf"))}
        out.update(extra)
        return out

    idx = pick - 1
    while idx < len(eligible):
        chosen = eligible[idx]
        # 다른 후보의 [번호] = 이번 목록에서의 최근 순위(화면 문구 「다른 후보: [2] … · [3] …」 유지).
        # hint의 명령은 '다음에 부르면 그 논문이 되는' 번호로 (QA H46③): 실제로 넣었으면 고른 논문이 빠지므로 1 작아진다.
        others = [dict(_brief(x), pick=i) for i, x in enumerate(eligible, 1) if i - 1 > idx][:2]
        hint = "다른 논문을 원하면: `$wiki-ingest <제목 일부>`"
        if others:
            n = others[0]["pick"] - (0 if dry_run else 1)
            hint += " 또는 `llmwiki zotero next" + (f" --pick {n}`" if n > 1 else "`") + f" (→ [{others[0]['pick']}] {others[0]['title'][:40]})"
        info = {"picked": _brief(chosen), "other_candidates": others, "hint": hint}
        if dry_run:
            return summary("dry-run", **info)
        seed = ingest_seed(chosen)
        res = extract_to_wiki(ws, Path(chosen["pdf"]), seed=seed, network=False if offline else None)
        if res.get("status") == "duplicate":  # Zotero 서지로는 몰랐지만 PDF 내용(DOI·arXiv)이 같은 논문 → 다음 후보로
            skipped["in_wiki"].append(f"{chosen.get('title', '')[:60]} → {res.get('slug')} (PDF 내용으로 확인)")
            idx += 1
            continue
        res["zotero_backend"] = backend.name
        return summary(res.get("status", "ok"), slug=res.get("slug", ""), import_result=res, **info)
    reason, msg = _none_message(cname, pick, len(eligible), skipped)
    return summary("none", none_reason=reason, message=msg)
