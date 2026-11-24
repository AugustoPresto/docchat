from typing import Literal

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Ollama settings — used only for chat/generation (local / offline mode)
    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "llama3.2:3b"

    # Cloud LLM settings (used when a key is provided)
    groq_api_key: str | None = None
    groq_chat_model: str = "llama-3.1-8b-instant"
    openai_api_key: str | None = None
    openai_chat_model: str = "gpt-4o-mini"

    # ── Embeddings ────────────────────────────────────────────────────────────
    # "fastembed" (default): ONNX runtime on CPU — no PyTorch, small RAM
    #   footprint, works offline once the model is cached.
    # "sentence-transformers": PyTorch path with CUDA/MPS auto-detection.
    #   Requires `pip install -r requirements-gpu.txt`.
    embed_backend: Literal["fastembed", "sentence-transformers"] = "fastembed"
    # CPU model: fast, lightweight (~90MB)
    embed_model_cpu: str = "sentence-transformers/all-MiniLM-L6-v2"
    # GPU model (sentence-transformers backend only): higher quality (~420MB)
    embed_model_gpu: str = "sentence-transformers/all-mpnet-base-v2"
    # Where downloaded embedding models are kept, so later runs work offline.
    embed_cache_dir: str = "model_cache"

    # Storage paths (relative to backend dir)
    upload_dir: str = "uploads"
    vector_store_dir: str = "vector_stores"

    # RAG settings
    chunk_size: int = 1000
    chunk_overlap: int = 200
    retriever_k: int = 4
    # Combine semantic search with BM25 keyword search (better for names, codes,
    # rare words). Set to false for vector-only retrieval.
    hybrid_search: bool = True

    # ── Limits / public demo ─────────────────────────────────────────────────
    max_upload_mb: int = 100
    # When true, each browser only sees its own documents (anonymous
    # X-Client-Id header, no login). Keep false for single-user local use.
    isolate_clients: bool = False
    # Delete documents older than this many hours (0 = keep forever).
    doc_ttl_hours: int = 0
    # Maximum documents per client (0 = unlimited).
    max_docs_per_client: int = 0

    # CORS
    allowed_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    model_config = ConfigDict(env_file=".env")

    @property
    def embed_model(self) -> str:
        """Return the embedding model for the active backend and device."""
        if self.embed_backend != "sentence-transformers":
            return self.embed_model_cpu
        from app.device import DEVICE
        return self.embed_model_gpu if DEVICE in ("cuda", "mps") else self.embed_model_cpu


settings = Settings()


def get_provider() -> tuple[str, str]:
    """Return (provider, chat model). Priority: Groq → OpenAI → Ollama."""
    if settings.groq_api_key:
        return "groq", settings.groq_chat_model
    if settings.openai_api_key:
        return "openai", settings.openai_chat_model
    return "ollama", settings.ollama_chat_model
