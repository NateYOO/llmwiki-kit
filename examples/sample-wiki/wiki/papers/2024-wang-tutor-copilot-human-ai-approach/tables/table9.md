<!-- 자동 추출 표: 열이 합쳐지거나 어긋날 수 있음. 정확한 값은 table9.png 확인 -->

**Table 9: Taxonomy of tutoring moments, including their definitions, examples, and frequency over the labelled dataset. We train binary classifiers to identify these moments at scale and report their test F1 score as well. A majority of Tutor CoPilot usage concetrates during the “meat” of student learning: when the student is attempting the problem, or after they have attempted the problem and the tutor is giving them feedback. The classifier for “after exit ticket attempt” scored a low test F1 score, even after tuning the class-imbalance loss, thus we omit its frequency. Note that the frequencies do not sum to 1 because the classifiers are not mutually exclusive.**

| Moment (Frequency) | Definition | Examples | F1 |
|---|---|---|---|
| Start of session | The tutoring session is just starting. The | “Happy to work with you today!” | 0.79 |
| (0.9%) | student and tutor have not yet started a problem. |  |  |
| Start of problem | The tutor starts a new problem and/or gives | “Go ahead and start showing your | 0.70 |
| (3.2%) | instructions for the new problem. | work for this question.” |  |
| During problem attempt | The student is attempting the problem and/or | “Are you working on this problem?” | 0.70 |
| (49.5%) | the tutor has not yet given away the answer |  |  |
| or explanation. |  |  |  |
| After problem attempt | The student has attempted the problem and | “We know that we cannot subtract | 0.84 |
| (42.1%) | the tutor is providing feedback. After a | 1 - 3, so we will need to borrow |  |
| problem has been attempted, the tutor may want | from the whole number.” |  |  |
| to start a new problem (category “start of |  |  |  |
| problem”). |  |  |  |
| Start of exit ticket | The tutor starts an exit ticket for the | “Now it is time for you to show | 0.83 |
| (1.1%) | student. Note that the exit ticket is a brief | what you have learned by completing |  |
| assessment near the end of the tutoring | the Exit Ticket.” |  |  |
| session and the tutor cannot help the student |  |  |  |
| here, unlike for the normal problems. |  |  |  |
| During exit ticket attempt | The student is attempting the exit ticket. | “I can’t help you with the exit | 0.0 |
| ticket question.” |  |  |  |
| After exit ticket attempt | The student has attempted the exit ticket and | Congratulations. You’ve scored 100% | 0.90 |
| (4.6%) | the tutor is providing feedback. Afterwards, | in Exit Ticket questions.” |  |
| the tutor may want to start a new exit ticket |  |  |  |
| (category “start of exit ticket”). |  |  |  |
| End of session | The tutoring session is ending. | “We will continue in the next session.” | 0.98 |
| (1.9%) |  |  |  |
