# Based on Paper Curation by 이제현 (https://github.com/jehyunlee/paper-curation)
"""위키 화면의 「지식 네트워크」(D3 힘 기반 배치, file:// 에서 동작).

원본 pipeline/generate_network.py 의 build_network_data()·화면 구성(왼쪽 조절 창, 오른쪽 상세 창, 통계, 단축키 표)을
이 키트의 데이터에 맞게 고친 것:
  - 논문 = wiki/papers/<slug>/review.md 의 frontmatter (category=분류, score=점 크기, essence=한 줄 요약)
  - 선 = 리뷰 근거 연결(에이전트 해석 링크) · 자동 유사도(related.json) · 주제 공유(주제 노트) · 저자 공유
  - 하위 분류 = llmwiki 자동 군집
데이터는 network-data.js(window.LLMWIKI_GRAPH)로 넣어 fetch 없이 file:// 에서 읽는다. D3 v7 은 assets/ 에 동봉(CDN 없음).
"""
from __future__ import annotations

import html
import json
import re
from typing import Any

E = html.escape

# 원본의 Tab10 색 순서
TAB10 = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]

REL_COLORS = {"review": "#8B5CF6", "auto": "#3B82F6", "topic": "#10B981", "author": "#F59E0B"}
REL_LABELS = {"review": "📝 리뷰 근거 연결", "auto": "🔄 자동 유사도", "topic": "🗂 주제 공유", "author": "👥 저자 공유"}
REL_HELP = {"review": "리뷰의 '에이전트 해석'에 근거와 함께 적어 둔 연결",
            "auto": "llmwiki related 가 계산한 어휘 유사도(TF-IDF·BM25)",
            "topic": "같은 주제 노트(wiki/topics)에 함께 들어 있음",
            "author": "같은 저자가 있음"}
REL_KO = {"foundation": "기반 연구", "extension": "후속 연구", "alternative": "다른 접근"}


def _strip(s: str) -> str:
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    s = re.sub(r"\[근거:[^\]]*\]", "", s)
    return re.sub(r"\s+", " ", re.sub(r"[*_`>#]", "", s)).strip()


def _agent_reasons(builder, slug: str) -> dict[str, str]:
    """review.md 의 '에이전트 해석' 등 블록 밖 문장에서, 다른 논문으로 가는 링크가 있는 줄 → 그 줄(설명)."""
    out: dict[str, str] = {}
    p = next((x for x in builder.papers if x.slug == slug), None)
    if not p:
        return out
    body = re.sub(r"<!-- llmwiki:related:start -->.*?<!-- llmwiki:related:end -->", "", p.body, flags=re.S)
    for line in body.splitlines():
        for m in re.finditer(r"\]\(\.\./([^/)]+)/review\.md\)", line):
            out.setdefault(m.group(1), _strip(line.lstrip("-* ")))
    return out


def build_data(builder, G: dict[str, Any]) -> dict[str, Any]:
    from .sitegraph import short_label
    papers = G["papers"]
    gnames = G["gnames"]
    cat_colors = {g: TAB10[i % len(TAB10)] for i, g in enumerate(gnames)}
    # 하위 분류 = 자동 군집
    sub_of: dict[str, str] = {}
    for c in getattr(builder, "clusters", None) or []:
        terms = ", ".join((c.get("top_terms") or [])[:2])
        for x in c.get("papers", []):
            sub_of[x.get("slug", "")] = f"군집 {c['cluster']}" + (f" · {terms}" if terms else "")
    nodes = []
    for s, p in sorted(papers.items()):
        fm = p.fm
        authors = fm.get("authors") or p.meta.get("authors") or []
        sc = fm.get("score")
        nodes.append({"id": s, "num": short_label(p), "title": p.title, "category": G["group_of"][s],
                      "all_categories": [G["group_of"][s]], "sub_category": sub_of.get(s, "군집 없음"),
                      "score": sc if isinstance(sc, (int, float)) else 0, "year": str(fm.get("year") or ""),
                      "essence": str(fm.get("essence") or "")[:200], "authors": ", ".join(map(str, authors[:6])),
                      "color": cat_colors[G["group_of"][s]], "shape": "circle", "multi": False})
    label = {s: short_label(p) for s, p in papers.items()}
    links: list[dict[str, Any]] = []
    conns: dict[str, dict[str, list]] = {s: {} for s in papers}

    def add(a: str, b: str, rel: str, w: float, reason_ab: str, reason_ba: str | None = None) -> None:
        links.append({"source": a, "target": b, "relation": rel, "reason": reason_ab, "w": round(w, 3),
                      "color": REL_COLORS[rel], "sl": label[a], "tl": label[b]})
        conns[a].setdefault(b, []).append([rel, reason_ab])
        conns[b].setdefault(a, []).append([rel, reason_ba if reason_ba is not None else reason_ab])

    maxcos = max([e["cos"] for e in G["edges"]] + [0.01])
    agent = {s: _agent_reasons(builder, s) for s in papers}
    rel_rows = builder.related or {}
    for e in G["edges"]:
        a, b = e["a"], e["b"]
        if e["agent"]:
            ra = agent[a].get(b) or agent[b].get(a) or REL_HELP["review"]
            add(a, b, "review", 1.0, ra, agent[b].get(a) or ra)
        if e["cos"] > 0:
            def why(x: str, y: str) -> str:
                r = next((r for r in rel_rows.get(x, []) if r.get("slug") == y), None)
                if not r:
                    return f"어휘 유사도 {e['cos']:.2f}"
                return " · ".join(filter(None, [REL_KO.get(r.get("relation"), ""), str(r.get("reason") or f"어휘 유사도 {e['cos']:.2f}")]))
            add(a, b, "auto", e["cos"] / maxcos, why(a, b), why(b, a))
    # 주제 공유
    shared: dict[tuple[str, str], list[str]] = {}
    for stem, v in G["notes"].items():
        mem = sorted(v["papers"])
        for i, a in enumerate(mem):
            for b in mem[i + 1:]:
                shared.setdefault((a, b), []).append(v["title"])
    for (a, b), titles in sorted(shared.items()):
        add(a, b, "topic", 0.35, "같은 주제 노트: " + ", ".join(titles))
    # 저자 공유
    au = {s: {str(x).strip().lower(): str(x) for x in (p.fm.get("authors") or p.meta.get("authors") or [])} for s, p in papers.items()}
    ss = sorted(papers)
    for i, a in enumerate(ss):
        for b in ss[i + 1:]:
            common = sorted(set(au[a]) & set(au[b]))
            if common:
                add(a, b, "author", 0.6, "공동 저자: " + ", ".join(au[a][c] for c in common[:3]))
    order = {"review": 0, "auto": 1, "topic": 2, "author": 3}
    node_conns = {s: sorted(({"o": o, "r": r} for o, r in d.items()), key=lambda x: order.get(x["r"][0][0], 9)) for s, d in conns.items() if d}
    cat_counts: dict[str, int] = {}
    sub_counts: dict[str, int] = {}
    cat_subs: dict[str, list[str]] = {}
    for n in nodes:
        cat_counts[n["category"]] = cat_counts.get(n["category"], 0) + 1
        sub_counts[n["sub_category"]] = sub_counts.get(n["sub_category"], 0) + 1
        cat_subs.setdefault(n["category"], [])
        if n["sub_category"] not in cat_subs[n["category"]]:
            cat_subs[n["category"]].append(n["sub_category"])
    subs = sorted(sub_counts)
    sub_colors = {s: TAB10[(i + 3) % len(TAB10)] for i, s in enumerate(subs)}
    years = sorted(int(n["year"]) for n in nodes if n["year"].isdigit())
    return {"nodes": nodes, "links": links, "conns": node_conns, "catColors": cat_colors,
            "catShapes": {g: "circle" for g in gnames}, "catCounts": cat_counts, "subColors": sub_colors,
            "subCounts": sub_counts, "catSubs": {k: sorted(v) for k, v in cat_subs.items()},
            "relColors": {k: REL_COLORS[k] for k in REL_LABELS}, "relLabels": REL_LABELS,
            "yearMin": years[0] if years else 2020, "yearMax": years[-1] if years else 2026}


def data_js(data: dict[str, Any]) -> str:
    return "window.LLMWIKI_GRAPH=" + json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + ";\n"


def body_html(data: dict[str, Any], static_svg: str, legend: str, extra_html: str, credit_line: str) -> str:
    """원본 화면 구성(왼쪽 조절 창 · 오른쪽 위 통계 · 상세 창 · 단축키 표) + 키트 추가(돌아가기·Codex 버튼·출처 줄·JS 없을 때 그림)."""
    ymin, ymax = data["yearMin"], data["yearMax"]
    rel_help = "".join(f'<tr><td>{E(REL_LABELS[k])}</td><td>{E(REL_HELP[k])}</td></tr>' for k in REL_LABELS)
    ask = "$wiki-query 내 위키 논문들은 서로 어떻게 연결돼 있어? 연결이 약한 주제 사이에서 연구 아이디어를 찾아 줘"
    return f"""<div id="controls">
  <button id="controls-toggle" title="접기/펴기">&laquo;</button>
  <div class="controls-inner">
  <h2>내 논문 네트워크</h2>
  <input type="text" id="search" placeholder="논문 찾기 (제목·저자·요약)">
  <div id="search-count"></div>
  <h3>색 기준</h3>
  <div id="colorby-btns">
    <span class="hl-btn active" id="colorby-cat">주제(분류)</span>
    <span class="hl-btn" id="colorby-sub">자동 군집</span>
  </div>
  <h3>주제 <span class="hl-btn" id="sel-all" style="font-size:0.65rem">전체</span> <span class="hl-btn" id="sel-none" style="font-size:0.65rem">없음</span></h3>
  <div id="cat-tree"></div>
  <h3>관계 종류</h3>
  <div id="rel-filters"></div>
  <h3>연도</h3>
  <div id="year-slider-box">
    <input type="range" id="year-min" min="{ymin}" max="{ymax}" value="{ymin}" style="width:120px">
    <input type="range" id="year-max" min="{ymin}" max="{ymax}" value="{ymax}" style="width:120px">
    <div id="year-label" style="font-size:0.8rem;color:#ccc;margin-top:0.2rem">{ymin} &mdash; {ymax}</div>
  </div>
  <h3>강조</h3>
  <div id="highlight-btns">
    <span class="hl-btn" id="hl-hub">연결 많은 논문 (상위 10)</span>
    <span class="hl-btn" id="hl-bridge">주제 잇는 논문</span>
    <span class="hl-btn" id="hl-reset">강조 끄기</span>
  </div>
  <h3>화면</h3>
  <div id="view-btns">
    <span class="hl-btn" id="view-reset" title="확대·이동을 처음 상태로">처음 화면으로</span>
  </div>
  <h3>점 크기 <span id="node-size-label" style="font-size:0.75rem;color:#ccc">1.0x</span></h3>
  <div><input type="range" id="node-size-slider" min="0.2" max="4.0" step="0.1" value="1.0" style="width:100%;accent-color:#4361EE"></div>
  <h3>테마</h3>
  <div id="theme-btns">
    <span class="hl-btn active" id="theme-dark">어둡게</span>
    <span class="hl-btn" id="theme-light">밝게</span>
  </div>
  <h3>힘 조절</h3>
  <div id="force-controls">
    <div class="force-row"><span>밀어내기</span><input type="range" id="f-charge" min="-1500" max="-10" value="-80"></div>
    <div class="force-row"><span>선 길이</span><input type="range" id="f-dist" min="10" max="300" value="60"></div>
    <div class="force-row"><span>선 당김</span><input type="range" id="f-str" min="5" max="100" value="40"></div>
    <div class="force-row"><span>가운데로</span><input type="range" id="f-grav" min="1" max="20" value="5"></div>
  </div>
  <h3>조작 방법</h3>
  <table id="help-table" style="font-size:0.75rem;border-collapse:collapse;width:100%">
    <tr><td>마우스 올리기</td><td>논문 한 줄 요약 · 선은 관계 설명</td></tr>
    <tr><td>점 클릭</td><td>오른쪽 상세 창(리뷰 링크)</td></tr>
    <tr><td>점 끌기</td><td>위치 옮기기</td></tr>
    <tr><td>휠 / 두 손가락</td><td>확대·축소</td></tr>
    <tr><td>빈 곳 끌기</td><td>화면 이동</td></tr>
    <tr><td>이웃만 보기</td><td>상세 창에서 누르면 바로 이어진 논문만</td></tr>
    <tr><td>Esc / 빈 곳 클릭</td><td>상세 창·이웃만 보기 닫기</td></tr>
    <tr><td>/</td><td>논문 찾기 칸으로</td></tr>
    {rel_help}
  </table>
  </div>
</div>
<div id="stats"><span id="node-count">0</span>편 &middot; 연결 <span id="link-count">0</span>개 <button id="info-hint-btn" title="단축키">&#x24D8;</button></div>
<div id="topnav"><a href="index.html">← 논문 목록</a><a href="index.html#topics">주제</a><button class="ask" type="button" data-ask="{E(ask, quote=True)}">💬 Codex에게 물어보기</button></div>
<div id="shortcuts-popup">
  <h4>단축키 · 조작</h4>
  <table>
    <tr><td>휠</td><td>확대·축소</td></tr>
    <tr><td>끌기</td><td>화면 이동</td></tr>
    <tr><td>점 클릭</td><td>상세 보기</td></tr>
    <tr><td>Shift+주제 클릭</td><td>자동 군집 펼치기</td></tr>
    <tr><td>Esc</td><td>선택·이웃만 보기 풀기</td></tr>
    <tr><td>/</td><td>논문 찾기</td></tr>
    <tr><td>?</td><td>이 창 열기/닫기</td></tr>
  </table>
</div>
<div id="info"><button id="info-close" title="닫기">&times;</button></div>
<div id="tooltip"></div>
<div class="link-tooltip" id="link-tooltip"></div>
<svg id="graph" role="img" aria-label="지식 네트워크"></svg>
<div class="nojs">
  <p><a href="index.html">← 논문 목록</a></p>
  <h1>지식 네트워크</h1>
  <p>JS가 꺼져 있거나 D3를 읽지 못해 고정 그림으로 보여 줘요. 점을 누르면 논문 페이지로 가요.</p>
  {static_svg}
  <h3>주제(분류)</h3><ul class="plain">{legend}</ul>
  {extra_html}
</div>
<div id="netfoot">{credit_line} · 네트워크 그림: D3.js v7.9.0 (ISC, <a href="assets/d3-LICENSE.txt">라이선스</a>)</div>"""
