from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Ollama settings (used only for chat/generation)
    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "llama3.2:3b"

    # Embedding model — uses sentence-transformers locally (fast CPU, no Ollama needed)
    # all-MiniLM-L6-v2: 23MB, 384-dim, excellent quality/speed tradeoff for RAG
    embed_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Storage paths (relative to backend dir)
    upload_dir: str = "uploads"
    vector_store_dir: str = "vector_stores"

    # RAG settings
    chunk_size: int = 1000
    chunk_overlap: int = 200
    retriever_k: int = 4  # how many chunks to retrieve per query

    # CORS
    allowed_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    model_config = ConfigDict(env_file=".env")


settings = Settings()
