"""기계 검사(lint). 의미 검사(모순·낡은 주장·빠진 개념)는 에이전트가 한다(wiki-format.md 7절).

심각도: ERROR(고쳐야 함) / WARN(확인 권장) / INFO
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import SCHEMA_VERSION
from .util import RELATED_END, RELATED_HEADING, RELATED_START, REVIEW_HEADINGS, Workspace, is_pipe_table_line, project_mds, read_text, split_frontmatter
from .wikiops import SKIP_NAMES, TODO_RE, get_section, iter_links, load_papers, resolve_link, strip_comments

REQUIRED_FM = ["title", "authors", "year", "slug", "category", "tags", "essence", "status", "schema_version",
               "score_novelty", "score_technical", "score_significance", "score_clarity", "score"]
OPTIONAL_FM = ["date", "doi", "arxiv", "venue", "url", "citekey", "zotero_key", "pdf", "review_date"]
SCORE_KEYS = {"score_novelty": "Novelty", "score_technical": "Technical Soundness", "score_significance": "Significance",
              "score_clarity": "Clarity", "score": "Overall"}
LOG_LINE = re.compile(r"^## \[(\d{4}-\d{2}-\d{2})\] (ingest|query|lint|draft|synthesize|related|setup|fix) \| .+$")


@dataclass
class Issue:
    level: str
    code: str
    path: str
    msg: str

    def as_dict(self) -> dict[str, str]:
        return {"level": self.level, "code": self.code, "path": self.path, "msg": self.msg}


def _shingles(text: str, n: int = 12) -> set[str]:
    words = re.findall(r"[A-Za-z0-9]+", text.lower())
    return {" ".join(words[i:i + n]) for i in range(0, max(0, len(words) - n + 1))}


def run(ws: Workspace) -> list[Issue]:
    issues: list[Issue] = []
    add = lambda lvl, code, path, msg: issues.append(Issue(lvl, code, path if isinstance(path, str) else ws.rel(path), msg))

    for d in ("wiki", "wiki/papers", "drafts"):
        if not (ws.root / d).is_dir():
            add("ERROR", "structure", d, "필수 폴더가 없습니다")
    if not ws.index.exists():
        add("ERROR", "structure", "wiki/index.md", "index.md 없음 → `llmwiki index`")
    if not ws.log.exists():
        add("WARN", "structure", "wiki/log.md", "log.md 없음")

    papers = load_papers(ws)
    slugs = {p.slug for p in papers}
    doi_map: dict[str, list[str]] = defaultdict(list)
    arxiv_map: dict[str, list[str]] = defaultdict(list)
    related_out: dict[str, set[str]] = {}

    for p in papers:
        rp = p.review
        if not rp.exists():
            add("ERROR", "missing-review", p.dir, "review.md 없음 (extract만 하고 리뷰를 안 씀)")
            continue
        if p.fm_error:
            add("ERROR", "frontmatter", rp, p.fm_error)
        fm = p.fm
        for k in REQUIRED_FM:
            if k not in fm:
                add("ERROR", "frontmatter", rp, f"필수 키 없음: {k}")
            elif fm[k] in (None, "", []) and k not in ("category",):
                lvl = "WARN" if fm.get("status") == "draft" else "ERROR"
                add(lvl, "frontmatter", rp, f"값이 비어 있음: {k}")
        if fm.get("slug") and fm["slug"] != p.slug:
            add("ERROR", "frontmatter", rp, f"slug({fm['slug']})가 폴더 이름({p.slug})과 다름")
        if fm.get("schema_version") and fm["schema_version"] != SCHEMA_VERSION:
            add("WARN", "frontmatter", rp, f"schema_version {fm['schema_version']} ≠ {SCHEMA_VERSION}")
        if fm.get("status") not in (None, "draft", "reviewed"):
            add("ERROR", "frontmatter", rp, "status는 draft 또는 reviewed")
        if not fm.get("category"):
            add("WARN", "frontmatter", rp, "category가 비어 있음 → index에서 '미분류'")
        if not isinstance(fm.get("authors", []), list):
            add("ERROR", "frontmatter", rp, "authors는 목록이어야 함")
        if not isinstance(fm.get("tags", []), list):
            add("ERROR", "frontmatter", rp, "tags는 목록이어야 함")
        for k in fm:
            if isinstance(fm[k], dict):
                add("WARN", "frontmatter", rp, f"중첩 속성 '{k}' — 위키 형식은 평평한 키만 써요(wiki-format 2절), 평평하게 펴세요")
        # 점수
        eval_sec = get_section(p.body, "## Evaluation")
        for k, label in SCORE_KEYS.items():
            v = fm.get(k)
            if v is None:
                continue
            if not isinstance(v, int) or not 1 <= v <= 5:
                add("ERROR", "score", rp, f"{k}={v!r}: 1–5 정수여야 함")
                continue
            m = re.search(r"^- " + re.escape(label) + r":\s*(\d)/5", eval_sec, re.M)
            if m and int(m.group(1)) != v:
                add("ERROR", "score", rp, f"{label} 본문 {m.group(1)}/5 ≠ frontmatter {k}={v}")
        # 7개 헤딩 + 순서 + Related
        pos = []
        for h in REVIEW_HEADINGS:
            m = re.search(r"^" + re.escape(h) + r"\s*$", p.body, re.M)
            if not m:
                add("ERROR", "headings", rp, f"헤딩 없음: {h}")
            else:
                pos.append(m.start())
        if pos != sorted(pos):
            add("ERROR", "headings", rp, "7개 헤딩 순서가 템플릿과 다름")
        if not re.search(r"^" + re.escape(RELATED_HEADING) + r"\s*$", p.body, re.M):
            add("ERROR", "headings", rp, "## Related Papers 없음")
        for h in REVIEW_HEADINGS[:-1]:
            sec = strip_comments(get_section(p.body, h)).strip()
            if h == "## Motivation":
                for sub in ("Known", "Gap", "Why", "Approach"):
                    m = re.search(r"\*\*" + sub + r"\*\*:\s*(.*)", sec)
                    if not m or not m.group(1).strip():
                        add("WARN" if fm.get("status") == "draft" else "ERROR", "empty-section", rp, f"Motivation/{sub} 비어 있음")
            elif len(sec) < 15:
                add("WARN" if fm.get("status") == "draft" else "ERROR", "empty-section", rp, f"{h} 내용이 비어 있음")
        if TODO_RE.search(p.body):
            add("WARN" if fm.get("status") == "draft" else "ERROR", "todo", rp, "TODO 자리표시가 남아 있음")
        if "?/5" in eval_sec:
            add("WARN" if fm.get("status") == "draft" else "ERROR", "score", rp, "Evaluation 점수가 ?/5 로 남아 있음")
        # 그림
        figs = p.meta.get("figures") or []
        embeds = [t for img, t, kind in iter_links(p.body) if img]
        if figs and not any("figures/" in t for t in embeds):
            add("WARN", "figures", rp, f"추출 그림 {len(figs)}개가 있지만 리뷰에 그림이 하나도 없음")
        cf = (p.meta.get("captions_found") or {}).get("figure", 0)
        files = list((p.dir / "figures").glob("*.png")) if (p.dir / "figures").exists() else []
        if cf and len(files) < min(cf, 20):
            add("WARN", "figures", p.dir / "figures", f"캡션 {cf}개 중 PNG {len(files)}개만 있음 → 다시 extract하거나 수동 캡처")
        for f in figs:
            if f.get("low_confidence") or str(f.get("method", "")).startswith("fallback"):
                if any(Path(t).name == Path(f["file"]).name for t in embeds):
                    add("WARN", "figures", rp, f"리뷰에 쓴 {Path(f['file']).name}은 자동 크롭 신뢰도가 낮음 — PNG를 눈으로 확인")
        # dual-coding 표식: 임베드된 그림 아래 '원문 PDF 캡처' 표기
        for t in embeds:
            if "figures/" in t and "원문 PDF 캡처" not in p.body:
                add("WARN", "figures", rp, "그림 출처 표기('원문 PDF 캡처 · 로컬 연구용')가 없음")
                break
        # 표는 PNG로만: 리뷰 안 markdown 표(| 로 시작하는 줄 2줄 연속, 코드 블록 밖)
        _in_code, _prev = False, False
        for _ln in strip_comments(p.body).split("\n"):
            if _ln.lstrip().startswith("```"):
                _in_code = not _in_code
            _cur = not _in_code and is_pipe_table_line(_ln)
            if _cur and _prev:
                add("WARN", "table-md", rp, "표는 PNG로만 보여 줘요 — 리뷰의 markdown 표를 지우고 그림 링크를 쓰세요(예: ![Table 1](tables/table1.png))")
                break
            _prev = _cur
        # 원문 덤프 의심: 영어 12단어 연속 일치가 많으면
        src = p.dir / "source.md"
        if src.exists():
            body_wo_quotes = re.sub(r"^>.*$", "", strip_comments(p.body), flags=re.M)
            overlap = _shingles(body_wo_quotes) & _shingles(read_text(src))
            if len(overlap) > 8:
                add("WARN", "verbatim", rp, f"원문과 12단어 이상 연속 일치 구간 {len(overlap)}개 — 원문 복사 의심(짧은 인용은 > 인용블록으로)")
        # 식별자
        doi = str(fm.get("doi") or p.meta.get("doi") or "").lower().strip()
        if doi:
            doi_map[doi].append(p.slug)
        ax = str(fm.get("arxiv") or p.meta.get("arxiv") or "").strip()
        if ax:
            arxiv_map[ax].append(p.slug)
        # 관련 링크
        rel_sec = get_section(p.body, RELATED_HEADING)
        outs = set()
        for img, t, kind in iter_links(rel_sec):
            r = resolve_link(ws, rp, t, kind)
            if r and r.name == "review.md" and r.parent.parent == ws.papers.resolve():
                outs.add(r.parent.name)
        related_out[p.slug] = outs
        if RELATED_START not in p.body or RELATED_END not in p.body:
            add("WARN", "related", rp, "자동 관련 링크 블록 표식이 없음 → `llmwiki related --write`")

    for doi, ss in doi_map.items():
        if len(ss) > 1:
            add("ERROR", "duplicate-doi", "wiki/papers", f"DOI {doi} 중복: {', '.join(ss)}")
    for ax, ss in arxiv_map.items():
        if len(ss) > 1:
            add("ERROR", "duplicate-arxiv", "wiki/papers", f"arXiv {ax} 중복: {', '.join(ss)}")
    for a, outs in related_out.items():
        for b in outs:
            if b in related_out and a not in related_out[b]:
                add("WARN", "related-asym", f"wiki/papers/{b}/review.md", f"{a} → {b} 링크는 있는데 {b} → {a} 링크가 없음 → `llmwiki related --write`")

    # 깨진 링크 + 들어오는 링크 집계 (wiki/, drafts/, projects/ 의 모든 md — projects/의 hwp·xlsx 등 md가 아닌 파일은 보지 않음)
    inbound: dict[str, set[str]] = defaultdict(set)
    md_files = [f for f in ws.wiki.rglob("*.md") if f.name not in SKIP_NAMES] if ws.wiki.exists() else []
    md_files += list(ws.drafts.rglob("*.md")) if ws.drafts.exists() else []
    md_files += project_mds(ws)
    for f in md_files:
        if any(part.startswith(".") for part in f.relative_to(ws.root).parts):
            continue
        text = read_text(f)
        for img, t, kind in iter_links(text):
            r = resolve_link(ws, f, t, kind)
            if r is None:
                continue
            if not r.exists():
                add("ERROR", "broken-link", f, f"깨진 {'이미지' if img else '링크'}: {t}")
                continue
            inbound[str(r)].add(str(f.resolve()))
    index_r = str(ws.index.resolve())
    for p in papers:
        if not p.review.exists():
            continue
        srcs = inbound.get(str(p.review.resolve()), set())
        if index_r not in srcs:
            add("ERROR", "orphan", p.review, "index.md에 없음 → `llmwiki index`")
        others = {s for s in srcs if s != index_r and s != str(p.review.resolve())}
        if not others and len(papers) > 1:
            add("WARN", "isolated", p.review, "다른 논문·주제 페이지에서 들어오는 링크가 없음")
    if ws.topics.exists():
        for t in ws.topics.glob("*.md"):
            if index_r not in inbound.get(str(t.resolve()), set()):
                add("WARN", "orphan", t, "주제 페이지가 index.md에 없음 → `llmwiki index`")
    # log 형식
    if ws.log.exists():
        for i, line in enumerate(read_text(ws.log).splitlines(), 1):
            if line.startswith("## [") and not LOG_LINE.match(line):
                add("WARN", "log", f"wiki/log.md:{i}", f"log 헤더 형식 불일치: {line[:60]}")
    # 위키 밖 금지 위치 점검(.obsidian 등은 건드리지 않음)
    return issues


def summarize(issues: list[Issue]) -> dict[str, Any]:
    c = defaultdict(int)
    for i in issues:
        c[i.level] += 1
    return {"errors": c["ERROR"], "warnings": c["WARN"], "info": c["INFO"]}
