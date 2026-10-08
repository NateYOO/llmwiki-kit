---
name: wiki-ingest
description: 논문 넣기(ingest). 입력 없음·'최근 1편'이면 zotero next, 제목·키·PDF면 그것으로 추출 → 한국어 7섹션 리뷰 → finish(관련 링크·index·log·lint).
---

# wiki-ingest — 논문 한 편을 위키에 넣기

먼저 `wiki/index.md`(현재 목록)를 읽는다. 리뷰 형식 상세는 `references/wiki-format.md`, 예시는 `references/review_example.md`. 아래에서 `llmwiki`는
macOS/Linux `./llmwiki`, Windows `.\llmwiki.cmd` 로 바꿔 실행한다.

## 입력 해석
사용자가 준 것(스킬 이름 뒤의 글)을 보고 고른다. 컬렉션 이름은 `llmwiki.yaml`의 `practice_collection`이 기본값이라 적지 않는다.
| 입력 | 할 일 |
|---|---|
| 아무것도 없음 · "최근" · "최근 1편" · "컬렉션에서 1편" | `llmwiki zotero next` (묻지 않음) |
| "컬렉션 X에서" | `llmwiki zotero next --collection "X"` |
| "저자 다시 채워 줘" · "다시 해 줘"(서지 사이트가 바빴던 논문) | `llmwiki meta --refresh <slug>` → 나온 한 줄을 그대로 전한다(있는 값은 안 바뀜) |
| PDF 경로 (`.pdf`로 끝남) | 2단계 B로 |
| Zotero 항목 키 (8자 영숫자, 예 `ABCD1234`) | `llmwiki zotero import <KEY>` |
| 논문 제목·저자·키워드 | `llmwiki zotero search "<영어 키워드>"` |

## 절차
1. **고르기**
   - `zotero next`: Zotero에 **추가한 날짜**가 가장 최근이고, 로컬 PDF가 있고, 위키에 아직 없는 논문을 골라 **바로 추출까지** 한다 → 2단계는 건너뛴다. 결과의 `picked`(고른 논문)·`other_candidates`(다음 후보 2편)를 기억한다. `status: none`(종료 코드 3)이면 `message`를 그대로 전하고 멈춘다. `picked.standalone_pdf`(Zotero에 상위 항목 없이 PDF만 있음)면 서지를 PDF에서 찾았으므로 meta.json의 제목·저자·연도를 첫 페이지와 대조해 리뷰에 바르게 쓴다.
   - `zotero search`: **키워드는 영어로 바꿔서**(예: "튜터링" → `tutoring`). 기본은 실습 컬렉션 안, 전체 라이브러리는 `--all`. 0건이면 영어 동의어로 한두 번 더, 초록까지는 `--everything`.
     후보 표(번호 · 제목 · 연도 · 제1저자 · PDF 유무). 하나면 바로 진행, 여럿이고 불분명하면 **번호로 고르게 한다**(유일한 질문 지점).
   - `[오류]`에 컬렉션 번호 목록이 나오면 그 목록을 보여 주고 번호를 고르게 한 뒤 `--collection "<이름>"`으로 다시 한다.
   - Zotero 연결 실패: 오류를 그대로 보여 준다(보통 "Zotero 실행 + Zotero 설정(윈도우: 편집 → 설정, 맥: Zotero → 설정) → 고급 → 기타 → 'Allow other applications on this computer to communicate with Zotero' 체크"). 샌드박스에서 127.0.0.1이 막힌 것 같으면 `--backend sqlite --offline`(Zotero 데이터 폴더 사본, 인터넷 없음)으로 한 번 시도, 안 되면 PDF 경로를 달라고 한다.
2. **추출** (`zotero next`를 썼으면 이미 끝남)
   - A. Zotero: `llmwiki zotero import <KEY>` · B. PDF: `llmwiki extract "<PDF 경로>"` (공백·한글 경로는 따옴표)
   - 네트워크가 막혔다는 오류/지연이 있으면 `--offline`을 붙여 다시.
   - `status`가 `duplicate`이면 이미 있는 논문이다 → 알려 주고 멈춘다(원하면 `--force`, review.md는 보존).
   - `slug`, `figures`, `tables`, `low_confidence_crops`, `warnings`를 기억한다.
   - `notice`가 있으면 그 한 줄을 그대로 전하고 **계속 진행**한다(서지 사이트가 바빠 저자가 비면 `meta_pending: true` — lint WARN일 뿐 오류 아님. 나중에 `llmwiki meta --refresh <slug>`).
   - 결과에 `"scanned": true`(글자 없는 스캔본)면 `notice`를 그대로 전하고 **리뷰를 쓰지 않는다** — 제목·저자만 넣은 자리 표시가 이미 있다. `llmwiki finish <slug>`만 실행하고 멈춘다(OCR 하지 않음).
3. **읽기** — `wiki/papers/<slug>/` 에서
   - `meta.json`(서지·초록) → `source.md` 전체(페이지 표시 `<!-- p.N -->`) → `figures/figures.md`, `tables/tables.md`.
   - 그림 후보 PNG를 **직접 열어 본다**(최대 5장). **표는 PNG로만 본다**: 숫자는 `tables/tableN.png`를 직접 열어 확인한다. `meta.json` 표 항목의 `text`는 화면에 안 보이는 검색용 글자라 표를 찾는 데만 쓴다(칸이 어긋날 수 있어 숫자 근거로 쓰지 않음).
   - 텍스트가 거의 없으면(스캔 PDF) 위 `scanned` 안내대로 finish만 하고 멈춘다.
4. **요약 후 바로 진행** — 서지(제목·연도·제1저자·DOI)와 핵심 2–3줄, 정한 `category`를 짧게 보여 주고 **묻지 않고** 5로 넘어간다. (위키 안에 새로 쓰는 작업은 확인이 필요 없다 — AGENTS.md 5절)
5. **리뷰 쓰기** — `wiki/papers/<slug>/review.md`의 뼈대(TODO 주석)를 채운다. 형식은 `references/wiki-format.md`, 예시는 `references/review_example.md`.
   - frontmatter: `category`, `tags`(paper + 주제어 2–4개), `essence`, 점수 5개, `citekey`(Zotero 값 우선), `status: reviewed`, `review_date: 오늘`.
   - 7개 헤딩을 모두 채우고 `<!-- TODO … -->` 주석을 지운다. Evaluation의 `?/5`를 숫자로.
   - 사실 문장마다 `[근거: <slug> · p.N]` 또는 `[근거: <slug> · Table N]`.
   - 그림 블록은 dual-coding 3줄 + "원문 PDF 캡처 · 로컬 연구용". ⚠️(신뢰도 낮음) 그림은 눈으로 확인 후에만.
   - 표 블록도 PNG 그림 + dual-coding 캡션만: `![Table 1](tables/table1.png)`. **리뷰에 markdown 표(`| … |`)를 만들거나 옮기지 않는다**(화면에 보이지 않고 lint가 WARN). 숫자 인용은 PNG에서 직접 본 것만.
   - 원문 문단을 옮기지 않는다. 한국어 서술, 용어는 원어.
6. **마무리** — `llmwiki finish <slug>` (related --write → index → lint, 완료일 때만 log. 단계별 rc 포함)
   - 이 논문의 `## Related Papers` 자동 블록을 읽고, 실제 관계가 보이면 블록 **밖**에 `### 에이전트 해석` 1–3줄(근거 포함). 근거 없으면 쓰지 않는다.
   - 같은 주제의 논문이 2편 이상이면 `wiki/topics/<주제>.md`를 만들거나 덧붙여 두 리뷰를 링크한다.
   - `paper_issues`의 ERROR를 고치고 `llmwiki finish <slug>`를 다시 부른다(log는 완료됐을 때 한 번만 남음). 마지막 줄이 `넣기 완료 ✅ …`이면 끝.
7. **보고** — `finish`의 마지막 줄, 만든/바꾼 파일, 사용한 그림. `finish`가 위키 화면(`site/`)도 다시 만들었으니 「브라우저에서 새로고침(F5 / Cmd+R) 하세요」와 이 논문의 관련 논문 수(「관련 논문 n편」 또는 「관련 논문 없음(논문을 더 넣으면 연결이 생겨요)」)를 알려 준다. `zotero next`였으면 끝에 한 줄: 「다른 논문을 원하면: `$wiki-ingest <제목 일부>` (다음 후보: …)」 — 묻지 않는다.

## 하지 말 것
- 유료 LLM API 호출, Zotero DB·PDF 수정, `source.md`/`meta.json` 손편집, related 자동 블록 손편집.
- 기존 review.md를 통째로 덮어쓰기(이미 채워진 리뷰는 사용자 확인 후에만), 근거 없는 수치.
