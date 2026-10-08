"""PDF 추출: 본문 텍스트(페이지 표시), 그림·그래프(캡션 포함 영역 PNG), 표(PNG + markdown).

방식은 sources.md §1.5·§4.3에 기록된 아이디어(캡션 정규식 → 그래픽 영역 합치기 → 영역 렌더)를
참고해 이 저장소에서 새로 작성했다. Paper Curation 코드를 복사하지 않았다.
의존성: PyMuPDF(pymupdf)만 사용.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import os

os.environ.setdefault("PYMUPDF_SUGGEST_LAYOUT_ANALYZER", "0")  # JSON 출력에 섞이는 안내문 끄기
import pymupdf  # noqa: E402

try:
    pymupdf.no_recommend_layout()
except AttributeError:
    pass

CAPTION_RE = re.compile(
    r"^\s*(?P<kind>f\s?i\s?g\s?u\s?r\s?e|fig\.?|t\s?a\s?b\s?l\s?e)\s*(?P<num>\d{1,3}|[ivxlc]{1,6})\b[ \t]*(?P<rest>.*)$",
    re.I | re.S,
)
ROMAN = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100}


def _roman_to_int(s: str) -> int:
    total, prev = 0, 0
    for ch in reversed(s.lower()):
        v = ROMAN.get(ch, 0)
        total = total - v if v < prev else total + v
        prev = max(prev, v)
    return total


@dataclass
class Caption:
    kind: str  # "figure" | "table"
    num: int
    page: int  # 0-based
    rect: pymupdf.Rect
    text: str


@dataclass
class Extracted:
    page_count: int
    pages: list[str]
    first_page_title: str = ""
    abstract: str = ""
    figures: list[dict[str, Any]] = field(default_factory=list)
    tables: list[dict[str, Any]] = field(default_factory=list)
    captions_found: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


# ------------------------------------------------------------------ text
def _clean_page_text(t: str) -> str:
    t = t.replace("\u00ad", "")
    t = re.sub(r"(\w)-\n(\w)", r"\1\2", t)  # 줄끝 하이픈 이음
    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def guess_title(page: pymupdf.Page) -> str:
    """첫 쪽 위쪽 절반에서 가장 큰 글씨 줄들을 제목 후보로 본다."""
    try:
        d = page.get_text("dict")
    except Exception:
        return ""
    spans = []
    h = page.rect.height
    for b in d.get("blocks", []):
        for line in b.get("lines", []):
            for s in line.get("spans", []):
                txt = s.get("text", "").strip()
                if len(txt) >= 2 and s["bbox"][1] < h * 0.5 and not txt.lower().startswith("arxiv"):
                    spans.append((round(s.get("size", 0), 1), s["bbox"][1], txt))
    if not spans:
        return ""
    top = max(s[0] for s in spans)
    lines = [s for s in spans if s[0] >= top - 0.6]
    lines.sort(key=lambda s: s[1])
    title = " ".join(s[2] for s in lines)
    return " ".join(title.split())[:300]


def guess_abstract(pages: list[str]) -> str:
    head = "\n".join(pages[:2])
    m = re.search(r"\babstract\b[\s.:—-]*(.+?)(?:\n\s*(?:1\.?|I\.?)?\s*introduction\b|\n\s*keywords?\b|\n\s*ccs concepts)", head, re.I | re.S)
    if not m:
        return ""
    return " ".join(m.group(1).split())[:3000]


# ------------------------------------------------------------------ captions
def _block_text(block: dict) -> str:
    lines = []
    for line in block.get("lines", []):
        lines.append("".join(s.get("text", "") for s in line.get("spans", [])))
    return "\n".join(lines).strip()


def find_captions(doc: pymupdf.Document) -> list[Caption]:
    """'Figure 1:' / 'Fig. 2.' / 'Table 3:' / 'TABLE I' 처럼 블록 첫머리에 오는 캡션만 인정한다.
    본문 속 'Table 6 reports ...' 같은 언급은 번호 뒤 구두점이 없으므로 제외한다."""
    seen: dict[tuple[str, int], Caption] = {}
    for page in doc:
        d = page.get_text("dict")
        tblocks = [b for b in d.get("blocks", []) if b.get("type") == 0]
        for b in tblocks:
            text = _block_text(b)
            m = CAPTION_RE.match(text)
            if not m:
                continue
            kind = "table" if m.group("kind").lower().startswith("t") else "figure"
            raw = m.group("num")
            num = int(raw) if raw.isdigit() else _roman_to_int(raw)
            rest = m.group("rest")
            first_line_rest = rest.split("\n", 1)[0].strip()
            punct = bool(re.match(r"^[:.|–—-]", rest.strip()))
            alone = first_line_rest == ""  # 'TABLE 1' 이 한 줄에 단독
            if not (punct or alone) or num <= 0:
                continue
            key = (kind, num)
            if key in seen:
                continue
            rect = pymupdf.Rect(b["bbox"])
            # 캡션이 여러 블록으로 쪼개진 경우(마지막 줄이 따로 떨어짐) 바로 아래 붙은 블록을 합친다
            changed = True
            while changed:
                changed = False
                for nb in tblocks:
                    r2 = pymupdf.Rect(nb["bbox"])
                    if nb is b or r2.y0 < rect.y1 - 1:
                        continue
                    if r2.y0 - rect.y1 <= 3.5 and _hoverlap(r2, rect.x0, rect.x1) > 0.6 and not CAPTION_RE.match(_block_text(nb)):
                        rect |= r2
                        text += " " + _block_text(nb)
                        changed = True
            seen[key] = Caption(kind, num, page.number, rect, " ".join(text.split())[:800])
    return sorted(seen.values(), key=lambda c: (c.kind, c.num))


# ------------------------------------------------------------------ graphics
def graphic_rects(page: pymupdf.Page) -> list[pymupdf.Rect]:
    """래스터 이미지 + 벡터 드로잉 영역(작은 조각·페이지 테두리 제외)."""
    pr = page.rect
    rects: list[pymupdf.Rect] = []
    try:
        for info in page.get_image_info():
            r = pymupdf.Rect(info["bbox"]) & pr
            if r.width > 20 and r.height > 20:
                rects.append(r)
    except Exception:
        pass
    try:
        for r in page.cluster_drawings():
            r = pymupdf.Rect(r) & pr
            if r.width * r.height > 400 and not (r.width > pr.width * 0.92 and r.height > pr.height * 0.92):
                rects.append(r)
            elif r.height < 3 and r.width > pr.width * 0.3 and (r.y1 < pr.height * 0.08 or r.y0 > pr.height * 0.92):
                continue  # 머리말·꼬리말 가로줄
            elif r.width > 30 and r.height < 3:
                rects.append(r)  # 표의 가로줄(booktabs)
    except Exception:
        pass
    top, bottom = pr.y0 + pr.height * 0.07, pr.y1 - pr.height * 0.07
    return [r for r in rects if not (r.y1 <= top or r.y0 >= bottom)]


def _column_range(page: pymupdf.Page, cap: pymupdf.Rect) -> tuple[float, float]:
    pr = page.rect
    margin = pr.width * 0.06
    if cap.width > pr.width * 0.5:
        return pr.x0 + margin * 0.5, pr.x1 - margin * 0.5
    mid = (pr.x0 + pr.x1) / 2
    if cap.x1 <= mid + 10:
        return pr.x0 + margin * 0.5, mid
    if cap.x0 >= mid - 10:
        return mid, pr.x1 - margin * 0.5
    return pr.x0 + margin * 0.5, pr.x1 - margin * 0.5


def _hoverlap(r: pymupdf.Rect, x0: float, x1: float) -> float:
    inter = max(0.0, min(r.x1, x1) - max(r.x0, x0))
    return inter / max(r.width, 1.0)


def _chain(cands: list[pymupdf.Rect], cap: pymupdf.Rect, upward: bool, max_gap_first: float = 70, max_gap: float = 30) -> pymupdf.Rect | None:
    """캡션에서 가까운 그래픽부터 이어 붙여 하나의 영역을 만든다."""
    if upward:
        cands = sorted(cands, key=lambda r: -r.y1)
    else:
        cands = sorted(cands, key=lambda r: r.y0)
    region: pymupdf.Rect | None = None
    for r in cands:
        if region is None:
            gap = cap.y0 - r.y1 if upward else r.y0 - cap.y1
            if -10 <= gap <= max_gap_first or (r.y0 < cap.y0 < r.y1):
                region = pymupdf.Rect(r)
        else:
            gap = region.y0 - r.y1 if upward else r.y0 - region.y1
            if gap <= max_gap:
                region |= r
    return region


def _is_tabular(block: dict) -> bool:
    """짧은 줄이 많거나 숫자 비율이 높은 블록 = 선 없는 표의 본문일 가능성."""
    lines = ["".join(sp.get("text", "") for sp in ln.get("spans", [])).strip() for ln in block.get("lines", [])]
    lines = [ln for ln in lines if ln]
    if len(lines) < 3:
        return False
    joined = "".join(lines)
    avg = len(joined) / len(lines)
    digits = sum(ch.isdigit() for ch in joined) / max(1, len(joined))
    return avg <= 28 or digits >= 0.25


def _words_table_md(page: pymupdf.Page, rect: pymupdf.Rect) -> str:
    """선 없는 표용: 단어 좌표로 행(y)과 셀(x 간격)을 나눠 대략적인 markdown 표를 만든다(검색·인용용)."""
    try:
        words = page.get_text("words", clip=rect)
    except Exception:
        return ""
    if len(words) < 6:
        return ""
    words.sort(key=lambda w: (round(w[3]), w[0]))
    rows: list[list[tuple]] = []
    for w in words:
        if rows and abs(rows[-1][0][3] - w[3]) <= 3:
            rows[-1].append(w)
        else:
            rows.append([w])
    table: list[list[str]] = []
    for row in rows:
        row.sort(key=lambda w: w[0])
        cells, cur, last_x1 = [], [], None
        for w in row:
            if last_x1 is not None and w[0] - last_x1 > 7:
                cells.append(" ".join(cur))
                cur = []
            cur.append(w[4])
            last_x1 = w[2]
        cells.append(" ".join(cur))
        table.append(cells)
    if len(table) < 2 or max(len(r) for r in table) < 2:
        return ""
    ncol = max(len(r) for r in table)
    esc = lambda c: c.replace("|", "\\|")
    lines = ["| " + " | ".join(esc(c) for c in table[0] + [""] * (ncol - len(table[0]))) + " |",
             "|" + "---|" * ncol]
    for r in table[1:]:
        lines.append("| " + " | ".join(esc(c) for c in r + [""] * (ncol - len(r))) + " |")
    return "\n".join(lines)


def _render(page: pymupdf.Page, rect: pymupdf.Rect, out: Path, scale: float = 2.0) -> dict[str, Any]:
    rect = (rect + (-6, -6, 6, 6)) & page.rect
    pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), clip=rect, alpha=False)
    out.parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(out))
    size = out.stat().st_size
    low = size < 4000 or pix.width < 100 or pix.height < 60
    return {"bbox": [round(v, 1) for v in rect], "px": [pix.width, pix.height], "low_confidence": low}


def _figure_region(page: pymupdf.Page, cap: Caption, caps_on_page: list[Caption]) -> tuple[pymupdf.Rect, str]:
    x0, x1 = _column_range(page, cap.rect)
    upper = page.rect.y0 + 20
    lower = page.rect.y1 - 20
    for other in caps_on_page:
        if other is cap or _hoverlap(other.rect, x0, x1) < 0.3:
            continue
        if other.rect.y1 <= cap.rect.y0:
            upper = max(upper, other.rect.y1)
        elif other.rect.y0 >= cap.rect.y1:
            lower = min(lower, other.rect.y0)
    gr = [r for r in graphic_rects(page) if _hoverlap(r, x0, x1) > 0.3 or (r.x0 <= x0 and r.x1 >= x1)]
    above = [r for r in gr if r.y1 <= cap.rect.y0 + 8 and r.y0 >= upper - 4]
    region = _chain(above, cap.rect, upward=True)
    method = "graphics-above"
    if region is None:
        below = [r for r in gr if r.y0 >= cap.rect.y1 - 8 and r.y1 <= lower + 4]
        region = _chain(below, cap.rect, upward=False)
        method = "graphics-below"
    if region is None:
        h = page.rect.height * 0.42
        region = pymupdf.Rect(x0, max(upper, cap.rect.y0 - h), x1, cap.rect.y0)
        method = "fallback-crop-above"
    return region | cap.rect, method


def _table_region(page: pymupdf.Page, cap: Caption, tables: list[Any], caps_on_page: list[Caption]) -> tuple[pymupdf.Rect, str, str]:
    x0, x1 = _column_range(page, cap.rect)
    best, best_d = None, 1e9
    for t in tables:
        tr = pymupdf.Rect(t.bbox)
        if _hoverlap(tr, x0, x1) < 0.3 and _hoverlap(cap.rect, tr.x0, tr.x1) < 0.3:
            continue
        if tr.y0 >= cap.rect.y1 - 6:
            d = tr.y0 - cap.rect.y1
        elif tr.y1 <= cap.rect.y0 + 6:
            d = (cap.rect.y0 - tr.y1) + 15  # 캡션 아래 표를 우선
        else:
            d = 0
        if d < best_d and d < 260:
            best, best_d = t, d
    if best is not None:
        md = ""
        try:
            md = best.to_markdown(clean=True)
        except TypeError:
            md = best.to_markdown()
        except Exception:
            md = ""
        return pymupdf.Rect(best.bbox) | cap.rect, "find_tables", md
    # 표 객체를 못 찾으면: ① 가로줄(booktabs) 드로잉 ② 표처럼 생긴 텍스트 블록을 캡션 아래→위 순서로 찾는다
    upper, lower = page.rect.y0 + 20, page.rect.y1 - 20
    for other in caps_on_page:
        if other is cap or _hoverlap(other.rect, x0, x1) < 0.3:
            continue
        if other.rect.y0 >= cap.rect.y1:
            lower = min(lower, other.rect.y0)
        elif other.rect.y1 <= cap.rect.y0:
            upper = max(upper, other.rect.y1)
    gr = [r for r in graphic_rects(page) if _hoverlap(r, x0, x1) > 0.3]
    region, method = None, ""
    below = [r for r in gr if r.y0 >= cap.rect.y1 - 6 and r.y1 <= lower + 4]
    region = _chain(below, cap.rect, upward=False, max_gap_first=40, max_gap=120)
    method = "rules-below"
    if region is None:
        tb = [pymupdf.Rect(b["bbox"]) for b in page.get_text("dict").get("blocks", []) if b.get("type") == 0 and _is_tabular(b)]
        tb = [r for r in tb if _hoverlap(r, x0, x1) > 0.3 and not r.intersects(cap.rect)]
        rb = _chain([r for r in tb if r.y0 >= cap.rect.y1 - 4 and r.y1 <= lower + 4], cap.rect, upward=False, max_gap_first=45, max_gap=25)
        ra = _chain([r for r in tb if r.y1 <= cap.rect.y0 + 4 and r.y0 >= upper - 4], cap.rect, upward=True, max_gap_first=45, max_gap=25)
        gb = (rb.y0 - cap.rect.y1) if rb is not None else 1e9
        ga = (cap.rect.y0 - ra.y1) if ra is not None else 1e9
        if rb is not None and gb <= ga:
            region, method = rb, "text-table-below"
        elif ra is not None:
            region, method = ra, "text-table-above"
    if region is None:
        above = [r for r in gr if r.y1 <= cap.rect.y0 + 6 and r.y0 >= upper - 4]
        region = _chain(above, cap.rect, upward=True, max_gap_first=40, max_gap=120)
        method = "rules-above"
    if region is None:
        h = page.rect.height * 0.35
        if cap.rect.y0 > page.rect.height * 0.55:  # 캡션이 페이지 아래쪽이면 표는 위에 있을 가능성이 크다
            region = pymupdf.Rect(x0, max(upper, cap.rect.y0 - h), x1, cap.rect.y0)
            method = "fallback-crop-above"
        else:
            region = pymupdf.Rect(x0, cap.rect.y1, x1, min(lower, cap.rect.y1 + h))
            method = "fallback-crop-below"
    body = pymupdf.Rect(region)
    region = region | cap.rect
    md = ""
    try:
        found = page.find_tables(clip=body + (-2, -2, 2, 2), strategy="lines")
        if found.tables and len(found.tables[0].extract()) >= 2 and found.tables[0].col_count >= 2:
            md = found.tables[0].to_markdown()
            method += "+md:lines"
    except Exception:
        pass
    if not md:
        md = _words_table_md(page, body)
        if md:
            method += "+md:words"
    return region, method, md


# ------------------------------------------------------------------ main entry
def extract_pdf(pdf_path: Path, out_dir: Path, *, max_figures: int = 20, max_tables: int = 20) -> Extracted:
    doc = pymupdf.open(str(pdf_path))
    pages = [_clean_page_text(p.get_text("text")) for p in doc]
    ex = Extracted(page_count=doc.page_count, pages=pages)
    ex.first_page_title = guess_title(doc[0]) if doc.page_count else ""
    ex.abstract = guess_abstract(pages)
    if sum(len(p) for p in pages) < 200 * max(1, doc.page_count) * 0.2:
        ex.warnings.append("텍스트가 거의 없습니다. 스캔 PDF일 수 있습니다(OCR 필요).")

    caps = find_captions(doc)
    ex.captions_found = {
        "figure": sum(1 for c in caps if c.kind == "figure"),
        "table": sum(1 for c in caps if c.kind == "table"),
    }
    by_page: dict[int, list[Caption]] = {}
    for c in caps:
        by_page.setdefault(c.page, []).append(c)
    table_cache: dict[int, list[Any]] = {}

    fig_dir, tab_dir = out_dir / "figures", out_dir / "tables"
    for c in caps:
        page = doc[c.page]
        try:
            if c.kind == "figure":
                if c.num > max_figures:
                    continue
                rect, method = _figure_region(page, c, by_page[c.page])
                fname = f"fig{c.num}.png"
                info = _render(page, rect, fig_dir / fname)
                ex.figures.append({"n": c.num, "page": c.page + 1, "caption": c.text, "file": f"figures/{fname}", "method": method, **info})
            else:
                if c.num > max_tables:
                    continue
                if c.page not in table_cache:
                    try:
                        table_cache[c.page] = list(page.find_tables().tables)
                    except Exception:
                        table_cache[c.page] = []
                rect, method, md = _table_region(page, c, table_cache[c.page], by_page[c.page])
                fname = f"table{c.num}"
                info = _render(page, rect, tab_dir / f"{fname}.png")
                entry = {"n": c.num, "page": c.page + 1, "caption": c.text, "png": f"tables/{fname}.png", "method": method, **info}
                if md.strip():
                    (tab_dir / f"{fname}.md").write_text(
                        f"<!-- 자동 추출 표: 열이 합쳐지거나 어긋날 수 있음. 정확한 값은 {fname}.png 확인 -->\n\n**{c.text}**\n\n{md.strip()}\n",
                        encoding="utf-8",
                    )
                    entry["md"] = f"tables/{fname}.md"
                else:
                    entry["md_note"] = "markdown 자동 추출 실패(이미지 표이거나 선 없는 표). PNG를 보고 필요한 값만 리뷰에 옮길 것"
                ex.tables.append(entry)
        except Exception as e:  # noqa: BLE001 - 그림 하나 실패로 전체를 멈추지 않는다
            ex.warnings.append(f"{c.kind} {c.num} (p.{c.page + 1}) 렌더 실패: {e}")
    doc.close()
    return ex
