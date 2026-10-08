# 위키 형식 상세 (wiki-format)

> AGENTS.md는 매 턴 읽히므로 짧게 두고, 리뷰·주제 페이지를 **쓸 때만** 이 파일을 읽는다.
> 리뷰 예시는 같은 폴더의 `review_example.md`.

## 1. 리뷰 형식 (`wiki/papers/<slug>/review.md`)
헤딩 이름과 순서를 **정확히** 지킨다 (7개 + Related Papers):
```
# <원제목>
> **저자**: … | **날짜**: … | **DOI**: [..](https://doi.org/..)
---
## Essence                      대표 그림(선택) + 핵심 1–2문장
## Motivation                   - **Known**: / - **Gap**: / - **Why**: / - **Approach**: (각 1–2문장)
## Achievement                  그림(선택) + 번호 목록 "1. **굵은 제목**: 설명 [근거: …]"
## How                          그림(선택) + 방법 bullet
## Originality                  bullet
## Limitation & Further Study   bullet (저자가 밝힌 한계 / 리뷰어 의견을 구분)
## Evaluation                   - Novelty: n/5 · - Technical Soundness: n/5 · - Significance: n/5 · - Clarity: n/5 · - Overall: n/5
                                **총평**: 1–2문장
## Related Papers               자동 블록(<!-- llmwiki:related:start/end -->) + 선택 "### 에이전트 해석"
```
- **한국어로 쓴다.** 단 기술 용어·모델명·데이터셋·알고리즘·통계량·제품명은 원어 그대로 둔다. ("conversational tutoring system을 설계했다" O / "대화형 튜터링 시스템(conversational tutoring system)" X)
- 점수는 1–5 정수. 본문 점수와 frontmatter 점수를 같게 쓴다.
- 자동 related 블록 안은 손으로 고치지 않는다(`llmwiki related --write`가 덮어씀). 해석은 블록 밖 `### 에이전트 해석`에 쓴다.

## 2. frontmatter 스키마 (평평한 키만 — Obsidian Properties 호환)
```yaml
title: "원제목"               # 필수
authors: ["First Last", …]    # 필수, 목록
year: 2024                    # 필수, 정수
date: "2024-04-26"
doi: "10.xxxx/…"              # 없으면 ""
arxiv: "2404.17460"
venue: ""
url: ""
citekey: "schmucker2024ruffle" # Zotero citation key가 있으면 그대로, 없으면 성+연도+제목첫단어(소문자)
zotero_key: ""                # Zotero 항목 키(있을 때)
pdf: ""                       # 로컬 PDF 경로(CLI가 채움)
slug: "<폴더 이름과 동일>"     # 필수
category: "주제 분류"          # 필수(에이전트가 정함, index.md 묶음 기준)
tags: [paper, …]              # 필수, 목록
essence: "한 줄 요약"          # 필수
score_novelty: 4              # 필수 1–5
score_technical: 4
score_significance: 4
score_clarity: 4
score: 4                      # = Overall
status: reviewed              # draft | reviewed (다 쓰고 lint 통과하면 reviewed)
schema_version: llmwiki-v1
review_date: "YYYY-MM-DD"
```
중첩 객체(`scores: {…}`)는 쓰지 않는다.

## 3. 링크 규칙 (하나로 통일)
- **표준 마크다운 상대 경로 링크만 쓴다.** 위키링크 `[[…]]`는 쓰지 않는다(Obsidian이 없어도 GitHub·VS Code·Codex에서 열리게).
  - 리뷰 → 리뷰: `[제목](../<slug>/review.md)` · 주제 → 리뷰: `[제목](../papers/<slug>/review.md)`
  - index → 리뷰: `[제목](papers/<slug>/review.md)` · drafts → 리뷰: `[제목](../wiki/papers/<slug>/review.md)`
- 그림: `![Figure 2](figures/fig2.png)` (리뷰 기준 상대 경로). 표: `![Table 1](tables/table1.png)`.
- 새 페이지를 만들면 반드시 index에 걸리게 하고(`llmwiki index`), 관련 페이지끼리 서로 링크한다.

## 4. 그림 규칙 (dual-coding)
Essence·Achievement·How에 각각 최대 1장. PNG를 **직접 열어 보고** 고른다(캡션만 보고 고르지 않는다). 형식:
```
![Figure 1](figures/fig1.png)

*Figure 1. <원문 캡션 앞부분>* — 원문 PDF 캡처 · 로컬 연구용
- 무엇이 보이는가: …
- 어떻게 읽을까: …
- 텍스트만 읽으면 놓치는 것: …
```
자동 크롭이 잘못됐으면(⚠️ 표시, 잘림, 엉뚱한 영역) 그 그림은 쓰지 말고 사용자에게 알린다.

## 5. 근거·인용 규칙
- 사실 주장마다 근거 꼬리표를 단다: `[근거: <slug> · p.N]`(source.md의 `<!-- p.N -->` 페이지), `[근거: <slug> · Table 2]`, `[근거: <slug> · Achievement]`(리뷰 섹션).
- 수치·인용문은 source.md나 표 PNG에서 **직접 확인한 것만** 쓴다. 확인 못 한 내용은 쓰지 않거나 "(원문 확인 필요)"로 표시한다.
- 원문 직접 인용은 한 번에 2문장 이하, `>` 인용 블록 + 페이지 표기. **원문을 통째로(문단 단위로) 옮기지 않는다** — source.md는 검색·확인용이다.
- 위키에 근거가 없으면 지어내지 말고 "위키에 근거 없음"이라고 말한 뒤 ingest를 제안한다. 추측·아이디어는 `(가설)`로 표시한다.

