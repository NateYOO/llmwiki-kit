---
title: 'Practical and Ethical Challenges of Large Language Models in Education: A Systematic Scoping Review'
authors: [Lixiang Yan, Lele Sha, Linxuan Zhao, Yuheng Li, Roberto Martinez-Maldonado, Guanliang Chen, Xinyu Li, Yueqiao Jin, Dragan Gašević]
year: 2023
date: '2023-03-17'
doi: 10.1111/bjet.13370
arxiv: '2303.13379'
venue: British Journal of Educational Technology
url: https://arxiv.org/abs/2303.13379
citekey: yan2023practical
zotero_key: ''
pdf: ''
slug: 2023-yan-practical-ethical-challenges-large
category: LLM 교육 활용 개관·윤리
tags: [paper, scoping-review, ethics, replicability, technology-readiness]
essence: 2017–2022년 동료심사 논문 118편을 체계적 스코핑 리뷰로 분석해 LLM 교육 활용 53개 과제(9개 범주)를 정리하고, 낮은 기술 성숙도·재현성·투명성 부족과 프라이버시·beneficence 고려 부족을 실천적·윤리적 과제로 제시했다.
score_novelty: 3
score_technical: 4
score_significance: 4
score_clarity: 4
score: 4
status: reviewed
schema_version: llmwiki-v1
review_date: '2026-10-08'
---

# Practical and Ethical Challenges of Large Language Models in Education: A Systematic Scoping Review

> **저자**: Lixiang Yan, Lele Sha, Linxuan Zhao, Yuheng Li, Roberto Martinez-Maldonado, Guanliang Chen, Xinyu Li, Yueqiao Jin, Dragan Gašević | **날짜**: 2023-03-17 | **DOI**: [10.1111/bjet.13370](https://doi.org/10.1111/bjet.13370) · arXiv [2303.13379](https://arxiv.org/abs/2303.13379)
> **자료**: [추출 원문](source.md) · [그림 목록](figures/figures.md) · [표 목록](tables/tables.md) — 원문 PDF는 Zotero/로컬 보관

---

## Essence

LLM으로 교육 과제를 자동화한 동료심사 논문 118편을 PRISMA 기반 스코핑 리뷰로 분석해 53개 활용 사례를 9개 범주로 묶고, 실천성(기술 성숙도·성능·재현성)과 윤리성(투명성·프라이버시·평등·beneficence)의 과제를 정리했다 [근거: 2023-yan-practical-ethical-challenges-large · p.1].

## Motivation

- **Known**: 텍스트 생성·분석은 교육에서 시간이 많이 드는 일이며, LLM은 문항 생성·에세이 채점 같은 교육 기술에 점점 많이 쓰인다 [근거: 2023-yan-practical-ethical-challenges-large · p.2].
- **Gap**: LLM 기반 교육 혁신의 실천성과 윤리성에 대한 우려가 있지만, 이를 체계적으로 평가한 개관이 없었다 [근거: 2023-yan-practical-ethical-challenges-large · p.1].
- **Why**: 이런 우려가 실제 교육 현장에서의 연구와 도입을 가로막을 수 있다 [근거: 2023-yan-practical-ethical-challenges-large · p.1].
- **Approach**: 4개 데이터베이스 + Google Scholar·ERIC 검색, 2017–2022 동료심사 논문, 귀납적 주제 분석과 7개 평가 항목(TRL, 성능, 재현성, 투명성, 프라이버시, 평등, beneficence)으로 코딩했다 [근거: 2023-yan-practical-ethical-challenges-large · p.7–9].

## Achievement

![Table 1](tables/table1.png)

*TABLE 1. Educational Tasks in LLMs Research* — 원문 PDF 캡처 · 로컬 연구용 (arXiv CC BY 4.0)
- 무엇이 보이는가: 9개 범주(profiling/labelling, detection, grading, teaching support, prediction, knowledge representation, feedback, content generation, recommendation)별 세부 과제 목록.
- 어떻게 읽을까: 범주별로 어떤 이해관계자·언어·과제가 연구되었는지 한눈에 비교하는 지도다.
- 텍스트만 읽으면 놓치는 것: 범주마다 세부 과제 수의 편차가 커서(profiling/labelling이 가장 많음) 연구가 분류 과제에 쏠려 있다는 인상.

1. **활용 지도**: 53개 활용 사례를 9개 범주로 정리했다 [근거: 2023-yan-practical-ethical-challenges-large · p.9, Table 1].
2. **낮은 기술 성숙도**: 3/4 이상(n=89)이 applied research 단계(TRL-2)였고, 실제 학습 환경에서 검증한 연구는 7편뿐이었다 [근거: 2023-yan-practical-ethical-challenges-large · p.10–11].
3. **재현성 부족**: 107편이 재현에 필요한 정보를 충분히 공개하지 않았고, 코드와 데이터를 모두 공개해 바로 재현 가능한 연구는 11편이었다 [근거: 2023-yan-practical-ethical-challenges-large · p.12].
4. **윤리적 과제**: 대부분(n=109)이 AI 연구자에게만 투명한 Tier 1 수준이었고, 학생 데이터로 fine-tuning한 연구 중 동의·보호 절차를 명시한 연구가 없었다 [근거: 2023-yan-practical-ethical-challenges-large · p.12–13].
5. **세 가지 권고**: 최신 모델로 갱신, 모델·시스템 오픈소스화, 개발 전 과정의 human-centred 접근 [근거: 2023-yan-practical-ethical-challenges-large · p.18].

## How

![Figure 1](figures/fig1.png)

*FIGURE 1. Systematic scoping review process following the PRISMA protocol.* — 원문 PDF 캡처 · 로컬 연구용 (arXiv CC BY 4.0)
- 무엇이 보이는가: Database search(n=854) → Title/abstract screen(663) → Full-text screen(197) → Included(118), 단계별 제외 수.
- 어떻게 읽을까: 왼쪽에서 오른쪽으로 걸러지는 PRISMA 흐름도.
- 텍스트만 읽으면 놓치는 것: 제목·초록 단계에서 가장 많이(466편) 빠졌다는 비율.

- PRISMA 프로토콜, Scopus·ACM DL·IEEE Xplore·Web of Science + Google Scholar·ERIC, 2017-01-01–2022-12-31, 동료심사 논문만 [근거: 2023-yan-practical-ethical-challenges-large · p.7].
- 두 연구자가 20편을 독립 코딩해 Cohen's kappa 0.80 이상을 확보한 뒤 나머지를 나눠 코딩·교차 확인했다 [근거: 2023-yan-practical-ethical-challenges-large · p.8].
- 기술 성숙도는 호주 국방부 TRL 9단계, 투명성은 Chaudhry et al.의 3 tier 지표로 평가했다 [근거: 2023-yan-practical-ethical-challenges-large · p.8; p.12].

## Originality

- LLM 교육 연구를 "무엇을 자동화하나"뿐 아니라 실천성·윤리성의 7개 항목으로 함께 평가한 구조화된 틀 [근거: 2023-yan-practical-ethical-challenges-large · p.2].
- TRL처럼 다른 분야의 성숙도 척도를 교육 AI 평가에 적용했다.

## Limitation & Further Study

- (저자) 7개 평가 항목이 실천성·윤리성의 모든 측면을 담지 못할 수 있다 [근거: 2023-yan-practical-ethical-challenges-large · p.17].
- (저자) 영어 논문만 포함했고, 동료심사 논문만 넣어 arXiv 등 최신 연구가 빠졌을 수 있다 [근거: 2023-yan-practical-ethical-challenges-large · p.17].
- (저자) 후속 연구는 투명성 Tier 3, TRL-7(실제 환경 통합·검증) 수준을 목표로 해야 한다 [근거: 2023-yan-practical-ethical-challenges-large · p.16].
- (리뷰어) 분석 기간이 2022년까지라 ChatGPT 이후 연구는 거의 포함되지 않는다; 연구 92%가 BERT 계열이었다 [근거: 2023-yan-practical-ethical-challenges-large · p.14].
- (리뷰어) 스코핑 리뷰 특성상 개별 연구의 질은 평가하지 않았다 [근거: 2023-yan-practical-ethical-challenges-large · p.7].

## Evaluation

- Novelty: 3/5
- Technical Soundness: 4/5
- Significance: 4/5
- Clarity: 4/5
- Overall: 4/5

**총평**: ChatGPT 이전 LLM 교육 연구의 지형과 약점(낮은 성숙도·재현성·프라이버시)을 정리한 기준 문헌으로, 이후 연구가 무엇을 증명해야 하는지 체크리스트를 준다.

## Related Papers

<!-- llmwiki:related:start -->
_자동 계산(llmwiki related): 어휘 유사도 + 저자·연도 규칙. 의미 해석은 아래 '에이전트 해석'에 근거와 함께._

- 🔄 다른 접근: [Ruffle&Riley: Insights from Designing and Evaluating a Large Language Model-Based Conversational Tutoring System](../2024-schmucker-ruffle-riley-insights-designing/review.md) — TF-IDF 유사도 0.07 · BM25 1위 · 1년 뒤의 연구
- 🔄 다른 접근: [Tutor CoPilot: A Human-AI Approach for Scaling Real-Time Expertise](../2024-wang-tutor-copilot-human-ai-approach/review.md) — TF-IDF 유사도 0.05 · BM25 2위 · 1년 뒤의 연구
<!-- llmwiki:related:end -->

### 에이전트 해석
- 🧪 [Tutor CoPilot](../2024-wang-tutor-copilot-human-ai-approach/review.md)은 이 리뷰가 드물다고 한 "실제 학습 환경 검증(TRL-7 수준)"과 사전등록·비식별화를 갖춘 사례로 읽을 수 있다 (가설: TRL 등급은 저자들이 매긴 것이 아님) [근거: 2023-yan-practical-ethical-challenges-large · p.16; 2024-wang-tutor-copilot-human-ai-approach · How].
- 🧪 [Ruffle&Riley](../2024-schmucker-ruffle-riley-insights-designing/review.md)는 시스템 오픈소스 공개를 밝혀 이 리뷰의 재현성 권고와 맞닿는다 [근거: 2024-schmucker-ruffle-riley-insights-designing · p.5; 2023-yan-practical-ethical-challenges-large · p.18].
