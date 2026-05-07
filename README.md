# RepoGPT — On-Demand Code RAG

Ask questions about any GitHub repository using AI.

## How It Works

1. Paste any GitHub repository URL
2. System clones and indexes the codebase
3. Ask questions in natural language
4. Get answers with code citations

## Architecture

```
GitHub URL → Clone → Language-Aware Chunking → 
Embeddings → ChromaDB → Retrieval → Reranking → LLM → Answer
```

## Tech Stack

**Backend**
- FastAPI
- LangChain (language-aware code splitting for 12 languages)
- ChromaDB (in-memory vector store)
- Sentence Transformers (embeddings)
- CrossEncoder (reranking)
- OpenRouter (LLM gateway)

**Frontend**
- React + Vite
- React Markdown with syntax highlighting

## Setup

### Backend

```bash
cd backend
pip install -r requirements.txt
```

Create a `.env` file in `backend/`:
```
OPENROUTER_API_KEY=your_key_here
```

Run:
```bash
uvicorn main:app --reload --reload-exclude "repo/*"
```

### Frontend

```bash
cd frontend/code-rag-ui
npm install
npm run dev
```

## Supported Languages

Python, JavaScript, TypeScript, Java, Go, Rust, C++, C, Markdown, HTML