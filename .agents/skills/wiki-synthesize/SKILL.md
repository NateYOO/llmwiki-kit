---
name: wiki-synthesize
description: 위키 종합(synthesize). 서론 초안·주제 탐색·아이디어 결합·공통 한계, 네트워크 질문(이웃·덩어리 서론·미해결 빈틈·군집 결합·허브). 결과는 drafts/.
---

# wiki-synthesize — 여러 논문을 엮어 내 연구로

먼저 `wiki/index.md`를 읽는다. `llmwiki`는 macOS/Linux `./llmwiki`, Windows `.\llmwiki.cmd`.
공통 규칙:
- **모든 문장**에 근거 꼬리표 `[근거: <slug> · <섹션 또는 p.N>]`. 여러 논문이면 `[근거: a · Gap; b · p.3]`. 근거 없는 문장은 `(가설)`로 시작한다.
- 결과는 **`drafts/`에 새 파일로 저장**한다(파일 이름은 아래 표). 같은 이름이 있으면 덮어쓰지 말고 `-2`를 붙인다. 사용자 글은 고치지 않는다.
- 저장 후 `llmwiki index` → `llmwiki log synthesize "<모드>: <주제>" --note "drafts/<파일>"`. (위키 화면 `site/`가 있으면 log가 자동 갱신 → 학생에게 "브라우저 새로고침(F5, 맥 Cmd+R)" 안내)
- **synthesize = `drafts/`에 남기는 문서.** 채팅으로 짧게 답하거나 비교·아이디어 몇 줄만 원하면 `$wiki-query`(사실 확인·비교·아이디어·연구 확장·반론·깊게 조사)로 안내한다. 웹 검색 금지, 위키 안 자료만.
- 위키에 논문이 부족하면(모드별 최소 편수 미만) 그렇게 말하고 `$wiki-ingest`를 제안한다. 그래도 원하면 진행하되 맨 위에 "근거 n편" 경고를 쓴다.

| 모드 | 한 줄 호출 예 | 저장 파일 |
|---|---|---|
| 1 서론 | `$wiki-synthesize 서론 LLM 튜터링의 학습 효과` | `drafts/intro-<주제-영문>-YYYYMMDD.md` |
| 2 주제탐색 | `$wiki-synthesize 주제탐색 AI 교육` | `wiki/topics/<주제>.md` (+ `drafts/topic-map-<분야>-YYYYMMDD.md`) |
| 3 결합 | `$wiki-synthesize 결합 2024-schmucker-… + 2024-wang-…` | `drafts/merge-<짧은이름>-YYYYMMDD.md` |
| 4 공통한계 | `$wiki-synthesize 공통한계` | `drafts/gaps-YYYYMMDD.md` (+ 원자료 `drafts/_sections-limitation-gap-YYYYMMDD.md`) |
| N1 이웃 | `$wiki-synthesize 이웃 <새 논문 slug>` | `drafts/net-neighbors-<slug>-YYYYMMDD.md` |
| N2 덩어리서론 | `$wiki-synthesize 덩어리서론` | `drafts/net-intro-flow-YYYYMMDD.md` |
| N3 미해결빈틈 | `$wiki-synthesize 미해결빈틈` | `drafts/net-open-gaps-YYYYMMDD.md` |
| N4 군집결합 | `$wiki-synthesize 군집결합` | `drafts/net-bridge-YYYYMMDD.md` |
| N5 허브 | `$wiki-synthesize 허브` | `drafts/net-hubs-YYYYMMDD.md` |

## 1. 서론 초안 (최소 2편)
1. `llmwiki search "<주제 핵심어>"` 로 관련 리뷰를 찾고, `llmwiki sections --name known,gap,why,essence,limitation --slugs <찾은 slug들>` 로 재료를 모은다.
2. 각 리뷰와 필요한 source.md 페이지를 읽어 수치·주장을 확인한다.
3. 구조(한국어, 학술 문체, 문단마다 3–6문장):
   ```
   # 서론 초안: <주제>
   > 근거 n편 · 자동 생성 초안 — 사람이 검토·수정할 것 (YYYY-MM-DD)
   ## 1. 배경            (Known 중심: 왜 중요한 분야인가)
   ## 2. 선행연구        (논문별 접근과 성과를 비교, 같은 흐름끼리 묶기)
   ## 3. 연구 공백        (Gap·Limitation의 공통점 → 아직 안 된 것)
   ## 4. 연구 목적        (공백에서 나온 목적·연구질문 1–3개, (가설) 표시)
   ## 참고한 위키 페이지  (리뷰 링크 목록: ../wiki/papers/<slug>/review.md)
   ```
4. 문장 끝마다 꼬리표. 원문 문장 복사 금지(인용은 2문장 이하 `>`).

## 2. 주제 탐색 (최소 3편 권장)
1. `llmwiki clusters` (군집·대표 단어·군집 간 유사도) 와 `llmwiki related --json` 을 본다. 각 리뷰의 category·tags·Essence도 읽는다.
2. 군집마다 이름을 짓고 `wiki/topics/<영문-소문자-하이픈>.md` 를 만들거나 갱신한다(형식은 wiki-lint 스킬 4절: 핵심 정리 / 논문 / 열린 질문). 새 파일을 만들기 전 목록을 보여 주고 확인.
3. `drafts/topic-map-<분야>-YYYYMMDD.md`:
   - 군집 표: 군집 이름 · 논문 · 대표 단어 · 공통 질문 (각 칸 근거)
   - 군집이 왜 이렇게 나뉘었는지 설명(자동 군집은 어휘 기반이라는 한계 명시)
   - **미탐색 조합**: `cross_links` 유사도가 낮은 군집 쌍 또는 서로 링크가 없는 논문 쌍 → "A의 방법 × B의 문제" 형식 2–4개, 각 조합마다 왜 비어 있는지 근거와 (가설).
4. `llmwiki related --write`(주제 페이지가 생기면 연결 확인) → `llmwiki index` → log.

## 3. 아이디어 결합 (2–3개 입력)
입력은 논문 slug/제목 또는 `drafts/` 아이디어 메모. 이름이 모호하면 `llmwiki search`로 찾아 확인한다.
1. 각 입력의 Essence·How·Achievement·Limitation(메모면 핵심 주장)을 읽는다 (`llmwiki sections --name essence,how,achievement,limitation --slugs a,b`).
2. `drafts/merge-<짧은이름>-YYYYMMDD.md`:
   ```
   # 아이디어 결합: <A> × <B> (× <C>)
   ## 1. 각 재료의 핵심       (입력별 2–3문장, 꼬리표)
   ## 2. 결합 제안            (무엇을 합치면 무엇이 새로 가능한가, 연구질문 1–2개, (가설))
   ## 3. 충돌·긴장             (가정·대상·측정·규모가 어긋나는 지점 — 표: 항목 | A | B | 해결안)
   ## 4. 검증 방법             (설계·대상·측정 지표·비교 조건·필요한 데이터, 예상 위험)
   ## 5. 다음 행동             (읽을 논문, 파일럿 규모 등 3개 이내)
   ```

## 4. 공통 한계·빈틈·후속연구 (최소 2편)
1. `llmwiki sections --name limitation,gap --out drafts/_sections-limitation-gap-YYYYMMDD.md` (원자료 저장; 이미 있으면 `--force` 대신 날짜 뒤 `-2`).
2. 원자료를 읽고 패턴을 묶는다(예: 표본·기간, 측정 도구, 일반화, 윤리·프라이버시, 비용·확장성, 재현성).
3. `drafts/gaps-YYYYMMDD.md`:
   ```
   # 공통 한계·빈틈·후속연구 (n편)
   | 패턴 | 해당 논문(꼬리표) | 구체 내용 | 후속연구 방향 (가설) |
   |---|---|---|---|
   ## 가장 자주 나온 빈틈 3개 — 왜 반복되나
   ## 내 연구로 이어질 수 있는 질문 (가설)
   ```
   표의 각 행은 최소 1개 꼬리표. 한 논문에만 나온 것은 "단발"로 표시.

## N. 네트워크를 질문거리로 (시각화가 아니라 "무엇을 물을지"를 찾는 용도)
링크 = review.md 사이의 상대 링크. 자동 링크(`## Related Papers` 블록)와 **근거 링크**(블록 밖 '에이전트 해석'에 근거와 함께 쓴 링크)를 구분한다.
논문이 적으면 자동 링크가 거의 모두를 잇는다 → 판단은 **근거 링크 수**와 관계(🏛 기반/🔗 후속/🔄 다른 접근)를 우선한다.
모든 문장에 근거 꼬리표, 저장 후 `llmwiki index` → `llmwiki log synthesize "N<번호> <이름>: <대상>" --note "drafts/<파일>"`.

### N1. 새 논문의 이웃과 관계 (`이웃 <slug>`)
1. `llmwiki related <slug>` (관계·링크 방향·공유 주제·공저자·자동 점수).
2. 이웃마다 review.md의 Essence·Motivation·Limitation을 읽고 표: `이웃 | 관계(자동) | 실제 관계(내 판단: 기반·후속·다른 접근·응용·반론) | 근거`.
3. "이 논문이 이웃들 사이에서 차지하는 자리" 3–5문장 + 새 논문의 review.md '에이전트 해석'에 넣을 링크 문장 제안(넣는 것은 사용자 확인 후).

### N2. 연결 덩어리별 서론 흐름 (`덩어리서론`)
1. `llmwiki hubs` 의 '연결 덩어리'와 `llmwiki clusters` 군집을 함께 본다(덩어리가 1개면 군집 단위로).
2. 덩어리/군집마다 서론 문단 흐름 한 줄씩: `배경 → 선행연구(이 덩어리의 논문들) → 빈틈 → 이 덩어리에서 나올 연구 목적`, 문장마다 근거.
3. 덩어리 간 연결 문장 1–2개(어느 덩어리의 빈틈을 다른 덩어리의 방법이 메우는지).

### N3. 연결된 논문들의 공통 한계 중 미해결 빈틈 (`미해결빈틈`)
1. `llmwiki hubs`로 덩어리(또는 지정한 논문 묶음)를 정하고 `llmwiki sections --name limitation,gap --slugs <그 묶음> --out drafts/_sections-limitation-gap-net-YYYYMMDD.md`.
2. 한계를 패턴으로 묶은 뒤, 각 패턴이 **묶음 안의 다른 논문에서 해결됐는지** 확인(그 논문의 Achievement·How). 표: `패턴 | 제기한 논문 | 해결 시도한 논문(있으면) | 상태(미해결/부분/해결) | 근거`.
3. 미해결 패턴만 골라 후속연구 질문 2–3개 (`(가설)`).

### N4. 링크가 없는 두 군집 결합 (`군집결합`)
1. `llmwiki clusters` 의 군집 간 `유사도`와 `링크 수`(근거 링크)를 본다. **근거 링크 0**이거나 링크가 가장 적은 군집 쌍을 고른다.
2. 두 군집의 대표 논문(허브)을 하나씩 골라 3절 '결합' 형식(공통 질문 · 결합 제안 · 충돌/전제 · 검증 방법)으로 쓴다.
3. 왜 아직 안 묶였는지(분야·방법·데이터 차이)를 근거와 함께 1–2문장.

### N5. 허브 논문 (`허브`)
1. `llmwiki hubs --top 5`.
2. 허브마다: 무엇이 여러 논의를 잇는지(공유 개념·방법), 허브를 빼면 끊기는 연결, 허브의 한계가 이웃들에 미치는 영향 — 문장마다 근거.
3. "처음 읽을 3편" 추천 순서(허브 → 이웃)와 이유.

## 하지 말 것
- 근거 없는 일반론으로 문단 채우기, 원문 문단 복사, 사용자 메모 수정, 유료 API.
