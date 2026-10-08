# INSTALL_FOR_AGENT.md — 에이전트용 설치 절차 (고정)

> 이제현 박사님의 Paper Curation(https://github.com/jehyunlee/paper-curation) 아이디어를 바탕으로 만든 키트입니다. 감사드립니다. (코드 복사 없음)

> 이 문서는 **AI 에이전트(Codex)** 가 읽고 그대로 실행하는 설치 절차입니다. 사람은 승인 창에서 [승인]만 누르면 됩니다.
> 학생이 보낸 문장 예: `<REPO_URL> 의 INSTALL_FOR_AGENT.md 를 그대로 따라 이 폴더에 설치해 주세요.`

## 규칙 (반드시 지킬 것)
1. 아래 명령을 **글자 그대로** 실행한다. 바꾸는 곳은 `{REPO}` 하나뿐이다. 학생이 준 저장소 주소를 넣되, 끝의 `/`와 `.git`은 뺀다(예: `https://github.com/abc/llmwiki-starter-kit`).
2. 🔐 표시가 있는 명령은 인터넷이 필요하다. 실행하기 **직전에** 학생에게 정확히 이렇게 말한다:
   **"곧 승인 창이 뜹니다. [승인]을 누르세요"**
   그리고 처음부터 샌드박스 밖 실행(승인 요청, escalated)으로 실행한다. 이유 문구: `설치 파일 받기`.
3. 시간 제한을 지정할 수 있으면 **1200000ms(20분)** 로 지정한다. 2단계는 5~10분 걸린다. 출력이 멈춘 것처럼 보여도 끝날 때까지 기다린다.
4. 명령이 실패하면 **한 번만** 똑같이 다시 실행한다. 같은 오류가 또 나면 멈추고 학생에게 말한다:
   **"설치가 멈췄습니다. 오류 코드 ○○ — 손을 들어 이 화면을 보여 주세요."** (○○ = 출력의 `[E..]` 코드. 없으면 종료 코드)
   그리고 출력의 마지막 20줄을 고치지 말고 그대로 붙인다.
5. 하지 말 것: 새 스크립트 작성, 다른 프로그램 설치, `Set-ExecutionPolicy` 같은 시스템 설정 변경, 학생 파일 이동·삭제, 이 문서에 없는 명령 실행.
   `Access denied`·`UnauthorizedAccess`·받은 파일이 사라짐이면 Windows 보안 → **보호 기록**을 학생에게 확인해 달라고 하고 멈춘다. 실시간 보호 끄기·제외 추가·제어된 폴더 액세스 끄기는 **제안하지 않는다**.
6. 학생 컴퓨터가 Windows이면 **W절**, macOS이면 **M절**만 따른다.

## W. Windows (PowerShell)

**W0. 폴더 점검** 🔐
```powershell
Invoke-WebRequest -UseBasicParsing -Uri "{REPO}/raw/main/setup/bootstrap-windows.ps1" -OutFile "$env:TEMP\llmwiki-bootstrap.ps1"
```
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:TEMP\llmwiki-bootstrap.ps1" -CheckOnly
```
- 마지막 줄이 `CHECK OK`로 시작하면 → W1로.
- `[E00]`이 나오면 → 출력의 `해결:` 줄을 학생에게 그대로 읽어 주고 **멈춘다**. (빈 폴더가 아님 / OneDrive 안 / 문서·바탕 화면 자체를 엶 → 권장 폴더 `C:\llmwiki`)
- 첫 명령이 실패하면(인터넷·주소 문제) → 규칙 4.

**W1. 설치** 🔐 (5~10분. 학생에게 먼저 "5~10분 걸립니다. 창을 닫지 마세요"라고 말한다.)
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:TEMP\llmwiki-bootstrap.ps1" -RepoUrl "{REPO}"
```
- 중간에 Windows의 "이 앱이 디바이스를 변경하도록 허용하시겠어요?" 창이 뜰 수 있다(Git 설치). 학생에게 "[예]를 누르세요"라고 말한다. 거절해도 설치는 계속된다(Git은 선택).
- 마지막 줄이 `설치 완료 ✅`로 시작하면 → W2로.
- 마지막 줄이 `설치 중단 ❌ / 오류 코드 E..`이면 → 규칙 4. (다시 실행해도 안전하다. 이미 받은 파일은 보존된다.)

**W2. 마무리** — 학생에게 아래 세 줄을 그대로 말하고 끝낸다.
1. 출력의 마지막 줄(`설치 완료 ✅ / 남은 일: …`)을 그대로.
2. "Codex 앱에서 이 폴더로 **새 채팅**을 열고 「이 폴더의 AGENTS.md와 사용 가능한 스킬 목록을 말해줘」라고 보내 보세요."
3. 남은 일에 Zotero가 있으면: "Zotero를 켜고 설정 → 고급 → '이 컴퓨터의 다른 응용 프로그램이 Zotero와 통신하도록 허용'을 켠 뒤, 새 채팅에서 `.\llmwiki.cmd doctor` 를 실행해 달라고 하세요."

## M. macOS (zsh/bash)

**M0. 폴더 점검** 🔐
```bash
curl -fsSL "{REPO}/raw/main/setup/bootstrap-mac.sh" -o /tmp/llmwiki-bootstrap.sh && bash /tmp/llmwiki-bootstrap.sh --check-only
```
- 마지막 줄이 `CHECK OK`로 시작하면 → M1로. `[E00]`이면 `해결:` 줄을 그대로 읽어 주고 멈춘다(권장 폴더 `~/llmwiki`).

**M1. 설치** 🔐 (5~10분. "5~10분 걸립니다. 창을 닫지 마세요"라고 먼저 말한다.)
```bash
bash /tmp/llmwiki-bootstrap.sh --repo "{REPO}"
```
- "명령어 개발자 도구를 설치하겠습니까?" 창이 뜨면 학생에게 "[설치]를 누르세요. 기다리지 않아도 됩니다"라고 말한다(Git용, 선택). 설치는 그대로 계속된다.
- 마지막 줄 `설치 완료 ✅` → M2. `설치 중단 ❌ / 오류 코드 E..` → 규칙 4.

**M2. 마무리** — W2와 같다. 단, doctor 명령은 `./llmwiki doctor`.

## 오류 코드 (bootstrap 출력의 `[E..]`, 종료 코드 = 10 + 번호)
| 코드 | 뜻 | 학생/강사 조치 |
|---|---|---|
| E00 | 폴더 문제(비어 있지 않음·OneDrive·iCloud·문서/바탕 화면 자체) | 새 빈 폴더 `C:\llmwiki` / `~/llmwiki`를 Codex 앱에서 열고 같은 문장 다시 |
| E01 | 인터넷/다운로드 실패 | 연결 확인 후 같은 문장 다시 |
| E02 | Git 설치 실패 | **치명 아님**(ZIP으로 계속됨) |
| E03 | uv 설치 실패 | 자동으로 winget Python으로 대체 시도 |
| E04 | Python/가상환경 실패 | 같은 문장 다시 → 반복되면 강사 |
| E05 | 키트 받기·복사 실패(주소 오류, 백신/제어된 폴더 액세스) | 저장소 주소 확인, `C:\llmwiki` 사용 |
| E06 | 패키지 설치 실패 | 연결 확인 후 다시 |
| E07 | doctor 실행 실패 | 강사 |
| 17 | 설치는 됐지만 doctor FAIL 있음 | 마지막 줄의 '해결할 것' 확인 |

> 참고(설치 뒤): `.agents/skills/`는 Codex가 쓰기 보호하는 폴더다. 나중에 스킬을 새로 만들 때 쓰기가 막히면 CLI는 `codex … -s workspace-write --add-dir .agents`로 실행한다(앱에서는 승인 창). 설치 단계에서는 필요 없다.
