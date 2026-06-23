# 💬 DocChat

> **Chat with your PDF documents using local AI — 100% private, no API keys, no cloud.**

DocChat is a full-stack RAG (Retrieval-Augmented Generation) application that lets you upload any PDF and ask questions about it in natural language. Everything runs locally, so your documents never leave your machine.

![CI](https://github.com/AugustoPresto/docchat/actions/workflows/ci.yml/badge.svg)

---

## ✨ Features

- 📄 **Upload any PDF** — contracts, books, docs, research papers
- 🔍 **Semantic search** with FAISS vector store
- 🧠 **RAG pipeline** — finds relevant chunks before answering
- 💬 **Conversational memory** — multi-turn chat with context
- 📚 **Source citations** — see exactly which page the answer came from
- 🔒 **100% local** — no data sent to the cloud
- ⚡ **Fast React UI** — dark mode, drag & drop, auto-scroll
- 🐳 **Docker Compose** for one-command setup
- 🖥️ **Auto GPU detection** — uses CUDA/MPS when available, falls back to CPU

---

## 🏗️ Architecture

```
┌─────────────────┐     HTTP      ┌──────────────────────────────────────┐
│   React + Vite  │ ──────────── │           FastAPI Backend             │
│   (Port 5173)   │              │            (Port 8000)                │
└─────────────────┘              │                                       │
                                 │  ┌──────────┐  ┌──────────────────┐  │
                                 │  │  PyPDF   │  │      FAISS       │  │
                                 │  │ (loader) │  │  (vector store)  │  │
                                 │  └──────────┘  └──────────────────┘  │
                                 │       │                │               │
                                 │       └── sentence-transformers ───┘  │
                                 │           (embeddings, local/fast)    │
                                 │                       │               │
                                 └───────────────────────┼───────────────┘
                                                         │ Ollama API
                                          ┌──────────────▼─────────────┐
                                          │          Ollama             │
                                          │   llama3.2:3b  (chat only) │
                                          └────────────────────────────┘
```

**How it works:**
1. PDF is uploaded and split into overlapping text chunks (`RecursiveCharacterTextSplitter`)
2. Each chunk is embedded via **sentence-transformers** (model chosen per device) — fast local CPU/GPU inference
3. Embeddings are stored in a **FAISS** index on disk (persisted per document)
4. On each question, top-K most similar chunks are retrieved via cosine similarity
5. The context + conversation history is sent to **Ollama** (`llama3.2:3b`) for a grounded answer
6. The answer and source page references are returned to the React UI

> **Why sentence-transformers for embeddings?**  
> Running `nomic-embed-text` via Ollama on CPU takes ~2 minutes per chunk.  
> `all-MiniLM-L6-v2` runs in pure Python and embeds 10 chunks in **~30ms** — 1000x faster.

---

## 🖥️ GPU Auto-Detection

DocChat automatically detects the best available compute device at startup and selects the appropriate embedding model:

| Device | Detected when | Embedding model | Quality |
|--------|--------------|-----------------|--------|
| **CUDA** | NVIDIA GPU with CUDA drivers | `all-mpnet-base-v2` (420MB) | ⭐⭐⭐ Best |
| **MPS** | Apple Silicon (M1/M2/M3) | `all-mpnet-base-v2` (420MB) | ⭐⭐⭐ Best |
| **CPU** | No GPU found (default) | `all-MiniLM-L6-v2` (91MB) | ⭐⭐ Good |

**Startup log** — you'll see one of these messages when the backend starts:

```bash
# NVIDIA GPU found:
🟢 GPU detected: RTX 4090 (24.0GB VRAM) — using CUDA

# Apple Silicon:
🟢 Apple Silicon detected — using MPS

# No GPU:
🟡 No GPU detected — using CPU
```

The **sidebar** shows a live badge: **`⚡ GPU · [name] · [VRAM]`** (green) or **`🖥️ CPU only`** (amber).

### Override via environment variables

You can manually set either model in `backend/.env`:

```bash
# Force a specific model regardless of detected device:
EMBED_MODEL_CPU=sentence-transformers/all-MiniLM-L6-v2
EMBED_MODEL_GPU=sentence-transformers/all-mpnet-base-v2
```

### NVIDIA GPU requirements

- CUDA-capable GPU (any generation from GTX 900 series onwards)
- CUDA drivers installed (`nvidia-smi` should work in your terminal)
- No special Docker flags needed for embedding — only needed for Ollama GPU inference

---

## 🚀 Quick Start

### Prerequisites

- [Ollama](https://ollama.com/) installed and running
- Python 3.10+
- Node.js 18+

### 1. Pull the Ollama chat model

```bash
# Only needed for answering questions (not for embedding)
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

> **First run:** the embedding model (`all-MiniLM-L6-v2`, ~91MB) is downloaded automatically from HuggingFace.

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
# Pull Ollama model first (one-time)
ollama pull llama3.2:3b

# Start everything
docker compose up -d
```

Open **http://localhost:5173**

---

## 📁 Project Structure

```
docchat/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app + CORS
│   │   ├── config.py          # Settings via env vars
│   │   ├── schemas.py         # Pydantic models
│   │   ├── routers/
│   │   │   ├── documents.py   # Upload, list, delete
│   │   │   └── chat.py        # RAG Q&A endpoint
│   │   └── services/
│   │       ├── document_service.py  # PDF → chunks → FAISS
│   │       └── chat_service.py      # RAG chain + Ollama
│   ├── tests/
│   │   └── test_api.py        # Pytest suite (8 tests)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # Root + state management
│   │   ├── components/
│   │   │   ├── Sidebar.jsx         # Document management + status
│   │   │   ├── DocumentUpload.jsx  # Drag & drop uploader
│   │   │   ├── DocumentList.jsx    # Document selector
│   │   │   ├── ChatInterface.jsx   # Message history + input
│   │   │   └── Message.jsx         # Message + source citations
│   │   └── services/
│   │       └── api.js         # Axios API layer
│   └── Dockerfile
├── docker-compose.yml
└── .github/workflows/ci.yml   # CI: lint + build
```

---

## ⚙️ Configuration

All settings are in `backend/.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_CHAT_MODEL` | `llama3.2:3b` | Model for generating answers |
| `EMBED_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Local embedding model |
| `CHUNK_SIZE` | `1000` | Characters per text chunk |
| `CHUNK_OVERLAP` | `200` | Overlap between chunks |
| `RETRIEVER_K` | `4` | Chunks retrieved per query |

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
| **Backend** | Python 3.10+, FastAPI, Uvicorn |
| **Embeddings** | sentence-transformers (`all-MiniLM-L6-v2`) — local, fast CPU |
| **AI / RAG** | LangChain (LCEL), FAISS-CPU |
| **LLM** | Ollama (`llama3.2:3b`) |
| **PDF parsing** | PyPDF |
| **Containers** | Docker, Docker Compose, Nginx |
| **CI** | GitHub Actions |

---

## 📝 API Reference

Interactive docs: **http://localhost:8000/docs** (Swagger UI)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Ollama + model status |
| `POST` | `/api/v1/documents/upload` | Upload and index a PDF |
| `GET` | `/api/v1/documents/` | List all documents |
| `DELETE` | `/api/v1/documents/{id}` | Delete a document |
| `POST` | `/api/v1/chat/` | Ask a question about a document |

---

## 🤝 Contributing

Pull requests are welcome! Please open an issue first for major changes.

---

## 📄 License

MIT © [Augusto de Souza Cardoso](https://github.com/AugustoPresto)
