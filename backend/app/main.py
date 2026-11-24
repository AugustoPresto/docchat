import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db
from app.config import get_provider, settings
from app.device import get_device_info
from app.routers import chat, documents
from app.services.document_service import cleanup_expired

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    cleanup_expired()
    yield


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="DocChat API",
    description="Chat with your PDF documents using local or cloud AI (RAG)",
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(documents.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["health"])
async def health():
    provider, model = get_provider()
    return {
        "status": "ok",
        "provider": provider,
        "chat_model": model,
        "embed_model": settings.embed_model,
        "embed_backend": settings.embed_backend,
        "ollama_url": settings.ollama_base_url if provider == "ollama" else None,
        "max_upload_mb": settings.max_upload_mb,
        "doc_ttl_hours": settings.doc_ttl_hours,
        "max_docs_per_client": settings.max_docs_per_client,
        **get_device_info(),  # adds: device, gpu_name, vram_gb
    }


@app.get("/", tags=["root"])
async def root():
    return {
        "message": "DocChat API is running 🚀",
        "docs": "/docs",
        "health": "/health",
    }
