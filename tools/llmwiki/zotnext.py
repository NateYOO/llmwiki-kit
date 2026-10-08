"""`llmwiki zotero next` — 컬렉션에서 '최근에 넣은' 논문 1편을 골라 바로 넣는다 (QA H39·H41·H42).

순서: 컬렉션 정하기(설정 기본값) → dateAdded 내림차순으로 받기 → 로컬 PDF 없음·이미 위키에 있음 건너뛰기
→ N번째 후보(기본 1)를 import → 고른 논문 + 다음 후보 2편을 함께 보고.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .metadata import find_arxiv
from .util import Workspace
from .zotero import normalize_item, resolve_collection


def _seed_meta(item: dict[str, Any]) -> dict[str, Any]:
    arx = item.get("arxiv") or find_arxiv(" ".join(str(item.get(k, "")) for k in ("doi", "url", "extra")))
    return {"doi": item.get("doi", ""), "arxiv": arx, "zotero_key": item.get("key", ""), "title": item.get("title", "")}


def _brief(item: dict[str, Any]) -> dict[str, Any]:
    authors = item.get("authors") or []
    return {"key": item.get("key", ""), "title": item.get("title", ""), "year": item.get("year", ""),
            "first_author": authors[0] if authors else "", "date_added": item.get("date_added", "")}


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
                               "skipped_detail": {k: v[:5] for k, v in skipped.items() if v}}
        out.update(extra)
        return out

    idx = pick - 1
    while idx < len(eligible):
        chosen = eligible[idx]
        others = [dict(_brief(x), pick=i) for i, x in enumerate(eligible, 1) if i - 1 > idx][:2]
        info = {"picked": _brief(chosen), "other_candidates": others,
                "hint": "다른 논문을 원하면: `$wiki-ingest <제목 일부>` 또는 `llmwiki zotero next --pick 2`"}
        if dry_run:
            return summary("dry-run", **info)
        seed = {k: v for k, v in chosen.items() if k not in ("pdf", "date_added")}
        res = extract_to_wiki(ws, Path(chosen["pdf"]), seed=seed, network=False if offline else None)
        if res.get("status") == "duplicate":  # Zotero 서지로는 몰랐지만 PDF 내용(DOI·arXiv)이 같은 논문 → 다음 후보로
            skipped["in_wiki"].append(f"{chosen.get('title', '')[:60]} → {res.get('slug')} (PDF 내용으로 확인)")
            idx += 1
            continue
        res["zotero_backend"] = backend.name
        return summary(res.get("status", "ok"), slug=res.get("slug", ""), import_result=res, **info)
    return summary("none", message=(
        f"'{cname}'에 아직 위키에 없는 PDF 논문이 없어요. Zotero에서 PDF를 컬렉션에 끌어다 넣고 다시 말해 주세요."
        if pick == 1 else f"{pick}번째 후보가 없습니다(넣을 수 있는 논문 {len(eligible)}편)."))
    seed = {k: v for k, v in chosen.items() if k not in ("pdf", "date_added")}
    res = extract_to_wiki(ws, Path(chosen["pdf"]), seed=seed, network=False if offline else None)
    res["zotero_backend"] = backend.name
    base.update(status=res.get("status", "ok"), import_result=res, slug=res.get("slug", ""))
    return base
