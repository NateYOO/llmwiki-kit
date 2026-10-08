"""위키 검색: BM25(섹션·문단 단위), 정확한 문구 찾기, 그림·표 캡션 찾기.
결과에는 인용 꼬리표 `[근거: slug · 섹션/p.N]`를 같이 준다(wiki-query 스킬이 그대로 사용)."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .textindex import BM25, tokenize
from .util import Workspace, read_text, split_frontmatter
from .wikiops import load_papers, strip_comments

PAGE_RE = re.compile(r"<!--\s*p\.(\d+)\s*-->")


@dataclass
class Chunk:
    path: Path
    slug: str
    where: str  # 섹션 이름 또는 p.N
    text: str
    kind: str  # review|topic|draft|source|figure|table
    extra: dict


def _review_chunks(ws: Workspace) -> list[Chunk]:
    out = []
    for p in load_papers(ws):
        if not p.review.exists():
            continue
        body = strip_comments(p.body)
        parts = re.split(r"^(## .+)$", body, flags=re.M)
        head = parts[0]
        out.append(Chunk(p.review, p.slug, "제목", p.title + "\n" + head + "\n" + str(p.fm.get("essence", "")), "review", {}))
        for i in range(1, len(parts) - 1, 2):
            name = parts[i][3:].strip()
            text = parts[i + 1]
            if name == "Related Papers":  # 자동 블록은 검색에서 제외, 에이전트 해석만 남김
                text = re.sub(r"<!-- llmwiki:related:start -->.*?<!-- llmwiki:related:end -->", "", p.body, flags=re.S)
                text = text.split("## Related Papers", 1)[-1]
                text = strip_comments(text)
                if len(text.strip()) < 20:
                    continue
            out.append(Chunk(p.review, p.slug, name, text, "review", {}))
    return out


def _page_chunks(ws: Workspace) -> list[Chunk]:
    out = []
    for slug in ws.paper_slugs():
        src = ws.paper_dir(slug) / "source.md"
        if not src.exists():
            continue
        text = read_text(src)
        pieces = PAGE_RE.split(text)
        for i in range(1, len(pieces) - 1, 2):
            page = int(pieces[i])
            for para in re.split(r"\n\s*\n", pieces[i + 1]):
                if len(para.strip()) > 40:
                    out.append(Chunk(src, slug, f"p.{page}", para.strip(), "source", {"page": page}))
    return out


def _md_chunks(folder: Path, kind: str, files: list[Path] | None = None) -> list[Chunk]:
    out = []
    if not folder.exists():
        return out
    for f in (files if files is not None else sorted(folder.glob("*.md"))):
        fm, body, _ = split_frontmatter(read_text(f))
        parts = re.split(r"^(#{1,3} .+)$", strip_comments(body), flags=re.M)
        out.append(Chunk(f, f.stem, "본문", str((fm or {}).get("title", f.stem)) + "\n" + parts[0], kind, {}))
        for i in range(1, len(parts) - 1, 2):
            out.append(Chunk(f, f.stem, parts[i].lstrip("#").strip(), parts[i + 1], kind, {}))
    return out


def _figure_chunks(ws: Workspace) -> list[Chunk]:
    out = []
    for p in load_papers(ws):
        for f in p.meta.get("figures") or []:
            out.append(Chunk(p.dir / f["file"], p.slug, f"Figure {f['n']}, p.{f['page']}", f["caption"], "figure", {"page": f["page"]}))
        for t in p.meta.get("tables") or []:
            out.append(Chunk(p.dir / t["png"], p.slug, f"Table {t['n']}, p.{t['page']}", t["caption"], "table", {"page": t["page"], "md": t.get("md", "")}))
        # 리뷰 안에서 그림 아래에 쓴 해설(dual-coding)도 찾을 수 있게
    return out


def _snippet(text: str, q_tokens: list[str], width: int = 220) -> str:
    flat = " ".join(text.split())
    low = flat.lower()
    pos = -1
    for t in q_tokens:
        pos = low.find(t)
        if pos >= 0:
            break
    start = max(0, pos - width // 3) if pos >= 0 else 0
    s = flat[start:start + width]
    return ("…" if start > 0 else "") + s + ("…" if start + width < len(flat) else "")


def cite_tag(c: Chunk) -> str:
    if c.kind in ("review", "source", "figure", "table"):
        return f"[근거: {c.slug} · {c.where}]"
    return f"[근거: {c.kind}/{c.slug} · {c.where}]"


def search(ws: Workspace, query: str, scope: str = "wiki", top: int = 8) -> list[dict[str, Any]]:
    chunks: list[Chunk] = []
    if scope in ("wiki", "all"):
        chunks += _review_chunks(ws) + _md_chunks(ws.topics, "topic")
    if scope in ("drafts", "all"):
        chunks += _md_chunks(ws.drafts, "draft")
        from .util import project_mds
        chunks += _md_chunks(ws.projects, "draft", files=project_mds(ws))
    if scope in ("source", "all"):
        chunks += _page_chunks(ws)
    if scope in ("figures", "all"):
        chunks += _figure_chunks(ws)
    if not chunks:
        return []
    bm = BM25([tokenize(c.text + " " + c.where) for c in chunks])
    qt = tokenize(query)
    scores = bm.scores(qt)
    order = sorted(range(len(chunks)), key=lambda i: -scores[i])
    res = []
    for i in order[:top]:
        if scores[i] <= 0:
            break
        c = chunks[i]
        item = {"score": round(scores[i], 3), "kind": c.kind, "slug": c.slug, "where": c.where, "path": ws.rel(c.path),
                "cite": cite_tag(c), "snippet": _snippet(c.text, [t for t in qt if t.isascii()] + qt)}
        if c.kind in ("figure", "table"):
            item["image"] = ws.rel(c.path)
            if c.extra.get("md"):
                item["markdown"] = ws.rel(ws.paper_dir(c.slug) / c.extra["md"])
        res.append(item)
    return res


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).replace("\u00ad", "")  # 합자(ﬁ)·전각·NFD 한글 정리
    s = re.sub(r"-\s*\n\s*", "", s)
    return re.sub(r"\s+", " ", s).lower()


def find_phrase(ws: Workspace, phrase: str, scope: str = "all", context: int = 160) -> list[dict[str, Any]]:
    """대소문자·줄바꿈·하이픈 차이를 무시하고 정확한 문구 위치(파일, 페이지)를 찾는다."""
    target = _norm(phrase).strip()
    if not target:
        return []
    files: list[tuple[str, Path]] = []
    for slug in ws.paper_slugs():
        d = ws.paper_dir(slug)
        if scope in ("all", "source") and (d / "source.md").exists():
            files.append((slug, d / "source.md"))
        if scope in ("all", "wiki") and (d / "review.md").exists():
            files.append((slug, d / "review.md"))
    if scope in ("all", "wiki"):
        files += [(f.stem, f) for f in sorted(ws.topics.glob("*.md"))] if ws.topics.exists() else []
    if scope in ("all", "drafts"):
        files += [(f.stem, f) for f in sorted(ws.drafts.glob("*.md"))] if ws.drafts.exists() else []
        from .util import project_mds
        files += [(f.stem, f) for f in project_mds(ws)]
    hits = []
    for slug, f in files:
        raw = read_text(f)
        pages = PAGE_RE.split(raw)
        segs = [(None, pages[0])] + [(int(pages[i]), pages[i + 1]) for i in range(1, len(pages) - 1, 2)]
        for page, seg in segs:
            norm = _norm(seg)
            start = 0
            while True:
                k = norm.find(target, start)
                if k < 0:
                    break
                ctx = norm[max(0, k - context): k + len(target) + context]
                where = f"p.{page}" if page else ("review" if f.name == "review.md" else f.stem)
                hits.append({"slug": slug, "path": ws.rel(f), "where": where, "cite": f"[근거: {slug} · {where}]", "context": "…" + ctx + "…"})
                start = k + len(target)
    return hits
