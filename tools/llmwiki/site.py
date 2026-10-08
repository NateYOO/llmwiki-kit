"""`llmwiki site` — wiki/·drafts/를 브라우저로 보는 정적 HTML(site/)로 만든다 (표준 라이브러리 + 기존 의존성만).
- 상대 링크만 쓴다 → site/index.html을 file://로 열어도 JS 없이 링크로 다닐 수 있다.
- 검색·필터·「Codex에게 물어보기」 복사 버튼은 JS(외부 라이브러리 없음). 검색 색인은 search-index.json + search-index.js.
- 디자인·코드는 새로 작성(Paper Curation 코드·CSS 복사 없음). 하단에 아이디어 출처 표기."""
from __future__ import annotations

import html
import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

from .mdhtml import convert, slug_id
from .util import RELATED_END, RELATED_START, Workspace, read_text, split_frontmatter, today

CREDIT = ('이제현 박사님 Paper Curation 아이디어 기반 · '
          '<a href="https://github.com/jehyunlee/paper-curation" target="_blank" rel="noopener">https://github.com/jehyunlee/paper-curation</a>')
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
        elif not rel.startswith("drafts/"):
            return None
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
            target = (src.parent / path)
            sr = self.ws_to_site(target)
            if sr is None:
                return url
            if frag and sr.endswith(".html"):
                frag = slug_id(frag) if not re.fullmatch(r"p-?\d+", frag) else frag
            return self.rel(out_rel, sr) + (f"#{frag}" if frag else "")
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
    def page(self, rel: str, title: str, body: str, *, ask: str, nav: str = "", body_class: str = "") -> None:
        root = self.root_of(rel)
        navs = [("index.html", "논문 목록", "home"), ("network.html", "네트워크", "network"), ("index.html#topics", "주제", "topics"),
                ("drafts/index.html", "초안·아이디어", "drafts"), ("log.html", "작업 기록", "log")]
        nav_html = "".join(f'<a href="{root}{h}"{" class=\"on\"" if k == nav else ""}>{E(t)}</a>' for h, t, k in navs)
        doc = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)} · 내 논문 위키</title>
<link rel="stylesheet" href="{root}assets/style.css">
<script>document.documentElement.classList.add('js');</script>
</head>
<body class="{body_class}" data-root="{root}">
<header class="top">
  <div class="top-in">
    <a class="brand" href="{root}index.html"><span class="logo">📚</span><span><b>내 논문 위키</b><small>나만의 지식 파트너</small></span></a>
    <nav class="nav">{nav_html}</nav>
    <div class="search js-only">
      <input id="q" type="search" placeholder="검색: 제목·저자·리뷰·그림 설명" autocomplete="off" aria-label="위키 검색">
      <div id="results" class="results" hidden></div>
    </div>
    <button class="ask js-only" type="button" data-ask="{E(ask, quote=True)}" title="Codex 채팅에 붙여넣을 문장을 복사합니다">💬 Codex에게 물어보기</button>
  </div>
</header>
<main class="wrap">
{body}
</main>
<footer class="foot">
  <div>{CREDIT}</div>
  <div class="muted">Karpathy LLM Wiki 방식 · <code>llmwiki site</code>로 만든 화면 ({today()}) · 위키 원본은 <code>wiki/</code> 폴더의 마크다운</div>
  <noscript><div class="muted">JS가 꺼져 있어 검색·복사 버튼은 숨겼어요. 링크로는 모두 볼 수 있어요. Codex에 물어볼 때: <code>{E(ask)}</code></div></noscript>
</footer>
<div id="toast" class="toast" role="status" aria-live="polite" hidden></div>
<div id="copybox" class="copybox" hidden><div class="copybox-in"><p>자동 복사가 막혔어요. 아래 글이 선택된 상태예요 — <b>Ctrl+C</b>(맥: ⌘+C)를 누른 뒤 Codex 채팅에 붙여넣으세요.</p><textarea readonly rows="3"></textarea><button type="button" class="close">닫기</button></div></div>
<script src="{root}search-index.js"></script>
<script src="{root}assets/app.js"></script>
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
            authors = p.fm.get("authors") or p.meta.get("authors") or []
            au = ", ".join(map(str, authors[:3])) + (" 외" if len(authors) > 3 else "")
            score = p.fm.get("score")
            stars = ("★" * int(score) + "☆" * (5 - int(score))) if isinstance(score, int) and 0 < score <= 5 else ""
            fig = next(iter(sorted((p.dir / "figures").glob("fig*.png"))), None) if (p.dir / "figures").exists() else None
            thumb = (f'<img class="thumb" src="papers/{E(p.slug)}/figures/{E(fig.name)}" alt="" loading="lazy">' if fig else '<div class="thumb none">📄</div>')
            tags = "".join(f'<span class="chip">{E(lbl.split(" · ", 1)[0] if k.startswith("cl:") else lbl.split(" · ", 1)[1])}</span>' for k, lbl in gs[:3])
            cards.append(f"""<article class="card" data-year="{E(str(p.fm.get('year') or ''))}" data-groups="{E('|'.join(k for k, _ in gs), quote=True)}">
  <a class="card-link" href="papers/{E(p.slug)}/index.html">{thumb}
  <div class="card-body"><h3>{E(p.title)}</h3>
  <p class="meta">{E(str(p.fm.get('year') or ''))} · {E(au)} {f'<span class="stars" title="종합 점수">{stars}</span>' if stars else ''}</p>
  <p class="essence">{E(str(p.fm.get('essence') or ''))}</p>
  <div class="chips">{tags}</div></div></a>
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
        body = f"""<section class="hero">
  <h1>내 논문 위키</h1>
  <p>Zotero에서 넣은 논문 <b>{len(self.papers)}편</b>의 리뷰·그림·관련 논문을 한눈에. 자세히 보고 싶은 논문을 누르고, 궁금한 점은 <b>💬 Codex에게 물어보기</b>로 채팅에 가져가세요.</p>
</section>
<section class="filters js-only" aria-label="필터">
  <label>연도 <select id="f-year"><option value="">전체</option>{year_opts}</select></label>
  <label>주제·군집 <select id="f-group"><option value="">전체</option>{grp_opts}</select></label>
  <span id="f-count" class="muted"></span>
</section>
{empty}
<section class="grid" id="paper-list">
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
        content = convert(body_md, self.linker(p.review, rel), toc)
        content = self.cite_links(content, rel)
        fm = p.fm
        authors = fm.get("authors") or p.meta.get("authors") or []
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
        rel_rows, seen = [], set()
        for r in self.related.get(p.slug, []):
            if (self.ws.papers / r.get("slug", "")).is_dir() and r["slug"] not in seen:
                seen.add(r["slug"])
                rel_rows.append(f'<li><a href="../{E(r["slug"])}/index.html">{E(r.get("title") or r["slug"])}</a>'
                                f'<span class="muted small"> {E(REL_LABEL.get(r.get("relation"), ""))} · {E(str(r.get("reason", "")))}</span></li>')
        for e in self.G["edges"]:  # 리뷰 안 근거 링크로만 이어진 논문도
            other = e["b"] if e["a"] == p.slug else e["a"] if e["b"] == p.slug else None
            if other and other not in seen:
                seen.add(other)
                rel_rows.append(f'<li><a href="../{E(other)}/index.html">{E(self.G["papers"][other].title)}</a><span class="muted small"> · 리뷰 안 링크</span></li>')
        n_rel = len(rel_rows)
        rel_html = "".join(rel_rows) or '<li class="muted">관련 논문 없음 — 논문을 더 넣으면 연결이 생겨요.</li>'
        badge = (f'<a class="badge ok" href="#related-papers">🔗 관련 논문 {n_rel}편</a>' if n_rel
                 else '<span class="badge none">관련 논문 없음(논문을 더 넣으면 연결이 생겨요)</span>')
        figs = sorted((p.dir / "figures").glob("*.png")) if (p.dir / "figures").exists() else []
        strip = "".join(f'<a href="figures/figures.html"><img src="figures/{E(f.name)}" alt="{E(f.stem)}" loading="lazy"></a>' for f in figs[:8])
        tags = "".join(f'<span class="chip">#{E(str(t))}</span>' for t in (fm.get("tags") or []) if str(t) != "paper")
        score = fm.get("score")
        head = f"""<section class="paper-head">
  <p class="crumb"><a href="../../index.html">논문 목록</a> › {E(str(fm.get('category') or '분류 없음'))}</p>
  <h1>{E(p.title)}</h1>
  <p class="meta">{E(', '.join(map(str, authors)))} · {E(str(fm.get('year') or ''))}{(' · ' + E(str(fm.get('venue')))) if fm.get('venue') else ''}{f' · 종합 {score}/5' if score else ''}</p>
  <div class="chips">{badge} {tags}</div>
  <p class="links">{' · '.join(links)} · <a href="../../network.html">네트워크에서 보기</a></p>
  {f'<div class="strip">{strip}</div>' if strip else ''}
</section>"""
        side = f"""<aside class="side">
  <div class="box"><h4>목차</h4><ul class="toc">{toc_html}</ul></div>
  <div class="box"><h4>원문 페이지 <span class="muted small">(리뷰가 인용한 곳)</span></h4><p class="pages">{pages_html}</p></div>
  <div class="box"><h4>관련 논문 {f"{n_rel}편" if n_rel else "없음"}</h4><ul class="plain small">{rel_html}</ul></div>
  <div class="box small muted">위키 파일: <code>wiki/papers/{E(p.slug)}/review.md</code></div>
</aside>"""
        body = head + f'<div class="paper-layout">{side}<article class="md review">{content}</article></div>'
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
                elif f.suffix == ".md":
                    orel = f"papers/{p.slug}/{sub}/{f.stem}.html"
                    toc2: list = []
                    md = read_text(f)
                    self.page(orel, f"{p.title} — {f.stem}", f'<p class="crumb"><a href="../index.html">← 리뷰로</a></p><article class="md">'
                              + convert(md, self.linker(f, orel), toc2) + "</article>",
                              ask=f"$wiki-query <질문을 여기에> (참고: wiki/papers/{p.slug}/{sub}/{f.name})", body_class="figs")
                    if f.name == "figures.md":
                        for m in re.finditer(r"^##\s+(Figure\s+\d+)[^\n]*\n(.*?)(?=^##\s|\Z)", md, re.M | re.S):
                            cap = _plain(m.group(2))
                            self.index.append({"k": "그림", "t": f"{p.title} › {m.group(1)}", "u": f"{orel}#{slug_id(m.group(0).splitlines()[0][3:])}", "x": cap[:1500]})

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
        body = f"""<section class="hero"><h1>지식 네트워크</h1>
<p>점 하나가 논문 한 편이에요. <b>색</b>은 주제(분류), <b>선 굵기</b>는 얼마나 관련 있는지(어휘 유사도), 진한 선은 리뷰에 근거와 함께 이어 둔 연결이에요. 점을 누르면 그 논문 페이지로 가요.</p></section>
<div class="net-wrap"><div class="net-box">{graph}</div>
<aside class="box legend"><h4>주제(분류)</h4><ul class="plain">{legend}</ul>
<p class="muted small">논문 {len(G["papers"])}편 · 연결 {len(G["edges"])}개<br>선이 굵을수록 더 관련 있음<br>점이 클수록 연결이 많음</p></aside></div>
<section class="cols">
<div class="panel"><h2>주제 사이 연결</h2><ul class="plain">{cross_html or '<li class="muted">아직 주제 사이 연결이 없어요.</li>'}</ul>
<h3>주제 노트</h3><ul class="plain">{notes_html or '<li class="muted">아직 주제 노트가 없어요.</li>'}</ul></div>
<div class="panel"><h2>주제별 논문</h2><div class="stack">{groups_html}</div></div>
</section>"""
        self.page(rel, "지식 네트워크", body, ask="$wiki-query 내 위키 논문들은 서로 어떻게 연결돼 있어? 연결이 약한 주제 사이에서 연구 아이디어를 찾아 줘", nav="network", body_class="network")

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
        body = ('<h1>초안·아이디어 <span class="muted small">(drafts/ 폴더)</span></h1>'
                '<p>Codex가 <code>$wiki-synthesize</code>로 만든 서론·아이디어 결합·공통 한계 문서와 내가 쓴 글이 여기 모여요.</p>'
                f'<ul class="plain drafts">{"".join(rows) or "<li class=muted>아직 초안이 없어요.</li>"}</ul>')
        self.page("drafts/index.html", "초안·아이디어", body, ask="$wiki-synthesize <서론|결합|공통한계> <주제를 여기에>", nav="drafts")

    def build_log(self) -> None:
        if self.ws.log.exists():
            content = convert(read_text(self.ws.log), self.linker(self.ws.log, "log.html"))
        else:
            content = '<p class="muted">기록이 없어요.</p>'
        self.page("log.html", "작업 기록", f'<article class="md">{content}</article>', ask="$wiki-query <질문을 여기에> (참고: wiki/log.md)", nav="log")

    def assets(self) -> None:
        for name in ("style.css", "app.js"):
            self.write(f"assets/{name}", (ASSET_DIR / name).read_text(encoding="utf-8"))
        data = json.dumps(self.index, ensure_ascii=False, separators=(",", ":"))
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
                "drafts": len(self.drafts), "clusters": len(self.clusters), "search_items": len(self.index),
                "removed_old_files": removed, "file_url": (self.out / "index.html").resolve().as_uri()}


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
