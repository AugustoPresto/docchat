"""
PDF ingestion: parse → chunk → embed → FAISS, run in the background with
progress reporting, plus document lookup/deletion and an in-memory index cache.
"""
from __future__ import annotations

import logging
import shutil
import threading
import uuid
from collections import OrderedDict
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from app import db
from app.config import settings
from app.embeddings import get_embeddings
from app.schemas import DocumentResponse

if TYPE_CHECKING:
    from langchain_community.vectorstores import FAISS

logger = logging.getLogger(__name__)

EMBED_BATCH_SIZE = 32

# Parsing reports progress 0→READ_SHARE %, embedding READ_SHARE→100 %.
READ_SHARE = 30

# One document is processed at a time: on a weak PC or a 512MB VM, two
# concurrent embedding jobs are slower overall and can run out of memory.
_processing_lock = threading.Lock()
# pdfium is not thread-safe.
_pdfium_lock = threading.Lock()


def upload_dir() -> Path:
    path = Path(settings.upload_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def vector_dir() -> Path:
    path = Path(settings.vector_store_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


# ── Records ───────────────────────────────────────────────────────────────────
def create_document(owner_id: str, filename: str, file_path: Path, size_bytes: int,
                    doc_id: str | None = None) -> DocumentResponse:
    doc_id = doc_id or str(uuid.uuid4())
    record = {
        "id": doc_id,
        "owner_id": owner_id,
        "filename": filename,
        "size_bytes": size_bytes,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "status": "processing",
        "stage": "queued",
        "progress": 0,
        "file_path": str(file_path),
        "store_path": str(vector_dir() / doc_id),
        "embed_model": settings.embed_model,
    }
    db.insert(record)
    return DocumentResponse(**record)


def list_documents(owner_id: str | None = None) -> list[DocumentResponse]:
    return [DocumentResponse(**d) for d in db.list_for(owner_id)]


def get_document(doc_id: str, owner_id: str | None = None) -> DocumentResponse | None:
    doc = db.get(doc_id, owner_id)
    return DocumentResponse(**doc) if doc else None


def count_documents(owner_id: str) -> int:
    return db.count_for(owner_id)


def delete_document(doc_id: str, owner_id: str | None = None) -> bool:
    doc = db.get(doc_id, owner_id)
    if not doc:
        return False
    _remove_files(doc)
    db.delete(doc_id)
    _cache_evict(doc_id)
    return True


def _remove_files(doc: dict) -> None:
    store_path = Path(doc["store_path"])
    if store_path.exists():
        shutil.rmtree(store_path, ignore_errors=True)
    if doc.get("file_path"):
        Path(doc["file_path"]).unlink(missing_ok=True)


def cleanup_expired() -> int:
    """Delete documents older than DOC_TTL_HOURS (public demo housekeeping)."""
    if settings.doc_ttl_hours <= 0:
        return 0
    expired = db.expired(settings.doc_ttl_hours)
    for doc in expired:
        _remove_files(doc)
        db.delete(doc["id"])
        _cache_evict(doc["id"])
    if expired:
        logger.info("Removed %d expired documents", len(expired))
    return len(expired)


# ── PDF parsing ───────────────────────────────────────────────────────────────
def iter_pdf_pages(file_path: str) -> Iterator[tuple[int, int, str]]:
    """
    Yield (page_index, page_total, text) for each page.

    Uses pypdfium2 (Google's PDFium, C++) which is many times faster than the
    pure-Python pypdf on weak CPUs; falls back to pypdf if it isn't installed.
    """
    try:
        import pypdfium2 as pdfium
    except ImportError:
        pdfium = None

    if pdfium is not None:
        with _pdfium_lock:
            pdf = pdfium.PdfDocument(file_path)
            try:
                total = len(pdf)
                for i in range(total):
                    page = pdf[i]
                    textpage = page.get_textpage()
                    text = textpage.get_text_range()
                    textpage.close()
                    page.close()
                    yield i, total, text
            finally:
                pdf.close()
        return

    from pypdf import PdfReader

    reader = PdfReader(file_path)
    total = len(reader.pages)
    for i, page in enumerate(reader.pages):
        yield i, total, page.extract_text() or ""


# ── Background processing ─────────────────────────────────────────────────────
def process_document(doc_id: str) -> None:
    """
    Parse, chunk, embed and index a PDF. Runs in a worker thread
    (FastAPI BackgroundTasks) and records progress in the database so the UI
    can show it. The PDF is deleted afterwards — answers only need the chunks.
    """
    doc = db.get(doc_id)
    if not doc:
        return

    with _processing_lock:
        try:
            _process(doc)
        except Exception as exc:
            logger.exception("Failed to process document %s", doc_id)
            shutil.rmtree(doc["store_path"], ignore_errors=True)
            db.update(doc_id, status="error", stage=None, error=_friendly_error(exc))
        finally:
            Path(doc["file_path"]).unlink(missing_ok=True)
            db.update(doc_id, file_path=None)


def _friendly_error(exc: Exception) -> str:
    if isinstance(exc, ValueError):
        return str(exc)
    name = type(exc).__name__
    if "Pdf" in name or "pdf" in str(exc).lower():
        return "This file could not be read as a PDF. It may be corrupted or password-protected."
    return "Something went wrong while processing this PDF."


def _process(doc: dict) -> None:
    from langchain_community.vectorstores import FAISS
    from langchain_core.documents import Document
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    doc_id = doc["id"]

    # 1. Read pages
    db.update(doc_id, stage="reading", progress=0)
    pages: list[Document] = []
    total = 0
    for i, total, text in iter_pdf_pages(doc["file_path"]):
        if text.strip():
            pages.append(Document(page_content=text, metadata={"page": i}))
        if i % 10 == 0 or i == total - 1:
            db.update(doc_id, progress=int(READ_SHARE * (i + 1) / max(total, 1)))

    # 2. Split
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    chunks = splitter.split_documents(pages)
    if not chunks:
        raise ValueError(
            "No text could be extracted from this PDF. "
            "Scanned/image-only PDFs are not supported yet."
        )
    db.update(doc_id, page_count=total, chunk_count=len(chunks), stage="indexing")

    # 3. Embed in batches (bounded memory, visible progress)
    embeddings = get_embeddings()
    vector_store = None
    for start in range(0, len(chunks), EMBED_BATCH_SIZE):
        batch = chunks[start:start + EMBED_BATCH_SIZE]
        if vector_store is None:
            vector_store = FAISS.from_documents(batch, embeddings)
        else:
            vector_store.add_documents(batch)
        done = min(start + EMBED_BATCH_SIZE, len(chunks))
        db.update(doc_id, progress=READ_SHARE + int((100 - READ_SHARE) * done / len(chunks)))

    # 4. Persist (unless the user deleted the document meanwhile)
    if db.get(doc_id) is None:
        return
    vector_store.save_local(doc["store_path"])
    db.update(doc_id, status="ready", stage=None, progress=100, error=None)


# ── Vector store loading (with a small LRU cache) ────────────────────────────
_CACHE_SIZE = 4
_cache: OrderedDict[str, FAISS] = OrderedDict()
_cache_lock = threading.Lock()


def _cache_evict(doc_id: str) -> None:
    with _cache_lock:
        _cache.pop(doc_id, None)


def load_vector_store(doc_id: str) -> FAISS | None:
    with _cache_lock:
        if doc_id in _cache:
            _cache.move_to_end(doc_id)
            return _cache[doc_id]

    doc = db.get(doc_id)
    if not doc or doc["status"] != "ready" or not Path(doc["store_path"]).exists():
        return None

    if doc.get("embed_model") and doc["embed_model"] != settings.embed_model:
        raise ValueError(
            f"This document was indexed with '{doc['embed_model']}' but the server now uses "
            f"'{settings.embed_model}'. Please upload it again."
        )

    from langchain_community.vectorstores import FAISS

    # Safe: these pickles are written only by this server, never uploaded.
    store = FAISS.load_local(doc["store_path"], get_embeddings(), allow_dangerous_deserialization=True)
    with _cache_lock:
        _cache[doc_id] = store
        while len(_cache) > _CACHE_SIZE:
            _cache.popitem(last=False)
    return store
