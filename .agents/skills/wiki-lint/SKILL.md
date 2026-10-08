---
name: wiki-lint
description: 위키 점검(lint). llmwiki lint 기계 검사 + 의미 점검(모순·근거 없는 주장·빠진 연결) + 안전한 수정·주제 페이지 제안.
---

# wiki-lint — 검증하고 연결하기

`llmwiki`는 macOS/Linux `./llmwiki`, Windows `.\llmwiki.cmd`. 먼저 `wiki/index.md`를 읽는다.

## 1. 기계 검사
`llmwiki lint` (자세히 보려면 `--json`). 검사 항목:
| code | 뜻 | 고치는 법 |
|---|---|---|
| frontmatter | 필수 키·형식·slug 불일치·중첩 속성 | review.md frontmatter 수정 (`../wiki-ingest/references/wiki-format.md` 2절) |
| headings / empty-section / todo | 7개 헤딩 누락·순서·빈 섹션·TODO 남음 | 리뷰 보완 (원문 근거 확인 후) |
| score | 1–5 정수 아님, 본문과 frontmatter 불일치, `?/5` | 숫자 맞추기 |
| broken-link | 없는 파일로 가는 링크·이미지 | 경로 수정 (wiki-format.md 3절) |
| orphan | index.md에 없음 | `llmwiki index` |
| isolated | 다른 논문·주제에서 들어오는 링크 없음 | related 갱신, 주제 페이지에 링크 |
| duplicate-doi / duplicate-arxiv | 같은 논문 두 번 | 사용자에게 어느 쪽을 남길지 **확인 후** 정리 |
| related-asym | A→B는 있는데 B→A 없음 | `llmwiki related --write` |
| figures | 리뷰에 그림 없음·PNG 누락·신뢰도 낮은 크롭·출처 표기 없음 | 그림 PNG 열어 보고 추가/교체 |
| verbatim | 원문과 긴 연속 일치(복사 의심) | 한국어로 다시 요약, 인용은 2문장 이하 |
| log | log 헤더 형식 불일치 | 새 항목부터 형식 지키기(과거 기록은 고치지 않음) |

## 2. 안전한 자동 수정
`llmwiki lint --fix` = 관련 링크 재계산(`related --write`) + `index` 재생성 후 다시 검사. 파일 내용(리뷰 본문)은 바꾸지 않는다.

## 3. 에이전트 검사 (읽고 판단)
기계가 못 보는 것을 리뷰들을 읽어 확인한다. 각 지적에는 근거 꼬리표를 단다.
- **모순**: 같은 질문에 다른 결론을 낸 논문(예: 효과 있음 vs 없음). 조건(대상·표본·측정)이 다른지 확인.
- **낡은 주장**: 더 최신 논문이 대체한 주장.
- **빠진 주제**: 2편 이상에 나오는데 `wiki/topics/`에 페이지가 없는 개념 → 주제 페이지 제안.
- **연결 보강**: 각 리뷰의 related 자동 블록을 보고, 실제 관계(🏛 기반·🔗 후속·⚖️ 반론·🧪 응용·🔄 다른 접근)가 분명한 것만 `### 에이전트 해석`에 근거와 함께 추가. 자동 블록은 손대지 않는다.
- **category 일관성**: 비슷한 논문이 다른 category 이름(띄어쓰기·영한 혼용)으로 흩어졌는지.
- **그림 검수**: lint가 ⚠️ 표시한 그림 PNG를 열어 잘림·엉뚱한 영역인지 확인.

## 4. 고치기
- 고칠 목록(파일·내용)을 먼저 보여 주고 확인을 받는다. 삭제·병합은 반드시 확인.
- 주제 페이지 형식 (`wiki/topics/<영문-소문자-하이픈>.md`):
  ```
  ---
  title: "주제 이름"
  summary: "한 줄 요약"
  tags: [topic]
  ---
  # 주제 이름
  ## 핵심 정리   (각 문장에 [근거: …])
  ## 논문
  - [제목](../papers/<slug>/review.md) — 이 주제에서의 역할
  ## 열린 질문
  ```
- 고친 뒤 `llmwiki related --write` → `llmwiki index` → `llmwiki lint` 다시.

## 5. 보고·기록
ERROR/WARN 개수(전→후), 고친 것, 사용자 판단이 필요한 것(중복·모순)을 표로. 마지막에 `llmwiki log lint "점검 요약" --note "ERROR a→b, WARN c→d"`.
