"""Hybrid retrieval: BM25 keyword index + vector search fused with RRF."""
import time

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import DeterministicFakeEmbedding

from app.config import settings
from app.services.retrieval import BM25, DocumentIndex, reciprocal_rank_fusion, tokenize
from tests.conftest import make_pdf


def test_tokenize_strips_accents_and_case():
    assert tokenize("Aldeia de URUÇUMIRIM, indígenas!") == ["aldeia", "de", "urucumirim", "indigenas"]


def test_bm25_ranks_rare_word_first():
    bm25 = BM25([
        "the bay and the river and the sea",
        "the river near the village",
        "Cunhambebe was a Tupinamba leader near the river",
    ])
    assert bm25.top("who was cunhambebe?", 3)[0] == 2
    assert bm25.top("nothing matches this", 3) == []


def test_bm25_handles_empty_corpus():
    assert BM25([]).top("anything", 5) == []


def test_rrf_rewards_documents_found_by_both():
    a, b, c = (Document(page_content=t, metadata={"page": 0}) for t in "abc")
    fused = reciprocal_rank_fusion([[a, b], [c, b]], k=3)
    assert fused[0] is b
    assert {d.page_content for d in fused} == {"a", "b", "c"}


def test_hybrid_search_finds_keyword_that_vectors_miss():
    # Fake embeddings are random: semantic search alone is a lottery here.
    texts = [f"filler text number {i} about nothing in particular" for i in range(40)]
    texts.append("Araryboia received the land of the future Niteroi")
    store = FAISS.from_texts(texts, DeterministicFakeEmbedding(size=16),
                             metadatas=[{"page": i} for i in range(len(texts))])
    index = DocumentIndex.from_store(store)
    assert index.search("Who was Araryboîa?", k=3)[0].metadata["page"] == 40


def test_bm25_build_is_fast_for_a_book():
    texts = [" ".join(f"word{(i * 7 + j) % 5000}" for j in range(180)) for i in range(1500)]
    start = time.perf_counter()
    BM25(texts).top("word42 word99", 4)
    assert time.perf_counter() - start < 5


def test_chat_uses_keyword_match_as_source(client, fake_llm):
    pages = [f"Page {i} is filler about weather and clouds." for i in range(12)]
    pages[7] = "The password of the vault is xylophone."
    from tests.test_api import upload

    doc_id = upload(client, make_pdf(pages)).json()["id"]
    response = client.post("/api/v1/chat/", json={"document_id": doc_id, "message": "What about xylophone?"})
    assert response.status_code == 200
    assert response.json()["sources"][0]["page"] == 8


def test_hybrid_search_can_be_disabled(client, fake_llm, monkeypatch):
    monkeypatch.setattr(settings, "hybrid_search", False)
    pages = [f"Page {i} is filler." for i in range(3)]
    from tests.test_api import upload

    doc_id = upload(client, make_pdf(pages)).json()["id"]
    response = client.post("/api/v1/chat/", json={"document_id": doc_id, "message": "filler?"})
    assert response.status_code == 200


def test_bm25_ignores_hits_that_only_share_common_words():
    bm25 = BM25([f"what about the weather on day {i}" for i in range(10)] + ["the vault code is xylophone"])
    assert bm25.top("what about xylophone?", 5) == [10]
