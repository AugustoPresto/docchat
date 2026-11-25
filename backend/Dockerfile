FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    EMBED_CACHE_DIR=/app/model_cache

WORKDIR /app

# libgomp1: OpenMP runtime used by faiss-cpu and onnxruntime wheels
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

# Bake the embedding model into the image: no download at startup, works offline.
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/all-MiniLM-L6-v2', cache_dir='/app/model_cache')"

COPY . .

RUN mkdir -p uploads vector_stores

EXPOSE 8000

# Host "" = all interfaces, IPv4 and IPv6. PORT is provided by the host; defaults to 8000.
CMD ["sh", "-c", "exec uvicorn app.main:app --host '' --port ${PORT:-8000}"]
