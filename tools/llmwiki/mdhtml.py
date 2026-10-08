"""아주 작은 마크다운 → HTML 변환기 (표준 라이브러리만).
지원: 제목(#), 문단, 목록(-, *, 1.; 들여쓰기 한 단계), 표(|), 인용(>), 코드 블록(```), 가로줄(---),
인라인: 이미지·링크·<자동링크>·**굵게**·*기울임*·`코드`. HTML 주석은 지운다. 원문 HTML은 그대로 쓰지 않고 이스케이프한다."""
from __future__ import annotations

import html
import re
from typing import Callable

LinkFn = Callable[[str, bool], str]  # (원래 주소, 이미지인가) → 바뀐 주소

_COMMENT = re.compile(r"<!--.*?-->", re.S)
_FENCE = re.compile(r"^\s*```")
_HEAD = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_HR = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$")
_UL = re.compile(r"^(\s*)[-*+]\s+(.*)$")
_OL = re.compile(r"^(\s*)(\d+)[.)]\s+(.*)$")
_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")


def slug_id(text: str) -> str:
    """제목 → id. 'Limitation & Further Study' → 'limitation-further-study', 한글은 그대로 둔다."""
    t = re.sub(r"<[^>]+>", "", text).strip().lower()
    t = re.sub(r"[^\w가-힣\s-]", "", t)
    return re.sub(r"[\s_]+", "-", t).strip("-") or "section"


def inline(text: str, link: LinkFn | None = None) -> str:
    link = link or (lambda u, img: u)
    codes: list[str] = []

    def keep(s: str) -> str:
        codes.append(s)
        return f"\x00{len(codes) - 1}\x00"

    text = re.sub(r"`([^`]+)`", lambda m: keep(f"<code>{html.escape(m.group(1))}</code>"), text)

    def img(m: re.Match) -> str:
        alt, url = m.group(1), m.group(2)
        return keep(f'<img src="{html.escape(link(url, True), quote=True)}" alt="{html.escape(alt, quote=True)}" loading="lazy">')

    text = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)", img, text)

    def lnk(m: re.Match) -> str:
        label, url = m.group(1), m.group(2)
        new = link(url, False)
        ext = new.startswith(("http://", "https://"))
        attrs = ' target="_blank" rel="noopener"' if ext else ""
        return keep(f'<a href="{html.escape(new, quote=True)}"{attrs}>') + label + keep("</a>")

    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)", lnk, text)
    text = re.sub(r"<(https?://[^>\s]+)>", lambda m: keep(
        f'<a href="{html.escape(m.group(1), quote=True)}" target="_blank" rel="noopener">{html.escape(m.group(1))}</a>'), text)
    text = html.escape(text, quote=False)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)([^*\n]+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", text)
    text = re.sub(r"(?<!\w)_(?!\s)([^_\n]+?)(?<!\s)_(?!\w)", r"<em>\1</em>", text)
    text = re.sub(r"\[근거:([^\]]+)\]", r'<span class="cite">[근거:\1]</span>', text)
    text = text.replace("(가설)", '<span class="hyp">(가설)</span>')
    for _ in range(3):  # 링크 라벨 안의 코드 등 중첩 자리표시자
        text = re.sub(r"\x00(\d+)\x00", lambda m: codes[int(m.group(1))], text)
    return text


def _cells(row: str) -> list[str]:
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|") and not row.endswith("\\|"):
        row = row[:-1]
    return [c.strip() for c in re.split(r"(?<!\\)\|", row)]


def convert(md: str, link: LinkFn | None = None, toc: list | None = None, table_note: str | None = None) -> str:
    """마크다운 문자열 → HTML 조각. toc 리스트를 주면 (level, id, text)를 채운다.
    table_note를 주면 markdown 표(| 로 시작하는 줄 2줄 이상)를 그리지 않고 그 안내(HTML)로 바꾼다(빈 문자열이면 그냥 숨김)."""
    md = _COMMENT.sub("", md.replace("\r\n", "\n"))
    lines = md.split("\n")
    out: list[str] = []
    para: list[str] = []
    used: set[str] = set()
    i = 0

    def flush() -> None:
        if para:
            out.append("<p>" + "<br>\n".join(inline(x, link) for x in para) + "</p>")
            para.clear()

    while i < len(lines):
        line = lines[i]
        if _FENCE.match(line):
            flush()
            lang = line.strip()[3:].strip()
            buf = []
            i += 1
            while i < len(lines) and not _FENCE.match(lines[i]):
                buf.append(lines[i])
                i += 1
            i += 1
            cls = f' class="lang-{html.escape(lang, quote=True)}"' if lang else ""
            out.append(f"<pre><code{cls}>{html.escape(chr(10).join(buf))}</code></pre>")
            continue
        if not line.strip():
            flush()
            i += 1
            continue
        m = _HEAD.match(line)
        if m:
            flush()
            lvl, txt = len(m.group(1)), m.group(2)
            hid = base = slug_id(txt)
            k = 2
            while hid in used:
                hid, k = f"{base}-{k}", k + 1
            used.add(hid)
            if toc is not None:
                toc.append((lvl, hid, re.sub(r"[*`]", "", txt)))
            out.append(f'<h{lvl} id="{hid}">{inline(txt, link)}</h{lvl}>')
            i += 1
            continue
        if _HR.match(line):
            flush()
            out.append("<hr>")
            i += 1
            continue
        if table_note is not None and line.lstrip().startswith("|") and i + 1 < len(lines) and lines[i + 1].lstrip().startswith("|"):
            flush()
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                i += 1
            if table_note:
                out.append(table_note)
            continue
        if line.lstrip().startswith("|") and i + 1 < len(lines) and _TABLE_SEP.match(lines[i + 1]):
            flush()
            head = _cells(line)
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(_cells(lines[i]))
                i += 1
            t = ["<div class=\"table-wrap\"><table><thead><tr>"]
            t += [f"<th>{inline(c, link)}</th>" for c in head]
            t.append("</tr></thead><tbody>")
            for r in rows:
                t.append("<tr>" + "".join(f"<td>{inline(c, link)}</td>" for c in r) + "</tr>")
            t.append("</tbody></table></div>")
            out.append("".join(t))
            continue
        if line.lstrip().startswith(">"):
            flush()
            buf = []
            while i < len(lines) and lines[i].lstrip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            out.append("<blockquote>" + convert("\n".join(buf), link) + "</blockquote>")
            continue
        if _UL.match(line) or _OL.match(line):
            flush()
            items: list[tuple[int, str, str]] = []  # (들여쓰기, 종류, 내용)
            while i < len(lines):
                mu, mo = _UL.match(lines[i]), _OL.match(lines[i])
                m_any = mu or mo
                if m_any and items and len(m_any.group(1).expandtabs(4)) <= items[0][0] \
                        and ("ul" if mu else "ol") != items[0][1]:
                    break  # 같은 깊이에서 목록 종류가 바뀌면 새 목록
                if mu:
                    items.append((len(mu.group(1).expandtabs(4)), "ul", mu.group(2)))
                elif mo:
                    items.append((len(mo.group(1).expandtabs(4)), "ol", mo.group(3)))
                elif lines[i].strip() and lines[i].startswith((" ", "\t")) and items:
                    ind, kind, txt = items[-1]
                    items[-1] = (ind, kind, txt + "\n" + lines[i].strip())
                else:
                    break
                i += 1
            out.append(_render_list(items, link))
            continue
        para.append(line.strip())
        i += 1
    flush()
    return "\n".join(out)


def _render_list(items: list[tuple[int, str, str]], link: LinkFn | None) -> str:
    base = min(x[0] for x in items)
    html_parts: list[str] = []
    kind = items[0][1]
    html_parts.append(f"<{kind}>")
    j = 0
    while j < len(items):
        ind, k, txt = items[j]
        sub = []
        j += 1
        while j < len(items) and items[j][0] > base:
            sub.append(items[j])
            j += 1
        body = "<br>".join(inline(x, link) for x in txt.split("\n"))
        if sub:
            body += _render_list(sub, link)
        html_parts.append(f"<li>{body}</li>")
    html_parts.append(f"</{kind}>")
    return "".join(html_parts)
