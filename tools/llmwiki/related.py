"""관련 논문 연결 (Paper Curation §9 방식의 무료·경량 대체).

- 입력 텍스트: 제목 + 초록(meta.json) + 리뷰의 Essence·Originality + tags
- 점수: 순수 Python TF-IDF 코사인 순위와 BM25 순위를 RRF(k=60)로 융합 → 논문당 상위 k개
- 관계 유형: 공저자 공유 + 연도 차이 → foundation(앞선 연구)/extension(후속 연구), 그 밖은 alternative
- 대칭화: A→B가 있으면 B→A도 쓴다
- 의미 해석(반론·응용 등)은 에이전트가 '### 에이전트 해석'에 근거와 함께 쓴다(자동 블록 밖).
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

from .textindex import BM25, TfIdf, ranks, rrf, tokenize
from .util import RELATED_END, RELATED_START, Workspace, dump_json, read_text, write_text
from .wikiops import Paper, load_papers, replace_related_block, strip_comments

ICON = {"foundation": "🏛 기반 연구", "extension": "🔗 후속 연구", "alternative": "🔄 다른 접근",
        "application": "🧪 응용 사례", "counterpoint": "⚖️ 반론/비판"}


def _author_key(name: str) -> str:
    name = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode() or str(name)
    name = name.strip()
    if "," in name:
        last, first = [x.strip() for x in name.split(",", 1)]
    else:
        parts = name.split()
        if not parts:
            return ""
        last, first = parts[-1], " ".join(parts[:-1])
    return (last.lower() + "_" + (first[:1].lower() if first else "")).strip("_")


def _year(p: Paper) -> int | None:
    for v in (p.fm.get("year"), p.meta.get("year"), str(p.fm.get("date") or p.meta.get("date") or "")[:4]):
        if v and str(v)[:4].isdigit():
            return int(str(v)[:4])
    return None


def _doc_text(p: Paper) -> str:
    parts = [p.title, p.title, str(p.meta.get("abstract", "")), str(p.fm.get("essence", ""))]
    for h in ("## Essence", "## Originality"):
        parts.append(strip_comments(p.section(h)))
    parts += [str(t) for t in (p.fm.get("tags") or []) if t != "paper"]
    return "\n".join(parts)


def compute(ws: Workspace, top_k: int | None = None, min_score: float | None = None) -> dict[str, list[dict[str, Any]]]:
    papers = [p for p in load_papers(ws) if p.review.exists() or p.meta]
    cfg = ws.config.get("related", {})
    top_k = int(top_k or cfg.get("top_k", 5))
    min_score = float(cfg.get("min_score", 0.0) if min_score is None else min_score)
    n = len(papers)
    if n < 2:
        return {p.slug: [] for p in papers}
    toks = [tokenize(_doc_text(p)) for p in papers]
    tfidf = TfIdf(toks)
    authors = [p.fm.get("authors") or p.meta.get("authors") or [] for p in papers]
    bm_docs = [tokenize(p.title + " " + " ".join(map(str, a)) + " " + str(p.meta.get("abstract", ""))) for p, a in zip(papers, authors)]
    bm = BM25(bm_docs)
    akeys = [{_author_key(a) for a in au if a} for au in authors]
    years = [_year(p) for p in papers]

    links: dict[int, dict[int, dict[str, Any]]] = {i: {} for i in range(n)}
    for i in range(n):
        others = [j for j in range(n) if j != i]
        cos = [TfIdf.cosine(tfidf.vecs[i], tfidf.vecs[j]) for j in others]
        bms = bm.scores(tokenize(papers[i].title + " " + str(papers[i].meta.get("abstract", ""))))
        bms_o = [bms[j] for j in others]
        r_cos, r_bm = ranks(cos), ranks(bms_o)
        fused = rrf([r_cos, r_bm], k=60)
        order = sorted(range(len(others)), key=lambda x: -fused[x])
        for x in order[:top_k]:
            if cos[x] < min_score:
                continue
            j = others[x]
            links[i][j] = {"cos": cos[x], "bm25_rank": r_bm[x], "cos_rank": r_cos[x], "rrf": fused[x]}
    # 대칭화
    for i in range(n):
        for j, info in list(links[i].items()):
            if i not in links[j]:
                links[j][i] = {**info, "symmetric": True}

    out: dict[str, list[dict[str, Any]]] = {}
    for i, p in enumerate(papers):
        rows = []
        for j, info in sorted(links[i].items(), key=lambda kv: -kv[1]["rrf"]):
            shared = akeys[i] & akeys[j]
            yi, yj = years[i], years[j]
            if shared and yi and yj and yi != yj:
                rel = "foundation" if yj < yi else "extension"
            else:
                rel = "alternative"
            reason = [f"TF-IDF 유사도 {info['cos']:.2f}", f"BM25 {info['bm25_rank']}위"]
            if shared:
                reason.append(f"공저자 {len(shared)}명 공유")
            if yi and yj and yi != yj:
                reason.append(f"{abs(yi - yj)}년 {'앞선' if yj < yi else '뒤의'} 연구")
            elif yi and yj:
                reason.append("같은 해")
            if info.get("symmetric"):
                reason.append("상대 논문 쪽 후보(대칭)")
            rows.append({"slug": papers[j].slug, "title": papers[j].title, "relation": rel, "reason": " · ".join(reason),
                         "cos": round(info["cos"], 4), "rrf": round(info["rrf"], 5)})
        out[p.slug] = rows
    return out


def write(ws: Workspace, result: dict[str, list[dict[str, Any]]], only: str | None = None) -> list[str]:
    changed = []
    for slug, rows in result.items():
        if only and slug != only and only not in [r["slug"] for r in rows]:
            continue
        review = ws.paper_dir(slug) / "review.md"
        if not review.exists():
            continue
        if rows:
            body = "\n".join(f"- {ICON[r['relation']]}: [{r['title']}](../{r['slug']}/review.md) — {r['reason']}" for r in rows)
            body = "_자동 계산(llmwiki related): 어휘 유사도 + 저자·연도 규칙. 의미 해석은 아래 '에이전트 해석'에 근거와 함께._\n\n" + body
        else:
            body = "_관련 논문 후보 없음(위키에 논문이 1편뿐이거나 유사도가 기준 미만)._"
        old = read_text(review)
        new = replace_related_block(old, body)
        if new != old:
            write_text(review, new)
            changed.append(slug)
    write_text(ws.wiki / "related.json", dump_json(result) + "\n")
    return changed


def clusters(ws: Workspace, threshold: float | None = None, top_terms: int = 8) -> dict[str, Any]:
    """주제 탐색용 가벼운 군집: TF-IDF 코사인 평균연결(average-link) 병합 + 군집별 대표 단어.
    threshold를 안 주면 (모든 쌍 코사인의 평균 + 0.5·표준편차)를 쓴다. 해석·이름짓기는 에이전트 몫."""
    import math
    papers = [p for p in load_papers(ws) if p.review.exists() or p.meta]
    n = len(papers)
    if n == 0:
        return {"threshold": None, "clusters": [], "cross_links": []}
    toks = [tokenize(_doc_text(p)) for p in papers]
    tf = TfIdf(toks)
    sim = [[TfIdf.cosine(tf.vecs[i], tf.vecs[j]) for j in range(n)] for i in range(n)]
    pairs = [sim[i][j] for i in range(n) for j in range(i + 1, n)]
    if threshold is None:
        if pairs:
            mu = sum(pairs) / len(pairs)
            sd = math.sqrt(sum((x - mu) ** 2 for x in pairs) / len(pairs))
            threshold = mu + 0.5 * sd
        else:
            threshold = 1.0
    groups = [[i] for i in range(n)]
    def link(a, b):
        return sum(sim[i][j] for i in a for j in b) / (len(a) * len(b))
    while len(groups) > 1:
        best, bi, bj = -1.0, -1, -1
        for x in range(len(groups)):
            for y in range(x + 1, len(groups)):
                v = link(groups[x], groups[y])
                if v > best:
                    best, bi, bj = v, x, y
        if best < threshold:
            break
        groups[bi] += groups.pop(bj)
    out = []
    for gi, g in enumerate(sorted(groups, key=lambda g: -len(g)), 1):
        cent: dict[str, float] = {}
        for i in g:
            for t, v in tf.vecs[i].items():
                cent[t] = cent.get(t, 0.0) + v / len(g)
        terms = [t for t, _ in sorted(cent.items(), key=lambda kv: -kv[1]) if len(t) > 2][:top_terms]
        cats = sorted({str(papers[i].fm.get("category") or "미분류") for i in g})
        out.append({"cluster": gi, "size": len(g), "top_terms": terms, "categories": cats,
                    "papers": [{"slug": papers[i].slug, "title": papers[i].title, "year": papers[i].fm.get("year")} for i in g],
                    "cohesion": round(link(g, g), 3) if len(g) > 1 else None})
    cross = []
    for a in range(len(out)):
        for b in range(a + 1, len(out)):
            ga = [i for i in range(n) if papers[i].slug in {p["slug"] for p in out[a]["papers"]}]
            gb = [i for i in range(n) if papers[i].slug in {p["slug"] for p in out[b]["papers"]}]
            cross.append({"a": out[a]["cluster"], "b": out[b]["cluster"], "similarity": round(link(ga, gb), 3)})
    cross.sort(key=lambda c: c["similarity"])
    return {"threshold": round(threshold, 3), "clusters": out,
            "cross_links": cross,
            "hint": "cross_links의 similarity가 낮은 군집 쌍 = 아직 함께 연구되지 않은 조합 후보(에이전트가 근거와 함께 해석)"}
