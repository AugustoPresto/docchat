# 💬 DocChat

> **Chat with your PDF documents using AI — runs locally or in the cloud.**

DocChat is a full-stack **RAG (Retrieval-Augmented Generation)** application that lets you upload any PDF and ask questions about it in natural language. It works fully locally with Ollama (private, no API keys) or in the cloud via Groq/OpenAI.

🔗 **Live demo:** [docchat-frontend.fly.dev](https://docchat-frontend.fly.dev)

![CI](https://github.com/AugustoPresto/docchat/actions/workflows/ci.yml/badge.svg)

---

## ✨ Features

- 📄 **Upload any PDF** — contracts, books, docs, research papers
- 🔍 **Semantic search** with FAISS vector store
- 🧠 **RAG pipeline** — finds relevant chunks before answering
- 💬 **Conversational memory** — multi-turn chat with context
- 📚 **Source citations** — see exactly which page the answer came from
- ☁️ **Cloud deployment** — Fly.io + Groq (no Ollama required)
- 🔒 **100% local option** — no data leaves your machine when using Ollama
- ⚡ **Fast React UI** — dark mode, drag & drop, auto-scroll
- 🐳 **Docker Compose** for one-command local setup
- 🖥️ **Auto GPU detection** — uses CUDA/MPS when available, falls back to CPU

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
│  │      sentence-transformers        │                       │
│  │   (local embeddings, very fast)   │                       │
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

### Cloud mode (Fly.io)

```
User
 │ HTTPS
 ▼
[docchat-frontend.fly.dev]  ← nginx container (Docker)
 │
 │ proxy_pass HTTPS → docchat-backend.fly.dev
 ▼
[docchat-backend.fly.dev]   ← FastAPI + uvicorn (Docker)
 │
 ├── Persistent volume /data  (PDF uploads + FAISS indexes)
 │
 └── Groq API (llama-3.1-8b-instant)  ← cloud LLM
```

### How RAG works (step by step)

1. **Upload** — PDF is parsed by PyPDF and split into ~1000-character chunks with 200-char overlap
2. **Embedding** — each chunk is converted to a numeric vector by `sentence-transformers` (local, fast)
3. **Indexing** — vectors are stored in FAISS on disk (one index per document)
4. **Question** — the user's question is also converted to a vector
5. **Retrieval** — the 4 most similar chunks are fetched via cosine similarity
6. **Answer** — chunks + conversation history are sent to the LLM for a grounded answer
7. **Citation** — the page number of each used chunk is returned to the UI

> **Why sentence-transformers instead of Ollama for embeddings?**
> `nomic-embed-text` via Ollama takes ~2 minutes per chunk on CPU.
> `all-MiniLM-L6-v2` embeds 10 chunks in **~30ms** — 1000× faster.

---

## 🖥️ GPU Auto-Detection

The backend detects the best available device at startup:

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
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

> [!TIP]
> If you have `OPENAI_API_KEY` or `GROQ_API_KEY` defined globally in your system environment variables and want to force the local backend to run **only using Ollama (local)**, start the server by clearing those variables for that execution:
> ```bash
> OPENAI_API_KEY="" GROQ_API_KEY="" uvicorn app.main:app --reload --port 8000
> ```

> **First run:** the embedding model (`all-MiniLM-L6-v2`, ~91 MB) downloads automatically from HuggingFace.

### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://127.0.0.1:5173** and upload a PDF. 🎉

---

## 🐳 Docker Compose (recommended)

```bash
ollama pull llama3.2:3b
docker compose up -d
```

Open **http://localhost:5173**

---

## ☁️ Cloud Deployment (Fly.io + Groq)

The project supports full cloud deployment on **Fly.io** using **Groq** as the LLM — free, fast, no Ollama needed.

### 1. Set your Groq API key as a secret

```bash
flyctl secrets set GROQ_API_KEY=your_key_here --app docchat-backend
```

Get a free key at [console.groq.com](https://console.groq.com).

### 2. Deploy

```bash
cd backend  && flyctl deploy
cd frontend && flyctl deploy
```

**LLM priority:** Groq → OpenAI → Ollama (local fallback)

---

## 📁 Project Structure

```
docchat/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app entry point, CORS, /health
│   │   ├── config.py                # All settings, loaded from env vars
│   │   ├── device.py                # Auto GPU detection (CUDA / MPS / CPU)
│   │   ├── schemas.py               # Request/response data models (Pydantic)
│   │   ├── routers/
│   │   │   ├── documents.py         # Upload, list, delete PDF endpoints
│   │   │   └── chat.py              # RAG Q&A endpoint
│   │   └── services/
│   │       ├── document_service.py  # PDF → chunks → embeddings → FAISS
│   │       └── chat_service.py      # RAG chain + LLM (Ollama / Groq / OpenAI)
│   ├── tests/
│   │   └── test_api.py              # Pytest suite
│   ├── requirements.txt             # Python dependencies
│   ├── Dockerfile                   # Backend container image
│   └── fly.toml                     # Fly.io config (backend)
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
│   ├── Dockerfile                   # Multi-stage image: build + nginx serve
│   └── fly.toml                     # Fly.io config (frontend)
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
| `UPLOAD_DIR` | `uploads` | Where PDFs are stored |
| `VECTOR_STORE_DIR` | `vector_stores` | Where FAISS indexes are stored |
| `CHUNK_SIZE` | `1000` | Characters per text chunk |
| `CHUNK_OVERLAP` | `200` | Overlap between chunks |
| `RETRIEVER_K` | `4` | Chunks retrieved per question |

---

## 🧪 Running Tests

```bash
cd backend
pytest tests/ -v
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18, Vite, Axios, react-dropzone, react-markdown |
| **Backend** | Python 3.11, FastAPI, Uvicorn |
| **Embeddings** | sentence-transformers (`all-MiniLM-L6-v2` / `all-mpnet-base-v2`) |
| **AI / RAG** | LangChain LCEL, FAISS-CPU |
| **LLM (local)** | Ollama (`llama3.2:3b`) |
| **LLM (cloud)** | Groq (`llama-3.1-8b-instant`) |
| **PDF parsing** | PyPDF |
| **Serving** | Docker, Docker Compose, Nginx |
| **Cloud** | Fly.io (backend + frontend) |
| **CI** | GitHub Actions |

---

## 📝 API Reference

Interactive docs available at **http://localhost:8000/docs** (Swagger UI).

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | AI provider + model status |
| `POST` | `/api/v1/documents/upload` | Upload and index a PDF |
| `GET` | `/api/v1/documents/` | List all uploaded documents |
| `DELETE` | `/api/v1/documents/{id}` | Delete a document and its index |
| `POST` | `/api/v1/chat/` | Ask a question about a document |

---

## 🤝 Contributing

Pull requests are welcome! Please open an issue first for major changes.

---

## 📄 License

MIT © [Augusto Souza](https://github.com/AugustoPresto)
