"""ingest의 기계적 부분: PDF → wiki/papers/<slug>/ (source.md, meta.json, figures/, tables/, review.md 뼈대).
리뷰 본문 작성·관련 논문 해석은 Codex 에이전트가 wiki-ingest 스킬 지시에 따라 한다(유료 API 없음)."""
from __future__ import annotations

import datetime as _dt
import json
import re
import time
import shutil
from pathlib import Path
from typing import Any

import pymupdf

from . import __version__
from .metadata import BIB_KEYS, enrich, find_arxiv, find_doi
from .pdfextract import extract_pdf
from .util import Workspace, dump_json, norm_title, read_text, slugify, unique_slug, write_text
from .wikiops import figures_listing, load_papers, review_skeleton, scanned_stub, tables_listing


ZOTERO_FALLBACK = "서지 사이트가 잠시 바빠요. Zotero 정보로 넣었어요."
PENDING_BUSY = ("서지 사이트가 잠시 바빠서 저자를 못 넣었어요. 넣기는 계속돼요. 잠시 뒤 Codex에 '저자 다시 채워 줘(다시 해 줘)'라고 하거나 "
                "`llmwiki meta --refresh {slug}` 를 실행하세요.")
PENDING_OTHER = ("저자를 자동으로 찾지 못했어요. 넣기는 계속돼요. 인터넷이 되면 Codex에 '저자 다시 채워 줘(다시 해 줘)'라고 하거나 "
                 "`llmwiki meta --refresh {slug}` 를 실행하세요(그래도 없으면 review.md의 authors를 직접 채우기).")


def _clean_authors(v: Any) -> list[str]:
    if isinstance(v, str):
        v = [v]
    return [str(a).strip() for a in (v or []) if str(a).strip()]


def _pdf_info_authors(s: str) -> list[str]:
    """PDF 문서 정보의 author 칸(있으면). 'A; B' / 'A, B and C' 꼴만 받고, 이상하면 버린다."""
    s = " ".join(str(s).split())
    if not s or len(s) > 400 or not re.search(r"[A-Za-z가-힣]", s) or re.search(r"(?i)\b(latex|microsoft|adobe|elsevier|springer|user|admin)\b", s):
        return []
    parts = re.split(r"\s*;\s*|\s*,\s*(?:and\s+)?|\s+and\s+|\s*&\s*", s)
    parts = [p.strip() for p in parts if p.strip()]
    if not parts or any(len(p) > 60 or len(p) < 3 for p in parts):
        return []
    return parts[:30]


SCANNED_MSG = ("이 PDF는 글자가 없는 스캔본이라 내용을 읽을 수 없어요. 글자가 들어 있는 PDF(출판사·arXiv 판)를 넣어 주세요. "
               "우선 제목·저자만 위키에 넣어 두었어요(리뷰는 비워 둠).")


def _filename_like(t: str, pdf: Path) -> bool:
    """'2410.03017v2', 'paper_final.pdf', 파일 이름 그대로인 제목 → 서지가 없는 것으로 본다."""
    t = " ".join(str(t).split())
    low = t.lower()
    if not t or low.endswith(".pdf") or low in (pdf.name.lower(), pdf.stem.lower()):
        return True
    if re.fullmatch(r"(arxiv[:_ ]?)?\d{4}\.\d{4,5}(v\d+)?", low):
        return True
    if re.search(r"(?i)microsoft word|\.docx?\b|untitled", t):
        return True
    return " " not in t and len(t) < 60  # 띄어쓰기 없는 한 덩어리(파일 이름 꼴)


def _xmp(doc) -> tuple[str, list[str]]:
    """PDF XMP의 dc:title·dc:creator(있으면)."""
    try:
        x = doc.get_xml_metadata() or ""
    except Exception:  # noqa: BLE001
        return "", []
    def lis(tag: str) -> list[str]:
        m = re.search(rf"<dc:{tag}>(.*?)</dc:{tag}>", x, re.S)
        if not m:
            return []
        return [" ".join(re.sub(r"<[^>]+>", " ", v).split()) for v in re.findall(r"<rdf:li[^>]*>(.*?)</rdf:li>", m.group(1), re.S)]
    import html as _html
    title = _html.unescape((lis("title") or [""])[0])
    authors = [a for a in (_html.unescape(a) for a in lis("creator")) if 2 < len(a) < 60]
    return title, authors[:30]


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

    zot_authors = bool(_clean_authors(meta.get("authors")))
    if meta.get("title") and _filename_like(str(meta["title"]), pdf):
        meta.pop("title")  # Zotero가 서지를 못 찾아 파일 이름이 제목인 경우 → 없는 것으로 본다(더 나은 값으로 바꿈)

    with pymupdf.open(str(pdf)) as doc:
        head = "\n".join(doc[i].get_text() for i in range(min(2, doc.page_count)))
        all_text_len = sum(len(doc[i].get_text().strip()) for i in range(min(doc.page_count, 30)))
        pdf_meta = doc.metadata or {}
        xmp_title, xmp_authors = _xmp(doc)
    scanned = all_text_len < 200  # 글자 층이 없는 스캔본(OCR 안 함)
    meta.setdefault("doi", find_doi(head))
    meta.setdefault("arxiv", find_arxiv(head, pdf.name))
    if not meta.get("doi"):
        meta.pop("doi", None)
    if not meta.get("arxiv"):
        meta.pop("arxiv", None)
    weak = set()
    if not meta.get("title"):
        for cand in (xmp_title, pdf_meta.get("title") or ""):
            cand = " ".join(str(cand).split())
            if len(cand) > 10 and not _filename_like(cand, pdf):
                meta["title"] = cand  # PDF 정보의 제목: arXiv·Crossref 제목이 오면 그것으로 바꾼다
                weak.add("title")
                break
    meta["_weak"] = weak

    t0 = time.monotonic()
    enrich(meta, network=network, timeout=float(cfg.get("timeout", 6)), mailto=str(cfg.get("mailto", "")))
    meta_seconds = round(time.monotonic() - t0, 2)
    busy = bool(meta.pop("_busy", False))
    meta.pop("_weak", None)
    if not _clean_authors(meta.get("authors")):
        pa = _pdf_info_authors("; ".join(xmp_authors)) or _pdf_info_authors(pdf_meta.get("author") or "")
        if pa:
            meta["authors"] = pa
            meta.setdefault("enrich_notes", []).append("authors from PDF info/XMP (확인 필요)")

    ex_probe_title = ""
    title_guessed = not meta.get("title")
    if not meta.get("title"):
        with pymupdf.open(str(pdf)) as doc:
            from .pdfextract import guess_title
            ex_probe_title = "" if scanned else guess_title(doc[0])
        meta["title"] = ex_probe_title or pdf.stem
        meta.setdefault("enrich_notes", []).append("title guessed from first page (확인 필요)")
    if meta.get("date") and not meta.get("year"):
        m = re.search(r"\d{4}", str(meta["date"]))
        if m:
            meta["year"] = m.group(0)

    if not meta.get("year") and re.match(r"^\d{4}\.\d{4,5}", str(meta.get("arxiv") or "")):
        meta["year"] = "20" + str(meta["arxiv"])[:2]  # 오프라인: arXiv 번호 YYMM.NNNNN에서 연도만 추정
        meta.setdefault("enrich_notes", []).append("year guessed from arXiv id (오프라인)")
    if not meta.get("year"):
        m = re.match(r"D:((?:19|20)\d\d)", str(pdf_meta.get("creationDate") or ""))
        if m:
            meta["year"] = m.group(1)  # PDF 만든 해(출판 연도와 다를 수 있음)
            meta.setdefault("enrich_notes", []).append("year from PDF creation date (확인 필요)")

    dup = find_duplicate(ws, meta)
    if dup and not force:
        return {"status": "duplicate", "slug": dup, "message": f"이미 위키에 있는 논문입니다: wiki/papers/{dup}/ (다시 추출하려면 --force)"}
    if dup and force:
        slug = dup
    if not slug:
        slug = unique_slug(ws, slugify(meta["title"], meta.get("year"), (meta.get("authors") or [None])[0]))
    out = ws.paper_dir(slug)
    # 다시 넣기(--force 등): 이미 있던 meta.json의 좋은 서지는 이번에 못 찾았어도 그대로 둔다(빈 값으로 덮지 않음)
    old_meta = {}
    if (out / "meta.json").exists():
        try:
            old_meta = json.loads(read_text(out / "meta.json"))
        except (ValueError, OSError):
            old_meta = {}
    for k in BIB_KEYS:
        if not (meta.get(k) if k != "authors" else _clean_authors(meta.get(k))) and old_meta.get(k):
            meta[k] = old_meta[k]
    if title_guessed and old_meta.get("title") and not _filename_like(str(old_meta["title"]), pdf):
        meta["title"] = old_meta["title"]  # 첫 페이지 추정 제목보다 이전에 찾은 서지 제목을 쓴다
    meta["authors"] = _clean_authors(meta.get("authors"))
    if meta["authors"] and meta.get("year"):
        meta.pop("meta_pending", None)
    else:
        meta["meta_pending"] = True  # 저자를 못 찾음 → lint는 WARN(ERROR 아님), `llmwiki meta --refresh <slug>`로 다시
    for sub in ("figures", "tables"):
        if (out / sub).exists():
            shutil.rmtree(out / sub)
    out.mkdir(parents=True, exist_ok=True)

    ex = extract_pdf(pdf, out)
    if scanned:
        meta["scanned"] = True
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
        write_text(out / "review.md", scanned_stub(meta, slug) if scanned else review_skeleton(meta, slug))
        created_review = True

    notice = ""
    if scanned:
        notice = SCANNED_MSG + (" 제목·저자·연도는 review.md에서 직접 고쳐도 돼요." if meta.get("meta_pending") else "")
    elif meta.get("meta_pending"):
        notice = (PENDING_BUSY if busy else PENDING_OTHER).format(slug=slug)
    elif busy and zot_authors:
        notice = ZOTERO_FALLBACK
    elif busy:
        notice = "서지 사이트가 잠시 바빠요. 찾은 정보(PDF·이전 기록)로 넣었어요. 빠진 칸은 잠시 뒤 `llmwiki meta --refresh " + slug + "` 로 채울 수 있어요."
    return {
        "status": "ok",
        "notice": notice,
        "meta_pending": bool(meta.get("meta_pending")),
        "scanned": bool(scanned),
        "metadata_seconds": meta_seconds,
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


def refresh_meta(ws: Workspace, slug: str, *, network: bool = True) -> dict[str, Any]:
    """`llmwiki meta --refresh <slug>`: 빈 서지 칸만 다시 채운다(있는 값은 그대로). review.md frontmatter도 빈 칸만 채운다."""
    from .util import dump_frontmatter, split_frontmatter
    d = ws.paper_dir(slug)
    mp = d / "meta.json"
    if not mp.exists():
        raise SystemExit(f"wiki/papers/{slug}/meta.json 이 없습니다. slug를 확인하세요(`llmwiki index` 목록).")
    meta = json.loads(read_text(mp))
    before = {k: meta.get(k) for k in BIB_KEYS}
    cfg = ws.config.get("network", {})
    enrich(meta, network=network, timeout=float(cfg.get("timeout", 6)), mailto=str(cfg.get("mailto", "")))
    busy = bool(meta.pop("_busy", False))
    for k, v in before.items():  # 혹시라도 비워진 값은 되돌린다
        if v and not meta.get(k):
            meta[k] = v
    meta["authors"] = _clean_authors(meta.get("authors"))
    if meta.get("date") and not meta.get("year"):
        m = re.search(r"\d{4}", str(meta["date"]))
        if m:
            meta["year"] = m.group(0)
    if meta["authors"] and meta.get("year"):
        meta.pop("meta_pending", None)
    write_text(mp, dump_json(meta) + "\n")
    changed = []
    rv = d / "review.md"
    if rv.exists():
        fm, body, err = split_frontmatter(read_text(rv))
        if fm is not None and not err:
            for k in ("title", "authors", "year", "date", "doi", "venue", "url"):
                v = meta.get(k)
                if k == "year" and v and str(v).isdigit():
                    v = int(v)
                if v and fm.get(k) in (None, "", []):
                    fm[k] = v
                    changed.append(k)
            if fm.get("authors") and fm.get("year") and fm.pop("meta_pending", None) is not None:
                changed.append("meta_pending 해제")
            if changed:
                write_text(rv, dump_frontmatter(fm) + body)
    filled = [k for k in BIB_KEYS if meta.get(k) and not before.get(k)]
    if meta.get("meta_pending"):
        line = ("서지 사이트가 아직 바빠요. 저자는 그대로 비워 두었어요 — 몇 분 뒤 다시 해 보세요." if busy
                else "저자를 아직 찾지 못했어요. review.md의 authors를 직접 채워도 돼요.")
    else:
        line = f"서지를 다시 채웠어요: {', '.join(filled) or '바뀐 칸 없음'}" + (" (review.md 반영)" if changed else "")
    return {"slug": slug, "filled": filled, "review_fields": changed, "meta_pending": bool(meta.get("meta_pending")), "message": line}
