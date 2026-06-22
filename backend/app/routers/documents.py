import os
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, status

from app.config import settings
from app.schemas import DocumentResponse, DocumentListResponse
from app.services import document_service

router = APIRouter(prefix="/documents", tags=["documents"])

UPLOAD_DIR = Path(settings.upload_dir)


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...)):
    """Upload a PDF and process it for RAG (chunking + embedding)."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported.",
        )

    # Save file to disk
    file_id = str(uuid.uuid4())
    save_path = UPLOAD_DIR / f"{file_id}_{file.filename}"
    content = await file.read()
    file_size = len(content)

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    with open(save_path, "wb") as f:
        f.write(content)

    try:
        doc = await document_service.process_document(
            file_path=str(save_path),
            original_filename=file.filename,
            file_size=file_size,
        )
    except Exception as e:
        # Clean up on failure
        save_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(e)}",
        )

    return doc


@router.get("/", response_model=DocumentListResponse)
async def list_documents():
    """List all uploaded documents."""
    docs = document_service.list_documents()
    return DocumentListResponse(documents=docs, total=len(docs))


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: str):
    """Get metadata for a specific document."""
    doc = document_service.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return doc


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(doc_id: str):
    """Delete a document and its vector index."""
    deleted = document_service.delete_document(doc_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
