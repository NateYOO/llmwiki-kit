"""ingest의 기계적 부분: PDF → wiki/papers/<slug>/ (source.md, meta.json, figures/, tables/, review.md 뼈대).
리뷰 본문 작성·관련 논문 해석은 Codex 에이전트가 wiki-ingest 스킬 지시에 따라 한다(유료 API 없음)."""
from __future__ import annotations

import datetime as _dt
import json
import re
import shutil
from pathlib import Path
from typing import Any

import pymupdf

from . import __version__
from .metadata import enrich, find_arxiv, find_doi
from .pdfextract import extract_pdf
from .util import Workspace, dump_json, norm_title, read_text, slugify, unique_slug, write_text
from .wikiops import figures_listing, load_papers, review_skeleton, tables_listing


def find_duplicate(ws: Workspace, meta: dict) -> str | None:
    doi = (meta.get("doi") or "").lower()
    arx = meta.get("arxiv") or ""
    zkey = meta.get("zotero_key") or ""
    nt = norm_title(meta.get("title", ""))
    for p in load_papers(ws):
        m = {**p.meta, **{k: v for k, v in p.fm.items() if v}}
        if doi and str(m.get("doi", "")).lower() == doi:
            return p.slug
        if arx and str(m.get("arxiv", "")) == arx:
            return p.slug
        if zkey and m.get("zotero_key") == zkey:
            return p.slug
        if nt and len(nt) > 15 and norm_title(str(m.get("title", ""))) == nt:
            return p.slug
    return None


def extract_to_wiki(ws: Workspace, pdf: Path, *, seed: dict | None = None, slug: str | None = None,
                    force: bool = False, network: bool | None = None) -> dict[str, Any]:
    pdf = Path(pdf).expanduser()
    if not pdf.exists():
        raise SystemExit(f"PDF가 없습니다: {pdf}")
    if pdf.suffix.lower() != ".pdf":
        raise SystemExit(f"PDF 파일이 아닙니다: {pdf}")
    cfg = ws.config.get("network", {})
    if network is None:
        network = bool(cfg.get("enabled", True))
    meta: dict[str, Any] = {k: v for k, v in (seed or {}).items() if v}
    if meta.get("key") and not meta.get("zotero_key"):
        meta["zotero_key"] = meta.pop("key")
    meta.pop("backend", None)

    with pymupdf.open(str(pdf)) as doc:
        head = "\n".join(doc[i].get_text() for i in range(min(2, doc.page_count)))
        pdf_meta = doc.metadata or {}
    meta.setdefault("doi", find_doi(head))
    meta.setdefault("arxiv", find_arxiv(head, pdf.name))
    if not meta.get("doi"):
        meta.pop("doi", None)
    if not meta.get("arxiv"):
        meta.pop("arxiv", None)
    if not meta.get("title") and (pdf_meta.get("title") or "").strip() and len(pdf_meta["title"]) > 10:
        meta["title"] = pdf_meta["title"].strip()

    enrich(meta, network=network, timeout=float(cfg.get("timeout", 12)), mailto=str(cfg.get("mailto", "")))

    ex_probe_title = ""
    if not meta.get("title"):
        with pymupdf.open(str(pdf)) as doc:
            from .pdfextract import guess_title
            ex_probe_title = guess_title(doc[0])
        meta["title"] = ex_probe_title or pdf.stem
        meta.setdefault("enrich_notes", []).append("title guessed from first page (확인 필요)")
    if meta.get("date") and not meta.get("year"):
        m = re.search(r"\d{4}", str(meta["date"]))
        if m:
            meta["year"] = m.group(0)

    if not meta.get("year") and re.match(r"^\d{4}\.\d{4,5}", str(meta.get("arxiv") or "")):
        meta["year"] = "20" + str(meta["arxiv"])[:2]  # 오프라인: arXiv 번호 YYMM.NNNNN에서 연도만 추정
        meta.setdefault("enrich_notes", []).append("year guessed from arXiv id (오프라인)")

    dup = find_duplicate(ws, meta)
    if dup and not force:
        return {"status": "duplicate", "slug": dup, "message": f"이미 위키에 있는 논문입니다: wiki/papers/{dup}/ (다시 추출하려면 --force)"}
    if dup and force:
        slug = dup
    if not slug:
        slug = unique_slug(ws, slugify(meta["title"], meta.get("year"), (meta.get("authors") or [None])[0]))
    out = ws.paper_dir(slug)
    for sub in ("figures", "tables"):
        if (out / sub).exists():
            shutil.rmtree(out / sub)
    out.mkdir(parents=True, exist_ok=True)

    ex = extract_pdf(pdf, out)
    if not meta.get("abstract") and ex.abstract:
        meta["abstract"] = ex.abstract
        meta.setdefault("sources", []).append("pdf-abstract-guess")

    meta.update({
        "slug": slug,
        "pdf": str(pdf.resolve()),
        "page_count": ex.page_count,
        "figures": ex.figures,
        "tables": ex.tables,
        "captions_found": ex.captions_found,
        "warnings": ex.warnings,
        "extracted_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "llmwiki_version": __version__,
    })
    write_text(out / "meta.json", dump_json(meta) + "\n")

    src = [f"<!-- llmwiki source: 자동 추출 원문(검색·인용 확인용). 리뷰/주제 페이지에 통째로 옮기지 말 것. 원문 PDF: {pdf.name} -->",
           f"# Source text — {meta['title']}", ""]
    for i, page in enumerate(ex.pages, 1):
        src += [f"<!-- p.{i} -->", page, ""]
    write_text(out / "source.md", "\n".join(src))
    write_text(out / "figures" / "figures.md", figures_listing(meta))
    write_text(out / "tables" / "tables.md", tables_listing(meta, out / "tables"))

    created_review = False
    if not (out / "review.md").exists():
        write_text(out / "review.md", review_skeleton(meta, slug))
        created_review = True

    return {
        "status": "ok",
        "slug": slug,
        "dir": ws.rel(out),
        "title": meta["title"],
        "authors": meta.get("authors", []),
        "year": meta.get("year", ""),
        "doi": meta.get("doi", ""),
        "arxiv": meta.get("arxiv", ""),
        "pages": ex.page_count,
        "figures": len(ex.figures),
        "tables": len(ex.tables),
        "tables_with_text": sum(1 for t in ex.tables if t.get("text")),
        "captions_found": ex.captions_found,
        "low_confidence_crops": [f"fig{f['n']}" for f in ex.figures if f.get("low_confidence") or f["method"].startswith("fallback")]
        + [f"table{t['n']}" for t in ex.tables if t.get("low_confidence") or t["method"].startswith("fallback")],
        "metadata_sources": meta.get("sources", []),
        "metadata_notes": meta.get("enrich_notes", []),
        "warnings": ex.warnings,
        "review_skeleton_created": created_review,
        "next": [
            f"review.md 작성: {ws.rel(out / 'review.md')} (7섹션, 한국어, 근거 페이지 표기)",
            "그림 확인: figures/figures.md 에서 Essence/Achievement/How용 그림 고르기",
            f"리뷰를 다 쓴 뒤: llmwiki finish {slug}  (related --write + index + log + lint)",
        ],
    }
