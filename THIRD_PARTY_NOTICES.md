# Third-party notices (외부에서 가져온 부분)

이 키트의 MIT 라이선스(LICENSE)는 키트 자체 코드에 적용됩니다. 아래 부분은 외부에서 가져와 고쳐 쓴 것입니다.

## 1. Paper Curation (이제현)

Based on Paper Curation by 이제현 (https://github.com/jehyunlee/paper-curation)

| 이 키트의 파일 | 원본 파일 (paper-curation/pipeline/) | 무엇을 가져왔나 / 바꾼 점 |
|---|---|---|
| `tools/llmwiki/site_assets/network.js` | `generate_network.py` (D3 네트워크 스크립트) | 힘 기반 배치·주제 토글·관계 필터·검색 강조·이웃만 보기(Ego)·상세 창·연도 슬라이더·강조·테마·힘 조절·단축키. UMAP/3D(three.js)·CDN 제거, 데이터는 `network-data.js`에서 읽음(file://), 관계 종류·한국어 화면 글자·점 크기(리뷰 점수)·「Codex에게 물어보기」 추가 |
| `tools/llmwiki/site_assets/network.css` | `generate_network.py` (네트워크 화면 스타일) | 외부 글꼴(CDN)·3D 캔버스 제거, 돌아가기·출처 줄·JS 없을 때 그림 스타일 추가 |
| `tools/llmwiki/site_network.py` | `generate_network.py` (`build_network_data`, 화면 구성) | 이 키트 데이터(wiki/papers, related.json, 주제 노트, 자동 군집)로 노드·링크·연결 목록을 만들도록 다시 씀(표준 라이브러리만) |
| `tools/llmwiki/site_assets/pc.css` | `build_topic_index.py` (hero·paper-card·search-box), `review_to_html.py` (`get_css`) | 외부 글꼴 제거, 색 고정(목록=남색, 리뷰=빨강), Audio·Deep Research·다운로드 버튼 스타일 제외 |
| `tools/llmwiki/site.py` (목록·리뷰 화면 구성 부분) | `build_topic_index.py`, `review_to_html.py` | 목록 hero(통계)·논문 카드, 리뷰의 section-box·essence-box·평가 배지·「같이 보면 좋은 논문」 구성을 이 키트 데이터에 맞게 다시 씀. API 키가 필요한 버튼(Deep Research, Audio Overview, 웹 검색)은 넣지 않고 「Codex에게 물어보기」 복사 버튼으로 바꿈 |

## 2. D3.js v7.9.0 (ISC)

- 파일: `tools/llmwiki/site_assets/d3.v7.min.js` (npm `d3@7.9.0` 의 `dist/d3.min.js` 그대로)
- sha256: `f2094bbf6141b359722c4fe454eb6c4b0f0e42cc10cc7af921fc158fceb86539` (279,706 B)
- npm integrity: `sha512-e1U46jVP+w7Iut8Jt8ri1YsPOvFpg46k+K8TpCb0P+zjCkjkPnV7WzfDJzMHy1LnA+wj5pLT1wjO901gLXeEhA==`
- 라이선스: ISC, Copyright 2010-2023 Mike Bostock — 전문은 `tools/llmwiki/site_assets/d3-LICENSE.txt` (위키 화면에는 `site/assets/d3-LICENSE.txt`로 함께 복사됨)
