#!/usr/bin/env bash
# 한 줄 설치 (macOS/Linux):
#   curl -LsSf https://github.com/NateYOO/llmwiki-kit/raw/main/setup/install_mac.sh | bash
#   curl -LsSf https://github.com/NateYOO/llmwiki-kit/raw/main/setup/install_mac.sh | bash -s -- ~/my-thesis   # 기존 연구 폴더에 설치 (iCloud 동기화 폴더는 피하기)
# 저장소를 임시 폴더로 받아(git 또는 ZIP) setup_mac.sh --target <폴더> 를 실행합니다. 기존 파일은 덮어쓰지 않습니다.
set -euo pipefail
REPO_URL="${LLMWIKI_REPO_URL:-https://github.com/NateYOO/llmwiki-kit}"
BRANCH="${LLMWIKI_BRANCH:-main}"
TARGET="${1:-$HOME/llmwiki}"
case "$REPO_URL" in *"<"*) echo "REPO_URL 자리표시가 그대로입니다. 저장소 주소로 바꾸거나 LLMWIKI_REPO_URL=https://github.com/<계정>/<저장소> 로 실행하세요." >&2; exit 2 ;; esac
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
if command -v git >/dev/null 2>&1 && git --version >/dev/null 2>&1; then
  git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$TMP/kit"
  KIT="$TMP/kit"
else
  curl -LsSf "${REPO_URL%.git}/archive/refs/heads/$BRANCH.zip" -o "$TMP/kit.zip"
  unzip -q "$TMP/kit.zip" -d "$TMP"
  KIT="$(find "$TMP" -mindepth 1 -maxdepth 1 -type d | head -1)"
fi
bash "$KIT/setup/setup_mac.sh" --target "$TARGET"
