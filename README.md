# 💬 DocChat

> **Chat with your PDF documents using AI — runs locally or in the cloud.**

DocChat is a full-stack **RAG (Retrieval-Augmented Generation)** application that lets you upload any PDF and ask questions about it in natural language. It works fully locally with Ollama (private, no API keys) or in the cloud via Groq/OpenAI.

🔗 **Live demo:** _(no login — just open it and drop a PDF; the free server may take ~1 min to wake up)_

![CI](https://github.com/AugustoPresto/docchat/actions/workflows/ci.yml/badge.svg)

---

## ✨ Features

- 📄 **Upload any PDF** — contracts, books, docs, research papers
- 🔍 **Hybrid search**: FAISS semantic search + BM25 keyword search, so names, codes and rare words are found too
- 🧠 **RAG pipeline** — finds relevant chunks before answering
- 💬 **Conversational memory** — multi-turn chat with context
- 📚 **Source citations** — see exactly which page the answer came from
- 📴 **Offline-first** — Ollama + local embeddings, no internet needed after the first setup
- 🪶 **Runs on weak PCs** — ONNX embeddings (no PyTorch) and a fast C++ PDF parser
- ⏳ **Background indexing** — upload returns at once; live progress per document
- ⌨️ **Streaming answers** — text appears as the model writes it (with a Stop button)
- 🙋 **No login** — each browser gets an anonymous id; on the demo you only see your own files
- ☁️ **Free cloud deployment** — one Render service (frontend + API) + Groq
- ⚡ **Fast React UI** — dark mode, drag & drop, auto-scroll
- 🐳 **Docker Compose** for one-command local setup
- 🖥️ **Optional GPU** — CUDA/MPS embeddings via the `sentence-transformers` backend

---

## 🏗️ Architecture

### Local mode (with Ollama)

```
User (Browser)
      │
      │  HTTP
      ▼
┌─────────────────────┐
│   React + Vite      │  ← UI: components, state, UX
│   (Port 5173)       │
└──────────┬──────────┘
           │ /api/* — Vite proxy (dev) / nginx reverse proxy (prod)
           ▼
┌──────────────────────────────────────────────────────────────┐
│                  FastAPI Backend  (Port 8000)                 │
│                                                              │
│  POST /upload          POST /chat/          GET /health      │
│       │                      │                               │
│  ┌────▼──────┐     ┌─────────▼──────────┐                   │
│  │  PyPDF    │     │  LangChain (LCEL)  │                    │
│  │  (read)   │     │  RAG Pipeline      │                    │
│  └────┬──────┘     └─────────┬──────────┘                   │
│       │                      │                               │
│  ┌────▼──────┐     ┌─────────▼──────────┐                   │
│  │  Chunking │     │  FAISS (similarity │                    │
│  │  (LCEL)   │     │  vector search)    │                    │
│  └────┬──────┘     └─────────┬──────────┘                   │
│       │                      │                               │
│  ┌────▼──────────────────────▼───────┐                       │
│  │   FastEmbed (ONNX, CPU, offline)  │                       │
│  │   all-MiniLM-L6-v2 embeddings     │                       │
│  └───────────────────────────────────┘                       │
└──────────────────────────┬───────────────────────────────────┘
                           │  HTTP (answer generation)
                           ▼
              ┌────────────────────────────┐
              │  Ollama / Groq / OpenAI    │
              │  llama3.2:3b (local) or   │
              │  llama-3.1-8b-instant (☁️) │
              └────────────────────────────┘
```

### Cloud mode (free: Render + Groq)

```
User (no login, anonymous X-Client-Id)
 │ HTTPS — one URL
 ▼
[Render free web service]  Docker, 512 MB
 │   FastAPI serves the React build (/) and the API (/api/v1, /health)
 │   FastEmbed + FAISS + BM25
 │   ephemeral disk: documents expire after DOC_TTL_HOURS or on restart
 │
 └── Groq API (llama-3.1-8b-instant)  ← cloud LLM
```

### How RAG works (step by step)

1. **Upload** — the file is streamed to disk and indexed in the background; PDF pages are read with pypdfium2 and split into ~1000-character chunks with 200-char overlap
2. **Embedding** — each chunk is converted to a vector by FastEmbed (ONNX, local, no GPU needed)
3. **Indexing** — vectors are stored in FAISS on disk (one index per document)
4. **Question** — the user's question is also converted to a vector
5. **Retrieval** — hybrid search: the top semantic matches (FAISS) and the top keyword matches
   (BM25, accent-insensitive) are merged with Reciprocal Rank Fusion, keeping the best 4 chunks.
   On a 469-page Portuguese book, this found the answer for 8/12 test questions vs 5/12 with
   vectors alone, at ~4 ms per question and no extra model
6. **Answer** — chunks + conversation history are sent to the LLM for a grounded answer
7. **Citation** — the page number of each used chunk is returned to the UI

> **Why FastEmbed instead of Ollama or PyTorch for embeddings?**
> `nomic-embed-text` via Ollama is very slow on CPU, and PyTorch alone is a
> ~1 GB dependency that takes seconds to import. FastEmbed runs the same
> `all-MiniLM-L6-v2` model through ONNX Runtime: small, fast on CPU, and the
> model is cached in `backend/model_cache/` so it works offline.

---

## 🖥️ Optional GPU embeddings

The default `fastembed` backend always runs on CPU. If you have a GPU, install
`requirements-gpu.txt` and set `EMBED_BACKEND=sentence-transformers`; the backend
then detects the best device at startup (re-upload documents after switching):

| Device | Detected when | Embedding model | Quality |
|--------|--------------|-----------------|---------|
| **CUDA** | NVIDIA GPU + CUDA drivers | `all-mpnet-base-v2` (420 MB) | ⭐⭐⭐ Best |
| **MPS** | Apple Silicon (M1/M2/M3) | `all-mpnet-base-v2` (420 MB) | ⭐⭐⭐ Best |
| **CPU** | No GPU found (default) | `all-MiniLM-L6-v2` (91 MB) | ⭐⭐ Good |

The **sidebar** shows a live badge: **`⚡ GPU · [name] · [VRAM]`** or **`🖥️ CPU only`**.

---

## 🚀 Quick Start (local)

### Prerequisites

- [Ollama](https://ollama.com/) installed and running
- Python 3.10+
- Node.js 18+

### 1. Pull the Ollama chat model

```bash
ollama pull llama3.2:3b
```

### 2. Start the backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt   # add -r requirements-gpu.txt for CUDA/MPS
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

> [!TIP]
> If you have `OPENAI_API_KEY` or `GROQ_API_KEY` defined globally in your system environment variables and want to force the local backend to run **only using Ollama (local)**, start the server by clearing those variables for that execution:
> ```bash
> OPENAI_API_KEY="" GROQ_API_KEY="" uvicorn app.main:app --reload --port 8000
> ```

> **First run:** the embedding model (`all-MiniLM-L6-v2`, ~90 MB) downloads once into `backend/model_cache/`.
> After that — with `ollama pull` done — **DocChat works with no internet connection**.
>
> **Coming from the old PyTorch setup?** If `torch`/`transformers` are still installed in your venv,
> LangChain imports them at startup (~500 MB of RAM for nothing). Unless you use the GPU backend, remove them:
> `pip uninstall -y torch transformers sentence-transformers langchain-huggingface`.
> Measured on a 469-page book (4-core laptop, no GPU): **66 MB idle, ~330 MB peak, ~45 s to index**;
> PDF parsing alone went from 24 s (pypdf) to 1.5 s (pypdfium2).
>
> **Upgrading from an older version:** existing documents are imported automatically from
> `documents_metadata.json` into `vector_stores/docchat.db` on the first start.

### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://127.0.0.1:5173** and upload a PDF. 🎉

---

## 🐳 Docker Compose (recommended)

Runs everything (Ollama + backend + frontend) with a single command. No Python, Node or local
Ollama needed:

```bash
docker compose up -d --build
```

Open **http://localhost:5173**

- **First run** (needs internet): builds the images (backend ~710 MB, embedding model included) and
  the `ollama-pull` container downloads `llama3.2:3b` (~2 GB) into the `ollama_data` volume.
  Follow it with `docker logs -f docchat-ollama-pull`; chat works once it exits.
- **After that it runs fully offline.** On later starts `ollama-pull` just fails quietly when there
  is no connection; the model is already in the volume.
- Use another model with `OLLAMA_CHAT_MODEL=qwen2.5:3b docker compose up -d`.
- Documents live in the `uploads` / `vector_stores` Docker volumes, separate from a local
  `uvicorn` run. `docker compose down` keeps them; `docker compose down -v` deletes them
  (and the downloaded model).
- This Ollama is separate from one installed on your machine, so the model is downloaded once more.

---

## ☁️ Free Cloud Deployment (Render + Groq)

The whole app (React frontend + FastAPI API) runs as **one free Render web service**, built from the
root [`Dockerfile`](Dockerfile): FastAPI serves the compiled frontend, so there is one URL and no CORS
setup. No credit card is needed for Render or Groq.

1. **Groq API key:** create a free key at [console.groq.com](https://console.groq.com/keys).
2. **Render:** dashboard → **New → Blueprint** → connect GitHub → select this repository.
   Render reads [`render.yaml`](render.yaml) and asks for `GROQ_API_KEY`. Paste the key and click **Apply**.
3. Wait for the first build (~5 min). The app is at `https://docchat-XXXX.onrender.com`.
   Every push to the default branch redeploys it.

The blueprint enables the demo protections: `ISOLATE_CLIENTS=true` (each browser sees only its own
documents, no login), `DOC_TTL_HOURS=24`, `MAX_DOCS_PER_CLIENT=5`, `MAX_UPLOAD_MB=20`.

**What to expect on the free plan** (512 MB RAM, 0.1 CPU; measured locally with the same limits):

- Sleeps after 15 min without visits; the next visit waits ~1 min while Render wakes it up.
- Idle memory ~60 MB, ~275 MB while indexing.
- Indexing is CPU-bound: about **7 s per page** at 0.1 CPU (a 33-page article took ~4 min; on a
  4-core laptop, 6 s). Short PDFs (≤ 10–15 pages) make the best demo. Answers come from Groq, so chat
  stays fast.
- No persistent disk: uploaded documents are temporary.

> **Alternative:** frontend on Vercel (Root Directory `frontend`, `VITE_API_URL=https://<api>/api/v1`)
> + backend only (`backend/Dockerfile`, set `ALLOWED_ORIGINS` to the Vercel URL).

**LLM priority:** Groq → OpenAI → Ollama (local fallback)

---

## 📁 Project Structure

```
docchat/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app entry point, CORS, /health
│   │   ├── config.py                # All settings, loaded from env vars
│   │   ├── db.py                    # SQLite document metadata
│   │   ├── deps.py                  # Anonymous client id (X-Client-Id)
│   │   ├── embeddings.py            # FastEmbed / sentence-transformers singleton
│   │   ├── device.py                # GPU detection (sentence-transformers backend)
│   │   ├── schemas.py               # Request/response data models (Pydantic)
│   │   ├── routers/
│   │   │   ├── documents.py         # Upload, list, delete PDF endpoints
│   │   │   └── chat.py              # RAG Q&A endpoint
│   │   └── services/
│   │       ├── document_service.py  # PDF → chunks → embeddings → FAISS (background)
│   │       ├── retrieval.py         # Hybrid search: FAISS + BM25 + rank fusion
│   │       └── chat_service.py      # RAG chain + LLM (Ollama / Groq / OpenAI)
│   ├── tests/
│   │   ├── test_api.py              # API tests (fake embeddings + LLM)
│   │   └── test_retrieval.py        # BM25 / hybrid search tests
│   ├── requirements.txt             # Python dependencies (CPU, no PyTorch)
│   ├── requirements-gpu.txt         # Optional PyTorch/GPU embeddings
│   ├── requirements-dev.txt         # pytest + ruff
│   └── Dockerfile                   # Backend image (docker-compose)
├── frontend/
│   ├── src/
│   │   ├── App.jsx                  # Root component + global state
│   │   ├── components/
│   │   │   ├── Sidebar.jsx          # Document list + AI status badge
│   │   │   ├── DocumentUpload.jsx   # Drag & drop PDF uploader
│   │   │   ├── DocumentList.jsx     # Document selector
│   │   │   ├── ChatInterface.jsx    # Message history + input box
│   │   │   └── Message.jsx          # Chat bubble + source citations
│   │   └── services/
│   │       └── api.js               # Axios HTTP client for backend calls
│   ├── nginx.conf                   # Reverse proxy config (production)
│   ├── vite.config.js               # Dev server config + API proxy
│   ├── vercel.json                  # SPA routing for Vercel deployments
│   └── Dockerfile                   # nginx image (docker-compose)
├── Dockerfile                       # Single-service image: API + built frontend (Render)
├── render.yaml                      # Render blueprint (free, one service)
├── docker-compose.yml               # Full local stack: Ollama + backend + frontend
└── .github/workflows/ci.yml         # CI: lint + build on every push
```

---

## ⚙️ Configuration

All settings live in `backend/.env` (copy from `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_CHAT_MODEL` | `llama3.2:3b` | Local chat model |
| `GROQ_API_KEY` | _(none)_ | Enables Groq cloud mode |
| `GROQ_CHAT_MODEL` | `llama-3.1-8b-instant` | Groq model |
| `OPENAI_API_KEY` | _(none)_ | Enables OpenAI fallback |
| `OPENAI_CHAT_MODEL` | `gpt-4o-mini` | OpenAI model |
| `EMBED_BACKEND` | `fastembed` | `fastembed` (CPU/ONNX) or `sentence-transformers` (GPU) |
| `EMBED_CACHE_DIR` | `model_cache` | Where embedding models are cached for offline use |
| `UPLOAD_DIR` | `uploads` | Temporary PDF storage while indexing |
| `VECTOR_STORE_DIR` | `vector_stores` | Where FAISS indexes are stored |
| `CHUNK_SIZE` | `1000` | Characters per text chunk |
| `CHUNK_OVERLAP` | `200` | Overlap between chunks |
| `RETRIEVER_K` | `4` | Chunks retrieved per question |
| `HYBRID_SEARCH` | `true` | Combine semantic search with BM25 keyword search (names, codes, rare words) |
| `MAX_UPLOAD_MB` | `100` | Maximum PDF size |
| `ISOLATE_CLIENTS` | `false` | Per-browser documents (public demo, no login) |
| `DOC_TTL_HOURS` | `0` | Auto-delete documents after N hours (0 = never) |
| `MAX_DOCS_PER_CLIENT` | `0` | Per-browser document limit (0 = unlimited) |
| `ALLOWED_ORIGINS` | localhost | CORS origins, JSON list (only when the frontend is on another domain) |
| `EMBED_THREADS` | one per core | Embedding threads; set `1` on fractional-CPU hosts (Render free) |
| `STATIC_DIR` | — | Built frontend folder; when set, the API also serves the web app |

---

## 🧪 Running Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest tests/ -v
```

Tests run fully offline (fake embeddings and LLM) — no Ollama or model download needed.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18, Vite, Axios, react-dropzone, react-markdown |
| **Backend** | Python 3.11, FastAPI, Uvicorn |
| **Embeddings** | FastEmbed / ONNX (`all-MiniLM-L6-v2`); optional sentence-transformers on GPU |
| **AI / RAG** | LangChain LCEL, FAISS-CPU, BM25 hybrid search |
| **LLM (local)** | Ollama (`llama3.2:3b`) |
| **LLM (cloud)** | Groq (`llama-3.1-8b-instant`) |
| **PDF parsing** | pypdfium2 (PDFium), pypdf fallback |
| **Metadata** | SQLite |
| **Serving** | Docker, Docker Compose, Nginx |
| **Cloud** | Render free web service (frontend + API in one Docker image) + Groq |
| **CI** | GitHub Actions |

---

## 📝 API Reference

Interactive docs available at **http://localhost:8000/docs** (Swagger UI).

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | AI provider + model status |
| `POST` | `/api/v1/documents/upload` | Upload a PDF (202, indexing continues in background) |
| `GET` | `/api/v1/documents/` | List documents |
| `GET` | `/api/v1/documents/{id}` | Document metadata + `status` / `stage` / `progress` |
| `DELETE` | `/api/v1/documents/{id}` | Delete a document and its index |
| `POST` | `/api/v1/chat/` | Ask a question about a document |
| `POST` | `/api/v1/chat/stream` | Same, streamed as NDJSON events |

---

## 🤝 Contributing

Pull requests are welcome! Please open an issue first for major changes.

---

## 📄 License

MIT © [Augusto Souza](https://github.com/AugustoPresto)
