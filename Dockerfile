# Single-service image: the FastAPI backend also serves the built React app,
# so the whole demo runs as ONE web service with ONE URL (used by render.yaml).
# For local development with Ollama, use docker-compose.yml instead.

# ── 1. Build the frontend ─────────────────────────────────────────────────────
FROM node:20-alpine AS frontend
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
# Same origin as the API: relative URLs, no CORS.
ENV VITE_API_URL=/api/v1
RUN npm run build

# ── 2. Backend + static frontend ──────────────────────────────────────────────
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    EMBED_CACHE_DIR=/app/model_cache \
    STATIC_DIR=/app/static

WORKDIR /app

# libgomp1: OpenMP runtime used by faiss-cpu and onnxruntime wheels
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install -r requirements.txt

# Bake the embedding model into the image: no download at startup.
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/all-MiniLM-L6-v2', cache_dir='/app/model_cache')"

COPY backend/ .
COPY --from=frontend /frontend/dist /app/static

RUN mkdir -p uploads vector_stores

EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn app.main:app --host '' --port ${PORT:-8000}"]
