from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Ollama settings
    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "llama3.2:3b"
    ollama_embed_model: str = "nomic-embed-text"

    # App settings
    upload_dir: str = "uploads"
    vector_store_dir: str = "vector_stores"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    retriever_k: int = 4  # how many chunks to retrieve per query

    # CORS
    allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    model_config = ConfigDict(env_file=".env")


settings = Settings()
