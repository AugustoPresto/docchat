from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Ollama settings — used only for chat/generation
    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "llama3.2:3b"

    # Embedding model (sentence-transformers)
    # These are the defaults; device is auto-detected at startup.
    # CPU model: fast, lightweight (~91MB)
    embed_model_cpu: str = "sentence-transformers/all-MiniLM-L6-v2"
    # GPU model: higher quality, larger (~420MB) — worth it if you have VRAM
    embed_model_gpu: str = "sentence-transformers/all-mpnet-base-v2"

    # Storage paths (relative to backend dir)
    upload_dir: str = "uploads"
    vector_store_dir: str = "vector_stores"

    # RAG settings
    chunk_size: int = 1000
    chunk_overlap: int = 200
    retriever_k: int = 4

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
        """Return the appropriate embedding model for the detected device."""
        from app.device import DEVICE
        return self.embed_model_gpu if DEVICE in ("cuda", "mps") else self.embed_model_cpu


settings = Settings()
