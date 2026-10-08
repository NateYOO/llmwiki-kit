"""순수 Python 검색 도구: 토크나이저, BM25, TF-IDF 코사인, RRF 융합.

scikit-learn(약 200MB 의존성)을 피하려고 표준 라이브러리만 쓴다(DESIGN.md 기술 원칙).
한국어는 형태소 분석기 없이 '어절 + 음절 2-gram'으로 색인해 조사 차이에도 걸리게 한다.
"""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from typing import Iterable, Sequence

EN_STOP = set(
    """a an the of for and or in on to with via from by is are was were be been being this that these those it its as at
    we our us they their them he she his her you your i not no but if then than so such can could may might will would
    should do does did done have has had into over under about between within without also more most other some any each
    which who whom whose what when where why how all both only very using use used based et al figure fig table section
    paper study results result show shows shown""".split()
)
KO_STOP = {"그리고", "그러나", "하지만", "또한", "이는", "있다", "한다", "했다", "위해", "통해", "대한", "등", "및", "것", "수", "이", "그", "저"}
HANGUL = re.compile(r"[\uac00-\ud7a3]+")
TOKEN = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)*|[\uac00-\ud7a3]+", re.I)


def tokenize(text: str) -> list[str]:
    text = unicodedata.normalize("NFKC", text or "").lower()
    out: list[str] = []
    for tok in TOKEN.findall(text):
        if HANGUL.fullmatch(tok):
            if tok in KO_STOP:
                continue
            if len(tok) <= 2:
                out.append(tok)
            else:
                out.append(tok)
                out.extend(tok[i:i + 2] for i in range(len(tok) - 1))
        else:
            if tok in EN_STOP or len(tok) < 2:
                continue
            if len(tok) > 4 and tok.endswith("s") and not tok.endswith("ss"):
                tok = tok[:-1]  # 아주 단순한 복수형 정리
            out.append(tok)
    return out


class BM25:
    def __init__(self, docs: Sequence[Sequence[str]], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.docs = [Counter(d) for d in docs]
        self.lens = [len(d) for d in docs]
        self.avg = (sum(self.lens) / len(self.lens)) if self.lens else 0.0
        df: Counter = Counter()
        for d in self.docs:
            df.update(d.keys())
        n = len(docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def scores(self, query: Iterable[str]) -> list[float]:
        q = list(query)
        out = []
        for d, ln in zip(self.docs, self.lens):
            s = 0.0
            for t in q:
                tf = d.get(t)
                if not tf:
                    continue
                denom = tf + self.k1 * (1 - self.b + self.b * ln / (self.avg or 1))
                s += self.idf.get(t, 0.0) * tf * (self.k1 + 1) / denom
            out.append(s)
        return out


class TfIdf:
    """sublinear tf + smooth idf + L2 정규화 (scikit-learn TfidfVectorizer 기본값과 같은 공식)."""

    def __init__(self, docs: Sequence[Sequence[str]]):
        n = len(docs)
        df: Counter = Counter()
        for d in docs:
            df.update(set(d))
        self.idf = {t: math.log((1 + n) / (1 + f)) + 1 for t, f in df.items()}
        self.vecs = [self.vector(d) for d in docs]

    def vector(self, tokens: Sequence[str]) -> dict[str, float]:
        tf = Counter(tokens)
        v = {t: (1 + math.log(c)) * self.idf.get(t, 0.0) for t, c in tf.items() if t in self.idf}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {t: x / norm for t, x in v.items()}

    @staticmethod
    def cosine(a: dict[str, float], b: dict[str, float]) -> float:
        if len(a) > len(b):
            a, b = b, a
        return sum(x * b.get(t, 0.0) for t, x in a.items())


def ranks(scores: Sequence[float]) -> list[int]:
    """점수 → 1부터 시작하는 순위(높을수록 1위)."""
    order = sorted(range(len(scores)), key=lambda i: -scores[i])
    r = [0] * len(scores)
    for pos, i in enumerate(order, 1):
        r[i] = pos
    return r


def rrf(rank_lists: Sequence[Sequence[int]], k: int = 60) -> list[float]:
    """Reciprocal Rank Fusion: sum 1/(k + rank). Paper Curation과 같은 k=60."""
    n = len(rank_lists[0]) if rank_lists else 0
    return [sum(1.0 / (k + rl[i]) for rl in rank_lists) for i in range(n)]
