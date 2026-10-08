"""`llmwiki init` (기존 연구 폴더에 키트 설치)과 `llmwiki sample` (복구용 샘플 위키 복사).
표준 라이브러리만 사용 — 가상환경이 없어도 `python -m llmwiki init`으로 돌 수 있게."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[2]

# (원본 경로, 설명) — 키트에서 학생 폴더로 복사할 것
KIT_ITEMS = [
    "AGENTS.md",
    "llmwiki.yaml",
    "llmwiki",
    "llmwiki.cmd",
    ".agents/skills/wiki-ingest",
    ".agents/skills/wiki-query",
    ".agents/skills/wiki-lint",
    ".agents/skills/wiki-synthesize",
    "tools",
    "setup",
    "wiki/index.md",
    "wiki/log.md",
    "wiki/papers/.gitkeep",
    "wiki/topics/.gitkeep",
    "drafts/README.md",
    "raw/README.md",
    "examples/sample-wiki",
    ".gitignore",
    ".gitattributes",
    "README.md",
    "COMMANDS.md",
    "INSTALL_FOR_AGENT.md",
    "LICENSE",
]
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".venv", ".DS_Store")

AGENTS_POINTER = """
<!-- llmwiki:agents-pointer -->
## 연구 위키(llmwiki) 규칙
이 폴더의 논문 위키 작업(ingest/query/lint, 위키 읽기·쓰기)은 **`AGENTS.llmwiki.md`의 규칙을 반드시 먼저 읽고 따른다.**
스킬: `.agents/skills/wiki-ingest`, `wiki-query`, `wiki-lint`, `wiki-synthesize`.
"""


def _iter_files(src: Path):
    if src.is_file():
        yield src
        return
    for dirpath, dirnames, filenames in os.walk(src):
        dirnames[:] = [d for d in dirnames if d not in ("__pycache__", ".venv")]
        for fn in filenames:
            if fn.endswith(".pyc") or fn == ".DS_Store":
                continue
            yield Path(dirpath) / fn


def init(target: Path, *, append_agents: bool = False, with_sample: bool = True) -> dict:
    target = Path(target).expanduser().resolve()
    if target == KIT_ROOT:
        return {"status": "noop", "message": "키트 폴더 자체입니다. 다른 폴더를 지정하세요."}
    target.mkdir(parents=True, exist_ok=True)
    created, skipped, notes = [], [], []
    for item in KIT_ITEMS:
        if item == "examples/sample-wiki" and not with_sample:
            continue
        src = KIT_ROOT / item
        if not src.exists():
            continue
        for f in _iter_files(src):
            rel = f.relative_to(KIT_ROOT)
            dst = target / rel
            if rel.as_posix() == "AGENTS.md" and dst.exists():
                alt = target / "AGENTS.llmwiki.md"
                if not alt.exists():
                    shutil.copy2(f, alt)
                    created.append("AGENTS.llmwiki.md")
                existing = dst.read_text(encoding="utf-8", errors="replace")
                if "llmwiki:agents-pointer" in existing:
                    notes.append("기존 AGENTS.md에 이미 llmwiki 안내 블록이 있습니다.")
                elif append_agents:
                    with open(dst, "a", encoding="utf-8", newline="\n") as fh:
                        fh.write("\n" + AGENTS_POINTER)
                    notes.append("기존 AGENTS.md 끝에 'AGENTS.llmwiki.md를 따르라'는 안내 블록을 덧붙였습니다(--append-agents).")
                else:
                    notes.append(
                        "기존 AGENTS.md는 그대로 두고 키트 규칙을 AGENTS.llmwiki.md로 저장했습니다.\n"
                        "    Codex는 폴더당 AGENTS.md 한 개만 자동으로 읽으므로, 아래 블록을 기존 AGENTS.md 끝에 붙여 넣으세요\n"
                        "    (또는 `llmwiki init <폴더> --append-agents` 로 자동 추가):\n" + AGENTS_POINTER
                    )
                continue
            if rel.as_posix() in ("README.md", ".gitignore") and dst.exists():
                alt = dst.with_name(dst.stem + ".llmwiki" + dst.suffix) if rel.as_posix() == "README.md" else target / ".gitignore.llmwiki"
                if not alt.exists():
                    shutil.copy2(f, alt)
                    created.append(alt.relative_to(target).as_posix())
                notes.append(f"기존 {rel.as_posix()}는 그대로 두고 {alt.name}로 저장했습니다. 필요한 줄만 옮기세요.")
                continue
            if dst.exists():
                skipped.append(rel.as_posix())
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dst)
            created.append(rel.as_posix())
    for d in ("wiki/papers", "wiki/topics", "drafts", "raw"):
        (target / d).mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(target / "llmwiki", 0o755)
        os.chmod(target / "setup" / "setup_mac.sh", 0o755)
    except OSError:
        pass
    return {"status": "ok", "target": str(target), "created": len(created), "skipped_existing": skipped, "notes": notes,
            "next": ["cd " + str(target), "macOS: bash setup/setup_mac.sh   |   Windows: powershell -ExecutionPolicy Bypass -File setup\\setup_windows.ps1",
                     "Codex(ChatGPT 데스크톱 앱)에서 이 폴더를 프로젝트 Primary 폴더로 열기"]}


def restore_sample(root: Path, overwrite: bool = False) -> dict:
    src = root / "examples" / "sample-wiki" / "wiki"
    if not src.exists():
        src = KIT_ROOT / "examples" / "sample-wiki" / "wiki"
    if not src.exists():
        raise SystemExit("examples/sample-wiki/wiki 를 찾지 못했습니다.")
    copied, skipped = [], []
    for sub in ("papers", "topics"):
        s = src / sub
        if not s.exists():
            continue
        for entry in sorted(s.iterdir()):
            if entry.name.startswith("."):
                continue
            dst = root / "wiki" / sub / entry.name
            if dst.exists() and not overwrite:
                skipped.append(f"{sub}/{entry.name}")
                continue
            if dst.exists():
                shutil.rmtree(dst) if dst.is_dir() else dst.unlink()
            (shutil.copytree(entry, dst, ignore=IGNORE) if entry.is_dir() else shutil.copy2(entry, dst))
            copied.append(f"{sub}/{entry.name}")
    return {"copied": copied, "skipped_existing": skipped}
