<!-- 자동 추출 표: 열이 합쳐지거나 어긋날 수 있음. 정확한 값은 table1.png 확인 -->

**Table 1: Taxonomy of high- and low-quality strategies, including their definitions, examples, and frequency over the labelled dataset. We train binary classifiers to identify these strategies at scale and report their test F1 score as well.**

| Quality | Strategy Name | Definition | Examples | F1 |
|---|---|---|---|---|
| Category | (Frequency) |  |  |  |
| High | Prompt Student | The tutor prompts the student | “Go ahead and try to explain | 0.89 |
| to Explain | to explain a concept, rule, or | how you got the answer.” |  |  |
| (2%) | their reasoning. |  |  |  |
| High | Ask Question | The tutor asks the student a | “What number can we multiply | 0.90 |
| to Guide Thinking | question to help them think | the number 10 to get an equal |  |  |
| (5%) | the problem. | value of 100?” |  |  |
| High | Affirm Student’s | The tutor affirms the student’s | “Yes, 20 is the correct answer.” | 0.65 |
| Correct Attempt | correct attempt. |  |  |  |
| (9%) |  |  |  |  |
| Low | Ask Student to Retry | The tutor asks the student to | “Please recheck your answer.” | 0.73 |
| (1% ) | recheck their work or try again. |  |  |  |
| Low | Give Away the | The tutor provides the answer | “So, the greatest number will | 0.76 |
| Answer / Explanation | or explanation to the student. | be 7520.” |  |  |
| (9%) |  |  |  |  |
| Low | Give Away the | The tutor provides a strategy | “We can order the list according | 0.79 |
| Solution Strategy | for solving the problem. | to the hundredths place value.” |  |  |
| (11%) |  |  |  |  |
| Low | Encourage Student | The tutor encourages the | “That’s a good try!” | 0.81 |
| in Generic Way | student without being specific |  |  |  |
| (12%) | about the student’s attempt. |  |  |  |
