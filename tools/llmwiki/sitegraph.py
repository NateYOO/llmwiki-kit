"""위키 화면의 「지식 네트워크」: 논문 = 점(주제 분류별 색), 관련 정도 = 선 굵기. 인라인 SVG(외부 라이브러리·JS 없음, file:// 동작).
배치는 만들 때 파이썬으로 계산한다(주제별 원 배치에서 시작하는 간단한 힘 기반 배치, 결정적)."""
from __future__ import annotations

import html
import math
import re
from typing import Any

E = html.escape
PALETTE = ["#2f5bea", "#e8590c", "#0f9d74", "#c2255c", "#7048e8", "#d4a106", "#1c7ed6", "#5c940d", "#ae3ec9", "#495057"]


def short_label(p) -> str:
    authors = [str(a) for a in (p.fm.get("authors") or p.meta.get("authors") or []) if a and str(a).split()] \
        if not isinstance(p.fm.get("authors"), str) else [p.fm["authors"]]
    first = authors[0].split()[-1] if authors and authors[0].split() else p.slug.split("-")[1] if "-" in p.slug else p.slug
    return f"{first} {p.fm.get('year') or ''}".strip()


def build_graph(builder) -> dict[str, Any]:
    """논문·선·주제(분류)·주제 노트 정보를 모은다."""
    from . import network
    papers = {p.slug: p for p in builder.papers}
    try:
        g = network.graph(builder.ws)
        raw_edges, topic_notes = g["edges"], g["topics"]
    except Exception:  # noqa: BLE001
        raw_edges, topic_notes = [], {}
    pairs: dict[tuple[str, str], dict[str, Any]] = {}
    for e in raw_edges:
        a, b = sorted((e["src"], e["dst"]))
        if a in papers and b in papers:
            d = pairs.setdefault((a, b), {"a": a, "b": b, "cos": 0.0, "agent": False, "reason": ""})
            d["agent"] = d["agent"] or e["kind"] == "agent"
    for src, rows in (builder.related or {}).items():
        for r in rows:
            a, b = sorted((src, r.get("slug", "")))
            if a in papers and b in papers:
                d = pairs.setdefault((a, b), {"a": a, "b": b, "cos": 0.0, "agent": False, "reason": ""})
                d["cos"] = max(d["cos"], float(r.get("cos") or 0))
                d["reason"] = d["reason"] or str(r.get("reason") or "")
    groups: dict[str, list[str]] = {}
    for s, p in papers.items():
        groups.setdefault(str(p.fm.get("category") or "분류 없음"), []).append(s)
    gnames = sorted(groups, key=lambda k: (-len(groups[k]), k))
    color = {g: PALETTE[i % len(PALETTE)] for i, g in enumerate(gnames)}
    group_of = {s: g for g, ss in groups.items() for s in ss}
    # 주제 노트: frontmatter papers + 본문 링크
    notes = {}
    for t in builder.topics:
        mem = set(t["papers"]) | set(topic_notes.get(t["stem"], []))
        notes[t["stem"]] = {"title": t["title"], "papers": sorted(m for m in mem if m in papers)}
    return {"papers": papers, "edges": list(pairs.values()), "groups": groups, "gnames": gnames,
            "color": color, "group_of": group_of, "notes": notes}


def layout(G: dict[str, Any], W: float = 1000, H: float = 560) -> dict[str, tuple[float, float]]:
    slugs = sorted(G["papers"])
    n = len(slugs)
    if n == 0:
        return {}
    cx, cy = W / 2, H / 2
    gn = G["gnames"]
    pos: dict[str, list[float]] = {}
    R = min(W, H) * (0.28 if len(gn) > 1 else 0.0)
    for gi, g in enumerate(gn):
        ang = 2 * math.pi * gi / max(1, len(gn)) - math.pi / 2
        gx, gy = cx + R * math.cos(ang) * 1.3, cy + R * math.sin(ang)
        mem = sorted(G["groups"][g])
        r2 = 40 + 14 * len(mem) if len(mem) > 1 else 0
        for k, s in enumerate(mem):
            a2 = 2 * math.pi * k / max(1, len(mem)) + gi
            pos[s] = [gx + r2 * math.cos(a2), gy + r2 * math.sin(a2)]
    if n == 1:
        return {slugs[0]: (cx, cy)}
    area = W * H
    k = math.sqrt(area / n) * 0.75
    maxcos = max([e["cos"] for e in G["edges"]] + [0.01])
    temp = W / 8
    for _ in range(300):
        disp = {s: [0.0, 0.0] for s in slugs}
        for i in range(n):
            for j in range(i + 1, n):
                a, b = slugs[i], slugs[j]
                dx, dy = pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]
                d = math.hypot(dx, dy) or 0.01
                f = k * k / d
                disp[a][0] += dx / d * f; disp[a][1] += dy / d * f
                disp[b][0] -= dx / d * f; disp[b][1] -= dy / d * f
        for e in G["edges"]:
            a, b = e["a"], e["b"]
            w = 0.4 + (e["cos"] / maxcos) + (0.6 if e["agent"] else 0)
            dx, dy = pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]
            d = math.hypot(dx, dy) or 0.01
            f = d * d / k * w * 0.5
            disp[a][0] -= dx / d * f; disp[a][1] -= dy / d * f
            disp[b][0] += dx / d * f; disp[b][1] += dy / d * f
        for g, mem in G["groups"].items():  # 같은 주제끼리 모이게
            if len(mem) < 2:
                continue
            mx = sum(pos[s][0] for s in mem) / len(mem); my = sum(pos[s][1] for s in mem) / len(mem)
            for s in mem:
                disp[s][0] += (mx - pos[s][0]) * 0.8; disp[s][1] += (my - pos[s][1]) * 0.8
        for s in slugs:
            dx, dy = disp[s]
            d = math.hypot(dx, dy) or 0.01
            pos[s][0] += dx / d * min(d, temp); pos[s][1] += dy / d * min(d, temp)
        temp *= 0.985
    # 화면 안으로 맞추기(여백 90px, 글자 자리)
    xs, ys = [p[0] for p in pos.values()], [p[1] for p in pos.values()]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    sx = (W - 220) / ((maxx - minx) or 1); sy = (H - 140) / ((maxy - miny) or 1)
    # 가로·세로를 따로 늘려 상자를 채운다(한쪽이 너무 길쭉해지지 않게 비율 차이는 2배까지만)
    sx, sy = min(sx, 2 * sy), min(sy, 2 * sx)
    ox = (W - (maxx - minx) * sx) / 2; oy = (H - (maxy - miny) * sy) / 2 - 10
    return {k2: (ox + (v[0] - minx) * sx, oy + (v[1] - miny) * sy) for k2, v in pos.items()}


def svg(G: dict[str, Any], pos: dict[str, tuple[float, float]], href, W: int = 1000, H: int = 560) -> str:
    """href(slug) → 링크 주소. 점·선·라벨에 <title>(마우스를 올리면 설명)."""
    maxcos = max([e["cos"] for e in G["edges"]] + [0.01])
    deg: dict[str, int] = {}
    for e in G["edges"]:
        deg[e["a"]] = deg.get(e["a"], 0) + 1
        deg[e["b"]] = deg.get(e["b"], 0) + 1
    out = [f'<svg class="net" viewBox="0 0 {W} {H}" role="img" aria-label="지식 네트워크: 논문 {len(pos)}편, 연결 {len(G["edges"])}개" xmlns="http://www.w3.org/2000/svg">',
           '<rect x="0" y="0" width="100%" height="100%" rx="14" fill="#fbfcfe"/>']
    for e in sorted(G["edges"], key=lambda e: e["cos"]):
        (x1, y1), (x2, y2) = pos[e["a"]], pos[e["b"]]
        w = 1.2 + 7 * (e["cos"] / maxcos) + (1.5 if e["agent"] else 0)
        col = "#5b6475" if e["agent"] else "#9aa3b5"
        ta, tb = G["papers"][e["a"]].title, G["papers"][e["b"]].title
        tip = f"{short_label(G['papers'][e['a']])} ↔ {short_label(G['papers'][e['b']])} · 어휘 유사도 {e['cos']:.2f}" + (" · 근거 링크 있음" if e["agent"] else "")
        out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{col}" stroke-width="{w:.1f}" stroke-linecap="round" opacity="0.75"'
                   + ('' if e["agent"] else ' stroke-dasharray="1 0"') + f'><title>{E(tip)}\n{E(ta)}\n{E(tb)}</title></line>')
    for s, (x, y) in sorted(pos.items()):
        p = G["papers"][s]
        r = 24 + 5 * min(deg.get(s, 0), 6)
        col = G["color"][G["group_of"][s]]
        lab = short_label(p)
        title = p.title if len(p.title) <= 64 else p.title[:62] + "…"
        out.append(f'<a href="{E(href(s), quote=True)}" class="node"><title>{E(p.title)} — 클릭하면 논문 페이지</title>'
                   f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{col}" stroke="#fff" stroke-width="3"/>'
                   f'<text x="{x:.1f}" y="{y + r + 22:.1f}" text-anchor="middle" class="nl">{E(lab)}</text>'
                   f'<text x="{x:.1f}" y="{y + r + 41:.1f}" text-anchor="middle" class="ns">{E(title[:38] + ("…" if len(title) > 38 else ""))}</text></a>')
    out.append("</svg>")
    return "".join(out)


def cross_links(G: dict[str, Any]) -> list[dict[str, Any]]:
    """서로 다른 주제(분류) 사이를 잇는 선 = 주제 사이 연결."""
    rows: dict[tuple[str, str], list] = {}
    for e in G["edges"]:
        ga, gb = G["group_of"][e["a"]], G["group_of"][e["b"]]
        if ga != gb:
            key = tuple(sorted((ga, gb)))
            rows.setdefault(key, []).append(e)
    return [{"a": k[0], "b": k[1], "edges": v} for k, v in sorted(rows.items(), key=lambda kv: -len(kv[1]))]


def shared_between_notes(G: dict[str, Any], stem: str) -> list[tuple[str, list[str]]]:
    """이 주제 노트의 논문 중 다른 주제 노트에도 들어 있는 것: [(slug, [다른 노트 stem…])]."""
    mine = set(G["notes"].get(stem, {}).get("papers", []))
    out = []
    for s in sorted(mine):
        others = [k for k, v in G["notes"].items() if k != stem and s in v["papers"]]
        if others:
            out.append((s, others))
    return out


def strip_tags(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s)
