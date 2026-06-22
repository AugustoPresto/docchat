# 💬 DocChat

> **Chat with your PDF documents using local AI — 100% private, no API keys, no cloud.**

DocChat is a full-stack RAG (Retrieval-Augmented Generation) application that lets you upload any PDF and ask questions about it in natural language. Everything runs locally using [Ollama](https://ollama.com/), so your documents never leave your machine.

![DocChat Demo](docs/demo.gif)

---

## ✨ Features

- 📄 **Upload any PDF** — contracts, books, docs, research papers
- 🔍 **Semantic search** with FAISS vector store
- 🧠 **RAG pipeline** — finds relevant chunks before answering
- 💬 **Conversational memory** — multi-turn chat with context
- 📚 **Source citations** — see exactly which page the answer came from
- 🔒 **100% local** — powered by Ollama, no data sent to the cloud
- ⚡ **Fast React UI** — dark mode, drag & drop, auto-scroll
- 🐳 **Docker Compose** for one-command setup

---

## 🏗️ Architecture

```
┌─────────────────┐     HTTP      ┌─────────────────────────────────┐
│   React + Vite  │ ──────────── │        FastAPI Backend           │
│   (Port 5173)   │              │         (Port 8000)              │
└─────────────────┘              │                                  │
                                 │  ┌──────────┐  ┌─────────────┐  │
                                 │  │  PyPDF   │  │   FAISS     │  │
                                 │  │ (loader) │  │ (vectors)   │  │
                                 │  └──────────┘  └─────────────┘  │
                                 │         │             │          │
                                 │         └──── RAG ────┘          │
                                 │                │                  │
                                 └────────────────┼──────────────────┘
                                                  │ Ollama API
                                    ┌─────────────▼──────────────┐
                                    │         Ollama              │
                                    │  llama3.2:3b  (chat)       │
                                    │  nomic-embed-text (embed)  │
                                    └────────────────────────────┘
```

**How it works:**
1. PDF is uploaded and split into overlapping text chunks (LangChain `RecursiveCharacterTextSplitter`)
2. Each chunk is embedded via Ollama (`nomic-embed-text`) and stored in a FAISS index on disk
3. On each question, the top-K most similar chunks are retrieved via cosine similarity
4. The retrieved context + conversation history is sent to Ollama (`llama3.2:3b`) for a grounded answer
5. The answer and source page references are returned to the React UI

---

## 🚀 Quick Start

### Prerequisites

- [Ollama](https://ollama.com/) installed and running
- Python 3.11+
- Node.js 18+

### 1. Pull Ollama models

```bash
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

### 2. Start the backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** and upload a PDF. 🎉

---

## 🐳 Docker Compose (recommended)

```bash
# Pull Ollama models first (one-time)
ollama pull llama3.2:3b && ollama pull nomic-embed-text

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
│   │   └── test_api.py        # Pytest suite
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # Root + state management
│   │   ├── components/
│   │   │   ├── Sidebar.jsx    # Document management + status
│   │   │   ├── DocumentUpload.jsx  # Drag & drop uploader
│   │   │   ├── DocumentList.jsx   # Document selector
│   │   │   ├── ChatInterface.jsx  # Message history + input
│   │   │   └── Message.jsx        # Message + sources
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
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Model for creating embeddings |
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
| **Backend** | Python 3.11, FastAPI, Uvicorn |
| **AI / RAG** | LangChain, LangChain-Ollama, FAISS-CPU |
| **LLM** | Ollama (llama3.2:3b + nomic-embed-text) |
| **PDF parsing** | PyPDF |
| **Containers** | Docker, Docker Compose, Nginx |
| **CI** | GitHub Actions |

---

## 📝 API Reference

Interactive docs available at `http://localhost:8000/docs` (Swagger UI).

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Ollama connection status |
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
