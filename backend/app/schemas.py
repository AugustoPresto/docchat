from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ── Document schemas ────────────────────────────────────────────────────────
class DocumentResponse(BaseModel):
    id: str
    filename: str
    page_count: int
    chunk_count: int
    uploaded_at: datetime
    size_bytes: int


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int


# ── Chat schemas ─────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    document_id: str
    message: str
    conversation_history: Optional[list[dict]] = []


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
