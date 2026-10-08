---
name: wiki-ingest
description: 논문 넣기(ingest). 논문 제목·Zotero 키·컬렉션·PDF 경로를 받아 추출 → 한국어 7섹션 리뷰 → 관련 링크 → index/log → lint.
---

# wiki-ingest — 논문 한 편을 위키에 넣기

먼저 `wiki/index.md`(현재 목록)를 읽는다. 리뷰 형식 상세는 `references/wiki-format.md`, 예시는 `references/review_example.md`. 아래에서 `llmwiki`는
macOS/Linux `./llmwiki`, Windows `.\llmwiki.cmd` 로 바꿔 실행한다.

## 입력 해석
사용자가 준 것(스킬 이름 뒤의 글)을 보고 고른다:
| 입력 | 할 일 |
|---|---|
| PDF 경로 (`.pdf`로 끝남) | 2단계 B로 |
| Zotero 항목 키 (8자 영숫자, 예 `ABCD1234`) | `llmwiki zotero import <KEY>` |
| 논문 제목·저자·키워드 | `llmwiki zotero search "<키워드>"` |
| "컬렉션 X" | `llmwiki zotero search --collection "X"` (실습 컬렉션 이름: `llmwiki-practice`) |
| 아무것도 없음 | 무엇을 넣을지 묻는다 |

## 절차
1. **찾기** — `llmwiki zotero search "<키워드>" [--collection 이름] [--tag 태그]`
   - **키워드는 영어로 바꿔서 검색한다.** Zotero 검색(`q=`)은 제목·저자·연도 글자를 그대로 비교하므로 "튜터링"으로는 영어 논문 "tutoring"이 0건이다.
     예: "대화형 튜터링 LLM" → `llmwiki zotero search "tutoring"` 후 필요하면 `"conversational"`, `"LLM"`처럼 한 단어씩. 저자 성(영문)과 연도도 잘 맞는다.
   - 0건이면 다른 영어 동의어로 한두 번 더 찾고, 그래도 없으면 `--collection llmwiki-practice`처럼 컬렉션 전체 목록을 보여 준다.
   - 후보를 표로 보여 준다: 번호 · 제목 · 연도 · 제1저자 · PDF 유무(`pdf`가 빈칸이면 없음).
   - 후보가 하나면 바로 진행한다. 여러 개이고 어느 것인지 분명하지 않으면 **번호로 고르게 한다**(유일한 질문 지점). 컬렉션 전체를 요청받으면 한 번에 한 편씩 차례로 진행한다.
   - Zotero 연결 실패 시: 오류 메시지를 그대로 보여 주고(보통 "Zotero 실행 + 설정→고급→다른 응용 프로그램과 통신 허용"), `llmwiki doctor`로 확인하거나 PDF 경로를 직접 달라고 한다.
2. **추출**
   - A. Zotero: `llmwiki zotero import <KEY>`
   - B. PDF: `llmwiki extract "<PDF 경로>"` (경로에 공백·한글이 있으면 따옴표)
   - 네트워크가 막혔다는 오류/지연이 있으면 `--offline`을 붙여 다시.
   - 결과 JSON의 `status`가 `duplicate`이면 이미 있는 논문이다 → 알려 주고 멈춘다(사용자가 원하면 `--force`, review.md는 보존됨).
   - `slug`, `figures`, `tables`, `low_confidence_crops`, `warnings`를 기억한다.
3. **읽기** — `wiki/papers/<slug>/` 에서
   - `meta.json`(서지·초록) → `source.md` 전체(페이지 표시 `<!-- p.N -->`) → `figures/figures.md`, `tables/tables.md`.
   - 그림 후보 PNG를 **직접 열어 본다**(최대 5장). 표 수치는 `tables/tableN.png`로 확인한다(markdown 표는 열이 어긋날 수 있음).
   - 텍스트가 거의 없으면(스캔 PDF 경고) 사용자에게 알리고 멈춘다.
4. **요약 후 바로 진행** — 서지(제목·연도·제1저자·DOI)와 핵심 2–3줄, 정한 `category`를 짧게 보여 주고 **묻지 않고** 5로 넘어간다. (위키 안에 새로 쓰는 작업은 확인이 필요 없다 — AGENTS.md 5절)
5. **리뷰 쓰기** — `wiki/papers/<slug>/review.md`의 뼈대(TODO 주석)를 채운다. 형식은 `references/wiki-format.md`, 예시는 `references/review_example.md`.
   - frontmatter: `category`, `tags`(paper + 주제어 2–4개), `essence`, 점수 5개, `citekey`(Zotero 값 우선), `status: reviewed`, `review_date: 오늘`.
   - 7개 헤딩을 모두 채우고 `<!-- TODO … -->` 주석을 지운다. Evaluation의 `?/5`를 숫자로.
   - 사실 문장마다 `[근거: <slug> · p.N]` 또는 `[근거: <slug> · Table N]`.
   - 그림 블록은 dual-coding 3줄 + "원문 PDF 캡처 · 로컬 연구용". ⚠️(신뢰도 낮음) 그림은 눈으로 확인 후에만.
   - 원문 문단을 옮기지 않는다. 한국어 서술, 용어는 원어.
6. **연결** — `llmwiki related --write` 실행 후 이 논문의 `## Related Papers` 자동 블록을 읽는다.
   - 실제로 관계가 보이면(같은 시스템의 후속 연구, 반대 결과, 응용 등) 블록 **밖**에 `### 에이전트 해석`을 추가해 1–3줄로 근거와 함께 쓴다. 근거 없으면 쓰지 않는다.
   - 같은 주제의 논문이 2편 이상이면 `wiki/topics/<주제>.md`를 만들거나 갱신해 두 리뷰를 링크한다(기존 주제 페이지는 덧붙이기만).
7. **목차·기록** — `llmwiki index` → `llmwiki log ingest "<논문 제목>" --note "wiki/papers/<slug>/review.md"`
8. **검사** — `llmwiki lint`. 이 논문 관련 ERROR는 고친다. WARN은 보고만 해도 된다.
9. **보고** — 만든/바꾼 파일 목록, 사용한 그림, lint 요약, 다음 제안(관련 논문 읽기, 질문 예시)을 짧게.

## 하지 말 것
- 유료 LLM API 호출, Zotero DB·PDF 수정, `source.md`/`meta.json` 손편집, related 자동 블록 손편집.
- 기존 review.md를 통째로 덮어쓰기(이미 채워진 리뷰는 사용자 확인 후에만), 근거 없는 수치.
