"""
Hybrid retrieval: semantic search (FAISS) + keyword search (BM25), merged with
Reciprocal Rank Fusion.

Small CPU embedding models handle meaning well but miss rare words — proper
names, acronyms, codes, words in other languages. BM25 catches exactly those.
Measured on a 469-page Portuguese book (12 questions with checkable answers):
vector-only found the answer in the top 5 for 5/12, hybrid for 8/12 — with no
extra model to download and a few MB of RAM per document.
"""
from __future__ import annotations

import math
import re
import unicodedata
from array import array
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

from langchain_core.documents import Document

if TYPE_CHECKING:
    from langchain_community.vectorstores import FAISS

_WORD = re.compile(r"\w+")

# How many candidates each retriever contributes before fusion.
FETCH_K = 20
# Standard RRF constant: damps the weight of the very first ranks.
RRF_K = 60
# Keyword hits scoring under this fraction of the best hit are ignored.
MIN_SCORE_RATIO = 0.3


def tokenize(text: str) -> list[str]:
    """Lowercase, strip accents (so "indígena" matches "indigena"), split on words."""
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return [w for w in _WORD.findall(text) if len(w) > 1]


class BM25:
    """Okapi BM25 over a fixed list of documents, stored as compact postings."""

    def __init__(self, texts: list[str], k1: float = 1.2, b: float = 0.75):
        self.k1, self.b = k1, b
        self.n = len(texts)
        self.lengths = array("I")
        postings: dict[str, tuple[array, array]] = {}
        for i, text in enumerate(texts):
            counts = Counter(tokenize(text))
            self.lengths.append(sum(counts.values()))
            for term, tf in counts.items():
                docs, tfs = postings.setdefault(term, (array("I"), array("I")))
                docs.append(i)
                tfs.append(tf)
        self.postings = postings
        self.avg_len = (sum(self.lengths) / self.n) if self.n else 0.0

    def top(self, query: str, k: int, min_ratio: float = MIN_SCORE_RATIO) -> list[int]:
        """
        Indices of the k best-scoring documents. Documents scoring below
        `min_ratio` × the best score are dropped: they only share common words
        ("the", "de", "about") with the query and would add noise to the fusion.
        """
        scores: dict[int, float] = {}
        for term in set(tokenize(query)):
            entry = self.postings.get(term)
            if entry is None:
                continue
            docs, tfs = entry
            idf = math.log(1 + (self.n - len(docs) + 0.5) / (len(docs) + 0.5))
            for i, tf in zip(docs, tfs, strict=True):
                norm = self.k1 * (1 - self.b + self.b * self.lengths[i] / self.avg_len)
                scores[i] = scores.get(i, 0.0) + idf * tf * (self.k1 + 1) / (tf + norm)
        if not scores:
            return []
        floor = min_ratio * max(scores.values())
        ranked = sorted(scores, key=scores.__getitem__, reverse=True)[:k]
        return [i for i in ranked if scores[i] >= floor]


@dataclass
class DocumentIndex:
    """Everything needed to search one document: vectors + keyword index."""

    store: FAISS
    docs: list[Document]
    bm25: BM25

    @classmethod
    def from_store(cls, store: FAISS) -> DocumentIndex:
        docs = [store.docstore.search(_id) for _id in store.index_to_docstore_id.values()]
        return cls(store=store, docs=docs, bm25=BM25([d.page_content for d in docs]))

    def search(self, query: str, k: int, hybrid: bool = True) -> list[Document]:
        semantic = self.store.similarity_search(query, k=FETCH_K if hybrid else k)
        if not hybrid:
            return semantic
        keyword = [self.docs[i] for i in self.bm25.top(query, FETCH_K)]
        return reciprocal_rank_fusion([semantic, keyword], k)


def _key(doc: Document) -> tuple:
    return doc.metadata.get("page"), doc.page_content


def reciprocal_rank_fusion(rankings: list[list[Document]], k: int) -> list[Document]:
    scores: dict[tuple, float] = {}
    by_key: dict[tuple, Document] = {}
    for ranking in rankings:
        for rank, doc in enumerate(ranking):
            key = _key(doc)
            by_key.setdefault(key, doc)
            scores[key] = scores.get(key, 0.0) + 1 / (RRF_K + rank + 1)
    best = sorted(scores, key=scores.__getitem__, reverse=True)[:k]
    return [by_key[key] for key in best]
