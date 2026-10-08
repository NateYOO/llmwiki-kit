"""여러 리뷰에서 같은 섹션만 모아 보기 (공통 한계·빈틈·후속 연구 분석, 서론 초안 재료 수집용).

  llmwiki sections --name limitation,gap
  llmwiki sections --name essence,originality --slugs a,b --out drafts/재료.md
"""
from __future__ import annotations

import re
from typing import Any

from .util import Workspace, write_text
from .wikiops import get_section, load_papers, strip_comments

SECTION_ALIASES = {
    "essence": ("## Essence", None),
    "motivation": ("## Motivation", None),
    "known": ("## Motivation", "Known"),
    "gap": ("## Motivation", "Gap"),
    "why": ("## Motivation", "Why"),
    "approach": ("## Motivation", "Approach"),
    "achievement": ("## Achievement", None),
    "how": ("## How", None),
    "originality": ("## Originality", None),
    "limitation": ("## Limitation & Further Study", None),
    "evaluation": ("## Evaluation", None),
    "verdict": ("## Evaluation", "총평"),
    "related": ("## Related Papers", None),
}
LABEL = {"known": "Motivation/Known", "gap": "Motivation/Gap", "why": "Motivation/Why", "approach": "Motivation/Approach",
         "verdict": "총평", "limitation": "Limitation & Further Study"}


def _clean(text: str) -> str:
    text = strip_comments(text)
    text = re.sub(r"^!\[[^\]]*\]\([^)]*\)\s*$", "", text, flags=re.M)  # 그림 임베드 제거(텍스트만)
    text = re.sub(r"^\*Figure.*$|^- (무엇이 보이는가|어떻게 읽을까|텍스트만 읽으면 놓치는 것):.*$", "", text, flags=re.M)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def extract(ws: Workspace, names: list[str], slugs: list[str] | None = None, category: str = "") -> list[dict[str, Any]]:
    if not names:
        raise SystemExit(f"섹션 이름을 적어 주세요. 예: --name limitation,gap  (가능: {', '.join(SECTION_ALIASES)})")
    bad = [n for n in names if n not in SECTION_ALIASES]
    if bad:
        raise SystemExit(f"알 수 없는 섹션: {bad}. 가능: {', '.join(SECTION_ALIASES)}")
    papers = load_papers(ws)
    if slugs:
        unknown = [x for x in slugs if x not in {p.slug for p in papers}]
        if unknown:
            raise SystemExit(f"논문 slug를 찾지 못했습니다: {', '.join(unknown)} (wiki/papers/ 아래 폴더 이름, `llmwiki index`로 목록 확인)")
    rows = []
    for p in papers:
        if not p.review.exists():
            continue
        if slugs and p.slug not in slugs:
            continue
        if category and category.lower() not in str(p.fm.get("category", "")).lower():
            continue
        entry = {"slug": p.slug, "title": p.title, "year": p.fm.get("year"), "category": p.fm.get("category", ""), "sections": {}}
        for n in names:
            heading, sub = SECTION_ALIASES[n]
            sec = get_section(p.body, heading)
            if sub == "총평":
                m = re.search(r"\*\*총평\*\*:\s*(.+)", sec)
                text = m.group(1) if m else ""
            elif sub:
                m = re.search(r"\*\*" + sub + r"\*\*:\s*(.+)", sec)
                text = m.group(1) if m else ""
            else:
                text = sec
            entry["sections"][n] = _clean(text)
        rows.append(entry)
    return rows


def to_markdown(rows: list[dict[str, Any]], names: list[str]) -> str:
    out = [f"# 섹션 모음: {', '.join(names)}", "",
           f"> `llmwiki sections --name {','.join(names)}` 자동 수집 ({len(rows)}편). 각 줄의 근거 꼬리표는 리뷰 섹션을 가리킨다.", ""]
    for n in names:
        label = LABEL.get(n, SECTION_ALIASES[n][0][3:])
        out += [f"## {label}", ""]
        for r in rows:
            text = r["sections"].get(n, "")
            out.append(f"### {r['title']} ({r.get('year') or 'n.d.'}) — `{r['slug']}`")
            out.append("")
            out.append(text if text else "_(비어 있음)_")
            out.append(f"\n[근거: {r['slug']} · {label}]")
            out.append("")
    return "\n".join(out).rstrip() + "\n"


def write_out(ws: Workspace, path: str, text: str, force: bool = False) -> str:
    target = (ws.root / path).resolve()
    if not str(target).startswith(str(ws.drafts.resolve())):
        raise SystemExit("--out 은 drafts/ 안의 경로만 허용합니다 (예: drafts/limitations-raw.md)")
    if target.exists() and not force:
        raise SystemExit(f"이미 있는 파일입니다: {ws.rel(target)} (덮어쓰려면 --force)")
    write_text(target, text)
    return ws.rel(target)
