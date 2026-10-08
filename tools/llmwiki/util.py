"""공통 도구: 작업 폴더 찾기, frontmatter, slug, HTTP(표준 라이브러리), 콘솔 인코딩."""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import yaml

USER_AGENT = "llmwiki/0.1 (student research wiki; +https://github.com/)"
REVIEW_HEADINGS = [
    "## Essence",
    "## Motivation",
    "## Achievement",
    "## How",
    "## Originality",
    "## Limitation & Further Study",
    "## Evaluation",
]
RELATED_HEADING = "## Related Papers"
RELATED_START = "<!-- llmwiki:related:start -->"
RELATED_END = "<!-- llmwiki:related:end -->"
INDEX_START = "<!-- llmwiki:index:start -->"
INDEX_END = "<!-- llmwiki:index:end -->"


def setup_console() -> None:
    """Windows 콘솔에서도 한글이 깨지지 않도록 stdout/stderr를 UTF-8로 맞춘다."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass


def today() -> str:
    return _dt.date.today().isoformat()


# ---------------------------------------------------------------- workspace
class Workspace:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.wiki = self.root / "wiki"
        self.papers = self.wiki / "papers"
        self.topics = self.wiki / "topics"
        self.drafts = self.root / "drafts"
        self.projects = self.root / "projects"
        self.index = self.wiki / "index.md"
        self.log = self.wiki / "log.md"
        self.config = load_config(self.root)

    def paper_dir(self, slug: str) -> Path:
        return self.papers / slug

    def paper_slugs(self) -> list[str]:
        if not self.papers.exists():
            return []
        return sorted(p.name for p in self.papers.iterdir() if p.is_dir() and not p.name.startswith((".", "_")))

    def rel(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.root).as_posix()
        except ValueError:
            return str(path)


def find_workspace(start: str | os.PathLike | None = None) -> Workspace:
    env = os.environ.get("LLMWIKI_ROOT")
    if start is None and env:
        start = env
    p = Path(start or Path.cwd()).resolve()
    for cand in [p, *p.parents]:
        if (cand / "AGENTS.md").exists() and (cand / "wiki").is_dir():
            return Workspace(cand)
    # 도구 폴더 기준(tools/llmwiki/..)으로도 시도
    here = Path(__file__).resolve().parents[2]
    if (here / "AGENTS.md").exists():
        return Workspace(here)
    raise SystemExit(
        "작업 폴더를 찾지 못했습니다. AGENTS.md와 wiki/ 폴더가 있는 곳에서 실행하거나 --root를 지정하세요."
    )


class UserError(Exception):
    """학생 입력 문제(없는 이름·잘못된 값). CLI가 Traceback 없이 '[오류] …' 한 덩어리로 보여 준다."""


DEFAULT_CONFIG: dict[str, Any] = {
    "zotero": {
        "practice_collection": "llmwiki-practice",
        "order": ["local_api", "sqlite", "external"],
        "local_api_url": "http://127.0.0.1:23119/api",
        "data_dir": "",
        "external_cli": {"search": "", "get": "", "collections": ""},
    },
    "network": {"enabled": True, "timeout": 12, "mailto": ""},
    "related": {"top_k": 5, "min_score": 0.0},
}


def _deep_merge(base: dict, extra: dict) -> dict:
    out = dict(base)
    for k, v in (extra or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(root: Path) -> dict:
    cfg_path = root / "llmwiki.yaml"
    data: dict = {}
    if cfg_path.exists():
        try:
            data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as e:
            print(f"[경고] llmwiki.yaml을 읽지 못했습니다: {e}", file=sys.stderr)
    return _deep_merge(DEFAULT_CONFIG, data)


# ---------------------------------------------------------------- text files
def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def split_frontmatter(text: str) -> tuple[dict | None, str, str | None]:
    """(frontmatter dict 또는 None, 본문, 오류메시지)"""
    if text.startswith("\ufeff"):
        text = text[1:]
    if not text.startswith("---"):
        return None, text, None
    m = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", text, re.S)
    if not m:
        return None, text, "frontmatter 닫는 --- 가 없습니다"
    try:
        data = yaml.safe_load(m.group(1)) or {}
        if not isinstance(data, dict):
            return None, text[m.end():], "frontmatter가 key: value 형식이 아닙니다"
        return data, text[m.end():], None
    except yaml.YAMLError as e:
        return None, text[m.end():], f"YAML 오류: {e}"


def dump_frontmatter(data: dict) -> str:
    body = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=1000, default_flow_style=None)
    return f"---\n{body}---\n"


# ---------------------------------------------------------------- slug
def slugify(title: str, year: Any = None, first_author: str | None = None, max_len: int = 50) -> str:
    """`2024-schmucker-ruffle-riley-insights` 같은 slug. 한글은 유지, 파일명 금지 문자는 제거."""
    def norm(s: str) -> str:
        s = unicodedata.normalize("NFKC", s or "").lower()
        s = s.replace("&", " ")
        s = re.sub(r"[^\w\s-]", " ", s, flags=re.U)
        return re.sub(r"[\s_]+", "-", s.strip()).strip("-")

    stop = {"a", "an", "the", "of", "for", "and", "in", "on", "to", "with", "via", "towards", "toward", "from", "by"}
    words = [w for w in norm(title).split("-") if w and w not in stop]
    parts = []
    if year:
        parts.append(str(year)[:4])
    if first_author:
        last = norm(first_author.split(",")[0] if "," in first_author else first_author.split()[-1])
        if last:
            parts.append(last)
    slug = "-".join(parts + words[:5])
    while len(slug) > max_len and "-" in slug:
        slug = slug.rsplit("-", 1)[0]  # 단어 경계에서 자르기
    slug = slug[:max_len].rstrip("-")
    return slug or "paper"


def unique_slug(ws: Workspace, base: str) -> str:
    slug, i = base, 2
    while (ws.papers / slug).exists():
        slug = f"{base}-{i}"
        i += 1
    return slug


# ---------------------------------------------------------------- http
def http_get(url: str, timeout: float = 12, headers: dict | None = None) -> tuple[int, bytes, dict]:
    h = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    h.update(headers or {})
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read() if hasattr(e, "read") else b"", dict(e.headers or {})


def http_get_json(url: str, timeout: float = 12, headers: dict | None = None) -> Any:
    status, body, _ = http_get(url, timeout=timeout, headers=headers)
    if status != 200:
        raise RuntimeError(f"HTTP {status}: {url}")
    return json.loads(body.decode("utf-8"))


def q(s: str) -> str:
    return urllib.parse.quote(s, safe="")


def norm_title(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "").lower()
    return re.sub(r"[^\w]+", " ", s).strip()


def title_similarity(a: str, b: str) -> float:
    ta, tb = set(norm_title(a).split()), set(norm_title(b).split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def dump_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def project_mds(ws: "Workspace") -> list[Path]:
    """projects/<주제>/**/*.md (README·숨김 제외). .md가 아닌 파일(hwp·xlsx 등)은 보지 않는다."""
    root = ws.root / "projects"
    if not root.exists():
        return []
    out = []
    for f in root.rglob("*.md"):
        parts = f.relative_to(root).parts
        if len(parts) < 2 or any(x.startswith(".") for x in parts) or f.name.lower() == "readme.md":
            continue
        out.append(f)
    import unicodedata as _ud
    return sorted(out, key=lambda f: _ud.normalize("NFC", f.relative_to(root).as_posix()).lower())
