# COMMANDS.md — 학생이 입력하는 모든 명령

> 이제현 박사님의 Paper Curation(https://github.com/jehyunlee/paper-curation) 아이디어와 Karpathy LLM Wiki를 바탕으로 새로 만든 키트입니다. 감사드립니다.
> CLI 옵션은 실제 `--help` 출력으로 확인했습니다: 하네스 저장소의 `example-run/logs/06_cli_help.log` (llmwiki 0.1.0).
> 표기: macOS `./llmwiki …` · Windows `.\llmwiki.cmd …` (아래 표는 `llmwiki`로 줄여 씀). 권장 모델: GPT-6 Luna(`gpt-6-luna`), 추론 노력 **Medium**.

## 1. 설치

### 1-1. 기본: 한 문장 설치 (Windows·macOS 공통, Codex 앱 채팅창)
빈 폴더(`C:\llmwiki` / `~/llmwiki`)를 Codex에서 연 뒤 그대로 붙여 넣기:
```
<REPO_URL> 의 INSTALL_FOR_AGENT.md 를 그대로 따라 이 폴더에 설치해 주세요.
```
학생은 "곧 승인 창이 뜹니다. [승인]을 누르세요"가 나오면 [승인]만 누릅니다. 에이전트가 실행하는 고정 명령은 `INSTALL_FOR_AGENT.md` 참고:
- Windows: `powershell -NoProfile -ExecutionPolicy Bypass -File "$env:TEMP\llmwiki-bootstrap.ps1" -CheckOnly` → `… -RepoUrl "<REPO_URL>"`
- macOS: `bash /tmp/llmwiki-bootstrap.sh --check-only` → `bash /tmp/llmwiki-bootstrap.sh --repo "<REPO_URL>"`

### 1-2. 대체 경로
| 방법 | 명령 |
|---|---|
| Download ZIP (표준 수동) | GitHub → Code → Download ZIP → 압축 풀기 → 폴더를 `C:\llmwiki`로 → Codex에서 열고 1-1 문장 |
| git clone (고급) | `git clone <REPO_URL> llmwiki` |
| 터미널 한 줄 (macOS) | `curl -LsSf <REPO_URL>/raw/main/setup/install_mac.sh \| bash` |
| 터미널 한 줄 (Windows) | `irm <REPO_URL>/raw/main/setup/install_windows.ps1 \| iex` |
| 키트 폴더 안에서 직접 (Windows) | `powershell -NoProfile -ExecutionPolicy Bypass -File setup\bootstrap-windows.ps1` |
| 키트 폴더 안에서 직접 (macOS) | `bash setup/bootstrap-mac.sh` |
| 기존 설치 스크립트(uv/venv, 대상 지정) | `bash setup/setup_mac.sh --target ~/my-thesis` · `powershell -NoProfile -ExecutionPolicy Bypass -File setup\setup_windows.ps1 -Target C:\my-thesis` (`--no-uv`/`-NoUv`: 이미 있는 Python 사용) |

### 1-3. 이미 있는 연구 폴더에 넣기
| 방법 | 명령 |
|---|---|
| CLI | `llmwiki init <폴더>` (덮어쓰지 않음, AGENTS.md가 있으면 `AGENTS.llmwiki.md`) · `llmwiki init <폴더> --append-agents` · `--no-sample` |
| Codex 복사 프롬프트 | 아래를 연구 폴더를 연 Codex 채팅에 붙여 넣기 |

```
다음 경로의 LLM 위키 스타터 키트를 지금 열린 이 폴더의 맨 위에 설치해 줘.
키트 경로: <키트 폴더 경로>
1) 복사: AGENTS.md, .agents/ (폴더째), tools/, setup/, llmwiki, llmwiki.cmd, llmwiki.yaml, wiki/(index.md·log.md·papers/·topics/), drafts/README.md, raw/README.md, examples/, .gitattributes
2) 같은 이름의 파일이 이미 있으면 절대 덮어쓰지 말고 건너뛴 뒤 목록으로 알려 줘.
3) 이 폴더에 AGENTS.md가 이미 있으면 덮어쓰지 말고 키트 것을 AGENTS.llmwiki.md로 복사한 다음, 두 파일을 어떻게 합칠지 제안만 해 줘(내가 승인하기 전엔 기존 AGENTS.md를 고치지 마).
4) 끝나면 복사/건너뜀/합치기 제안을 표로 보여 주고, Windows면 powershell -NoProfile -ExecutionPolicy Bypass -File setup\bootstrap-windows.ps1 -AllowNonEmpty, macOS면 bash setup/bootstrap-mac.sh --allow-nonempty 를 실행해 줘. 실행 전에 "곧 승인 창이 뜹니다. [승인]을 누르세요"라고 말해 줘.
```

### 1-4. 인식 확인 (새 채팅)
```
이 폴더의 AGENTS.md와 사용 가능한 스킬 목록을 말해줘
```
기대: AGENTS.md 설명 + 스킬 4개(wiki-ingest, wiki-query, wiki-lint, wiki-synthesize).

## 2. CLI 명령
| 명령 | 하는 일 | 자주 쓰는 옵션 |
|---|---|---|
| `llmwiki doctor` | 환경 점검(Python·패키지·폴더·Zotero 로컬 API·실습 컬렉션·네트워크) + 한 줄 요약 | `--offline`, `--json` |
| `llmwiki init <폴더>` | 기존 폴더에 키트 설치(덮어쓰지 않음) | `--append-agents`, `--no-sample` |
| `llmwiki sample` | 복구용 샘플 위키 3편을 `wiki/`에 복사(+관련 링크·목차 갱신) | `--overwrite` |
| `llmwiki zotero status` | 어떤 백엔드(로컬 API·sqlite 사본·외부 CLI)로 연결되는지 | `--backend` |
| `llmwiki zotero collections` | 컬렉션 목록 | |
| `llmwiki zotero search "tutoring" --collection llmwiki-practice` | 항목 찾기(키워드는 **영어**) | `--tag`, `--limit N`, `--no-pdf`, `--everything`(초록까지) |
| `llmwiki zotero get <KEY>` | 항목 하나의 서지·PDF 경로 | |
| `llmwiki zotero import <KEY>` | Zotero 항목 PDF를 위키로 추출 | `--offline`, `--force`, `--slug` |
| `llmwiki extract "<PDF>"` | PDF 직접 추출 → `wiki/papers/<slug>/` | `--offline`, `--force`, `--slug` |
| `llmwiki related --write` | 관련 논문 자동 블록 갱신(모든 리뷰) | `--top N`, `--slug` |
| `llmwiki related <slug>` | 한 논문의 이웃: 관계·링크 방향·공유 주제·공저자 | `--json` |
| `llmwiki hubs` | 링크가 많은 허브 논문 + 연결 덩어리 | `--top N`, `--json` |
| `llmwiki clusters` | 주제 군집 + 군집 간 유사도·링크 수 | `--threshold`, `--json` |
| `llmwiki search "질문"` | BM25 검색(근거 꼬리표 포함) | `--scope wiki\|source\|figures\|drafts\|all`, `--top` |
| `llmwiki find "정확한 문구"` | 문구 위치(페이지) 찾기 | `--scope` |
| `llmwiki figures "architecture"` | 그림·표 캡션 검색 | `--top` |
| `llmwiki sections --name limitation,gap` | 여러 리뷰의 같은 섹션 모으기 | `--slugs`, `--category`, `--out drafts/…md`, `--force` |
| `llmwiki index` | `wiki/index.md` 재생성 | |
| `llmwiki log ingest "제목" --note "파일"` | `wiki/log.md`에 기록 | 종류: ingest, query, lint, draft, synthesize, related, setup, fix |
| `llmwiki lint` | 기계 검사 | `--fix`(related+index 후 재검사), `--json` |

## 3. 스킬 (채팅 한 줄)
| 목적 | 프롬프트 |
|---|---|
| 논문 넣기 | `$wiki-ingest tutoring` · `llmwiki-practice 컬렉션 논문 넣어줘` · `$wiki-ingest raw/논문.pdf` |
| 근거 답변 | `$wiki-query LLM 튜터의 학습 효과 근거는?` |
| 문구 찾기 | `"learning by teaching" 문구 어디 나와?` |
| 그림 찾기 | `시스템 구조 그림 찾아줘` |
| 이어쓰기 | `drafts/문헌고찰.md 이어서 써줘` |
| 점검 | `$wiki-lint` |
| 서론 초안 | `$wiki-synthesize 서론 LLM 튜터링의 학습 효과` → `drafts/intro-…-YYYYMMDD.md` |
| 주제 탐색 | `$wiki-synthesize 주제탐색 AI 교육` → `wiki/topics/…` + `drafts/topic-map-…` |
| 아이디어 결합 | `$wiki-synthesize 결합 <slug1> + <slug2>` → `drafts/merge-…` |
| 공통 한계·빈틈 | `$wiki-synthesize 공통한계` → `drafts/gaps-…` (+ `llmwiki sections --name limitation,gap --out drafts/_sections-limitation-gap-YYYYMMDD.md`) |
| 새 논문의 이웃 | `$wiki-synthesize 이웃 <slug>` → `drafts/net-neighbors-<slug>-…` |
| 덩어리별 서론 흐름 | `$wiki-synthesize 덩어리서론` → `drafts/net-intro-flow-…` |
| 미해결 빈틈 | `$wiki-synthesize 미해결빈틈` → `drafts/net-open-gaps-…` |
| 링크 없는 군집 결합 | `$wiki-synthesize 군집결합` → `drafts/net-bridge-…` |
| 허브 논문 | `$wiki-synthesize 허브` → `drafts/net-hubs-…` |
`$`가 안 되면 같은 내용을 말로 요청해도 됩니다(AGENTS.md가 SKILL.md를 읽게 함). 실제 산출물 예는 강의 하네스의 `example-run/workspace/drafts/`.

## 4. Codex CLI (선택, 터미널)
| 목적 | 명령 |
|---|---|
| 대화형 | `codex -C <작업폴더> -c model_reasoning_effort=medium` |
| 비대화형 1회 | `codex exec -C <작업폴더> -s workspace-write -c model_reasoning_effort=medium "\$wiki-ingest raw/논문.pdf"` |
| 스킬 만들기 허용 | 위 명령에 `--add-dir .agents` (`.agents/skills/` 쓰기 보호 해제, QA 실측 0.161.0) |
| 스킬 인식 확인 | `codex debug prompt-input "hi"` 출력에 `wiki-ingest/SKILL.md` 등이 보이는지 |

## 5. 문제 해결
| 증상 | 할 일 |
|---|---|
| 설치 출력에 `[E00]`~`[E07]` | `INSTALL_FOR_AGENT.md`의 오류 코드 표. 같은 오류 2번이면 강사에게 |
| doctor: Zotero 로컬 API WARN | Zotero 실행 + 설정→고급 "다른 응용 프로그램과 통신 허용" |
| doctor: 실습 컬렉션 WARN | Zotero에 `llmwiki-practice` 컬렉션 만들고 PDF 2~3편 |
| Zotero 검색 0건 | 영어 키워드로, 또는 `--everything` |
| 스킬이 안 보임 | 연 폴더 맨 위에 AGENTS.md·`.agents/skills/` 확인 → 새 채팅 → 앱 재시작 |
| 위키가 망가짐 | `llmwiki sample`로 샘플 3편 복구, `llmwiki lint --fix` |
