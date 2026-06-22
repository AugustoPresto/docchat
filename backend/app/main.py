from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import documents, chat

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="DocChat API",
    description="Chat with your PDF documents using local AI (Ollama + RAG)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
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
    return {
        "status": "ok",
        "chat_model": settings.ollama_chat_model,
        "embed_model": settings.ollama_embed_model,
        "ollama_url": settings.ollama_base_url,
    }


@app.get("/", tags=["root"])
async def root():
    return {
        "message": "DocChat API is running 🚀",
        "docs": "/docs",
        "health": "/health",
    }
