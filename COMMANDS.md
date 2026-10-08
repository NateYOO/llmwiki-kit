# COMMANDS.md — 학생이 입력하는 모든 명령

> 이제현 박사님의 Paper Curation(https://github.com/jehyunlee/paper-curation) 아이디어와 Karpathy LLM Wiki를 바탕으로 만든 키트입니다. 감사드립니다. Based on Paper Curation by 이제현 (https://github.com/jehyunlee/paper-curation)
> CLI 옵션은 실제 `--help` 출력으로 확인했습니다 (llmwiki 0.1.0).
> 표기: macOS `./llmwiki …` · Windows `.\llmwiki.cmd …` (아래 표는 `llmwiki`로 줄여 씀). 권장 모델: GPT-6 Luna(`gpt-6-luna`), 추론 노력 **Medium**.

## 1. 설치

### 1-1. 기본: 설치 문장 (Windows·macOS 공통, Codex 앱 채팅창)
빈 폴더(`C:\llmwiki` / `~/llmwiki`)를 Codex에서 연 뒤 그대로 붙여 넣기:
```text
LLM 위키 키트를 이 폴더에 설치해 주세요. 저장소: https://github.com/NateYOO/llmwiki-kit
1) 먼저 저에게 "곧 승인 창이 뜹니다. [승인]을 누르세요"라고 말하고,
2) 제 컴퓨터에 맞는 아래 한 줄을 샌드박스 밖(승인 요청)으로 글자 그대로 실행한 뒤,
3) 출력 끝의 RESULT: 줄과 AGENT: 줄이 시키는 대로만 하세요. 다른 명령은 만들지 마세요.
Windows: [Console]::OutputEncoding=[Text.Encoding]::UTF8; iwr -useb https://github.com/NateYOO/llmwiki-kit/raw/main/setup/bootstrap-windows.ps1 -OutFile "$env:TEMP\llmwiki-bootstrap.ps1"; powershell -NoProfile -ExecutionPolicy Bypass -File "$env:TEMP\llmwiki-bootstrap.ps1" -CheckOnly -RepoUrl https://github.com/NateYOO/llmwiki-kit
macOS: curl -fsSL https://github.com/NateYOO/llmwiki-kit/raw/main/setup/bootstrap-mac.sh -o /tmp/llmwiki-bootstrap.sh && bash /tmp/llmwiki-bootstrap.sh --check-only --repo https://github.com/NateYOO/llmwiki-kit
```
학생은 "곧 승인 창이 뜹니다. [승인]을 누르세요"가 나오면 [승인]만 누릅니다(보통 2번). Windows에서 화면이 어두워지는 확인 창(UAC)이 뜨면 [예], 안 보이면 작업 표시줄의 깜빡이는 방패 아이콘.
에이전트 쪽 흐름(원본: `INSTALL_FOR_AGENT.md`):
| 단계 | 명령 | 판정 |
|---|---|---|
| 1. 받기 + 폴더 점검 | 위 문장의 Windows/macOS 한 줄 (샌드박스 밖) | `RESULT: CHECK_OK` / `RESULT: FAIL E00` |
| 2. 설치 | 1단계 출력의 `AGENT_CMD:` 줄 그대로 — Windows `… powershell -NoProfile -ExecutionPolicy Bypass -File "<TEMP>\llmwiki-bootstrap.ps1" -RepoUrl "https://github.com/NateYOO/llmwiki-kit"`, macOS `bash "/tmp/llmwiki-bootstrap.sh" --repo "https://github.com/NateYOO/llmwiki-kit"` | `RESULT: OK` (0) / `RESULT: DOCTOR_FAIL` (17, 다시 실행 안 함) / `RESULT: FAIL E0n` (10+n, E07만 27) |

### 1-2. 대체 경로
| 방법 | 명령 |
|---|---|
| Download ZIP (표준 수동) | GitHub → Code → Download ZIP → 압축 풀기 → 폴더를 `C:\llmwiki`로 → Codex에서 열고 1-1 문장 |
| git clone (고급) | `git clone https://github.com/NateYOO/llmwiki-kit llmwiki` |
| 터미널 한 줄 (macOS) | `curl -LsSf https://github.com/NateYOO/llmwiki-kit/raw/main/setup/install_mac.sh \| bash` |
| 터미널 한 줄 (Windows) | `irm https://github.com/NateYOO/llmwiki-kit/raw/main/setup/install_windows.ps1 \| iex` |
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
1) 복사: AGENTS.md, .agents/ (폴더째), tools/, setup/, llmwiki, llmwiki.cmd, llmwiki.yaml, wiki/(index.md·log.md·papers/·topics/), drafts/README.md, projects/README.md, raw/README.md, examples/, .gitattributes
2) 같은 이름의 파일이 이미 있으면 절대 덮어쓰지 말고 건너뛴 뒤 목록으로 알려 줘.
3) 이 폴더에 AGENTS.md가 이미 있으면 덮어쓰지 말고 키트 것을 AGENTS.llmwiki.md로 복사한 다음, 두 파일을 어떻게 합칠지 제안만 해 줘(내가 승인하기 전엔 기존 AGENTS.md를 고치지 마).
4) 끝나면 복사/건너뜀/합치기 제안을 표로 보여 주고, Windows면 powershell -NoProfile -ExecutionPolicy Bypass -File setup\bootstrap-windows.ps1 -AllowNonEmpty, macOS면 bash setup/bootstrap-mac.sh --allow-nonempty 를 실행해 줘. 실행 전에 "곧 승인 창이 뜹니다. [승인]을 누르세요"라고 말해 줘.
```

### 1-4. 인식 확인 (새 채팅)
```
이 폴더의 AGENTS.md와 사용 가능한 스킬 목록을 말해줘
```
기대: AGENTS.md 설명 + 스킬 3개(wiki-ingest, wiki-query, wiki-synthesize).

## 2. CLI 명령
| 명령 | 하는 일 | 자주 쓰는 옵션 |
|---|---|---|
| `llmwiki doctor` | 환경 점검(Python·패키지·폴더·Zotero 로컬 API·실습 컬렉션·네트워크) + 한 줄 요약 | `--offline`, `--json` |
| `llmwiki init <폴더>` | 기존 폴더에 키트 설치(덮어쓰지 않음) | `--append-agents`, `--no-sample` |
| `llmwiki sample` | 복구용 샘플 위키 3편을 `wiki/`에 복사(+관련 링크·목차 갱신). 설치 마지막 단계에서 위키가 비어 있으면 자동으로 들어감 | `--overwrite`, `--remove`(샘플 3편·샘플 주제만 빼기, 내 논문은 그대로 → 목차·관련 링크·위키 화면 갱신) |
| `llmwiki welcome` | 설치 스크립트 9단계: 위키가 비어 있으면 샘플 3편 → `site/` 만들기 → 브라우저로 열기(학생이 직접 칠 일 없음) | `--no-open`, `--json` |
| `llmwiki zotero status` | 어떤 백엔드(로컬 API·sqlite 사본·외부 CLI)로 연결되는지 | `--backend` |
| `llmwiki zotero collections` | 컬렉션 목록 | |
| `llmwiki zotero next` | 실습 컬렉션에서 **Zotero에 추가한 날짜**가 가장 최근이고 PDF가 있고 위키에 없는 논문 1편을 골라 바로 추출 + 다음 후보 2편 표시. 상위 항목 없는 **단독 PDF**도 후보(서지는 PDF에서 찾음). 넣을 것이 없으면 이유(빈 컬렉션·이미 있음·PDF 없음)와 함께 종료 코드 3 | `--collection`, `--pick N`, `--dry-run`, `--offline`, `--backend sqlite`(Zotero 데이터 폴더 사본, 로컬 API 없이) |
| `llmwiki zotero search "tutoring"` | 항목 찾기(키워드는 **영어**). 기본은 실습 컬렉션(`llmwiki.yaml`의 `practice_collection`) 안 | `--collection`, `--all`(라이브러리 전체), `--tag`, `--limit N`, `--no-pdf`, `--everything`(초록까지) |
| `llmwiki zotero get <KEY>` | 항목 하나의 서지·PDF 경로 | |
| `llmwiki zotero import <KEY>` | Zotero 항목 PDF를 위키로 추출 | `--offline`, `--force`, `--slug` |
| `llmwiki extract "<PDF>"` | PDF 직접 추출 → `wiki/papers/<slug>/` | `--offline`, `--force`, `--slug` |
| `llmwiki meta --refresh <slug>` | 저자·연도 등 **빈 서지 칸만** 다시 채우기(arXiv·Crossref·OpenAlex). 넣을 때 서지 사이트가 바빠 저자가 비었으면(`meta_pending`, lint WARN) 잠시 뒤 실행. 있는 값은 바꾸지 않음, review.md frontmatter도 빈 칸만 | `--offline` |
| `llmwiki finish <slug>` | 넣기 마무리 한 번에: related --write → index → lint → log(**완료일 때만**, 같은 날 같은 제목은 한 번만). 단계별 rc, 이 논문 문제만 따로, 마지막 줄 `넣기 완료 ✅ …` / `넣기 미완료 ❌ / 고칠 것: …` (앞에 `RESULT: OK/FAIL`) | `--op`, `--note`, `--json` |
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
| `llmwiki site` | **위키 화면 만들기**: `wiki/`·`drafts/` → `site/index.html`(논문 목록·연도/주제 필터·검색·논문별 리뷰·그림·관련 논문·원문 페이지·초안). 파일로 바로 열림(file://), 마지막에 열 경로와 새로고침 안내. `finish`·`log` 뒤 자동 갱신 | `--open`(브라우저로 열기), `--json` |
| `llmwiki serve` | (선택) 위키 화면을 주소로 보기: http://127.0.0.1:8765/ (백그라운드, 이미 켜져 있으면 재사용, 포트가 쓰이고 있으면 다음 번호) | `--no-open`, `--stop`, `--status`, `--port N` |

## 3. 스킬 (채팅 한 줄)
| 목적 | 프롬프트 |
|---|---|
| 논문 넣기 (기본) | `$wiki-ingest 최근 1편` → `zotero next` → 리뷰 → `finish` (묻지 않음) |
| 논문 넣기 (골라서) | `$wiki-ingest tutoring` · `$wiki-ingest ABCD1234` · `$wiki-ingest raw/논문.pdf` · `$wiki-ingest 컬렉션 "내 컬렉션"에서` |
| 근거 답변 | `$wiki-query LLM 튜터의 학습 효과 근거는?` |
| 사실 확인·비교·아이디어·연구 확장·질문 다듬기·방법 고르기·반론 | `$wiki-query 정말 있나? …` · `$wiki-query 비교: …` 등 (아래 「연구자 질문 예시」) |
| 깊게 조사 (관점 3–6개로 나눠 위키 안에서 조사) | `$wiki-query 깊게 조사: LLM 기반 튜터링의 효과와 한계` |
| 문구 찾기 | `"learning by teaching" 문구 어디 나와?` |
| 그림 찾기 | `시스템 구조 그림 찾아줘` |
| 이어쓰기 | `$wiki-synthesize 이어쓰기 drafts/문헌고찰.md` (파일 끝에 덧붙이기만) |
| 주제 폴더에 저장 | 「… 결과는 projects/<주제이름>/ 에 저장해 주세요」 |
| 점검 | 「점검해 줘」 (`llmwiki lint` 실행 후 결과 설명) |
| 서론 초안 | `$wiki-synthesize 서론 LLM 튜터링의 학습 효과` → `drafts/intro-…-YYYYMMDD.md` |
| 주제 탐색 | `$wiki-synthesize 주제탐색 AI 교육` → `wiki/topics/…` + `drafts/topic-map-…` |
| 아이디어 결합 | `$wiki-synthesize 결합 <slug1> + <slug2>` → `drafts/merge-…` |
| 공통 한계·빈틈 | `$wiki-synthesize 공통한계` → `drafts/gaps-…` (+ `llmwiki sections --name limitation,gap --out drafts/_sections-limitation-gap-YYYYMMDD.md`) |
| 새 논문의 이웃 | `$wiki-synthesize 이웃 <slug>` → `drafts/net-neighbors-<slug>-…` |
| 덩어리별 서론 흐름 | `$wiki-synthesize 덩어리서론` → `drafts/net-intro-flow-…` |
| 미해결 빈틈 | `$wiki-synthesize 미해결빈틈` → `drafts/net-open-gaps-…` |
| 링크 없는 군집 결합 | `$wiki-synthesize 군집결합` → `drafts/net-bridge-…` |
| 허브 논문 | `$wiki-synthesize 허브` → `drafts/net-hubs-…` |
`$`가 안 되면 같은 내용을 말로 요청해도 됩니다(AGENTS.md가 SKILL.md를 읽게 함).

`$wiki-query`는 **내 위키 안 자료만** 씁니다(웹 검색 안 함). 위키에 없으면 「없음」이라고 말하고 Zotero에 넣을 논문 검색어만 알려 줍니다. 답 끝에는 항상 「참고한 곳」(리뷰 파일 `wiki/papers/<slug>/review.md#섹션` · 원문 p.N · 화면 `site/papers/<slug>/index.html`)이 붙습니다. query는 채팅으로만 답하고 파일은 만들지 않습니다. `drafts/`(또는 주제 폴더)에 남길 문서와 이어쓰기는 `$wiki-synthesize`. 아이디어·비교·깊게 조사 답 끝에 「이 대화 내용을 문서 파일로 정리해 드릴까요?」가 붙고, 「응」이라고 하면 synthesize가 `drafts/`(또는 말한 주제 폴더)에 파일을 만듭니다.

### 3-1. 연구자 질문 예시 (복사해서 채팅창에)
```text
$wiki-query 정말 있나? LLM 튜터가 학생 학습 성과를 높였다는 RCT가 내 위키에 있어? 어느 논문 몇 쪽?
$wiki-query 비교: 학생과 직접 대화하는 LLM 튜터 vs 사람 튜터를 돕는 AI — 중학생 수학 수업에는 어느 쪽이 나을까?
$wiki-query 아이디어: 내 위키 논문 2편 이상을 엮어서 새 연구 아이디어 3개 제안해 줘
$wiki-query 연구 확장: Tutor CoPilot 연구를 대상·맥락·방법·변수 면에서 어떻게 넓힐 수 있을까?
$wiki-query 연구질문 다듬기: "AI 튜터는 학습에 도움이 될까?"를 실제로 연구할 수 있는 질문으로 다듬어 줘
$wiki-query 방법·데이터: 대학생 대상 AI 튜터 효과를 보려면 어떤 연구 설계와 측정 도구가 좋을까?
$wiki-query 반론: "LLM 튜터는 학습 효과가 있다"는 주장의 약점과 반대 근거는?
$wiki-query 깊게 조사: LLM 기반 튜터링의 효과와 한계
$wiki-query 내 위키 논문들이 공통으로 다루지 않은 빈틈은 뭐야?
$wiki-query 이 논문은 학생 개인정보를 어떻게 다뤘어? (참고: wiki/papers/2024-wang-tutor-copilot-human-ai-approach/review.md)
```
마지막 줄은 위키 화면의 **💬 Codex에게 물어보기** 버튼이 복사해 주는 문장과 같은 모양입니다(`<질문을 여기에>` 자리에 질문을 쓰세요).

### 3-1-1. 예시 대화 — 샘플 3편으로 실제 답이 나오는 질문
설치 직후 들어 있는 샘플 3편(Ruffle&Riley 2024 · Tutor CoPilot 2024 · Yan et al. 2023)만으로 답이 나오는 질문입니다. 오른쪽은 답에 나와야 할 근거(샘플 리뷰에서 확인한 내용)입니다.

| 목적 | 채팅에 (복사) | 답에 나올 근거 |
|---|---|---|
| 연구 방법 비교 | `$wiki-query Ruffle&Riley 연구는 어떤 연구 방법을 썼지? Tutor CoPilot, Yan et al.의 연구 방법과 비교해 줘` | R&R: 온라인 사용자 연구 2회(각 N=100, Prolific 성인, Reading·QA 챗봇과 비교) · Tutor CoPilot: 튜터 900명·학생 1,800명 사전등록 RCT · Yan: PRISMA 스코핑 리뷰 118편, 코딩 일치도 kappa 0.80 이상 → 비교표 + 조건부 추천 |
| 연구 아이디어 | `$wiki-query 아이디어: Tutor CoPilot(사람 튜터를 돕는 AI)과 Ruffle&Riley(학생과 직접 대화하는 AI)를 엮으면 어떤 연구를 할 수 있을까?` | CoPilot은 숙달률 +4%p, R&R은 학습 성과 차이 없음 → "누가 LLM과 대화하는가"를 설계 변수로 비교하는 아이디어 (가설) |
| 배경 정보 | `$wiki-query 배경: LLM을 교육에 쓸 때 실천적·윤리적 문제로 무엇이 알려져 있어?` | Yan: 89편이 TRL-2, 실제 현장 검증 7편 · 재현 정보 부족 107편 · 투명성 Tier 1이 109편 · 학생 데이터 동의 절차 명시 없음 |
| 연구 설계 아이디어 | `$wiki-query 연구 설계: Ruffle&Riley의 한계(성인 표본·단일 세션·학습 시간 차이)를 보완하는 후속 실험을 설계해 줘` | R&R 한계: Prolific 성인, 단일 세션, 학습 시간 20.8분 vs 5.5분 · CoPilot의 설계(무작위 배정·사전등록)를 빌려 오는 안 (가설) |
| 깊게 조사 | `$wiki-query 깊게 조사: LLM 튜터는 학습 성과를 정말 높이나? 효과·조건·한계` | 관점 3–6개(효과·누가 쓰나·대상·측정·한계) → 관점별 문단 → 종합 → 「참고한 곳」(세 논문 리뷰 파일·원문 페이지·화면 경로) |
| 「없음」 확인 | `$wiki-query 정말 있나? LLM 튜터를 초등학생 영어 말하기 수업에 쓴 연구가 내 위키에 있어?` | **없음** + Zotero 검색어(영어) 제안 — 샘플 3편에는 없는 내용 |

### 3-2. 위키 화면 (브라우저로 보기) — 채팅에 한 마디
| 말하기 | Codex가 하는 일 |
|---|---|
| 「위키 화면 열어 줘」 | `llmwiki site --open` → `site/index.html`을 브라우저로 열고 file:// 경로를 알려 줌 |
| 「위키 화면 새로 만들어 줘」 | 논문을 넣은 뒤 `llmwiki site` → "브라우저 새로고침(F5, 맥 Cmd+R)" 안내 |
| 「이 폴더에서 위키 화면 다시 켜 줘」 | `llmwiki site --open`, 주소(serve)로 보던 경우 `llmwiki serve`도 다시 실행 |
| 「샘플 논문 빼 줘」 | `llmwiki sample --remove` → 샘플 3편·샘플 주제만 빼고 목차·관련 링크·화면 갱신 |
기본은 **파일로 열기**(서버·인터넷 필요 없음). 주소로 보고 싶으면(선택) `llmwiki serve` → http://127.0.0.1:8765/ , 끄기 `llmwiki serve --stop`. 주소 서버는 컴퓨터를 껐다 켜거나 Codex를 닫으면 꺼질 수 있습니다.
화면에서: 위쪽 검색창(제목·저자·리뷰·그림 설명, `/` 키) · 연도/주제 필터 · 논문 페이지의 목차·그림·관련 논문·원문 페이지 · 초안 목록 · 모든 페이지의 **💬 Codex에게 물어보기**(질문 문장 복사 → Codex 채팅에 붙여넣기).

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
| doctor: Zotero 로컬 API WARN | Zotero 실행 + Zotero 설정(윈도우: 편집 → 설정, 맥: Zotero → 설정) → 고급 → 기타 → 'Allow other applications on this computer to communicate with Zotero' 체크. 새 채팅에서는 「llmwiki doctor --offline 을 승인 요청으로 실행해 줘」(샌드박스 안이면 거짓 WARN) |
| doctor: 실습 컬렉션 WARN | Zotero에 `llmwiki-practice` 컬렉션 만들고 논문 PDF 1편(2편째 선택). 이름이 다르면 `llmwiki.yaml`의 `practice_collection` 수정 |
| `[오류] … 컬렉션이 여러 개입니다` + 번호 목록 | 번호를 골라 `--collection "<이름>"`으로 다시 |
| `[오류] …` (Traceback 없음) | 안내의 `해결:`대로. 자세한 내부 오류가 필요하면 `LLMWIKI_DEBUG=1` |
| Zotero 검색 0건 | 영어 키워드로, 또는 `--everything` |
| 스킬이 안 보임 | 연 폴더 맨 위에 AGENTS.md·`.agents/skills/` 확인 → 새 채팅 → 앱 재시작 |
| 위키가 망가짐 | `llmwiki sample`로 샘플 3편 복구, `llmwiki lint --fix` |
| 위키 화면이 없음·안 열림 | 채팅에 「위키 화면 열어 줘」(→ `llmwiki site --open`). 자동으로 안 열리면 안내된 `file:///…/site/index.html`을 브라우저 주소창에 붙여넣기 |
| 새 논문이 화면에 안 보임 | 「위키 화면 새로 만들어 줘」 → 브라우저 새로고침(F5, 맥 Cmd+R) |
| 주소(http://127.0.0.1:…)가 안 열림 | 「이 폴더에서 위키 화면 다시 켜 줘」(컴퓨터 재시작·Codex 종료 뒤 꺼질 수 있음). 그동안은 파일로 열기 |
| 샘플 논문 3편을 빼고 싶음 | 「샘플 논문 빼 줘」(→ `llmwiki sample --remove`, 내 논문은 그대로) → 브라우저 새로고침. 다시 넣기: `llmwiki sample` |
| 「Codex에게 물어보기」가 복사 안 됨 | 뜨는 상자의 선택된 글을 Ctrl+C(맥 ⌘+C) → Codex 채팅에 붙여넣기 |
