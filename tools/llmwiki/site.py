# Based on Paper Curation by 이제현 (https://github.com/jehyunlee/paper-curation) — 목록·리뷰·네트워크 화면 구성 부분
"""`llmwiki site` — wiki/·drafts/를 브라우저로 보는 정적 HTML(site/)로 만든다 (표준 라이브러리 + 기존 의존성만).
- 상대 링크만 쓴다 → site/index.html을 file://로 열어도 JS 없이 링크로 다닐 수 있다.
- 검색·필터·「Codex에게 물어보기」 복사 버튼은 JS(외부 라이브러리 없음). 검색 색인은 search-index.json + search-index.js.
- 목록·리뷰·네트워크 화면: Based on Paper Curation by 이제현 (https://github.com/jehyunlee/paper-curation) (THIRD_PARTY_NOTICES.md). 하단에 같은 출처 표기."""
from __future__ import annotations

import html
import json
import unicodedata
import os
import re
import shutil
from pathlib import Path
from typing import Any

from .mdhtml import convert, slug_id
from .util import RELATED_END, RELATED_START, Workspace, project_mds, read_text, split_frontmatter, table_search_text, today
from .wikiops import tables_listing
from urllib.parse import quote as _quote, unquote as _unquote



def _authors(v) -> list[str]:
    """저자 목록 정리: 비었거나(서지 사이트가 바빴을 때) 문자열·None이 섞여도 화면이 깨지지 않게."""
    if not v:
        return []
    if isinstance(v, str):
        v = [v]
    return [str(a).strip() for a in v if a is not None and str(a).strip() and str(a).strip() != "None"]

def _href(path: str) -> str:
    """한글 폴더·파일 이름: NFC로 맞추고 URL 인코딩(맥 NFD 대비)."""
    return _quote(unicodedata.normalize("NFC", path), safe="/#._-~")

CREDIT = ('Based on Paper Curation by 이제현 '
          '(<a href="https://github.com/jehyunlee/paper-curation" target="_blank" rel="noopener">https://github.com/jehyunlee/paper-curation</a>)')
IMG_EXT = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}
REL_LABEL = {"foundation": "🏛 기반 연구", "extension": "🔗 후속 연구", "alternative": "🔄 다른 접근"}
ASSET_DIR = Path(__file__).with_name("site_assets")
E = html.escape


def site_dir(ws: Workspace) -> Path:
    return ws.root / "site"


class Builder:
    def __init__(self, ws: Workspace):
        self.ws = ws
        self.out = site_dir(ws)
        self.written: set[Path] = set()
        self.index: list[dict[str, Any]] = []

    # ------------------------------------------------------------ 경로
    def ws_to_site(self, p: Path) -> str | None:
        try:
            rel = p.resolve().relative_to(self.ws.root).as_posix()
        except ValueError:
            return None
        if rel == "wiki/index.md":
            return "index.html"
        if rel == "wiki/log.md":
            return "log.html"
        m = re.fullmatch(r"wiki/papers/([^/]+)/review\.md", rel)
        if m:
            return f"papers/{m.group(1)}/index.html"
        if rel.startswith("wiki/"):
            rel = rel[5:]
        elif not rel.startswith(("drafts/", "projects/")):
            return None
        rel = unicodedata.normalize("NFC", rel)
        if rel.endswith(".md"):
            return rel[:-3] + ".html"
        if Path(rel).suffix.lower() in IMG_EXT:
            return rel
        return None

    def linker(self, src: Path, out_rel: str):
        def fn(url: str, is_img: bool) -> str:
            if re.match(r"^[a-z][a-z0-9+.-]*:", url, re.I) or url.startswith("#"):
                return url
            path, _, frag = url.partition("#")
            target = (src.parent / _unquote(path))
            sr = self.ws_to_site(target)
            if sr is None:
                return url
            if frag and sr.endswith(".html"):
                frag = slug_id(frag) if not re.fullmatch(r"p-?\d+", frag) else frag
            r = self.rel(out_rel, sr)
            if not r.isascii():
                r = _href(r)
            return r + (f"#{frag}" if frag else "")
        return fn

    @staticmethod
    def rel(from_page: str, to: str) -> str:
        r = os.path.relpath(to, os.path.dirname(from_page) or ".").replace(os.sep, "/")
        return r

    @staticmethod
    def root_of(page: str) -> str:
        return "../" * page.count("/")

    def write(self, rel: str, text: str) -> None:
        p = self.out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists() or p.read_text(encoding="utf-8", errors="replace") != text:
            p.write_text(text, encoding="utf-8", newline="\n")
        self.written.add(p.resolve())

    def copy(self, src: Path, rel: str) -> None:
        dst = self.out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists() or dst.stat().st_size != src.stat().st_size or dst.stat().st_mtime < src.stat().st_mtime:
            shutil.copy2(src, dst)
        self.written.add(dst.resolve())

    # ------------------------------------------------------------ 틀
    def page(self, rel: str, title: str, body: str, *, ask: str, nav: str = "", body_class: str = "", bare: bool = False,
             head_extra: str = "", scripts_extra: str = "") -> None:
        root = self.root_of(rel)
        navs = [("index.html", "논문 목록", "home"), ("network.html", "네트워크", "network"), ("index.html#topics", "주제", "topics"),
                ("drafts/index.html", "초안·아이디어", "drafts"), ("log.html", "작업 기록", "log")]
        nav_html = "".join(f'<a href="{root}{h}"{" class=\"on\"" if k == nav else ""}>{E(t)}</a>' for h, t, k in navs)
        chrome_top = "" if bare else f"""<header class="top">
  <div class="top-in">
    <a class="brand" href="{root}index.html"><span class="logo">📚</span><span><b>내 논문 위키</b><small>나만의 지식 파트너</small></span></a>
    <nav class="nav">{nav_html}</nav>
    <div class="search js-only">
      <input id="q" type="search" placeholder="검색: 제목·저자·리뷰·그림·표 설명" autocomplete="off" aria-label="위키 검색">
      <div id="results" class="results" hidden></div>
    </div>
    <button class="ask js-only" type="button" data-ask="{E(ask, quote=True)}" title="Codex 채팅에 붙여넣을 문장을 복사합니다">💬 Codex에게 물어보기</button>
  </div>
</header>
<main class="wrap">
"""
        chrome_bottom = "" if bare else f"""
</main>
<footer class="foot">
  <div>{CREDIT}</div>
  <div class="muted">Karpathy LLM Wiki 방식 · <code>llmwiki site</code>로 만든 화면 ({today()}) · 위키 원본은 <code>wiki/</code> 폴더의 마크다운</div>
  <noscript><div class="muted">JS가 꺼져 있어 검색·복사 버튼은 숨겼어요. 링크로는 모두 볼 수 있어요. Codex에 물어볼 때: <code>{E(ask)}</code></div></noscript>
</footer>
"""
        doc = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)} · 내 논문 위키</title>
<link rel="stylesheet" href="{root}assets/style.css">
<link rel="stylesheet" href="{root}assets/pc.css">{head_extra}
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 16 16%22%3E%3Ctext y=%2214%22 font-size=%2214%22%3E%F0%9F%93%9A%3C/text%3E%3C/svg%3E">
<script>document.documentElement.classList.add('js');</script>
</head>
<body class="{body_class}" data-root="{root}">
{chrome_top}{body}{chrome_bottom}
<div id="toast" class="toast" role="status" aria-live="polite" hidden></div>
<div id="copybox" class="copybox" hidden><div class="copybox-in"><p>자동 복사가 막혔어요. 아래 글이 선택된 상태예요 — <b>Ctrl+C</b>(맥: ⌘+C)를 누른 뒤 Codex 채팅에 붙여넣으세요.</p><textarea readonly rows="3"></textarea><button type="button" class="close">닫기</button></div></div>
<script src="{root}search-index.js"></script>
<script src="{root}assets/app.js"></script>{scripts_extra}
</body>
</html>
"""
        self.write(rel, doc)

    # ------------------------------------------------------------ 근거 꼬리표 → 원문·섹션 링크
    def cite_links(self, html_text: str, page: str) -> str:
        def seg(s: str, last_slug: list) -> str:
            s0 = s.strip()
            m = re.match(r"(?P<slug>[0-9]{4}-[\w-]+)\s*·\s*(?P<loc>.+)$", s0)
            if m:
                last_slug[0] = m.group("slug")
                slug, loc = m.group("slug"), m.group("loc").strip()
            elif last_slug[0]:
                slug, loc = last_slug[0], s0
            else:
                return E(s)
            if not (self.ws.papers / slug).is_dir():
                return E(s)
            pm = re.match(r"p\.\s*(\d+)", loc)
            if pm:
                href = self.rel(page, f"papers/{slug}/source.html") + f"#p-{pm.group(1)}"
                tip = "원문 페이지 보기"
            else:
                sec = {"known": "motivation", "gap": "motivation", "why": "motivation", "approach": "motivation"}.get(
                    loc.split(",")[0].strip().lower(), slug_id(loc.split(",")[0]))
                href = self.rel(page, f"papers/{slug}/index.html") + f"#{sec}"
                tip = "리뷰 섹션 보기"
            return f' <a href="{E(href, quote=True)}" title="{tip}">{E(s0)}</a>'

        def rep(m: re.Match) -> str:
            inner = html.unescape(m.group(1))
            last = [""]
            parts = [seg(x, last) for x in inner.split(";")]
            return '<span class="cite">[근거:' + ";".join(parts) + "]</span>"
        return re.sub(r'<span class="cite">\[근거:(.*?)\]</span>', rep, html_text)

    # ------------------------------------------------------------ 데이터
    def load(self) -> None:
        from .wikiops import load_papers
        self.papers = [p for p in load_papers(self.ws) if p.review.exists()]
        rj = self.ws.wiki / "related.json"
        try:
            self.related = json.loads(read_text(rj)) if rj.exists() else {}
        except json.JSONDecodeError:
            self.related = {}
        self.topics = []
        if self.ws.topics.exists():
            for f in sorted(self.ws.topics.glob("*.md")):
                fm, body, _ = split_frontmatter(read_text(f))
                fm = fm or {}
                h1 = re.search(r"^#\s+(.+)$", body, re.M)
                self.topics.append({"file": f, "stem": f.stem, "title": str(fm.get("title") or (h1.group(1) if h1 else f.stem)),
                                    "papers": [str(x) for x in (fm.get("papers") or [])], "body": body})
        self.clusters = []
        if len(self.papers) >= 2:
            try:
                from . import related
                self.clusters = related.clusters(self.ws).get("clusters", [])
            except Exception:  # noqa: BLE001 — 군집은 있으면 좋은 정보
                self.clusters = []
        from .sitegraph import build_graph, layout
        self.G = build_graph(self)
        self.pos = layout(self.G)
        self.drafts = []
        if self.ws.drafts.exists():
            self.drafts = sorted((f for f in self.ws.drafts.glob("*.md")), key=lambda f: (f.name.lower() == "readme.md", -f.stat().st_mtime))
        self.projects = project_mds(self.ws)

    # ------------------------------------------------------------ 페이지들
    def groups_of(self, p) -> list[tuple[str, str]]:
        g = []
        if p.fm.get("category"):
            g.append((f"cat:{p.fm['category']}", f"분류 · {p.fm['category']}"))
        for t in self.topics:
            if p.slug in t["papers"]:
                g.append((f"topic:{t['stem']}", f"주제 · {t['title']}"))
        for c in self.clusters:
            if any(x.get("slug") == p.slug for x in c.get("papers", [])):
                terms = ", ".join(c.get("top_terms", [])[:3])
                g.append((f"cl:{c['cluster']}", f"군집 {c['cluster']} · {terms}"))
        return g

    def build_home(self) -> None:
        rel = "index.html"
        years = sorted({str(p.fm.get("year") or "") for p in self.papers if p.fm.get("year")}, reverse=True)
        groups: dict[str, str] = {}
        cards = []
        for p in sorted(self.papers, key=lambda p: (-(int(p.fm.get("year") or 0)), p.title.lower())):
            gs = self.groups_of(p)
            groups.update(dict(gs))
            authors = _authors(p.fm.get("authors") or p.meta.get("authors"))
            au = ", ".join(map(str, authors[:3])) + (" 외" if len(authors) > 3 else "")
            score = p.fm.get("score")
            stars = ("★" * int(score) + "☆" * (5 - int(score))) if isinstance(score, int) and 0 < score <= 5 else ""
            fig = next(iter(sorted((p.dir / "figures").glob("fig*.png"))), None) if (p.dir / "figures").exists() else None
            thumb = (f'<img class="thumb" src="papers/{E(p.slug)}/figures/{E(fig.name)}" alt="" loading="lazy">' if fig else '<div class="thumb none">📄</div>')
            tags = "".join(f'<span class="chip">{E(lbl.split(" · ", 1)[0] if k.startswith("cl:") else lbl.split(" · ", 1)[1])}</span>' for k, lbl in gs[:3])
            n_rel = len({r.get("slug") for r in self.related.get(p.slug, []) if (self.ws.papers / str(r.get("slug", ""))).is_dir()}
                        | {e["b"] if e["a"] == p.slug else e["a"] for e in self.G["edges"] if p.slug in (e["a"], e["b"])})
            rbadge = (f'<span class="badge ok">🔗 관련 논문 {n_rel}편</span>' if n_rel else '<span class="badge none">관련 논문 없음</span>')
            hay = unicodedata.normalize("NFC", " ".join([p.title, au, ", ".join(map(str, authors)), str(p.fm.get("essence") or ""), str(p.fm.get("category") or "")])).lower()
            fig_html = (f'<div class="paper-fig"><img src="papers/{E(p.slug)}/figures/{E(fig.name)}" alt="" loading="lazy"></div>' if fig else "")
            cards.append(f"""<article class="card paper-card" data-year="{E(str(p.fm.get('year') or ''))}" data-groups="{E('|'.join(k for k, _ in gs), quote=True)}" data-text="{E(hay, quote=True)}">
  <div class="paper-header"><span class="paper-num">#{len(cards) + 1} · {E(str(p.fm.get('category') or '분류 없음'))}</span>{f'<span class="paper-score" title="종합 점수">{score}/5</span>' if stars else ''}</div>
  <h3><a href="papers/{E(p.slug)}/index.html">{E(p.title)}</a></h3>
  <p class="meta">{E(au)} · {E(str(p.fm.get('date') or p.fm.get('year') or ''))}{f' · <span class="stars">{stars}</span>' if stars else ''}</p>
  <div class="section"><div class="section-label">Essence</div><p class="essence">{E(str(p.fm.get('essence') or ''))}</p></div>
  {fig_html}
  <div class="chips">{rbadge}{tags}</div>
</article>""")
        year_opts = "".join(f'<option value="{E(y)}">{E(y)}</option>' for y in years)
        grp_opts = "".join(f'<option value="{E(k, quote=True)}">{E(v)}</option>' for k, v in sorted(groups.items(), key=lambda kv: kv[1]))
        topics_html = "".join(f'<li><a href="topics/{E(t["stem"])}.html">{E(t["title"])}</a> <span class="muted">논문 {len(t["papers"])}편</span></li>' for t in self.topics) \
            or '<li class="muted">아직 주제 노트가 없어요. Codex에게 <code>$wiki-synthesize 주제탐색 &lt;분야&gt;</code>라고 말해 보세요.</li>'
        cl_html = ""
        if self.clusters:
            rows = []
            for c in self.clusters:
                links = ", ".join(f'<a href="papers/{E(x["slug"])}/index.html">{E(x["slug"])}</a>' for x in c.get("papers", []))
                rows.append(f'<li><b>군집 {c["cluster"]}</b> <span class="muted">({E(", ".join(c.get("top_terms", [])[:5]))})</span><br>{links}</li>')
            cl_html = f'<h3>자동 군집 <span class="muted small">(어휘가 비슷한 논문끼리 — 이름은 직접 붙여 보세요)</span></h3><ul class="plain">{"".join(rows)}</ul>'
        dt = getattr(self, "draft_titles", {})
        drafts_html = "".join(f'<li><a href="drafts/{E(f.stem)}.html">{E(dt.get(f.stem, f.stem))}</a> <span class="muted small">{E(f.name)}</span></li>' for f in self.drafts[:6]) or '<li class="muted">아직 초안이 없어요.</li>'
        empty = "" if self.papers else '<p class="empty">아직 위키에 논문이 없어요. Codex 채팅에 <code>$wiki-ingest 최근 1편</code> 이라고 말해 시작하세요.</p>'
        body = f"""<section class="pc-hero">
  <h1>내 논문 위키 — Paper Curation</h1>
  <p class="subtitle">Zotero에서 넣은 논문의 리뷰·그림·관련 논문을 한눈에. 궁금한 점은 <b>💬 Codex에게 물어보기</b>로 채팅에 가져가세요.</p>
  <div class="notice">⚠️ 이 위키의 리뷰·요약은 Codex(생성형 AI)가 내 논문을 읽고 정리한 결과예요. 논문 원문의 저작권은 <b>원저작자</b>에게 있고, 정확한 내용은 원문 페이지에서 확인하세요.</div>
  <div class="stats">
    <div class="stat"><div class="stat-num">{len(self.papers)}</div><div class="stat-label">리뷰 완료</div></div>
    <div class="stat"><div class="stat-num">{len({str(p.fm.get('category') or '분류 없음') for p in self.papers})}</div><div class="stat-label">주제 분류</div></div>
    <div class="stat"><div class="stat-num">{today()}</div><div class="stat-label">큐레이션 일자</div></div>
  </div>
  <div class="hero-links"><a href="network.html">🕸 지식 네트워크</a><a href="drafts/index.html">📝 초안·아이디어</a><a href="#topics">🗂 주제</a></div>
</section>
<section class="search-box js-only-block">
  <input id="home-q" type="search" placeholder="논문 거르기: 제목·저자·요약 (예: 튜터, RCT)" autocomplete="off" aria-label="논문 거르기">
  <div class="search-hint">리뷰 본문·그림 설명까지 찾으려면 맨 위 검색칸(단축키 /)을 쓰세요.</div>
  <div id="home-count" class="search-count"></div>
</section>
<section class="sort-bar filters js-only" aria-label="필터">
  <label>연도 <select id="f-year"><option value="">전체</option>{year_opts}</select></label>
  <label>주제·군집 <select id="f-group"><option value="">전체</option>{grp_opts}</select></label>
  <span id="f-count" class="muted"></span>
</section>
{empty}
<section class="pc-list" id="paper-list">
{''.join(cards)}
</section>
<section class="cols">
  <div class="panel" id="topics"><h2>주제</h2><ul class="plain">{topics_html}</ul>{cl_html}<p><a href="network.html">🕸 지식 네트워크 보기 →</a></p></div>
  <div class="panel"><h2>초안·아이디어</h2><ul class="plain">{drafts_html}</ul><p><a href="drafts/index.html">전체 보기 →</a></p></div>
</section>"""
        self.page(rel, "논문 목록", body, ask="$wiki-query <질문을 여기에> (참고: wiki/index.md)", nav="home", body_class="home")

    def build_paper(self, p) -> None:
        rel = f"papers/{p.slug}/index.html"
        toc: list = []
        body_md = re.sub(r"^#\s+.+\n", "", p.body.lstrip(), count=1)  # 제목은 머리 카드에
        body_md = body_md.replace(RELATED_START, "").replace(RELATED_END, "")
        has_tables = (p.dir / "tables" / "tables.md").exists() or bool(p.meta.get("tables"))
        note = ('<p class="table-hidden muted small">📊 여기 있던 markdown 표는 화면에 보여 주지 않아요(자동 추출 표는 칸이 어긋날 수 있어요). '
                + ('표는 <a href="tables/tables.html">표 목록</a>의 PNG로 보세요.' if has_tables else '표는 원문 PDF에서 확인하세요.') + '</p>')
        content = convert(body_md, self.linker(p.review, rel), toc, table_note=note)
        content = self.cite_links(content, rel)
        fm = p.fm
        authors = _authors(fm.get("authors") or p.meta.get("authors"))
        url = fm.get("url") or p.meta.get("url") or ""
        doi = fm.get("doi") or ""
        links = [f'<a href="source.html">추출 원문(페이지별)</a>']
        if (p.dir / "figures" / "figures.md").exists():
            links.append('<a href="figures/figures.html">그림 목록</a>')
        if (p.dir / "tables" / "tables.md").exists():
            links.append('<a href="tables/tables.html">표 목록</a>')
        if url:
            links.append(f'<a href="{E(str(url), quote=True)}" target="_blank" rel="noopener">논문 사이트 ↗</a>')
        if doi:
            links.append(f'<a href="https://doi.org/{E(str(doi), quote=True)}" target="_blank" rel="noopener">DOI ↗</a>')
        toc_html = "".join(f'<li class="l{lv}"><a href="#{hid}">{E(t)}</a></li>' for lv, hid, t in toc if lv <= 3)
        pages = sorted({int(x) for x in re.findall(re.escape(p.slug) + r"\s*·\s*p\.\s*(\d+)", p.body)})
        pages_html = " ".join(f'<a class="pg" href="source.html#p-{n}">p.{n}</a>' for n in pages) or '<span class="muted">인용한 페이지 없음</span>'
        # 같이 보면 좋은 논문(원본 review_to_html.py 의 connections-box 구성) = related.json + 리뷰 안 근거 링크
        from .site_network import _agent_reasons
        agent = _agent_reasons(self, p.slug)
        items: dict[str, dict] = {}
        for r in self.related.get(p.slug, []):
            sl = str(r.get("slug", ""))
            if (self.ws.papers / sl).is_dir() and sl not in items:
                items[sl] = {"title": r.get("title") or sl, "rows": [(str(r.get("relation") or "alternative"),
                             REL_LABEL.get(r.get("relation"), "🔄 관련"), str(r.get("reason", "")))]}
        for e in self.G["edges"]:  # 리뷰 안 근거 링크로만 이어진 논문도
            other = e["b"] if e["a"] == p.slug else e["a"] if e["b"] == p.slug else None
            if other:
                items.setdefault(other, {"title": self.G["papers"][other].title, "rows": []})
        for sl, it in items.items():
            if sl in agent:
                it["rows"].append(("review", "📝 리뷰 근거", agent[sl]))
        n_rel = len(items)
        conn_html = "".join(
            f'<div class="conn-item {E(it["rows"][0][0] if it["rows"] else "review")}"><div class="conn-title"><a href="../{E(sl)}/index.html">{E(it["title"])}</a></div>'
            + "".join(f'<div class="conn-reason"><span class="conn-rel-badge {E(k)}">{E(lbl)}</span>{E(why)}</div>' for k, lbl, why in it["rows"]) + "</div>"
            for sl, it in items.items()) or '<p class="muted">관련 논문 없음 — 논문을 더 넣으면 연결이 생겨요.</p>'
        badge = (f'<a class="badge ok" href="#related-papers">🔗 관련 논문 {n_rel}편</a>' if n_rel
                 else '<span class="badge none">관련 논문 없음(논문을 더 넣으면 연결이 생겨요)</span>')
        figs = sorted((p.dir / "figures").glob("*.png")) if (p.dir / "figures").exists() else []
        strip = "".join(f'<a href="figures/figures.html"><img src="figures/{E(f.name)}" alt="{E(f.stem)}" loading="lazy"></a>' for f in figs[:8])
        tags = "".join(f'<span class="chip">#{E(str(t))}</span>' for t in (fm.get("tags") or []) if str(t) != "paper")
        score = fm.get("score")
        # 리뷰 본문: h2 마다 흰 상자(section-box), Essence 는 essence-box, Evaluation 점수는 배지, Related Papers 는 connections-box
        parts = re.split(r'(?=<h2 id=")', content)
        boxes = [parts[0]] if parts[0].strip() else []
        for part in parts[1:]:
            m = re.match(r'<h2 id="([^"]+)">(.*?)</h2>', part)
            hid = m.group(1) if m else ""
            if hid == "essence":
                boxes.append(f'<div class="essence-box" id="sec-{hid}">{part}</div>')
            elif hid == "evaluation":
                part = re.sub(r"<ul>((?:<li>[^<]*?:\s*\d(?:\.\d)?/5</li>)+)</ul>",
                              lambda mm: '<div class="eval-badges">' + re.sub(r"<li>(.*?)</li>", r'<span class="eval-badge">\1</span>', mm.group(1)) + "</div>", part, count=1)
                boxes.append(f'<div class="section-box" id="sec-{hid}">{part}</div>')
            elif hid == "related-papers":
                k = part.find("<h3")
                agent_part = part[k:] if k >= 0 else ""
                boxes.append(f'<div class="connections-box" id="sec-{hid}"><h2 id="related-papers">같이 보면 좋은 논문 <span class="muted small">({n_rel}편)</span></h2>{conn_html}'
                             f'<p class="muted small">자동 계산(llmwiki related: 어휘 유사도·저자·연도) + 리뷰에 근거와 함께 적은 연결 · <a href="../../network.html">🕸 네트워크에서 보기</a></p>{agent_part}</div>')
            else:
                boxes.append(f'<div class="section-box" id="sec-{hid}">{part}</div>')
        if not any('id="sec-related-papers"' in b for b in boxes):
            boxes.append(f'<div class="connections-box"><h2 id="related-papers">같이 보면 좋은 논문</h2>{conn_html}</div>')
        ask = f"$wiki-query <질문을 여기에> (참고: wiki/papers/{p.slug}/review.md)"
        head = f"""<p class="crumb"><a href="../../index.html">논문 목록</a> › {E(str(fm.get('category') or '분류 없음'))}</p>
<h1 class="pc-title">{E(p.title)}</h1>
<div class="dl-bar"><button class="dl-btn ask-inline" type="button" data-ask="{E(ask, quote=True)}">💬 Codex에게 물어보기</button>
<a class="dl-btn ghost" href="../../network.html">🕸 네트워크에서 보기</a> {badge}</div>
<span class="dl-note">질문 문장이 복사돼요 → Codex 채팅에 붙여넣고 &lt;질문을 여기에&gt;만 바꾸세요. (API 키 필요 없음)</span>
<blockquote class="pc-authors"><b>저자</b>: {E(', '.join(map(str, authors)) or '(저자 확인 필요)')} | <b>날짜</b>: {E(str(fm.get('date') or fm.get('year') or ''))}{(' | <b>학회·저널</b>: ' + E(str(fm.get('venue')))) if fm.get('venue') else ''}{f' | <b>종합</b>: {score}/5' if score else ''}<br>{' · '.join(links)}</blockquote>
<div class="ai-notice">⚠️ 이 페이지의 요약·평가·해설은 <b>Codex(생성형 AI)</b>가 내 위키에 정리한 2차 분석이에요. 논문 원문의 저작권은 <b>원저작자</b>에게 있고, 정확한 내용은 원문 페이지(아래 p.번호)에서 확인하세요.</div>
<div class="section-box"><h2>목차</h2><ul class="pc-toc">{toc_html}</ul>
<p class="small" style="margin-top:.6rem"><b>원문 페이지</b> <span class="muted">(리뷰가 인용한 곳)</span> {pages_html}</p>
{f'<div class="strip">{strip}</div>' if strip else ''}<div class="chips">{tags}</div>
<p class="muted small">위키 파일: <code>wiki/papers/{E(p.slug)}/review.md</code></p></div>"""
        body = head + f'<article class="md review pc-review">{"".join(boxes)}</article><div class="back"><a href="../../index.html">← 논문 목록으로</a></div>'
        self.page(rel, p.title, body, ask=f"$wiki-query <질문을 여기에> (참고: wiki/papers/{p.slug}/review.md)", body_class="paper")
        # 검색 색인: 논문 1개 + 섹션별
        self.index.append({"k": "논문", "t": p.title, "u": rel, "a": ", ".join(map(str, authors)), "y": str(fm.get("year") or ""),
                           "x": " ".join([str(fm.get("essence") or ""), str(fm.get("category") or ""), " ".join(map(str, fm.get("tags") or []))])})
        for lv, hid, t in toc:
            if lv != 2:
                continue
            sec = re.search(r"^##\s+" + re.escape(t) + r"\s*$(.*?)(?=^##\s|\Z)", body_md, re.M | re.S)
            if sec:
                txt = _plain(sec.group(1))
                if txt:
                    self.index.append({"k": "리뷰", "t": f"{p.title} › {t}", "u": f"{rel}#{hid}", "x": txt[:6000]})
        # 원문·그림·표 페이지
        src = p.dir / "source.md"
        if src.exists():
            self.build_source(p, src)
        for sub in ("figures", "tables"):
            d = p.dir / sub
            if not d.exists():
                continue
            for f in sorted(d.iterdir()):
                if f.suffix.lower() in IMG_EXT:
                    self.copy(f, f"papers/{p.slug}/{sub}/{f.name}")
                elif f.suffix == ".md" and f.name in ("figures.md", "tables.md"):  # 예전 tableN.md(markdown 표)는 화면에 만들지 않음
                    orel = f"papers/{p.slug}/{sub}/{f.stem}.html"
                    toc2: list = []
                    md = read_text(f)
                    if f.name == "tables.md" and p.meta.get("tables"):
                        md = tables_listing(p.meta)  # 표 화면은 meta.json으로 다시 만든다: PNG + 캡션만(예전 tables.md의 markdown 링크·표는 안 보임, 파일은 그대로)
                    self.page(orel, f"{p.title} — {f.stem}", f'<p class="crumb"><a href="../index.html">← 리뷰로</a></p><article class="md">'
                              + convert(md, self.linker(f, orel), toc2, table_note="") + "</article>",
                              ask=f"$wiki-query <질문을 여기에> (참고: wiki/papers/{p.slug}/{sub}/{f.name})", body_class="figs")
                    if f.name == "figures.md":
                        for m in re.finditer(r"^##\s+(Figure\s+\d+)[^\n]*\n(.*?)(?=^##\s|\Z)", md, re.M | re.S):
                            cap = _plain(m.group(2))
                            self.index.append({"k": "그림", "t": f"{p.title} › {m.group(1)}", "u": f"{orel}#{slug_id(m.group(0).splitlines()[0][3:])}", "x": cap[:1500]})
                    if f.name == "tables.md":  # 표: 캡션 + 화면에 안 보이는 검색용 표 글자
                        for t in p.meta.get("tables") or []:
                            head = f"Table {t['n']} (p.{t['page']})" + (" ⚠️ 자동 크롭 신뢰도 낮음 — PNG 확인" if str(t.get("method", "")).startswith("fallback") else "")
                            self.index.append({"k": "표", "t": f"{p.title} › Table {t['n']}", "u": f"{orel}#{slug_id(head)}",
                                               "x": unicodedata.normalize("NFKC", str(t.get("caption") or "") + " " + table_search_text(p.dir, t).replace("\n", " · "))[:3000]})

    def build_source(self, p, src: Path) -> None:
        rel = f"papers/{p.slug}/source.html"
        text = read_text(src)
        parts = re.split(r"<!--\s*p\.(\d+)\s*-->", text)
        secs = []
        nav = []
        for i in range(1, len(parts), 2):
            n = parts[i]
            chunk = re.sub(r"<!--.*?-->", "", parts[i + 1], flags=re.S).strip()
            nav.append(f'<a href="#p-{n}">{n}</a>')
            secs.append(f'<section class="srcpage" id="p-{n}"><h3>p.{n}</h3><div class="srctext">{E(chunk)}</div></section>')
        body = (f'<p class="crumb"><a href="index.html">← 리뷰로</a> · {E(p.title)}</p>'
                f'<h1>추출 원문 <span class="muted small">(검색·인용 확인용 · 원문 PDF 캡처 · 로컬 연구용)</span></h1>'
                f'<p class="pagenav">페이지: {" ".join(nav)}</p>' + "".join(secs))
        self.page(rel, f"{p.title} — 원문", body, ask=f"$wiki-query <질문을 여기에> (참고: wiki/papers/{p.slug}/source.md)", body_class="source")

    def build_topics(self) -> None:
        for t in self.topics:
            rel = f"topics/{t['stem']}.html"
            content = self.cite_links(convert(t["body"], self.linker(t["file"], rel)), rel)
            content += self.topic_members_html(t["stem"])
            self.page(rel, t["title"], f'<p class="crumb"><a href="../index.html#topics">← 주제</a> · <a href="../network.html">네트워크</a></p><article class="md">{content}</article>',
                      ask=f"$wiki-query <질문을 여기에> (참고: wiki/topics/{t['stem']}.md)", nav="topics")
            self.index.append({"k": "주제", "t": t["title"], "u": rel, "x": _plain(t["body"])[:4000]})

    def topic_members_html(self, stem: str) -> str:
        from .sitegraph import shared_between_notes
        G = self.G
        mem = G["notes"].get(stem, {}).get("papers", [])
        li = "".join(f'<li><span class="dot" style="background:{G["color"][G["group_of"][s]]}"></span>'
                     f'<a href="../papers/{E(s)}/index.html">{E(G["papers"][s].title)}</a> <span class="muted small">{E(G["group_of"][s])}</span></li>' for s in mem)
        sh = shared_between_notes(G, stem)
        sh_html = "".join(f'<li><a href="../papers/{E(s)}/index.html">{E(G["papers"][s].title)}</a> — 함께 있는 주제: '
                          + ", ".join(f'<a href="{E(o)}.html">{E(G["notes"][o]["title"])}</a>' for o in os_) + "</li>" for s, os_ in sh)
        inner = [s2 for s2 in G["edges"] if s2["a"] in mem and s2["b"] in mem]
        return (f'<h2 id="topic-papers">이 주제의 논문 ({len(mem)}편)</h2><ul class="plain">{li or "<li class=muted>링크된 논문 없음</li>"}</ul>'
                f'<h2 id="topic-shared">다른 주제와 겹치는 논문</h2><ul class="plain">{sh_html or "<li class=muted>없음 — 다른 주제 노트와 겹치는 논문이 아직 없어요.</li>"}</ul>'
                f'<p class="muted small">이 주제 안의 연결 {len(inner)}개 · <a href="../network.html">지식 네트워크에서 보기</a></p>')

    def build_network(self) -> None:
        from .sitegraph import cross_links, svg
        G = self.G
        rel = "network.html"
        legend = "".join(f'<li><span class="dot" style="background:{G["color"][g]}"></span>{E(g)} <span class="muted">({len(G["groups"][g])}편)</span></li>' for g in G["gnames"])
        graph = svg(G, self.pos, lambda s: f"papers/{s}/index.html") if self.pos else '<p class="empty">아직 논문이 없어요.</p>'
        groups_html = "".join(
            f'<div class="box"><h4><span class="dot" style="background:{G["color"][g]}"></span>{E(g)}</h4><ul class="plain small">'
            + "".join(f'<li><a href="papers/{E(s)}/index.html">{E(G["papers"][s].title)}</a></li>' for s in sorted(G["groups"][g])) + "</ul></div>"
            for g in G["gnames"])
        cl = cross_links(G)
        cross_html = "".join(f'<li><b>{E(x["a"])}</b> ↔ <b>{E(x["b"])}</b> — 연결 {len(x["edges"])}개: '
                             + ", ".join(f'<a href="papers/{E(e["a"])}/index.html">{E(G["papers"][e["a"]].title[:40])}</a> ↔ '
                                         f'<a href="papers/{E(e["b"])}/index.html">{E(G["papers"][e["b"]].title[:40])}</a>' for e in x["edges"][:4]) + "</li>" for x in cl)
        notes_html = "".join(f'<li><a href="topics/{E(k)}.html">{E(v["title"])}</a> <span class="muted small">논문 {len(v["papers"])}편</span></li>' for k, v in G["notes"].items())
        from . import site_network
        data = site_network.build_data(self, G)
        self.write("network-data.js", unicodedata.normalize("NFC", site_network.data_js(data)))
        extra = f"""<h3>주제 사이 연결</h3><ul class="plain">{cross_html or '<li class="muted">아직 주제 사이 연결이 없어요.</li>'}</ul>
<h3>주제 노트</h3><ul class="plain">{notes_html or '<li class="muted">아직 주제 노트가 없어요.</li>'}</ul>
<h3>주제별 논문</h3><div class="stack">{groups_html}</div>"""
        body = site_network.body_html(data, graph, legend, extra, CREDIT)
        self.page(rel, "지식 네트워크", body, ask="$wiki-query 내 위키 논문들은 서로 어떻게 연결돼 있어? 연결이 약한 주제 사이에서 연구 아이디어를 찾아 줘",
                  nav="network", body_class="network", bare=True, head_extra='\n<link rel="stylesheet" href="assets/network.css">',
                  scripts_extra='\n<script src="assets/d3.v7.min.js"></script>\n<script src="network-data.js"></script>\n<script src="assets/network.js"></script>')

    def build_drafts(self) -> None:
        rows = []
        self.draft_titles: dict[str, str] = {}
        for f in self.drafts:
            rel = f"drafts/{f.stem}.html"
            fm, body, _ = split_frontmatter(read_text(f))
            content = self.cite_links(convert(body, self.linker(f, rel)), rel)
            h1 = re.search(r"^#\s+(.+)$", body, re.M)
            title = (fm or {}).get("title") or (h1.group(1) if h1 else f.stem)
            self.page(rel, str(title), f'<p class="crumb"><a href="index.html">← 초안·아이디어</a> · <code>drafts/{E(f.name)}</code></p><article class="md">{content}</article>',
                      ask=f"$wiki-query <질문을 여기에> (참고: drafts/{f.name})", nav="drafts")
            import datetime as _dt
            when = _dt.datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            rows.append(f'<li><a href="{E(f.stem)}.html"><b>{E(str(title))}</b></a> <span class="muted small">drafts/{E(f.name)} · {when}</span></li>')
            self.index.append({"k": "초안", "t": str(title), "u": rel, "x": _plain(body)[:4000]})
            self.draft_titles[f.stem] = str(title)
        # projects/<주제>/**/*.md — 주제별 묶음 (README·hwp·xlsx 등 md가 아닌 파일은 제외)
        groups: dict[str, list[str]] = {}
        for f in self.projects:
            relp = unicodedata.normalize("NFC", f.relative_to(self.ws.projects).as_posix())
            topic = relp.split("/", 1)[0]
            rel = "projects/" + relp[:-3] + ".html"
            fm, body, _ = split_frontmatter(read_text(f))
            content = self.cite_links(convert(body, self.linker(f, rel)), rel)
            h1 = re.search(r"^#\s+(.+)$", body, re.M)
            title = str((fm or {}).get("title") or (h1.group(1) if h1 else f.stem))
            back = _href(self.rel(rel, "drafts/index.html"))
            self.page(rel, title, f'<p class="crumb"><a href="{back}">← 초안·아이디어</a> · <code>projects/{E(relp)}</code></p><article class="md">{content}</article>',
                      ask=f"$wiki-query <질문을 여기에> (참고: projects/{relp})", nav="drafts")
            import datetime as _dt
            when = _dt.datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            groups.setdefault(topic, []).append(f'<li><a href="{E(_href(self.rel("drafts/index.html", rel)))}"><b>{E(title)}</b></a> <span class="muted small">projects/{E(relp)} · {when}</span></li>')
            self.index.append({"k": "주제 폴더", "t": title, "u": _href(rel), "x": _plain(body)[:4000]})
        proj_html = "".join(f'<h3>📁 {E(t)}</h3><ul class="plain drafts">{"".join(v)}</ul>' for t, v in groups.items())
        body = ('<h1>초안·아이디어 <span class="muted small">(drafts/ 폴더)</span></h1>'
                '<p>Codex가 <code>$wiki-synthesize</code>로 만든 서론·아이디어 결합·공통 한계 문서와 내가 쓴 글이 여기 모여요.</p>'
                f'<ul class="plain drafts">{"".join(rows) or "<li class=muted>아직 초안이 없어요.</li>"}</ul>'
                '<h2>주제 폴더 <span class="muted small">(projects/ 폴더의 .md)</span></h2>'
                + (proj_html or '<p class="muted">아직 주제 폴더 글이 없어요. 요청 끝에 「결과는 projects/&lt;주제이름&gt;/ 에 저장해 주세요」라고 하면 여기에 모여요.</p>'))
        self.page("drafts/index.html", "초안·아이디어", body, ask="$wiki-synthesize <서론|결합|공통한계> <주제를 여기에>", nav="drafts")

    def build_log(self) -> None:
        if self.ws.log.exists():
            content = convert(read_text(self.ws.log), self.linker(self.ws.log, "log.html"))
        else:
            content = '<p class="muted">기록이 없어요.</p>'
        self.page("log.html", "작업 기록", f'<article class="md">{content}</article>', ask="$wiki-query <질문을 여기에> (참고: wiki/log.md)", nav="log")

    def assets(self) -> None:
        for name in ("style.css", "pc.css", "app.js", "network.css", "network.js", "d3.v7.min.js", "d3-LICENSE.txt"):
            self.write(f"assets/{name}", (ASSET_DIR / name).read_text(encoding="utf-8"))
        # 한글 제목이 NFD(맥에서 온 파일 등)여도 검색되게 NFC로 맞춘다(H51)
        data = unicodedata.normalize("NFC", json.dumps(self.index, ensure_ascii=False, separators=(",", ":")))
        self.write("search-index.json", data)
        self.write("search-index.js", "window.LLMWIKI_INDEX=" + data.replace("</", "<\\/") + ";\n")

    def prune(self) -> int:
        n = 0
        for p in sorted(self.out.rglob("*"), reverse=True):
            if p.is_file() and p.resolve() not in self.written:
                p.unlink()
                n += 1
            elif p.is_dir() and not any(p.iterdir()):
                p.rmdir()
        return n

    def run(self) -> dict[str, Any]:
        self.out.mkdir(parents=True, exist_ok=True)
        self.load()
        for p in self.papers:
            self.build_paper(p)
        self.build_topics()
        self.build_drafts()
        self.build_log()
        self.build_network()
        self.build_home()
        self.assets()
        removed = self.prune()
        return {"site": self.ws.rel(self.out / "index.html"), "papers": len(self.papers), "topics": len(self.topics),
                "drafts": len(self.drafts), "projects": len(self.projects), "clusters": len(self.clusters), "search_items": len(self.index),
                "removed_old_files": removed, "file_url": (self.out / "index.html").resolve().as_uri(), "index_path": str((self.out / "index.html").resolve())}


def _plain(md: str) -> str:
    t = re.sub(r"<!--.*?-->", " ", md, flags=re.S)
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", t)
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"[#>*`|_]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def build(ws: Workspace) -> dict[str, Any]:
    return Builder(ws).run()


def summary_lines(res: dict[str, Any]) -> list[str]:
    return [f"위키 화면 파일을 만들었어요 ✅ 논문 {res['papers']}편 · 주제 {res['topics']}개 · 초안 {res['drafts']}개 · 검색 항목 {res['search_items']}개",
            f"열기: 이 파일을 브라우저로 여세요 → {res['file_url']}",
            f"  (폴더 경로: {res.get('index_path') or res['file_url']})",
            "이미 열어 둔 화면이면 브라우저에서 새로고침(F5 / Cmd+R) 하세요.",
            "(선택) 주소로 보기: llmwiki serve → http://127.0.0.1:8765/"]


def open_in_browser(url: str, path: Path | None = None) -> bool:
    """기본 브라우저로 열기. LLMWIKI_NO_BROWSER=1 이거나 화면 없는 Linux면 열지 않는다(터미널용 브라우저가 멈추는 일 방지)."""
    import subprocess
    import sys
    if os.environ.get("LLMWIKI_NO_BROWSER") == "1":
        return False
    try:
        if os.name == "nt":
            os.startfile(str(path) if path else url)  # type: ignore[attr-defined]  # noqa: S606
            return True
        if sys.platform == "darwin":
            return subprocess.run(["open", str(path) if path else url], capture_output=True, timeout=15).returncode == 0
        if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
            return False
        import webbrowser
        return bool(webbrowser.open(url))
    except Exception:  # noqa: BLE001
        return False


def try_rebuild(ws: Workspace, only_if_exists: bool = True) -> str:
    """ingest·finish·synthesize 뒤 가벼운 자동 갱신. 실패해도 예외를 내지 않고 한 줄 설명을 돌려준다."""
    if only_if_exists and not (site_dir(ws) / "index.html").exists():
        return ""
    try:
        r = build(ws)
        return f"site/ 갱신 (논문 {r['papers']}편) → 브라우저에서 새로고침(F5 / Cmd+R) 하세요"
    except Exception as e:  # noqa: BLE001
        return f"화면 갱신 실패(무시해도 됨): {type(e).__name__}: {e}"
