"""메타데이터: DOI·arXiv ID 찾기와 키 없는 보강(arXiv API, Crossref, OpenAlex DOI 단건 조회).

모든 네트워크 호출은 실패해도 추출을 멈추지 않는다(오프라인 강의실 대비).
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any

from .util import http_get, http_get_json, q, title_similarity

DOI_RE = re.compile(r"\b(10\.\d{4,9}/[^\s\"<>{}|\\^`\[\]]+)", re.I)
ARXIV_RE = re.compile(r"arXiv:\s*(\d{4}\.\d{4,5})(v\d+)?", re.I)
ARXIV_FILE_RE = re.compile(r"(?<!\d)(\d{4}\.\d{4,5})(v\d+)?(?!\d)")


def clean_doi(doi: str) -> str:
    doi = doi.strip().rstrip(".,;)")
    doi = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", doi, flags=re.I)
    return doi


def find_doi(text: str) -> str:
    m = DOI_RE.search(text or "")
    if not m:
        return ""
    doi = clean_doi(m.group(1))
    # arXiv가 부여한 DOI(10.48550/arXiv.xxxx)는 그대로 둬도 되지만 저널 DOI가 우선
    return doi


def find_arxiv(text: str, filename: str = "") -> str:
    m = ARXIV_RE.search(text or "")
    if m:
        return m.group(1)
    m = ARXIV_FILE_RE.search(filename or "")
    if m:
        return m.group(1)
    return ""


def arxiv_lookup(arxiv_id: str, timeout: float = 12) -> dict[str, Any]:
    status, body, _ = http_get(f"https://export.arxiv.org/api/query?id_list={q(arxiv_id)}", timeout=timeout)
    if status != 200:
        raise RuntimeError(f"arXiv HTTP {status}")
    ns = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    root = ET.fromstring(body)
    entry = root.find("a:entry", ns)
    if entry is None or entry.find("a:title", ns) is None:
        raise RuntimeError("arXiv 결과 없음")
    title = " ".join((entry.findtext("a:title", "", ns) or "").split())
    if not title or title.lower() == "error":
        raise RuntimeError("arXiv 결과 없음")
    out = {
        "title": title,
        "authors": [" ".join((a.findtext("a:name", "", ns) or "").split()) for a in entry.findall("a:author", ns)],
        "date": (entry.findtext("a:published", "", ns) or "")[:10],
        "abstract": " ".join((entry.findtext("a:summary", "", ns) or "").split()),
        "url": f"https://arxiv.org/abs/{arxiv_id}",
        "arxiv": arxiv_id,
    }
    doi = entry.findtext("arxiv:doi", "", ns)
    if doi:
        out["doi"] = clean_doi(doi)
    jr = entry.findtext("arxiv:journal_ref", "", ns)
    if jr:
        out["venue"] = " ".join(jr.split())
    return out


def _crossref_item(item: dict) -> dict[str, Any]:
    authors = []
    for a in item.get("author", []) or []:
        name = " ".join(x for x in [a.get("given", ""), a.get("family", "")] if x).strip()
        if name:
            authors.append(name)
    parts = (item.get("issued", {}) or {}).get("date-parts", [[None]])[0]
    date = "-".join(f"{p:02d}" if i else str(p) for i, p in enumerate(parts) if p) if parts and parts[0] else ""
    abstract = re.sub(r"<[^>]+>", " ", item.get("abstract", "") or "")
    return {
        "title": " ".join((item.get("title") or [""])[0].split()),
        "authors": authors,
        "date": date,
        "doi": clean_doi(item.get("DOI", "")),
        "venue": (item.get("container-title") or [""])[0],
        "abstract": " ".join(abstract.split()),
        "url": item.get("URL", ""),
    }


def crossref_by_doi(doi: str, timeout: float = 12, mailto: str = "") -> dict[str, Any]:
    url = f"https://api.crossref.org/works/{q(doi)}" + (f"?mailto={q(mailto)}" if mailto else "")
    return _crossref_item(http_get_json(url, timeout=timeout)["message"])


def crossref_by_title(title: str, first_author: str = "", year: str = "", timeout: float = 12, mailto: str = "") -> dict[str, Any] | None:
    """제목 검색은 엉뚱한 결과가 1위로 오는 일이 있어(sources.md §4.4) 제목 유사도로 반드시 검증한다."""
    query = title + (" " + first_author if first_author else "")
    url = f"https://api.crossref.org/works?rows=5&query.bibliographic={q(query)}" + (f"&mailto={q(mailto)}" if mailto else "")
    items = http_get_json(url, timeout=timeout)["message"].get("items", [])
    best, best_s = None, 0.0
    for it in items:
        cand = _crossref_item(it)
        s = title_similarity(title, cand["title"])
        if year and cand["date"][:4] and abs(int(cand["date"][:4]) - int(str(year)[:4])) > 2:
            s -= 0.3
        if s > best_s:
            best, best_s = cand, s
    if best and best_s >= 0.8:
        best["match_score"] = round(best_s, 2)
        return best
    return None


def openalex_by_doi(doi: str, timeout: float = 12) -> dict[str, Any]:
    """OpenAlex는 2026-02부터 키 없는 '검색'이 매우 제한적이지만 DOI 단건 조회는 비용 0(sources.md §4.4)."""
    data = http_get_json(f"https://api.openalex.org/works/doi:{q(doi)}", timeout=timeout)
    return {
        "openalex": data.get("id", ""),
        "cited_by_count": data.get("cited_by_count"),
        "concepts": [c.get("display_name") for c in (data.get("concepts") or [])[:5]],
    }


def enrich(meta: dict[str, Any], *, network: bool = True, timeout: float = 12, mailto: str = "") -> dict[str, Any]:
    """빈칸만 채운다. 이미 있는 값(Zotero 등)은 덮어쓰지 않는다. 출처는 meta['sources']에 남긴다."""
    sources = meta.setdefault("sources", [])
    notes = meta.setdefault("enrich_notes", [])
    if not network:
        notes.append("network disabled")
        return meta

    def fill(new: dict, tag: str) -> None:
        for k, v in new.items():
            if v and not meta.get(k):
                meta[k] = v
        sources.append(tag)

    if meta.get("arxiv"):
        try:
            fill(arxiv_lookup(meta["arxiv"], timeout), "arxiv")
        except Exception as e:  # noqa: BLE001
            notes.append(f"arxiv: {e}")
    if meta.get("doi") and not meta["doi"].lower().startswith("10.48550/"):
        try:
            fill(crossref_by_doi(meta["doi"], timeout, mailto), "crossref")
        except Exception as e:  # noqa: BLE001
            notes.append(f"crossref: {e}")
    elif not meta.get("doi") and meta.get("title"):
        try:
            hit = crossref_by_title(meta["title"], (meta.get("authors") or [""])[0], meta.get("date", "")[:4], timeout, mailto)
            if hit:
                # 검증된 제목 일치일 때만 DOI·학술지를 받는다
                for k in ("doi", "venue"):
                    if hit.get(k) and not meta.get(k):
                        meta[k] = hit[k]
                        if k == "doi":
                            meta["doi_source"] = f"crossref title match {hit['match_score']} (다른 판본 DOI일 수 있음 — 확인)"
                sources.append(f"crossref-title({hit['match_score']})")
            else:
                notes.append("crossref-title: no verified match")
        except Exception as e:  # noqa: BLE001
            notes.append(f"crossref-title: {e}")
    if meta.get("doi"):
        try:
            fill(openalex_by_doi(meta["doi"], timeout), "openalex")
        except Exception as e:  # noqa: BLE001
            notes.append(f"openalex: {e}")
    return meta
