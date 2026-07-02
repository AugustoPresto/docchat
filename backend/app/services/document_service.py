import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

from app.config import settings
from app.device import DEVICE
from app.schemas import DocumentResponse


# ── Paths ─────────────────────────────────────────────────────────────────────
UPLOAD_DIR = Path(settings.upload_dir)
VECTOR_DIR = Path(settings.vector_store_dir)

UPLOAD_DIR.mkdir(exist_ok=True)
VECTOR_DIR.mkdir(exist_ok=True)

METADATA_FILE = VECTOR_DIR / "documents_metadata.json"


# ── Metadata helpers ──────────────────────────────────────────────────────────
def _load_metadata() -> dict:
    if METADATA_FILE.exists():
        with open(METADATA_FILE, "r") as f:
            return json.load(f)
    return {}


def _save_metadata(data: dict) -> None:
    with open(METADATA_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)


# ── Embedding model (singleton) ──────────────────────────────────────────────
# Device auto-detected at startup: CUDA > MPS > CPU
# GPU → all-mpnet-base-v2 (higher quality, 420MB)
# CPU → all-MiniLM-L6-v2 (fast, lightweight, 91MB)
_embeddings_instance = None


def _get_embeddings() -> HuggingFaceEmbeddings:
    global _embeddings_instance
    if _embeddings_instance is None:
        _embeddings_instance = HuggingFaceEmbeddings(
            model_name=settings.embed_model,
            model_kwargs={"device": DEVICE},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embeddings_instance


# ── Core service functions ────────────────────────────────────────────────────
async def process_document(file_path: str, original_filename: str, file_size: int) -> DocumentResponse:
    """
    Load a PDF, split it into chunks, embed with sentence-transformers and save to FAISS.
    """
    doc_id = str(uuid.uuid4())

    # 1. Load PDF pages
    loader = PyPDFLoader(file_path)
    pages = loader.load()
    page_count = len(pages)

    # 2. Split into chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    chunks = splitter.split_documents(pages)
    chunk_count = len(chunks)

    # 3. Create FAISS vector store with local embeddings in batches to prevent memory spikes (OOM)
    embeddings = _get_embeddings()
    if not chunks:
        raise ValueError("No text content could be extracted from this PDF.")

    # Initialize the vector store with the first chunk
    vector_store = FAISS.from_documents(chunks[:1], embeddings)

    # Add the remaining chunks in batches
    batch_size = 32
    for i in range(1, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        vector_store.add_documents(batch)

    # 4. Persist the vector store to disk
    store_path = str(VECTOR_DIR / doc_id)
    vector_store.save_local(store_path)

    # 5. Save document metadata
    metadata = _load_metadata()
    doc_record = {
        "id": doc_id,
        "filename": original_filename,
        "page_count": page_count,
        "chunk_count": chunk_count,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "size_bytes": file_size,
        "file_path": file_path,
        "store_path": store_path,
    }
    metadata[doc_id] = doc_record
    _save_metadata(metadata)

    return DocumentResponse(**doc_record)


def list_documents() -> list[DocumentResponse]:
    metadata = _load_metadata()
    return [DocumentResponse(**doc) for doc in metadata.values()]


def get_document(doc_id: str) -> DocumentResponse | None:
    metadata = _load_metadata()
    doc = metadata.get(doc_id)
    return DocumentResponse(**doc) if doc else None


def delete_document(doc_id: str) -> bool:
    metadata = _load_metadata()
    doc = metadata.get(doc_id)
    if not doc:
        return False

    store_path = Path(doc["store_path"])
    if store_path.exists():
        shutil.rmtree(store_path)

    file_path = Path(doc["file_path"])
    if file_path.exists():
        file_path.unlink()

    del metadata[doc_id]
    _save_metadata(metadata)
    return True


def load_vector_store(doc_id: str) -> FAISS | None:
    metadata = _load_metadata()
    doc = metadata.get(doc_id)
    if not doc:
        return None

    store_path = doc["store_path"]
    if not Path(store_path).exists():
        return None

    embeddings = _get_embeddings()
    return FAISS.load_local(store_path, embeddings, allow_dangerous_deserialization=True)
