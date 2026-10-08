"""`llmwiki finish <slug>` — 넣기 뒤 처리(related --write → index → lint → 완료일 때만 log)를 한 번에 (QA H40).
단계별 rc를 남기고, 마지막 줄은 표준 문구(ASCII 표지 RESULT: 포함).
미완료(헤딩 빈칸·이 논문 ERROR·단계 실패)면 log에 쓰지 않는다 — 미완성 넣기가 완료처럼 기록되지 않게 (QA H46①)."""
from __future__ import annotations

import re
from typing import Any

from .util import RELATED_HEADING, REVIEW_HEADINGS, Workspace, read_text
from .wikiops import TODO_RE, get_section, load_paper, strip_comments


def _meta(pdir) -> dict:
    import json
    try:
        return json.loads((pdir / "meta.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def heading_fill(body: str) -> tuple[int, int, list[str]]:
    """채워진 헤딩 수 / 전체(7개 + Related Papers) / 빈 헤딩 이름."""
    heads = list(REVIEW_HEADINGS) + [RELATED_HEADING]
    empty = []
    for h in heads:
        sec = get_section(body, h) if re.search(r"^" + re.escape(h) + r"\s*$", body, re.M) else ""
        if not sec or TODO_RE.search(sec) or "?/5" in sec or len(strip_comments(sec).strip()) < 15:
            empty.append(h.lstrip("# "))
    return len(heads) - len(empty), len(heads), empty


def run(ws: Workspace, slug: str, *, op: str = "ingest", note: str = "") -> dict[str, Any]:
    from . import lint, related
    from .wikiops import append_log, write_index
    pdir = ws.papers / slug
    if not (pdir / "review.md").exists():
        raise SystemExit(f"논문 slug를 찾지 못했습니다: {slug} (wiki/papers/<slug>/review.md가 있어야 함)")
    steps: list[dict[str, Any]] = []

    def step(name: str, fn):
        try:
            detail = fn()
            steps.append({"step": name, "rc": 0, "detail": detail})
        except SystemExit as e:
            steps.append({"step": name, "rc": 2, "detail": str(e.code)})
        except Exception as e:  # noqa: BLE001
            steps.append({"step": name, "rc": 1, "detail": f"{type(e).__name__}: {e}"})

    step("related --write", lambda: f"갱신 {len(related.write(ws, related.compute(ws)))}개")
    step("index", lambda: ws.rel(write_index(ws)))
    paper = load_paper(ws, slug)
    title = paper.title or slug

    issues: list[Any] = []

    def do_lint():
        issues.extend(lint.run(ws))
        s = lint.summarize(issues)
        return f"전체 ERROR {s['errors']} · WARN {s['warnings']}"
    step("lint", do_lint)

    mine = [i.as_dict() for i in issues if f"papers/{slug}/" in i.path.replace("\\", "/")]
    errs = [i for i in mine if i["level"] == "ERROR"]
    warns = [i for i in mine if i["level"] == "WARN"]
    filled, total, empty = heading_fill(read_text(pdir / "review.md"))
    others_err = sum(1 for i in issues if i.level == "ERROR") - len(errs)
    failed = [s for s in steps if s["rc"] != 0]
    scanned = bool((p_meta := _meta(pdir)).get("scanned"))
    if scanned:
        empty = []  # 스캔본 자리 표시: 리뷰를 쓸 수 없으니 헤딩 검사 대신 안내만(lint는 WARN)
    ok = not failed and not errs and not empty

    def do_log():
        clean = " ".join(title.split()).replace("|", "/")
        from .util import today
        head = f"## [{today()}] {op} | {clean}"
        if ws.log.exists() and head in read_text(ws.log):
            return "오늘 같은 기록이 이미 있어 건너뜀"
        notes = [f"wiki/papers/{slug}/review.md"] + ([note] if note else [])
        append_log(ws, op, title, notes)
        return head

    if ok:
        step("log", do_log)
        failed = [s for s in steps if s["rc"] != 0]
        ok = not failed
    else:
        steps.append({"step": "log", "rc": 0, "skipped": True, "detail": "건너뜀 — 미완료라 기록하지 않음(완료 후 finish를 다시 부르면 기록)"})
    from .site import try_rebuild
    msg = try_rebuild(ws, only_if_exists=False)  # 위키 화면(site/) 갱신 — 실패해도 finish 결과에 영향 없음
    steps.append({"step": "site", "rc": 0, "skipped": msg.startswith("화면 갱신 실패"), "detail": msg})
    if ok:
        result, last = "RESULT: OK", f"넣기 완료 ✅ {title} · 헤딩 {filled}/{total} · lint ERROR 0 (이 논문 WARN {len(warns)})"
        if scanned:
            last = f"넣기 완료(제목·저자만) ⚠️ {title} — 스캔본이라 리뷰는 비워 뒀어요. 글자가 들어 있는 PDF를 넣으면 다시 쓸 수 있어요. (lint ERROR 0)"
        elif p_meta.get("meta_pending"):
            last += " · 저자는 잠시 뒤 `llmwiki meta --refresh " + slug + "` 로 채우기"
    else:
        todo = [f"{s['step']} 실패({s['detail']})" for s in failed]
        if empty:
            todo.append(f"헤딩 {filled}/{total} — 채울 곳: {', '.join(empty)}")
        todo += [f"{e['code']}: {e['msg']}" for e in errs[:5]]
        result, last = "RESULT: FAIL", f"넣기 미완료 ❌ / 고칠 것: " + " · ".join(todo)
    return {"slug": slug, "title": title, "steps": steps, "headings": f"{filled}/{total}",
            "paper_issues": mine, "other_papers_errors": others_err, "ok": ok, "result": result, "last_line": last}
