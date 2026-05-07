# RepoGPT — CodeBase Intelligence System

Ask questions about any GitHub repository using AI. Paste a repo URL, wait for indexing, then chat with the codebase.

---

## What It Does

1. Paste any GitHub repository URL
2. System clones the repo, chunks code by language, embeds everything into a vector store
3. Ask questions in natural language
4. Get answers with code citations and source file references

---

## Architecture

```
┌─────────────┐
│ React + Vite│  ← Chat UI with markdown + syntax highlighting
└──────┬──────┘
       │ HTTP
       ▼
┌─────────────┐
│   FastAPI   │  ← REST API: /ingest, /query, /reset, /status
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│                    Code RAG Pipeline                      │
│                                                           │
│  GitHub URL                                               │
│      ↓                                                    │
│  Clone Repo (GitPython)                                   │
│      ↓                                                    │
│  Filter Files (12 languages)                              │
│      ↓                                                    │
│  Language-Aware Chunking (LangChain)                      │
│      ↓                                                    │
│  Embeddings (all-MiniLM-L6-v2)                            │
│      ↓                                                    │
│  ChromaDB (in-memory)                                     │
│      ↓                                                    │
│  Semantic Retrieval (top 10)                              │
│      ↓                                                    │
│  Cross-Encoder Reranking (top 3)                          │
│      ↓                                                    │
│  LLM Generation (OpenRouter / GPT-4o-mini)                │
│      ↓                                                    │
│  Cited Answer with Code Snippets                          │
└──────────────────────────────────────────────────────────┘
```

---

## Tech Stack

**Backend**
- FastAPI — REST API framework
- LangChain — Language-aware code splitting (12 languages)
- ChromaDB — In-memory vector store
- Sentence Transformers — Text embeddings
- CrossEncoder — Reranking for retrieval quality
- GitPython — Repository cloning
- OpenRouter — LLM gateway (GPT-4o-mini)

**Frontend**
- React + Vite
- React Markdown — Markdown rendering
- React Syntax Highlighter — Code block highlighting

---

## Supported Languages

Python, JavaScript, TypeScript, JSX, TSX, Java, Go, Rust, C++, C, Markdown, HTML

---

## Setup

### Backend

```bash
cd backend
pip install -r requirements.txt
```

Create `.env` in `backend/` folder:
```
OPENROUTER_API_KEY=your_openrouter_api_key
```

Run the server:
```bash
uvicorn main:app --reload --reload-exclude "repo/*"
```

Backend runs on `http://localhost:8000`

### Frontend

```bash
cd frontend/code-rag-ui
npm install
npm run dev
```

Frontend runs on `http://localhost:5173`

---

## API Endpoints

| Method | Endpoint  | Description                             |
|--------|-----------|-----------------------------------------|
| GET    | /status   | Check if a repo is loaded               |
| POST   | /ingest   | Clone and index a GitHub repository     |
| POST   | /query    | Ask a question about the loaded repo    |
| POST   | /reset    | Clear the loaded repo and start fresh   |

---

## Key Features

- **On-demand processing** — No precomputed indexes, works with any GitHub repo at runtime
- **Multi-language support** — 12 languages with language-specific code splitting
- **Two-stage retrieval** — Vector search (recall) + CrossEncoder reranking (precision)
- **Source citations** — Every answer cites the exact file it came from
- **Clean state per session** — Each user gets a fresh instance, no cross-contamination
- **Markdown responses** — Code blocks with syntax highlighting

---

## Evaluation

Tested on the [FastAPI Full-Stack Template](https://github.com/fastapi/full-stack-fastapi-template) repository (154 files, 584 chunks).

| Metric              | Score      |
|---------------------|------------|
| Retrieval Accuracy  | 6/8 (75%)  |
| Answer Quality      | 6/8 (75%)  |
| Avg Response Time   | 2-4 seconds|

### Test Cases

| Question                              | Retrieval | Answer |
|---------------------------------------|-----------|--------|
| How is user authentication handled?   | ✅        | ✅     |
| How are database sessions managed?    | ✅        | ✅     |
| What models are defined in this project? | ❌     | ❌     |
| How does the login endpoint work?     | ⚠️        | ✅     |
| How are API routes organized?         | ✅        | ✅     |
| How is password hashing implemented?  | ✅        | ✅     |
| How does the email functionality work?| ✅        | ✅     |
| How are tests structured in this project? | ⚠️    | ⚠️     |

### Known Limitations
- Vague queries like "what models are defined" sometimes fail because vector search needs more specific terminology
- For repos with both frontend and backend code, queries may return frontend results when backend was intended
- Functions larger than the chunk size get split mid-line; reranker mitigates but does not eliminate this
- Free LLM models on OpenRouter are rate-limited; system falls back to paid GPT-4o-mini for reliability

---

## Project Structure

```
code-rag/
├── backend/
│   ├── main.py            # FastAPI endpoints
│   ├── rag.py             # Core RAG pipeline (CodeRAG class)
│   ├── requirements.txt
│   └── .env               # API keys (not in git)
├── frontend/
│   └── code-rag-ui/
│       ├── src/
│       │   ├── App.jsx
│       │   └── App.css
│       └── package.json
├── screenshots/
├── runtime.txt
├── .gitignore
└── README.md
```

---

## What I Learned Building This

- Real chunking is harder than it looks — language-aware splitting still cuts large functions
- Vector search alone is insufficient — reranking with CrossEncoder dramatically improves quality
- LangChain abstractions are useful only after you understand what they abstract
- ChromaDB has Windows-specific file lock issues that EphemeralClient solves
- Free-tier deployment of ML systems is unrealistic; embeddings + reranker + LLM client need ~1.5GB RAM minimum

---

## Why This Project

I first built a text RAG over the 2026 FIA Formula 1 regulations from scratch (no LangChain) to understand the internals — chunking, embeddings, retrieval, reranking, prompting. Then I built this Code RAG with LangChain to learn the abstractions while using my existing understanding.

The progression was:
1. Toy RAG (4 hardcoded strings) — understand the concept
2. F1 RAG (manual implementation) — understand the internals
3. Code RAG (LangChain + production patterns) — understand abstractions and apply to a more complex domain

---

## License

MIT