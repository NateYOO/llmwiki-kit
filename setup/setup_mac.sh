#!/usr/bin/env bash
# llmwiki 설치 (macOS; Linux에서도 동작). Python이 없어도 됩니다 — uv가 Python 3.12를 받아 옵니다.
#
#   bash setup/setup_mac.sh                       # 이 폴더(키트)를 작업 폴더로 설치
#   bash setup/setup_mac.sh --target ~/Documents/my-thesis   # 기존 연구 폴더에 키트 복사 후 설치(덮어쓰지 않음)
#   bash setup/setup_mac.sh --no-uv               # uv 대신 시스템 python3 -m venv 사용
#
# 관리자 권한(sudo) 필요 없음. 모든 파일은 홈 폴더(~/.local/bin의 uv)와 작업 폴더(.venv) 안에만 생깁니다.
set -euo pipefail

KIT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET=""
USE_UV=1
APPEND_AGENTS=""
PYVER="3.12"
while [ $# -gt 0 ]; do
  case "$1" in
    --target) TARGET="$2"; shift 2 ;;
    --target=*) TARGET="${1#*=}"; shift ;;
    --no-uv) USE_UV=0; shift ;;
    --append-agents) APPEND_AGENTS="--append-agents"; shift ;;
    -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
    *) echo "알 수 없는 옵션: $1" >&2; exit 2 ;;
  esac
done

say() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
export PYTHONUTF8=1

# 1) uv 준비 (없으면 공식 설치 스크립트로 ~/.local/bin 에 설치)
UV=""
if [ "$USE_UV" = 1 ]; then
  UV="$(command -v uv || true)"
  [ -z "$UV" ] && [ -x "$HOME/.local/bin/uv" ] && UV="$HOME/.local/bin/uv"
  [ -z "$UV" ] && [ -x "$HOME/.cargo/bin/uv" ] && UV="$HOME/.cargo/bin/uv"
  if [ -z "$UV" ]; then
    say "uv 설치 (https://astral.sh/uv, 관리자 권한 불필요)"
    if curl -LsSf https://astral.sh/uv/install.sh | sh; then
      UV="$HOME/.local/bin/uv"
      [ -x "$UV" ] || UV="$(command -v uv || true)"
    fi
  fi
  if [ -z "$UV" ] || [ ! -x "$UV" ]; then
    echo "uv 설치에 실패했습니다. 시스템 python3로 계속합니다(--no-uv)." >&2
    USE_UV=0
  fi
fi

# 2) Python 찾기/받기
if [ "$USE_UV" = 1 ]; then
  say "Python $PYVER 준비 (uv python install — 시스템 Python을 건드리지 않음)"
  "$UV" python install "$PYVER"
  PY="$("$UV" python find "$PYVER")"
else
  PY="$(command -v python3 || true)"
  if [ -z "$PY" ] || ! "$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)'; then
    echo "Python 3.10 이상이 필요합니다. --no-uv 없이 다시 실행하거나 https://www.python.org 에서 설치하세요." >&2
    exit 1
  fi
fi
echo "Python: $PY"

# 3) (선택) 기존 연구 폴더에 키트 복사
WORK="$KIT"
if [ -n "$TARGET" ]; then
  say "키트를 $TARGET 에 설치 (기존 파일은 덮어쓰지 않음)"
  PYTHONPATH="$KIT/tools" "$PY" -m llmwiki init "$TARGET" $APPEND_AGENTS
  WORK="$(cd "$TARGET" && pwd)"
fi
cd "$WORK"

# 4) 작업 폴더 안에 .venv 만들고 패키지 설치
say "가상환경 .venv 만들기 + pymupdf, pyyaml, pyzotero 설치"
if [ "$USE_UV" = 1 ]; then
  [ -x .venv/bin/python ] || "$UV" venv --python "$PYVER" .venv
  "$UV" pip install --python .venv/bin/python -r setup/requirements.txt
else
  [ -x .venv/bin/python ] || "$PY" -m venv .venv
  .venv/bin/python -m pip install --upgrade pip >/dev/null
  .venv/bin/python -m pip install -r setup/requirements.txt
fi
chmod +x ./llmwiki

# 5) 점검
say "환경 점검 (llmwiki doctor)"
./llmwiki doctor || true
cat <<MSG

설치 완료: $WORK
  다음 단계
  1) ChatGPT 데스크톱 앱 → Codex → 프로젝트 → 폴더 추가 → 이 폴더를 Primary로
  2) 채팅창에:  \$wiki-ingest 논문제목   (또는 "이 논문 위키에 넣어줘")
  터미널에서 직접:  ./llmwiki --help
MSG
