# LLM 위키 스타터 키트 — Zotero 논문을 나만의 지식 파트너로

> **이제현 박사님의 Paper Curation 아이디어를 바탕으로 만들었습니다. 감사드립니다.**
> 원작: [이제현 박사님 · Paper Curation](https://github.com/jehyunlee/paper-curation) · 위키 구조: [Andrej Karpathy · LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
> 이 키트는 두 아이디어(리뷰 형식, raw→wiki→schema 3층 구조)를 바탕으로 **새로 구현**했습니다. 원작의 코드는 한 줄도 복사하지 않았습니다(Paper Curation 저장소에는 라이선스가 없어 형식만 참고했습니다).

0\) 빈 폴더를 만들고 Codex 앱에서 [폴더 열기] (예: C:\llmwiki)\
1\) 오른쪽 위 복사 버튼\
2\) 새 채팅에 붙여넣기\
3\) [승인]

```text
LLM 위키 키트를 이 폴더에 설치해 주세요. 저장소: https://github.com/NateYOO/llmwiki-kit
1) 먼저 저에게 "곧 승인 창이 뜹니다. [승인]을 누르세요"라고 말하고,
2) 제 컴퓨터에 맞는 아래 한 줄을 샌드박스 밖(승인 요청)으로 글자 그대로 실행한 뒤,
3) 출력 끝의 RESULT: 줄과 AGENT: 줄이 시키는 대로만 하세요. 다른 명령은 만들지 마세요.
Windows: [Console]::OutputEncoding=[Text.Encoding]::UTF8; iwr -useb https://github.com/NateYOO/llmwiki-kit/raw/main/setup/bootstrap-windows.ps1 -OutFile "$env:TEMP\llmwiki-bootstrap.ps1"; powershell -NoProfile -ExecutionPolicy Bypass -File "$env:TEMP\llmwiki-bootstrap.ps1" -CheckOnly -RepoUrl https://github.com/NateYOO/llmwiki-kit
macOS: curl -fsSL https://github.com/NateYOO/llmwiki-kit/raw/main/setup/bootstrap-mac.sh -o /tmp/llmwiki-bootstrap.sh && bash /tmp/llmwiki-bootstrap.sh --check-only --repo https://github.com/NateYOO/llmwiki-kit
```

## 0. 한눈에: 이 폴더 = 내 작업 폴더

```
llmwiki/                        ← ChatGPT 데스크톱 앱(Codex)에서 "이 폴더"를 엽니다
├── AGENTS.md                   ← 에이전트 규칙서 (반드시 맨 위에)
├── .agents/skills/             ← 스킬 4개 (반드시 맨 위에) — 숨김 폴더
│   ├── wiki-ingest/  wiki-query/  wiki-lint/  wiki-synthesize/
├── llmwiki   llmwiki.cmd       ← CLI 실행기 (macOS / Windows)
├── llmwiki.yaml                ← 설정 (Zotero 주소, 실습 컬렉션 이름)
├── wiki/                       ← 위키 (에이전트가 씀)
│   ├── index.md  log.md
│   ├── papers/<논문>/review.md · source.md · figures/ · tables/
│   └── topics/
├── drafts/                     ← 내 글·초안 (서론, 아이디어 메모)
├── raw/                        ← Zotero 밖 PDF (선택)
├── examples/sample-wiki/       ← 복구용 샘플 위키 3편 (CC BY 4.0)
├── tools/  setup/  .venv/      ← 프로그램 (건드리지 않음)
└── INSTALL_FOR_AGENT.md        ← 에이전트용 설치 절차
```

**왜 맨 위인가?** Codex는 앱에서 연 폴더(Primary 폴더)에서 `AGENTS.md`와 `.agents/skills/`를 자동으로 찾습니다.
- git이 없는 폴더에서는 **연 폴더 하나만** 봅니다. 키트를 하위 폴더(예: `내연구/starter-kit/`)에 넣고 바깥 폴더를 열거나, 하위 폴더를 열고 규칙서는 상위에 두면 **인식되지 않습니다.**
- git 저장소면 저장소 루트부터 연 폴더까지 차례로 찾습니다.
- (박스에서 codex-cli 0.154.0 `codex debug prompt-input`으로 5가지 배치를 직접 확인했습니다. 앱 버전에 따라 달라질 수 있습니다.)

**Claude Code를 쓰나요?** `CLAUDE.md`가 AGENTS.md와 같은 역할입니다. 맨 위에 `CLAUDE.md`를 만들고 한 줄만 쓰세요: `이 폴더의 AGENTS.md를 읽고 그대로 따르세요.`

**macOS Finder에서 `.agents`가 안 보이나요?** 이름이 `.`으로 시작하는 폴더는 숨겨집니다. Finder에서 **Cmd + Shift + .(마침표)** 를 누르면 보입니다(다시 누르면 숨김).

**권장 설정:** 모델 **GPT-6 Luna (`gpt-6-luna`)** · 추론 노력 **Medium**. (무료 계정에서 쓸 수 있는 모델이 Luna입니다. High는 사용량이 약 1.5배라 Medium으로 고정하세요.)

## 1. 설치 (기본: 한 문장 설치 — 터미널 필요 없음)

1. **빈 폴더 만들기** — Windows: `C:\llmwiki` · macOS: 홈 폴더의 `llmwiki` (OneDrive·iCloud·문서·바탕 화면 **안은 피하세요**: 동기화가 설치 파일 수천 개와 충돌합니다)
2. ChatGPT 데스크톱 앱 → Codex → 그 폴더 열기 (모델 Luna, 추론 Medium)
3. 채팅창에 **맨 위 복사 상자의 설치 문장**을 그대로 붙여 넣기 (상자 오른쪽 위 복사 버튼)
4. 에이전트가 "곧 승인 창이 뜹니다. [승인]을 누르세요"라고 하면 **[승인]** 을 누릅니다(보통 2번). Windows 확인 창(화면이 어두워지며 "이 앱이 디바이스를 변경하도록 허용…")은 보통 뜨지 않습니다(Git은 이미 있을 때만 씀). 혹시 뜨면 **[예]**, 창이 안 보이는데 오래 멈춰 있으면 **작업 표시줄에서 깜빡이는 방패 아이콘**을 누르세요.
5. 5~10분 뒤 `설치 완료 ✅ / 남은 일: …` 이 나오면 끝. **새 채팅**을 열어 2절의 인식 확인을 해 보세요.

- 설치 문장에 첫 명령(받기 + 폴더 점검)이 글자 그대로 들어 있어 에이전트가 따로 판단할 것이 없습니다. 다음 명령은 그 명령의 출력이 알려 줍니다(`AGENT_CMD:` 줄). 절차의 원본은 [INSTALL_FOR_AGENT.md](INSTALL_FOR_AGENT.md)입니다.

에이전트가 하는 일(학생은 승인만): 받기 + 폴더 점검 → (Windows) winget 확인·Git 확인(이미 있으면 사용, 설치는 강사 옵션 `-WithGit`) → **uv로 Python 3.12 설치(관리자 권한 없음, Microsoft Store python 별칭을 쓰지 않음)** → 키트 받기(Git이 없으면 ZIP) → `.venv`에 pymupdf·pyyaml·pyzotero 설치 → UTF-8 설정 → `llmwiki doctor`.
다시 실행해도 안전합니다(이미 있는 파일은 덮어쓰지 않음). 내 컴퓨터에 남는 변경: 사용자 환경 변수 `PYTHONUTF8=1`(한글 출력용, Windows) 하나와 uv·Python(사용자 폴더). 오류 코드(E00~E07, DOCTOR_FAIL 17)는 [INSTALL_FOR_AGENT.md](INSTALL_FOR_AGENT.md) 표를 보세요.

### 1-1. 다른 설치 방법
| 방법 | 언제 | 하는 법 |
|---|---|---|
| **Download ZIP** (표준 수동) | 에이전트 설치가 안 될 때 | GitHub 저장소 → 초록색 **Code** → **Download ZIP** → 압축 풀기 → 풀린 폴더를 `C:\llmwiki`(또는 `~/llmwiki`)로 옮김 → Codex에서 그 폴더를 열고 맨 위 설치 문장을 보냄(이미 키트가 있으면 받기를 건너뛰고 설치만 함) |
| git clone (고급) | Git을 쓰는 사람 | `git clone https://github.com/NateYOO/llmwiki-kit llmwiki` → 그 폴더에서 맨 위 설치 문장, 또는 아래 터미널 명령 |
| 터미널 한 줄 | 터미널에 익숙한 사람 | macOS: `curl -LsSf https://github.com/NateYOO/llmwiki-kit/raw/main/setup/install_mac.sh \| bash` · Windows PowerShell: `irm https://github.com/NateYOO/llmwiki-kit/raw/main/setup/install_windows.ps1 \| iex` |
| 수동 스크립트 | 키트 폴더 안에서 | Windows: `powershell -NoProfile -ExecutionPolicy Bypass -File setup\bootstrap-windows.ps1` · macOS: `bash setup/bootstrap-mac.sh` |

Windows에는 Git이 기본으로 없으므로 **Download ZIP**이 표준 수동 경로입니다.

### 1-2. 이미 있는 내 연구 폴더에 넣기 (중급)
**방법 A — CLI** (키트 폴더에서 한 번 설치를 마친 뒤):
```
./llmwiki init ~/Documents/my-thesis            # macOS
.\llmwiki.cmd init C:\Users\me\my-thesis         # Windows
```
기존 파일은 **절대 덮어쓰지 않습니다.** 대상에 `AGENTS.md`가 이미 있으면 키트 규칙서를 `AGENTS.llmwiki.md`로 옆에 두고 합치는 방법을 안내합니다(`--append-agents`를 주면 기존 AGENTS.md 끝에 "AGENTS.llmwiki.md를 따르라"는 짧은 블록만 덧붙임). 그다음 그 폴더에서 `setup` 스크립트를 한 번 더 실행해 `.venv`를 만듭니다.

**방법 B — Codex에 복사 부탁** (내 연구 폴더를 Codex에서 연 상태로, 아래를 그대로 붙여 넣기):
```
다음 경로의 LLM 위키 스타터 키트를 지금 열린 이 폴더의 맨 위에 설치해 줘.
키트 경로: <키트 폴더 경로>
1) 복사: AGENTS.md, .agents/ (폴더째), tools/, setup/, llmwiki, llmwiki.cmd, llmwiki.yaml, wiki/(index.md·log.md·papers/·topics/), drafts/README.md, raw/README.md, examples/, .gitattributes
2) 같은 이름의 파일이 이미 있으면 절대 덮어쓰지 말고 건너뛴 뒤 목록으로 알려 줘.
3) 이 폴더에 AGENTS.md가 이미 있으면 덮어쓰지 말고 키트 것을 AGENTS.llmwiki.md로 복사한 다음, 두 파일을 어떻게 합칠지 제안만 해 줘(내가 승인하기 전엔 기존 AGENTS.md를 고치지 마).
4) 끝나면 복사/건너뜀/합치기 제안을 표로 보여 주고, Windows면 powershell -NoProfile -ExecutionPolicy Bypass -File setup\bootstrap-windows.ps1 -AllowNonEmpty, macOS면 bash setup/bootstrap-mac.sh --allow-nonempty 를 실행해 줘. 실행 전에 "곧 승인 창이 뜹니다. [승인]을 누르세요"라고 말해 줘.
```

## 2. 인식 확인 (설치 후 새 채팅에서)
```
이 폴더의 AGENTS.md와 사용 가능한 스킬 목록을 말해줘
```
기대하는 답(예시):
> 이 폴더의 AGENTS.md는 Zotero 논문으로 연구 위키를 관리하는 규칙서입니다(리뷰 형식은 이제현 박사님의 Paper Curation 기반). 사용할 수 있는 스킬은 4개입니다.
> - **wiki-ingest** — 논문 넣기(추출 → 한국어 7섹션 리뷰 → 관련 링크)
> - **wiki-query** — 근거를 달아 답하기, 문구·그림 찾기, 아이디어, 이어쓰기
> - **wiki-lint** — 위키 점검·연결
> - **wiki-synthesize** — 서론 초안·주제 탐색·아이디어 결합·공통 한계·네트워크 질문

스킬이 안 보이면: ① 연 폴더의 맨 위에 `AGENTS.md`와 `.agents/skills/`가 있는지(0절) ② 새 채팅을 열었는지 ③ 앱 재시작. 그래도 `$스킬`이 안 되면 "논문 넣어줘"처럼 말로 요청하세요 — AGENTS.md가 해당 SKILL.md를 직접 읽게 합니다.

## 3. Zotero 준비 (무료 계정, PDF는 내 컴퓨터에 저장)
1. Zotero 7 이상 설치·실행 → **설정 → 고급 → "이 컴퓨터의 다른 응용 프로그램이 Zotero와 통신하도록 허용"** 켜기 (macOS: Zotero → 설정, Windows: 편집 → 설정)
2. 새 컬렉션 **`llmwiki-practice`** 를 만들고 넣을 논문 PDF **1편**을 끌어다 넣기(2편째는 선택). PDF가 Zotero에 첨부된 로컬 파일이어야 하고, 하위 컬렉션은 만들지 마세요. 이름을 다르게 만들었으면 `llmwiki.yaml`의 `practice_collection`을 그 이름으로 바꾸세요(컬렉션이 하나뿐이면 자동으로 그것을 씁니다).
3. 새 채팅에서 「llmwiki doctor --offline 을 승인 요청으로 실행해 줘」 → `Zotero 로컬 API`와 `실습 컬렉션`이 PASS인지 확인 (샌드박스 안에서 돌리면 Zotero 접속이 막혀 거짓 WARN이 날 수 있어 승인 요청으로 실행합니다)
- `$wiki-ingest 최근 1편`은 이 컬렉션에서 **Zotero에 추가한 날짜**가 가장 최근이고, PDF가 있고, 위키에 아직 없는 논문을 골라 넣습니다(`llmwiki zotero next`). 그래서 컬렉션에는 실습할 논문만 넣으세요.
- Zotero 검색은 제목·저자·연도의 **글자를 그대로** 비교합니다. 한국어로 찾으면 영어 논문이 0건이므로 **영어 단어**로 찾으세요(에이전트는 자동으로 영어로 바꿔 검색합니다). 초록까지 찾으려면 `--everything`.
- Zotero가 꺼져 있으면 `zotero.sqlite`의 **복사본**(-wal·-shm 포함)을 읽습니다. 원본 DB에는 절대 쓰지 않습니다.
- 별도 Zotero CLI를 쓰고 싶으면 `llmwiki.yaml`의 `external_cli`에 명령 템플릿을 넣습니다(JSON 출력, `{query}` `{collection}` `{tag}` `{limit}` `{key}` 치환).

## 4. 쓰는 법 (한 줄 프롬프트)
| 하고 싶은 일 | 채팅에 |
|---|---|
| 논문 넣기 | `$wiki-ingest 최근 1편` (가장 기본) · `$wiki-ingest tutoring` · `$wiki-ingest raw/논문.pdf` |
| 근거 있는 답 | `$wiki-query LLM 튜터의 학습 효과 근거는?` (내 위키 안 자료만, 웹 검색 안 함, 끝에 「참고한 곳」) |
| 연구자 질문 | `$wiki-query 정말 있나? …` · `비교: …` · `연구 확장: …` · `반론: …` · `깊게 조사: …` → [COMMANDS.md 3-1 연구자 질문 예시](COMMANDS.md#3-1-연구자-질문-예시-복사해서-채팅창에) |
| 위키 화면 보기 | 「위키 화면 열어 줘」 · 「위키 화면 새로 만들어 줘」 · 「이 폴더에서 위키 화면 다시 켜 줘」 |
| 문구·그림 찾기 | `"learning by teaching" 문구 어디 나와?` · `시스템 구조 그림 찾아줘` |
| 점검 | `$wiki-lint` |
| 서론 초안 | `$wiki-synthesize 서론 LLM 튜터링의 학습 효과` |
| 주제 탐색 | `$wiki-synthesize 주제탐색 AI 교육` |
| 아이디어 결합 | `$wiki-synthesize 결합 <논문1 slug> + <논문2 slug>` |
| 공통 한계·빈틈 | `$wiki-synthesize 공통한계` |
| 새 논문의 이웃 | `$wiki-synthesize 이웃 <slug>` |
| 연결 덩어리별 서론 흐름 | `$wiki-synthesize 덩어리서론` |
| 미해결 빈틈 | `$wiki-synthesize 미해결빈틈` |
| 링크 없는 군집 결합 | `$wiki-synthesize 군집결합` |
| 허브 논문 | `$wiki-synthesize 허브` |
결과는 `drafts/`에 저장되고 `wiki/log.md`에 기록됩니다. 모든 문장에 `[근거: 논문slug · 섹션/p.N]`이 붙습니다.
**위키 화면(브라우저)**: `llmwiki site`가 `site/index.html`을 만듭니다. 이 파일을 브라우저로 열면(서버·인터넷 필요 없음) 논문 목록·연도/주제 필터·검색·논문별 리뷰·그림·관련 논문·원문 페이지·초안을 클릭하며 볼 수 있고, 모든 페이지의 **💬 Codex에게 물어보기** 버튼이 Codex 채팅에 붙여넣을 질문 문장을 복사해 줍니다. 주소로 보기(`llmwiki serve` → http://127.0.0.1:8765/)는 선택입니다.
샘플로 연습하려면: `llmwiki sample` (3편이 `wiki/`에 들어옴). 학생이 입력하는 모든 명령은 [COMMANDS.md](COMMANDS.md), CLI 옵션은 `llmwiki <명령> --help`.

## 5. 승인 창에 대해
- git이 없는 폴더는 처음에 읽기 전용으로 시작할 수 있고, `.agents/`(스킬 폴더)는 쓰기가 보호됩니다. 그래서 첫 쓰기·스킬 만들기에서 승인 창이 뜹니다. 설치 스크립트는 Git이 있으면 `git init`을 해서 이 폴더를 버전 관리 폴더로 만듭니다.
- 새 채팅에서 `llmwiki doctor`는 **승인 요청으로** 실행해 달라고 하세요(`--offline`이면 인터넷 점검은 생략). 샌드박스 안에서는 Zotero(127.0.0.1)·인터넷 접속이 막혀 거짓 WARN이 날 수 있습니다.
- 터미널의 `codex exec`로 스킬을 만들 때는 `--add-dir .agents`를 붙이면 `.agents/skills/` 쓰기가 허용됩니다(QA 실측, codex-cli 0.161.0). 앱에서는 승인 창으로 허용합니다.

## 6. 개인 자료와 공개 저장소
- `.gitignore`는 `.venv/`·캐시를 제외합니다. 내 리뷰·PDF까지 GitHub에 올리지 않으려면 `.gitignore` 아래쪽 **"개인 위키 내용 제외"** 블록의 `#`을 지우세요.
- 원문 PDF는 저장소에 넣지 마세요(저작권). 그림 PNG는 "원문 PDF 캡처 · 로컬 연구용"입니다.

## 7. 라이선스
- 이 키트: MIT ([LICENSE](LICENSE)) — 원작이 아닌 재구현이며, 아이디어 출처는 맨 위에 밝혔습니다.
- PyMuPDF는 AGPL-3.0(또는 Artifex 상용) 라이선스입니다. 개인 연구용 로컬 사용 기준입니다.
- `examples/sample-wiki/`의 원문 추출물·그림은 CC BY 4.0 논문 3편에서 왔습니다([ATTRIBUTION.md](examples/sample-wiki/ATTRIBUTION.md)).
