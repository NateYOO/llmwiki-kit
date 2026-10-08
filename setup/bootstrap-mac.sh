#!/usr/bin/env bash
# shellcheck disable=SC2088  # 안내 문구 속 "~/llmwiki"는 사람에게 보여 주는 글자(확장 의도 없음)
# LLM 위키 스타터 키트 - macOS 원프롬프트 설치 (bootstrap)
# Codex 앱 에이전트가 INSTALL_FOR_AGENT.md 절차대로 실행한다. 학생은 [승인]만 누른다.
#
#   실행(고정):  bash <이 파일> --repo <저장소 주소>
#   점검만:      bash <이 파일> --check-only --repo <저장소 주소>   (학생 설치 문장의 첫 명령. 끝에 다음 명령을 AGENT_CMD: 줄로 알려 줌)
#   에이전트 판정: 마지막 부분의 ASCII 줄 'RESULT: …'(CHECK_OK / OK / DOCTOR_FAIL / FAIL Exx)과 'AGENT: …'만 보면 된다.
# 하는 일 (8단계, 다시 실행해도 안전 / 기존 파일은 절대 덮어쓰지 않음):
#   0 폴더 점검  1 기본 도구(curl·unzip)  2 Git(선택: Xcode 명령어 도구)  3 uv + Python 3.12(관리자 권한 없음)
#   4 키트 받기(git clone 또는 ZIP) + 병합  5 .venv + 패키지  6 UTF-8  7 git init  8 doctor + 한 줄 요약
# 오류 코드: E00 폴더 / E01 인터넷 / E02 Git(치명 아님) / E03 uv / E04 Python / E05 키트 / E06 패키지 / E07 doctor
set -u
REPO_URL=""; BRANCH="main"; TARGET=""; KIT_SOURCE=""; CHECK_ONLY=0; SKIP_GIT=0; ALLOW_NONEMPTY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --repo) REPO_URL="$2"; shift 2 ;;
    --branch) BRANCH="$2"; shift 2 ;;
    --target) TARGET="$2"; shift 2 ;;
    --kit-source) KIT_SOURCE="$2"; shift 2 ;;
    --check-only) CHECK_ONLY=1; shift ;;
    --skip-git) SKIP_GIT=1; shift ;;
    --allow-nonempty) ALLOW_NONEMPTY=1; shift ;;
    *) echo "알 수 없는 옵션: $1"; exit 2 ;;
  esac
done
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8 LC_ALL="${LC_ALL:-en_US.UTF-8}"
TOTAL=8; LOG=""
say()  { echo "$*"; [ -n "$LOG" ] && echo "$*" >> "$LOG" 2>/dev/null; return 0; }
step() { say ""; say "[$1/$TOTAL] $2   ($(date +%H:%M:%S))"; }
die()  {
  say ""; say "[$1] $2"; [ -n "${3:-}" ] && say "  해결: $3"; say "설치 중단 ❌ / 오류 코드 $1"; say "RESULT: FAIL $1"
  case "$1" in
    E00|E05) say "AGENT: Read the line starting with '해결:' to the student word for word and STOP. Do not retry, do not try other commands." ;;
    *) say "AGENT: Retry the same command ONCE. If it fails again, say: '설치가 멈췄습니다. 오류 코드 $1 - 손을 들어 이 화면을 보여 주세요.' and paste the last 20 lines. Then STOP." ;;
  esac
  exit $((10 + 10#${1#E}))
}
run()  { "$@" 2>&1 | while IFS= read -r l; do say "    $l"; done; return "${PIPESTATUS[0]}"; }
dl()   { for i in 1 2; do curl -fL --retry 2 -sS "$1" -o "$2" && return 0; say "    다운로드 실패($i/2): $1"; sleep 2; done; return 1; }

# ---------------------------------------------------------------- 0. 폴더 점검
[ -z "$TARGET" ] && TARGET="$PWD"
TARGET="$(cd "$TARGET" 2>/dev/null && pwd -P)" || die E00 "작업 폴더가 없습니다." "Codex 앱에서 빈 폴더(권장: ~/llmwiki)를 열고 다시 시작하세요."
say "LLM 위키 스타터 키트 설치 (macOS bootstrap) - 예상 5~10분, 다운로드 약 60MB"
step 0 "폴더 점검"
say "  작업 폴더   : $TARGET"
say "  실행 사용자 : $(whoami)"
say "  사용자 폴더 : $HOME"
H="$(cd "$HOME" && pwd -P)"
case "$TARGET" in
  *"/Library/Mobile Documents/"*|*"/Library/CloudStorage/"*|*OneDrive*|*"Google Drive"*|*Dropbox*)
    die E00 "클라우드 동기화 폴더 안입니다(iCloud/OneDrive/Google Drive/Dropbox)." "Finder에서 홈 폴더에 llmwiki 폴더를 만들고(~/llmwiki), Codex 앱에서 그 폴더를 연 뒤 같은 문장을 다시 보내세요." ;;
esac
for s in "$H" "$H/Documents" "$H/Desktop" "$H/Downloads" "/"; do
  [ "$TARGET" = "$s" ] && die E00 "홈/문서/바탕화면/다운로드 폴더 자체를 열었습니다." "~/llmwiki 같은 새 빈 폴더를 만들어 Codex 앱에서 열고 다시 시작하세요."
done
if [ -d "$H/Library/Mobile Documents/com~apple~CloudDocs/Documents" ] || [ -d "$H/Library/Mobile Documents/com~apple~CloudDocs/Desktop" ]; then
  case "$TARGET" in "$H/Documents/"*|"$H/Desktop/"*)
    die E00 "iCloud '데스크탑 및 문서 폴더'가 켜져 있어 이 폴더는 iCloud로 동기화됩니다." "~/llmwiki(홈 바로 아래)에 새 폴더를 만들어 다시 시작하세요." ;;
  esac
fi
KIT_HERE=0; [ -f "$TARGET/tools/llmwiki/cli.py" ] && [ -f "$TARGET/AGENTS.md" ] && KIT_HERE=1
# shellcheck disable=SC2010  # 화면 표시용 이름 목록
OTHERS="$(cd "$TARGET" && ls -A | grep -v -x -e .DS_Store -e .git -e .llmwiki-install.log -e .codex -e .localized | head -8 | tr '\n' ' ')"
if [ -n "$OTHERS" ] && [ $KIT_HERE -eq 0 ] && [ $ALLOW_NONEMPTY -eq 0 ]; then
  die E00 "폴더가 비어 있지 않습니다: $OTHERS" "새 빈 폴더(권장: ~/llmwiki)를 열어 다시 시작하세요. 기존 연구 폴더에 넣으려면 README의 'llmwiki init' 방법을 쓰세요."
fi
[ $KIT_HERE -eq 1 ] && say "  이미 키트가 있는 폴더 → 이어서 설치(기존 파일 보존)" || say "  빈 폴더 확인"
if [ $CHECK_ONLY -eq 1 ]; then
  say ""; say "CHECK OK - 설치를 진행해도 됩니다."; say "RESULT: CHECK_OK"
  case "$REPO_URL" in
    ""|*"<"*) ;;
    *)
      SELF="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
      say "AGENT: Step 2 of 2. First say to the student exactly (Korean):"
      say "AGENT_SAY: 설치를 시작합니다(5~10분, 창을 닫지 마세요). 곧 승인 창이 뜹니다. [승인]을 누르세요. '명령어 도구 설치' 창이 뜨면 [설치]를 눌러도, [나중에]를 눌러도 됩니다(설치는 그대로 계속됩니다)."
      say "AGENT: Then run this ONE command outside the sandbox (request approval/escalated, justification '설치 파일 받기', timeout 1200000 ms). Wait until it ends, even if it looks stuck:"
      say "AGENT_CMD: bash \"$SELF\" --repo \"$REPO_URL\""
      say "AGENT: Then branch ONLY on the line starting with 'RESULT:' and follow the 'AGENT:' lines printed after it." ;;
  esac
  exit 0
fi
LOG="$TARGET/.llmwiki-install.log"; say "--- 설치 시작 $(date '+%Y-%m-%d %H:%M:%S') ---"

# ---------------------------------------------------------------- 1. 기본 도구
step 1 "기본 도구 확인 (curl · unzip)"
for t in curl unzip; do command -v "$t" >/dev/null 2>&1 || die E01 "$t 명령이 없습니다." "macOS 기본 도구입니다. 화면을 강사에게 보여 주세요."; done
say "  OK"

# ---------------------------------------------------------------- 2. Git (선택)
step 2 "Git (선택 - 없어도 설치는 계속됩니다)"
GIT=""
# /usr/bin/git 은 Xcode 명령어 도구가 없으면 설치 팝업을 띄우는 '빈 껍데기'이므로 xcode-select로 먼저 확인한다.
if [ -x /opt/homebrew/bin/git ]; then GIT=/opt/homebrew/bin/git
elif [ -x /usr/local/bin/git ]; then GIT=/usr/local/bin/git
elif [ "$(uname)" != "Darwin" ] && command -v git >/dev/null 2>&1; then GIT="$(command -v git)"
elif [ "$(uname)" = "Darwin" ] && xcode-select -p >/dev/null 2>&1; then GIT=/usr/bin/git
fi
if [ -n "$GIT" ]; then say "  Git 있음: $GIT"
elif [ $SKIP_GIT -eq 1 ]; then say "  Git 건너뜀"
elif [ "$(uname)" = "Darwin" ]; then
  xcode-select --install >/dev/null 2>&1 || true
  say "  [E02] Git이 없습니다. 화면에 'Xcode 명령어 도구 설치' 창이 뜨면 [설치]를 누르세요(5~15분)."
  say "        창을 기다리지 않아도 이번 설치는 ZIP으로 계속됩니다. Git은 나중에 버전 관리용입니다."
fi

# ---------------------------------------------------------------- 3. uv + Python
step 3 "Python 3.12 준비 (uv, 관리자 권한 없음, 1~2분)"
find_uv() { for c in "$HOME/.local/bin/uv" /opt/homebrew/bin/uv /usr/local/bin/uv; do [ -x "$c" ] && { echo "$c"; return; }; done; command -v uv 2>/dev/null; }
UV="$(find_uv)"
if [ -z "$UV" ]; then
  say "  uv 설치(astral.sh 공식 설치 스크립트, 홈 폴더에 설치)"
  TMPI="$(mktemp -t llmwiki-uv.XXXXXX)"
  if dl https://astral.sh/uv/install.sh "$TMPI"; then run sh "$TMPI"; fi
  rm -f "$TMPI"; UV="$(find_uv)"
fi
PY=""
if [ -n "$UV" ]; then
  say "  uv: $UV"
  run "$UV" python install 3.12 || run "$UV" python install 3.12
  PY="$("$UV" python find 3.12 2>/dev/null)"
else
  say "  [E03] uv를 설치하지 못했습니다 → 이미 설치된 Python을 찾습니다"
  for c in /opt/homebrew/bin/python3 /usr/local/bin/python3 /Library/Frameworks/Python.framework/Versions/3.1[0-9]/bin/python3; do
    [ -x "$c" ] && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null && { PY="$c"; break; }
  done
fi
[ -z "$PY" ] && die E04 "Python 3.10 이상을 준비하지 못했습니다." "인터넷 연결을 확인하고 같은 문장을 다시 보내세요. 두 번째도 같으면 강사에게 화면을 보여 주세요."
say "  Python: $PY"

# ---------------------------------------------------------------- 4. 키트 받기 + 병합
step 4 "키트 받기 + 작업 폴더에 복사 (기존 파일은 건드리지 않음)"
TMPK="$(mktemp -d -t llmwiki-kit.XXXXXX)"; KIT=""
if [ -n "$KIT_SOURCE" ]; then KIT="$KIT_SOURCE"; say "  로컬 키트 사용: $KIT"
elif [ $KIT_HERE -eq 1 ] && [ -f "$TARGET/setup/requirements.txt" ]; then say "  이미 키트가 있음 → 받기 생략"
else
  case "$REPO_URL" in ""|*"<"*) die E05 "저장소 주소(--repo)가 없습니다." "INSTALL_FOR_AGENT.md의 명령에 학생이 준 주소를 그대로 넣으세요." ;; esac
  REPO_URL="${REPO_URL%/}"; REPO_URL="${REPO_URL%.git}"
  if [ -n "$GIT" ]; then
    say "  git clone $REPO_URL"
    run "$GIT" clone --depth 1 --branch "$BRANCH" "$REPO_URL.git" "$TMPK/kit" && KIT="$TMPK/kit" || say "  git clone 실패 → ZIP으로 받기"
  fi
  if [ -z "$KIT" ]; then
    say "  ZIP 받기: $REPO_URL/archive/refs/heads/$BRANCH.zip"
    dl "$REPO_URL/archive/refs/heads/$BRANCH.zip" "$TMPK/kit.zip" || die E01 "키트 ZIP을 받지 못했습니다." "인터넷 연결과 저장소 주소를 확인하세요."
    unzip -q "$TMPK/kit.zip" -d "$TMPK/x" || die E05 "ZIP 압축 풀기 실패" "같은 문장을 다시 보내 주세요."
    KIT="$(find "$TMPK/x" -mindepth 1 -maxdepth 1 -type d | head -1)"
  fi
fi
if [ -n "$KIT" ]; then
  [ -f "$KIT/tools/llmwiki/cli.py" ] || die E05 "받은 파일에 키트(tools/llmwiki)가 없습니다: $KIT" "저장소 주소가 맞는지 확인하세요."
  COPIED=0; SKIPPED=0
  while IFS= read -r -d '' f; do
    rel="${f#"$KIT"/}"
    case "$rel" in .git/*|.venv/*|*__pycache__*) continue ;; esac
    dst="$TARGET/$rel"
    if [ -e "$dst" ]; then
      case "$rel" in
        AGENTS.md|README.md|.gitignore)
          alt="AGENTS.llmwiki.md"; [ "$rel" = README.md ] && alt="README.llmwiki.md"; [ "$rel" = .gitignore ] && alt=".gitignore.llmwiki"
          if ! cmp -s "$f" "$dst" && [ ! -e "$TARGET/$alt" ]; then cp -p "$f" "$TARGET/$alt"; say "  기존 파일과 달라서 옆에 둠: $alt (합칠지는 사람이 결정)"; fi ;;
      esac
      SKIPPED=$((SKIPPED + 1)); continue
    fi
    mkdir -p "$(dirname "$dst")" && cp -p "$f" "$dst" || die E05 "파일 복사 실패: $rel" "폴더 권한을 확인하세요(~/llmwiki 권장)."
    COPIED=$((COPIED + 1))
  done < <(find "$KIT" -type f -print0)
  say "  복사 ${COPIED}개 · 이미 있어서 건너뜀 ${SKIPPED}개"
fi
for need in AGENTS.md tools/llmwiki/cli.py setup/requirements.txt .agents/skills/wiki-ingest/SKILL.md; do
  [ -f "$TARGET/$need" ] || die E05 "필수 파일이 없습니다: $need" "같은 문장을 다시 보내 주세요(이미 받은 파일은 보존됩니다)."
done
chmod +x "$TARGET/llmwiki" 2>/dev/null || true

# ---------------------------------------------------------------- 5. .venv + 패키지
step 5 "가상환경(.venv) + 패키지 설치 (pymupdf · pyyaml · pyzotero, 1~3분)"
VPY="$TARGET/.venv/bin/python"
if [ -x "$VPY" ] && "$VPY" -c 'import sys' 2>/dev/null; then say "  기존 .venv 재사용: $VPY"
else
  [ -d "$TARGET/.venv" ] && { say "  망가진 .venv를 다시 만듭니다"; rm -rf "$TARGET/.venv"; }
  if [ -n "$UV" ]; then run "$UV" venv "$TARGET/.venv" --python "$PY"; else run "$PY" -m venv "$TARGET/.venv"; fi
  [ -x "$VPY" ] || die E04 "가상환경을 만들지 못했습니다." "같은 문장을 다시 보내 주세요."
fi
REQ="$TARGET/setup/requirements.txt"
if [ -n "$UV" ]; then run "$UV" pip install --python "$VPY" -r "$REQ" || run "$UV" pip install --python "$VPY" -r "$REQ"
else run "$VPY" -m pip install --disable-pip-version-check -r "$REQ" || run "$VPY" -m pip install --disable-pip-version-check -r "$REQ"; fi
[ $? -eq 0 ] || die E06 "패키지 설치 실패." "인터넷 연결을 확인하고 같은 문장을 다시 보내세요."

# ---------------------------------------------------------------- 6. UTF-8
step 6 "한글 출력 설정"
say "  macOS 기본이 UTF-8 · ./llmwiki 실행기가 PYTHONUTF8=1을 매번 설정"

# ---------------------------------------------------------------- 7. git init
step 7 "버전 관리 폴더로 만들기 (git init, Git이 있을 때만)"
if [ -n "$GIT" ] && [ ! -e "$TARGET/.git" ]; then run "$GIT" -C "$TARGET" init -q; say "  git init 완료"
elif [ -n "$GIT" ]; then say "  이미 git 저장소"; else say "  Git 없음 - 건너뜀(없어도 됨)"; fi

# ---------------------------------------------------------------- 8. doctor
step 8 "환경 점검 (llmwiki doctor)"
JSON="$(PYTHONPATH="$TARGET/tools" LLMWIKI_ROOT="$TARGET" "$VPY" -m llmwiki --root "$TARGET" doctor --json 2>/dev/null)"
OUT="$(printf '%s' "$JSON" | "$VPY" -c '
import json, sys
d = json.load(sys.stdin)
for c in d["checks"]:
    if c["level"] != "PASS":
        print("  [%s] %s  %s" % (c["level"], c["name"], c["message"]))
print("  PASS %d개 생략 · FAIL %d · WARN %d" % (sum(c["level"] == "PASS" for c in d["checks"]), d["fail"], d["warn"]))
print("FAIL=%d" % d["fail"])
print(d["summary"])' 2>&1)" || die E07 "doctor를 실행하지 못했습니다." "같은 문장을 다시 보내 주세요."
FAILS="$(printf '%s\n' "$OUT" | sed -n 's/^FAIL=//p')"
printf '%s\n' "$OUT" | grep -v '^FAIL=' | sed '$d' | while IFS= read -r l; do say "$l"; done
rm -rf "$TMPK"
say ""
if [ "${FAILS:-1}" != "0" ]; then  # 종료 17: '다음' 안내는 찍지 않는다(QA H33)
  say "$(printf '%s\n' "$OUT" | tail -1)"
  say "RESULT: DOCTOR_FAIL"
  say "AGENT: Do NOT rerun. Read the line '설치 미완료 ❌ / 해결할 것: …' above to the student word for word, then say: '이것을 고친 뒤 같은 설치 문장을 다시 보내 주세요(이미 받은 것은 건너뜁니다).' Then STOP."
  exit 17
fi
say "다음: Codex 앱에서 이 폴더로 '새 채팅'을 열고 「이 폴더의 AGENTS.md와 사용 가능한 스킬 목록을 말해줘」라고 보내세요."
say "$(printf '%s\n' "$OUT" | tail -1)"
say "RESULT: OK"
say "AGENT: Say to the student, in this order: (1) the line starting with '설치 완료' above; (2) '새 채팅을 열고 「이 폴더의 AGENTS.md와 사용 가능한 스킬 목록을 말해줘」라고 보내세요.'; (3) 'Zotero를 켜고 설정 → 고급에서 다른 응용 프로그램과 통신 허용을 켠 뒤, 새 채팅에서 「llmwiki doctor --offline 을 승인 요청으로 실행해 줘」라고 보내세요.' Then STOP."
# 받은 bootstrap 사본은 성공했을 때만 지운다(QA H37)
[ "$(basename "$0")" = "llmwiki-bootstrap.sh" ] && case "$0" in /tmp/*) rm -f "$0" ;; esac
exit 0
