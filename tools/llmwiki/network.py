"""링크 네트워크를 '질문거리'로 쓰기 위한 계산 (시각화 아님).

그래프: 노드 = wiki/papers/<slug>, 간선 = review.md 안의 다른 논문 review.md로 가는 상대 링크.
  - auto  : '## Related Papers' 자동 블록(llmwiki related --write)이 만든 링크. 관계 아이콘(🏛/🔗/🔄/🧪/⚖️)을 읽는다.
  - agent : 블록 밖(에이전트 해석·본문)에 사람이/에이전트가 근거와 함께 쓴 링크.
  - topic : wiki/topics/*.md 가 논문을 묶은 정보(주제 공유).
활용 5가지(wiki-synthesize 'N1~N5'): 새 논문의 이웃 · 연결 덩어리별 서론 흐름 · 공통 한계 중 미해결 빈틈 ·
연결 없는 두 군집 결합 · 허브 논문.
"""
from __future__ import annotations

import re
from typing import Any

from .util import RELATED_END, RELATED_START, Workspace, read_text
from .wikiops import iter_links, load_papers, resolve_link

REL_BY_ICON = {"🏛": "foundation", "🔗": "extension", "🔄": "alternative", "🧪": "application", "⚖": "counterpoint"}


def _paper_slug_of(ws: Workspace, path) -> str | None:
    try:
        rel = path.relative_to(ws.papers.resolve())
    except (ValueError, AttributeError):
        return None
    parts = rel.parts
    return parts[0] if parts else None


def graph(ws: Workspace) -> dict[str, Any]:
    papers = {p.slug: p for p in load_papers(ws) if p.review.exists()}
    edges: list[dict[str, Any]] = []
    for slug, p in papers.items():
        text = read_text(p.review)
        a, b = text.find(RELATED_START), text.find(RELATED_END)
        auto_part = text[a:b] if a >= 0 and b > a else ""
        rest = text[:a] + text[b:] if a >= 0 and b > a else text
        for kind, part in (("auto", auto_part), ("agent", rest)):
            for line in part.splitlines():
                for is_img, target, lk in iter_links(line):
                    if is_img:
                        continue
                    dst = resolve_link(ws, p.review, target, lk)
                    other = _paper_slug_of(ws, dst) if dst else None
                    if not other or other == slug or other not in papers:
                        continue
                    rel = ""
                    if kind == "auto":
                        rel = next((r for ic, r in REL_BY_ICON.items() if ic in line), "")
                    edges.append({"src": slug, "dst": other, "kind": kind, "relation": rel})
    topics: dict[str, list[str]] = {}
    if ws.topics.exists():
        for t in sorted(ws.topics.glob("*.md")):
            members = set()
            for is_img, target, lk in iter_links(read_text(t)):
                dst = resolve_link(ws, t, target, lk)
                s = _paper_slug_of(ws, dst) if dst else None
                if s in papers:
                    members.add(s)
            topics[t.stem] = sorted(members)
    # 중복 제거(같은 방향·같은 종류는 1개)
    seen, uniq = set(), []
    for e in edges:
        k = (e["src"], e["dst"], e["kind"])
        if k not in seen:
            seen.add(k)
            uniq.append(e)
    return {"papers": papers, "edges": uniq, "topics": topics}


def _undirected(edges, kinds=("auto", "agent")) -> dict[str, set[str]]:
    adj: dict[str, set[str]] = {}
    for e in edges:
        if e["kind"] in kinds:
            adj.setdefault(e["src"], set()).add(e["dst"])
            adj.setdefault(e["dst"], set()).add(e["src"])
    return adj


def neighbors(ws: Workspace, slug: str) -> dict[str, Any]:
    """새 논문(또는 아무 논문)의 이웃: 자동 후보 점수·관계 + 명시 링크(들어오는/나가는) + 주제 공유 + 공저자."""
    from .related import compute
    g = graph(ws)
    if slug not in g["papers"]:
        raise SystemExit(f"논문 slug를 찾지 못했습니다: {slug} (wiki/papers/ 아래 폴더 이름)")
    cand = {r["slug"]: r for r in compute(ws).get(slug, [])}
    out_e = [e for e in g["edges"] if e["src"] == slug]
    in_e = [e for e in g["edges"] if e["dst"] == slug]
    me = g["papers"][slug]
    my_auth = {a.split()[-1].lower() for a in (me.fm.get("authors") or []) if isinstance(a, str) and a.split()}
    rows = []
    for other in sorted(set(cand) | {e["dst"] for e in out_e} | {e["src"] for e in in_e}):
        op = g["papers"][other]
        auth = {a.split()[-1].lower() for a in (op.fm.get("authors") or []) if isinstance(a, str) and a.split()}
        rows.append({
            "slug": other, "title": op.title, "year": op.fm.get("year"), "category": op.fm.get("category") or "",
            "relation": (cand.get(other) or {}).get("relation") or next((e["relation"] for e in out_e + in_e if e["relation"] and other in (e["src"], e["dst"])), ""),
            "auto_reason": (cand.get(other) or {}).get("reason", ""),
            "links": sorted({f"{e['kind']}:{'→' if e['src'] == slug else '←'}" for e in out_e + in_e if other in (e["src"], e["dst"])}),
            "shared_topics": [t for t, m in g["topics"].items() if slug in m and other in m],
            "shared_authors": sorted(my_auth & auth),
            "cite": f"[근거: {other} · Essence]",
        })
    rows.sort(key=lambda r: (0 if r["relation"] in ("foundation", "extension") else 1, -len(r["links"]), r["slug"]))
    return {"slug": slug, "title": me.title, "neighbors": rows,
            "hint": "관계(foundation/extension/alternative)는 자동 추정. 각 이웃 review.md의 Essence·Motivation·Limitation을 읽고 근거와 함께 해석하세요."}


def hubs(ws: Workspace, top: int = 10) -> dict[str, Any]:
    """링크가 가장 많은 논문(허브). degree = 연결된 서로 다른 논문 수(자동+명시, 방향 무시)."""
    g = graph(ws)
    adj = _undirected(g["edges"])
    agent_adj = _undirected(g["edges"], kinds=("agent",))
    rows = []
    for slug, p in g["papers"].items():
        rows.append({"slug": slug, "title": p.title, "year": p.fm.get("year"),
                     "degree": len(adj.get(slug, ())), "agent_links": len(agent_adj.get(slug, ())),
                     "in": sum(1 for e in g["edges"] if e["dst"] == slug), "out": sum(1 for e in g["edges"] if e["src"] == slug),
                     "topics": [t for t, m in g["topics"].items() if slug in m],
                     "cite": f"[근거: {slug} · Essence]"})
    rows.sort(key=lambda r: (-r["degree"], -r["agent_links"], -r["in"], r["slug"]))
    comps = components(ws, g)
    return {"hubs": rows[:top], "components": comps, "edges": len(g["edges"]),
            "hint": "degree가 높은 논문 = 여러 논의가 만나는 지점. agent_links(근거 있는 명시 링크)가 많을수록 해석이 탄탄합니다."}


def components(ws: Workspace, g: dict[str, Any] | None = None, kinds=("auto", "agent")) -> list[list[str]]:
    g = g or graph(ws)
    adj = _undirected(g["edges"], kinds)
    seen, comps = set(), []
    for s in sorted(g["papers"]):
        if s in seen:
            continue
        stack, comp = [s], []
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            comp.append(x)
            stack.extend(adj.get(x, ()))
        comps.append(sorted(comp))
    comps.sort(key=lambda c: -len(c))
    return comps


def links_between(ws: Workspace, groups: list[list[str]]) -> list[dict[str, Any]]:
    """군집(또는 덩어리) 쌍 사이의 명시 링크 수. 0이면 '서로 링크 없는 두 군집'(결합 아이디어 후보)."""
    g = graph(ws)
    out = []
    for i in range(len(groups)):
        for j in range(i + 1, len(groups)):
            a, b = set(groups[i]), set(groups[j])
            n_all = sum(1 for e in g["edges"] if (e["src"] in a and e["dst"] in b) or (e["src"] in b and e["dst"] in a))
            n_agent = sum(1 for e in g["edges"] if e["kind"] == "agent" and ((e["src"] in a and e["dst"] in b) or (e["src"] in b and e["dst"] in a)))
            out.append({"a": i + 1, "b": j + 1, "links": n_all, "agent_links": n_agent})
    return out
