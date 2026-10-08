"""위키 파일 다루기: 논문 목록 읽기, 리뷰 뼈대, index.md 재생성, log.md 추가, 링크 파싱."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import SCHEMA_VERSION
from .util import (INDEX_END, INDEX_START, RELATED_END, RELATED_HEADING, RELATED_START, REVIEW_HEADINGS,
                   Workspace, dump_frontmatter, read_text, split_frontmatter, today, write_text)

MD_LINK = re.compile(r"(!?)\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
WIKI_LINK = re.compile(r"(!?)\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
TODO_RE = re.compile(r"<!--\s*TODO", re.I)
SKIP_NAMES = {"source.md", "figures.md", "tables.md"}


@dataclass
class Paper:
    slug: str
    dir: Path
    review: Path
    fm: dict = field(default_factory=dict)
    body: str = ""
    fm_error: str | None = None
    meta: dict = field(default_factory=dict)

    @property
    def title(self) -> str:
        return str(self.fm.get("title") or self.meta.get("title") or self.slug)

    def section(self, heading: str) -> str:
        return get_section(self.body, heading)


def load_paper(ws: Workspace, slug: str) -> Paper:
    d = ws.paper_dir(slug)
    p = Paper(slug=slug, dir=d, review=d / "review.md")
    if p.review.exists():
        fm, body, err = split_frontmatter(read_text(p.review))
        p.fm, p.body, p.fm_error = fm or {}, body, err
        if fm is None and err is None:
            p.fm_error = "frontmatter 없음"
    mj = d / "meta.json"
    if mj.exists():
        try:
            p.meta = json.loads(read_text(mj))
        except json.JSONDecodeError:
            p.meta = {}
    return p


def load_papers(ws: Workspace) -> list[Paper]:
    return [load_paper(ws, s) for s in ws.paper_slugs()]


def get_section(body: str, heading: str) -> str:
    """'## X' 헤딩 아래 본문(다음 '## ' 전까지)."""
    pat = re.compile(r"^" + re.escape(heading) + r"\s*$", re.M)
    m = pat.search(body)
    if not m:
        return ""
    rest = body[m.end():]
    n = re.search(r"^## ", rest, re.M)
    return rest[: n.start()] if n else rest


def strip_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def iter_links(text: str) -> list[tuple[bool, str, str]]:
    """(이미지 여부, 링크 대상, 종류 'md'|'wiki') — 코드블록 안 링크는 무시."""
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"`[^`\n]*`", "", text)
    text = strip_comments(text)
    out = []
    for m in MD_LINK.finditer(text):
        out.append((m.group(1) == "!", m.group(3), "md"))
    for m in WIKI_LINK.finditer(text):
        out.append((m.group(1) == "!", m.group(2).strip(), "wiki"))
    return out


def resolve_link(ws: Workspace, src: Path, target: str, kind: str) -> Path | None:
    """외부 URL·앵커는 None. 상대 경로는 파일 기준, 위키링크는 작업 폴더/위키 기준으로 해석."""
    if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith("#"):
        return None
    from urllib.parse import unquote
    t = unquote(target.split("#", 1)[0])
    if not t:
        return None
    if kind == "md":
        return (src.parent / t).resolve()
    cands = [ws.wiki / t, ws.root / t]
    for c in cands:
        for cc in (c, c.with_name(c.name + ".md")):
            if cc.exists():
                return cc.resolve()
    return (ws.wiki / (t if t.endswith(".md") else t + ".md")).resolve()


def relpath(from_file: Path, to_file: Path) -> str:
    import os
    return Path(os.path.relpath(to_file.resolve(), from_file.resolve().parent)).as_posix()


# ------------------------------------------------------------------ review skeleton
def ref_line(meta: dict) -> str:
    doi, url = meta.get("doi", ""), meta.get("url", "")
    if doi:
        return f"**DOI**: [{doi}](https://doi.org/{doi})"
    if url:
        return f"**URL**: <{url}>"
    return "**DOI**: N/A"


def new_frontmatter(meta: dict, slug: str) -> dict[str, Any]:
    authors = meta.get("authors") or []
    return {
        "title": meta.get("title", ""),
        "authors": authors,
        "year": int(meta["year"]) if str(meta.get("year", "")).isdigit() else None,
        "date": meta.get("date", ""),
        "doi": meta.get("doi", ""),
        "arxiv": meta.get("arxiv", ""),
        "venue": meta.get("venue", ""),
        "url": meta.get("url", ""),
        "citekey": meta.get("citekey", ""),
        "zotero_key": meta.get("zotero_key", ""),
        "pdf": meta.get("pdf", ""),
        "slug": slug,
        "category": "",
        "tags": ["paper"],
        "essence": "",
        "score_novelty": None,
        "score_technical": None,
        "score_significance": None,
        "score_clarity": None,
        "score": None,
        "status": "draft",
        "schema_version": SCHEMA_VERSION,
        "review_date": "",
    }


def review_skeleton(meta: dict, slug: str) -> str:
    fm = new_frontmatter(meta, slug)
    authors = ", ".join(meta.get("authors") or []) or "N/A"
    figs = meta.get("figures") or []
    tabs = meta.get("tables") or []
    fig_hint = "; ".join(f"Fig {f['n']}(p.{f['page']}): {f['caption'][:60]}" for f in figs[:8]) or "추출된 그림 없음"
    tab_hint = "; ".join(f"Table {t['n']}(p.{t['page']})" for t in tabs[:10]) or "추출된 표 없음"
    return dump_frontmatter(fm) + f"""
# {meta.get('title', slug)}

> **저자**: {authors} | **날짜**: {meta.get('date') or 'N/A'} | {ref_line(meta)}
> **자료**: [추출 원문](source.md) · [그림 목록](figures/figures.md) · [표 목록](tables/tables.md) — 원문 PDF는 Zotero/로컬 보관(재배포 금지)

---

## Essence

<!-- TODO(essence): 대표 그림 1장(선택) + 핵심 요약 1–2문장. 그림 후보: {fig_hint} -->

## Motivation

- **Known**: <!-- TODO: 1–2문장 -->
- **Gap**: <!-- TODO: 1–2문장 -->
- **Why**: <!-- TODO: 1–2문장 -->
- **Approach**: <!-- TODO: 1–2문장 -->

## Achievement

<!-- TODO(achievement): 그림 1장(선택) + 번호 목록 '1. **굵은 제목**: 설명 (근거: p.N, Table N)'. 표 후보: {tab_hint} -->

## How

<!-- TODO(how): 그림 1장(선택) + 방법 bullet 목록 (근거 페이지 표기) -->

## Originality

<!-- TODO: bullet 목록 -->

## Limitation & Further Study

<!-- TODO: 한계 + 후속 연구 bullet 목록 (저자가 밝힌 한계와 리뷰어 의견을 구분) -->

## Evaluation

- Novelty: ?/5
- Technical Soundness: ?/5
- Significance: ?/5
- Clarity: ?/5
- Overall: ?/5

**총평**: <!-- TODO: 1–2문장 -->

{RELATED_HEADING}

{RELATED_START}
_아직 계산 전입니다. `llmwiki related --write` 를 실행하세요._
{RELATED_END}
"""


def figures_listing(meta: dict) -> str:
    lines = [f"# 그림 목록 — {meta.get('title', '')}", "", "> 자동 생성(llmwiki extract). 원문 PDF 캡처 · 로컬 연구용. 캡션은 원문 그대로.", ""]
    for f in meta.get("figures") or []:
        flag = " ⚠️ 자동 크롭 신뢰도 낮음 — PNG 확인" if f.get("low_confidence") or f.get("method", "").startswith("fallback") else ""
        lines += [f"## Figure {f['n']} (p.{f['page']}){flag}", "", f"![Figure {f['n']}]({Path(f['file']).name})", "", f"*{f['caption']}*", ""]
    if not meta.get("figures"):
        lines.append("_추출된 그림이 없습니다._")
    return "\n".join(lines) + "\n"


def tables_listing(meta: dict, tables_dir: Path) -> str:
    lines = [f"# 표 목록 — {meta.get('title', '')}", "", "> 자동 생성. PNG가 정본이고 markdown은 검색·인용 보조용(열이 어긋날 수 있음).", ""]
    for t in meta.get("tables") or []:
        flag = " ⚠️ 자동 크롭 신뢰도 낮음 — PNG 확인" if t.get("method", "").startswith("fallback") else ""
        lines += [f"## Table {t['n']} (p.{t['page']}){flag}", "", f"![Table {t['n']}]({Path(t['png']).name})", ""]
        if t.get("md"):
            lines += [f"markdown: [table{t['n']}.md]({Path(t['md']).name})", ""]
        else:
            lines += [f"_{t.get('md_note', 'markdown 없음')}_", ""]
    if not meta.get("tables"):
        lines.append("_추출된 표가 없습니다._")
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------ index & log
def _short_authors(authors: list) -> str:
    if not authors:
        return ""
    first = str(authors[0]).split()[-1] if str(authors[0]).split() else str(authors[0])
    return first + (" 외" if len(authors) > 1 else "")


def build_index_block(ws: Workspace) -> str:
    papers = load_papers(ws)
    lines = []
    topics = sorted(ws.topics.glob("*.md")) if ws.topics.exists() else []
    lines.append("## 주제 (topics)\n")
    if topics:
        for t in topics:
            fm, body, _ = split_frontmatter(read_text(t))
            title = (fm or {}).get("title") or t.stem
            summary = (fm or {}).get("summary", "")
            lines.append(f"- [{title}](topics/{t.name})" + (f" — {summary}" if summary else ""))
    else:
        lines.append("_아직 주제 페이지가 없습니다. 논문이 3편 이상 모이면 wiki-lint/wiki-query로 묶어 보세요._")
    lines.append("")
    groups: dict[str, list[Paper]] = {}
    for p in papers:
        groups.setdefault(str(p.fm.get("category") or "미분류"), []).append(p)
    lines.append(f"## 논문 ({len(papers)}편)\n")
    if not papers:
        lines.append("_아직 논문이 없습니다. `$wiki-ingest 논문제목` 으로 시작하세요._\n")
    for cat in sorted(groups, key=lambda c: (c == "미분류", c)):
        lines.append(f"### {cat}\n")
        for p in sorted(groups[cat], key=lambda x: (str(x.fm.get("year") or ""), x.slug)):
            year = p.fm.get("year") or (p.meta.get("year") if p.meta else "") or "n.d."
            ess = str(p.fm.get("essence") or "").strip().replace("\n", " ")
            score = p.fm.get("score")
            status = p.fm.get("status", "")
            extra = []
            if score:
                extra.append(f"★{score}")
            if status and status != "reviewed":
                extra.append(status)
            tail = f" — {ess}" if ess else ""
            lines.append(f"- [{p.title}](papers/{p.slug}/review.md) ({year}, {_short_authors(p.fm.get('authors') or [])})" + (f" `{' · '.join(extra)}`" if extra else "") + tail)
        lines.append("")
    drafts = sorted(ws.drafts.glob("*.md")) if ws.drafts.exists() else []
    lines.append("## 초안 (drafts)\n")
    lines += [f"- [{d.stem}](../drafts/{d.name})" for d in drafts] or ["_없음_"]
    return "\n".join(lines).rstrip() + "\n"


INDEX_HEADER = """# 위키 목차 (index)

> 질문에 답하거나 새 논문을 넣기 전에 에이전트가 **가장 먼저 읽는 파일**입니다.
> 아래 자동 블록은 `llmwiki index`가 frontmatter(category, essence, score)로 다시 만듭니다. 블록 밖에는 자유롭게 메모해도 됩니다.

"""


def write_index(ws: Workspace) -> Path:
    block = f"{INDEX_START}\n{build_index_block(ws)}{INDEX_END}"
    if ws.index.exists():
        text = read_text(ws.index)
        if INDEX_START in text and INDEX_END in text:
            text = re.sub(re.escape(INDEX_START) + r".*?" + re.escape(INDEX_END), lambda m: block, text, flags=re.S)
        else:
            text = text.rstrip() + "\n\n" + block + "\n"
    else:
        text = INDEX_HEADER + block + "\n"
    write_text(ws.index, text)
    return ws.index


LOG_HEADER = """# 작업 기록 (log)

> append-only. 형식: `## [YYYY-MM-DD] ingest|query|lint|draft|synthesize|related | 제목` (Karpathy LLM Wiki 관례)
> 최근 5개 보기: `grep "^## \\[" wiki/log.md | tail -5` (Windows: `Select-String "^## \\[" wiki\\log.md | Select-Object -Last 5`)
"""
LOG_OPS = {"ingest", "query", "lint", "draft", "synthesize", "related", "setup", "fix"}


def append_log(ws: Workspace, op: str, title: str, notes: list[str] | None = None, date: str | None = None) -> str:
    op = op.strip().lower()
    if op not in LOG_OPS:
        raise SystemExit(f"log 종류는 {sorted(LOG_OPS)} 중 하나여야 합니다: {op}")
    title = " ".join(title.split()).replace("|", "/")
    entry = f"\n## [{date or today()}] {op} | {title}\n"
    for n in notes or []:
        entry += f"- {n}\n"
    if not ws.log.exists():
        write_text(ws.log, LOG_HEADER)
    with open(ws.log, "a", encoding="utf-8", newline="\n") as f:
        f.write(entry)
    return entry.strip()


def replace_related_block(review_text: str, block_body: str) -> str:
    block = f"{RELATED_START}\n{block_body.rstrip()}\n{RELATED_END}"
    if RELATED_START in review_text and RELATED_END in review_text:
        return re.sub(re.escape(RELATED_START) + r".*?" + re.escape(RELATED_END), lambda m: block, review_text, flags=re.S)
    if re.search(r"^" + re.escape(RELATED_HEADING) + r"\s*$", review_text, re.M):
        return re.sub(r"^(" + re.escape(RELATED_HEADING) + r")\s*$", lambda m: m.group(1) + "\n\n" + block, review_text, count=1, flags=re.M)
    return review_text.rstrip() + f"\n\n{RELATED_HEADING}\n\n{block}\n"


__all__ = [
    "Paper", "load_paper", "load_papers", "get_section", "iter_links", "resolve_link", "relpath", "review_skeleton",
    "figures_listing", "tables_listing", "write_index", "append_log", "replace_related_block", "strip_comments",
    "REVIEW_HEADINGS", "TODO_RE", "SKIP_NAMES",
]
