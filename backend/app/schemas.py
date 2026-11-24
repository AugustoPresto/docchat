from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ── Document schemas ────────────────────────────────────────────────────────
class DocumentResponse(BaseModel):
    id: str
    filename: str
    page_count: int = 0
    chunk_count: int = 0
    uploaded_at: datetime
    size_bytes: int
    status: Literal["processing", "ready", "error"] = "ready"
    stage: str | None = None  # queued | reading | indexing
    progress: int = 100  # 0–100
    error: str | None = None


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int


# ── Chat schemas ─────────────────────────────────────────────────────────────
class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=20_000)


class ChatRequest(BaseModel):
    document_id: str
    message: str = Field(max_length=4_000)
    conversation_history: list[HistoryMessage] = Field(default_factory=list, max_length=100)


class SourceChunk(BaseModel):
    content: str
    page: int


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    document_id: str


# ── Error schema ─────────────────────────────────────────────────────────────
class ErrorResponse(BaseModel):
    detail: str
