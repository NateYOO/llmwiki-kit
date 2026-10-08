# INSTALL_FOR_AGENT.md — 에이전트용 설치 절차 (고정)

> 이제현 박사님의 Paper Curation(https://github.com/jehyunlee/paper-curation) 아이디어를 바탕으로 만든 키트입니다. 감사드립니다. (코드 복사 없음)

> 이 문서는 **AI 에이전트(Codex)** 가 따르는 설치 절차의 원본입니다. 사람은 승인 창에서 [승인]만 누르면 됩니다.
> **에이전트는 이 문서를 따로 받지 않아도 됩니다.** 학생 설치 문장에 첫 명령이 글자 그대로 들어 있고, 그다음 명령은 그 명령의 출력(`AGENT_CMD:` 줄)이 알려 줍니다.
> 이 문서를 읽어야 할 때의 주소: `{REPO}/raw/main/INSTALL_FOR_AGENT.md` (🔐 인터넷, 사람이 볼 때는 `{REPO}/blob/main/INSTALL_FOR_AGENT.md`).

## 0. 학생 설치 문장 (저장소: https://github.com/NateYOO/llmwiki-kit)
````text
LLM 위키 키트를 이 폴더에 설치해 주세요. 저장소: https://github.com/NateYOO/llmwiki-kit
1) 먼저 저에게 "곧 승인 창이 뜹니다. [승인]을 누르세요"라고 말하고,
2) 제 컴퓨터에 맞는 아래 한 줄을 샌드박스 밖(승인 요청)으로 글자 그대로 실행한 뒤,
3) 출력 끝의 RESULT: 줄과 AGENT: 줄이 시키는 대로만 하세요. 다른 명령은 만들지 마세요.
Windows: [Console]::OutputEncoding=[Text.Encoding]::UTF8; iwr -useb https://github.com/NateYOO/llmwiki-kit/raw/main/setup/bootstrap-windows.ps1 -OutFile "$env:TEMP\llmwiki-bootstrap.ps1"; powershell -NoProfile -ExecutionPolicy Bypass -File "$env:TEMP\llmwiki-bootstrap.ps1" -CheckOnly -RepoUrl https://github.com/NateYOO/llmwiki-kit
macOS: curl -fsSL https://github.com/NateYOO/llmwiki-kit/raw/main/setup/bootstrap-mac.sh -o /tmp/llmwiki-bootstrap.sh && bash /tmp/llmwiki-bootstrap.sh --check-only --repo https://github.com/NateYOO/llmwiki-kit
````
- 이 한 줄이 **받기 + 폴더 점검**을 학생 계정(샌드박스 밖)에서 한 번에 한다. 그래서 샌드박스 사용자가 `%TEMP%`를 못 읽는 문제가 없고, 점검 결과(사용자 폴더·바탕 화면/문서 판정)도 학생 기준이다(QA H32).
- `[Console]::OutputEncoding=…UTF8`은 안쪽 powershell의 UTF-8 출력을 바깥 셸이 깨지지 않게 읽게 한다(QA H34). 판정은 어차피 ASCII 줄(`RESULT:`)로만 한다.

## 규칙 (반드시 지킬 것)
1. 명령은 **글자 그대로** 실행한다. 1단계는 학생 문장의 명령, 2단계는 출력의 `AGENT_CMD:` 줄 그대로. 새 명령을 만들지 않는다.
2. 🔐 명령(1단계·2단계)은 실행 **직전에** 학생에게 말할 문장을 먼저 말한다(1단계: "곧 승인 창이 뜹니다. [승인]을 누르세요", 2단계: 출력의 `AGENT_SAY:` 줄). 처음부터 샌드박스 밖(승인 요청, escalated)으로, 이유 문구 `설치 파일 받기`.
3. 시간 제한을 지정할 수 있으면 **1200000ms(20분)**. 2단계는 5~10분 걸린다. 멈춘 것처럼 보여도 끝날 때까지 기다린다.
4. 분기는 **`RESULT:` 줄로만** 한다(아래 표). 한글 문구가 깨져 보여도 `RESULT:`·`AGENT:` 줄은 ASCII라 읽을 수 있다.
5. 하지 말 것: 새 스크립트 작성, 다른 프로그램 설치, `Set-ExecutionPolicy` 같은 시스템 설정 변경, 학생 파일 이동·삭제, 이 문서에 없는 명령 실행.
   `Access denied`·`UnauthorizedAccess`·받은 파일이 사라짐이면 Windows 보안 → **보호 기록**을 학생에게 확인해 달라고 하고 멈춘다. 실시간 보호 끄기·제외 추가·제어된 폴더 액세스 끄기는 **제안하지 않는다**.
6. 1단계 명령 자체가 실패해 `RESULT:` 줄이 없으면(인터넷·주소 문제): 한 번만 다시 실행 → 또 실패하면 "설치가 멈췄습니다. 오류 코드 E01 — 손을 들어 이 화면을 보여 주세요." + 출력 마지막 20줄을 붙이고 멈춘다.

## 단계
| 단계 | 실행 | 학생에게 먼저 말할 것 |
|---|---|---|
| 1. 받기 + 폴더 점검 🔐 | 학생 문장의 Windows/macOS 한 줄 | "곧 승인 창이 뜹니다. [승인]을 누르세요" |
| 2. 설치 🔐 | 1단계 출력의 `AGENT_CMD:` 줄 그대로 (Windows 예: `[Console]::OutputEncoding=[Text.Encoding]::UTF8; powershell -NoProfile -ExecutionPolicy Bypass -File "<TEMP>\llmwiki-bootstrap.ps1" -RepoUrl "{REPO}"`, macOS 예: `bash "/tmp/llmwiki-bootstrap.sh" --repo "{REPO}"`) | `AGENT_SAY:` 줄 그대로 — 아래 참고 |
| 3. 마무리 | 없음 | `RESULT: OK` 뒤의 `AGENT:` 줄 그대로 (아래 W2) |

2단계 직전 문장(`AGENT_SAY:`, Windows): **"설치를 시작합니다(5~10분, 창을 닫지 마세요). 곧 승인 창이 뜹니다. [승인]을 누르세요. 설치 중에 화면이 어두워지며 'Windows 확인 창'이 뜨면 [예]를 누르세요. 아무 창도 안 보이는데 오래 멈춰 있으면 화면 아래 작업 표시줄에서 깜빡이는 방패 아이콘을 눌러 주세요."**
(명령이 도는 동안에는 에이전트가 말할 수 없으므로 UAC 안내는 **미리** 한다. bootstrap은 기본으로 Git을 설치하지 않아(이미 있으면 사용, 강사가 `-WithGit`을 붙일 때만 winget 설치) 보통 UAC가 뜨지 않는다. 뜨는 경우(대체 설치 경로)에도 작업 표시줄에서 깜빡이기만 할 수 있어 미리 안내한다 — QA H35. 거절해도 설치는 계속된다.)
macOS: **"설치를 시작합니다(5~10분, 창을 닫지 마세요). 곧 승인 창이 뜹니다. [승인]을 누르세요. '명령어 도구 설치' 창이 뜨면 [설치]를 눌러도, [나중에]를 눌러도 됩니다(설치는 그대로 계속됩니다)."**

## RESULT 줄에 따른 행동
| `RESULT:` | 종료 코드 | 에이전트 행동 |
|---|---|---|
| `CHECK_OK` | 0 | 2단계로(`AGENT_SAY:` 말하기 → `AGENT_CMD:` 실행) |
| `OK` | 0 | W2 마무리 네 문장을 말하고 끝 |
| `DOCTOR_FAIL` | 17 | **다시 실행하지 않는다.** 위의 `설치 미완료 ❌ / 해결할 것: …` 줄을 그대로 읽어 주고 "이것을 고친 뒤 같은 설치 문장을 다시 보내 주세요(이미 받은 것은 건너뜁니다)."라고 말한 뒤 멈춘다(QA H33) |
| `FAIL E00` / `FAIL E05` | 10 / 15 | `해결:` 줄을 그대로 읽어 주고 멈춘다(다시 실행해도 같은 결과) |
| `FAIL E01`~`E07` (그 밖) | 10+n (E07만 27) | 같은 명령을 **한 번만** 다시 → 또 실패하면 "설치가 멈췄습니다. 오류 코드 E0n — 손을 들어 이 화면을 보여 주세요." + 마지막 20줄, 멈춤 |

**W2. 마무리 (RESULT: OK)** — 네 문장을 순서대로 말하고 끝낸다.
설치 스크립트는 doctor가 통과하면 **같은 실행 안에서**(승인 추가 없음) 9단계 `llmwiki welcome`을 돌린다: 위키가 비어 있으면 샘플 논문 3편을 넣고(`llmwiki sample`과 같음, 나중에 「샘플 논문 빼 줘」 = `llmwiki sample --remove`), 위키 화면 `site/index.html`을 만들고, 가능하면 브라우저로 연다. 실패해도 설치 결과(`RESULT: OK`)는 바뀌지 않는다.
1. 출력의 `설치 완료 ✅ / 남은 일: …` 줄 그대로.
2. 출력의 `위키 화면: file:///…/site/index.html` 줄 그대로(브라우저로 열었다고 나오면 "브라우저에 샘플 논문 3편이 보이면 성공이에요."를 덧붙인다).
3. "**새 채팅**을 열고 「이 폴더의 AGENTS.md와 사용 가능한 스킬 목록을 말해줘」라고 보내세요."
4. "Zotero를 켜고 설정 → 고급에서 다른 응용 프로그램과 통신 허용을 켠 뒤, 새 채팅에서 「llmwiki doctor --offline 을 승인 요청으로 실행해 줘」라고 보내세요."
   (새 채팅의 doctor는 샌드박스 안이면 인터넷·127.0.0.1 접속이 막혀 거짓 WARN이 날 수 있다. `--offline`은 arXiv·Crossref 점검을 빼고, 승인 요청(샌드박스 밖)은 Zotero 로컬 API 접속을 보장한다 — QA H36.)

## 오류 코드 (bootstrap 출력의 `[E..]`, 종료 코드 = 10 + 번호, E07만 27 — 17은 DOCTOR_FAIL 전용)
| 코드 | 뜻 | 학생/강사 조치 |
|---|---|---|
| E00 | 폴더 문제(비어 있지 않음·OneDrive·iCloud·문서/바탕 화면 자체) | 새 빈 폴더 `C:\llmwiki` / `~/llmwiki`를 Codex 앱에서 열고 같은 문장 다시 |
| E01 | 인터넷/다운로드 실패(설치 파일을 새로 받지 못해 남아 있던 옛 사본이 돈 경우 포함 — 옛 사본은 지워짐) | 연결 확인 후 같은 문장 다시 |
| E02 | Git 설치 실패(`-WithGit`일 때만 시도) | **치명 아님**(ZIP으로 계속됨) |
| E03 | uv 설치 실패 | 자동으로 winget Python으로 대체 시도 |
| E04 | Python/가상환경 실패 | 같은 문장 다시 → 반복되면 강사 |
| E05 | 키트 받기·복사 실패(주소 오류, 백신/제어된 폴더 액세스) | 저장소 주소 확인, `C:\llmwiki` 사용, 보호 기록 확인 |
| E06 | 패키지 설치 실패 | 연결 확인 후 다시 |
| E07 (종료 27) | doctor 실행 실패 | 같은 명령 한 번 다시 → 반복되면 강사 |
| 17 (`DOCTOR_FAIL`) | 설치는 됐지만 doctor FAIL 있음 | '해결할 것'을 고치고 같은 문장 다시(받은 것은 건너뜀) |

> 참고: 설치는 사용자 환경 변수 `PYTHONUTF8=1`을 한 번 설정한다(한글 출력용, 관리자 권한 불필요). 임시 파일(`%TEMP%\llmwiki-bootstrap.ps1`, `/tmp/llmwiki-bootstrap.sh`)은 성공하면 지운다(실패 때는 다시 실행할 수 있게 남김). 남은 사본이 15분보다 오래됐는데 점검 명령으로 실행되면(받기 실패) 그 사본을 지우고 E01로 멈춘다. 키트 임시 폴더(`llmwiki-kit-*`)는 오류로 끝나도 지운다.
> 참고(설치 뒤): `.agents/skills/`는 Codex가 쓰기 보호하는 폴더다. 나중에 스킬을 새로 만들 때 쓰기가 막히면 CLI는 `codex … -s workspace-write --add-dir .agents`로 실행한다(앱에서는 승인 창). 설치 단계에서는 필요 없다.
