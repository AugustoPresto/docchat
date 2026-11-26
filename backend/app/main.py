import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

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


# ── Frontend (optional, single-service deploy) ─────────────────────────────────
# Registered last so API routes, /health and /docs always win.
def _static_root() -> Path | None:
    if not settings.static_dir:
        return None
    root = Path(settings.static_dir).resolve()
    return root if (root / "index.html").is_file() else None


@app.get("/", include_in_schema=False)
async def root():
    static = _static_root()
    if static:
        return FileResponse(static / "index.html", headers={"Cache-Control": "no-cache"})
    return {
        "message": "DocChat API is running 🚀",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/{path:path}", include_in_schema=False)
async def frontend(path: str):
    """Serve built frontend files; unknown paths fall back to index.html (SPA)."""
    static = _static_root()
    if not static or path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not Found")
    candidate = (static / path).resolve()
    if candidate.is_file() and candidate.is_relative_to(static):
        # Vite puts content hashes in asset names, so they can be cached forever.
        cache = "public, max-age=31536000, immutable" if path.startswith("assets/") else "no-cache"
        return FileResponse(candidate, headers={"Cache-Control": cache})
    return FileResponse(static / "index.html", headers={"Cache-Control": "no-cache"})
