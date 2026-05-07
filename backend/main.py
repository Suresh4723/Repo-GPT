from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from rag import CodeRAG

app = FastAPI(title="Code RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

rag = CodeRAG()

class IngestRequest(BaseModel):
    repo_url: str

class QueryRequest(BaseModel):
    question: str

@app.get("/status")
def status():
    return rag.status()

@app.post("/reset")
def reset():
    try:
        rag._cleanup_repo("./repo")
        return {"status": "cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest")
def ingest(request: IngestRequest):
    try:
        result = rag.ingest(request.repo_url)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
def query(request: QueryRequest):
    result = rag.query(request.question)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result