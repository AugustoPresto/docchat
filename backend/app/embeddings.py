"""Embedding model singleton (FastEmbed by default, sentence-transformers optional)."""
from __future__ import annotations

import threading

from langchain_core.embeddings import Embeddings

from app.config import settings

_instance: Embeddings | None = None
_lock = threading.Lock()


def get_embeddings() -> Embeddings:
    global _instance
    if _instance is not None:
        return _instance
    with _lock:
        if _instance is None:
            _instance = _build()
    return _instance


def _build() -> Embeddings:
    if settings.embed_backend == "sentence-transformers":
        from langchain_huggingface import HuggingFaceEmbeddings

        from app.device import DEVICE

        return HuggingFaceEmbeddings(
            model_name=settings.embed_model,
            model_kwargs={"device": DEVICE},
            encode_kwargs={"normalize_embeddings": True},
            cache_folder=settings.embed_cache_dir,
        )

    from langchain_community.embeddings import FastEmbedEmbeddings

    return FastEmbedEmbeddings(
        model_name=settings.embed_model_cpu,
        cache_dir=settings.embed_cache_dir,
        batch_size=32,
    )
