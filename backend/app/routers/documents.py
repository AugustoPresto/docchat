import asyncio
import re
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status

from app.config import settings
from app.deps import LOCAL_OWNER, get_owner
from app.schemas import DocumentListResponse, DocumentResponse
from app.services import document_service

router = APIRouter(prefix="/documents", tags=["documents"])

_CHUNK = 1024 * 1024  # 1 MB


def _safe_filename(name: str) -> str:
    name = name.replace("\\", "/").rsplit("/", 1)[-1]
    name = re.sub(r"[\x00-\x1f]", "", name).strip() or "document.pdf"
    return name[:200]


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    owner: str | None = Depends(get_owner),
):
    """
    Save a PDF and start indexing it in the background.

    Returns immediately with status="processing"; poll GET /documents/{id}
    for progress until status is "ready" or "error".
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only PDF files are supported.")

    owner_id = owner or LOCAL_OWNER
    document_service.cleanup_expired()
    if (
        settings.max_docs_per_client
        and owner is not None
        and document_service.count_documents(owner_id) >= settings.max_docs_per_client
    ):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Limit of {settings.max_docs_per_client} documents reached. Delete one to upload another.",
        )

    doc_id = str(uuid.uuid4())
    save_path = document_service.upload_dir() / f"{doc_id}.pdf"
    max_bytes = settings.max_upload_mb * 1024 * 1024
    size = 0

    # Stream to disk in chunks — never hold the whole file in memory.
    # File I/O runs in a thread so the event loop stays responsive.
    try:
        out = await asyncio.to_thread(open, save_path, "wb")
        try:
            while chunk := await file.read(_CHUNK):
                if size == 0 and not chunk.startswith(b"%PDF"):
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "This file is not a valid PDF.")
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(413, f"File is larger than {settings.max_upload_mb} MB.")
                await asyncio.to_thread(out.write, chunk)
        finally:
            await asyncio.to_thread(out.close)
    except BaseException:
        save_path.unlink(missing_ok=True)
        raise

    if size == 0:
        save_path.unlink(missing_ok=True)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Uploaded file is empty.")

    doc = document_service.create_document(
        owner_id=owner_id,
        filename=_safe_filename(file.filename),
        file_path=save_path,
        size_bytes=size,
        doc_id=doc_id,
    )
    background_tasks.add_task(document_service.process_document, doc.id)
    return doc


@router.get("/", response_model=DocumentListResponse)
async def list_documents(owner: str | None = Depends(get_owner)):
    """List uploaded documents (only the caller's when client isolation is on)."""
    document_service.cleanup_expired()
    docs = document_service.list_documents(owner)
    return DocumentListResponse(documents=docs, total=len(docs))


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: str, owner: str | None = Depends(get_owner)):
    """Get metadata and processing status for a document."""
    doc = document_service.get_document(doc_id, owner)
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")
    return doc


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(doc_id: str, owner: str | None = Depends(get_owner)):
    """Delete a document and its vector index."""
    if not document_service.delete_document(doc_id, owner):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")
