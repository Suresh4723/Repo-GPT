import os
import stat
import time
import shutil
import gc
import uuid

import chromadb
from git import Repo
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from sentence_transformers import CrossEncoder
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

LANGUAGE_MAP = {
    ".py":   Language.PYTHON,
    ".js":   Language.JS,
    ".ts":   Language.TS,
    ".jsx":  Language.JS,
    ".tsx":  Language.TS,
    ".java": Language.JAVA,
    ".go":   Language.GO,
    ".rs":   Language.RUST,
    ".cpp":  Language.CPP,
    ".c":    Language.CPP,
    ".md":   Language.MARKDOWN,
    ".html": Language.HTML,
}

def force_remove_readonly(func, path, excinfo):
    os.chmod(path, stat.S_IWRITE)
    func(path)

def safe_delete(path):
    if not os.path.exists(path):
        return
    for root, dirs, files in os.walk(path):
        for file in files:
            try:
                os.chmod(os.path.join(root, file), stat.S_IWRITE)
            except Exception:
                pass
    try:
        shutil.rmtree(path, onerror=force_remove_readonly)
    except Exception as e:
        print(f"Warning: could not delete {path}: {e}")


class CodeRAG:
    def __init__(self):
        print("Loading models...")

        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        self.llm_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
        self.vectorstore = None
        self.current_repo_url = None

        # Clean any leftover repo folder on startup
        safe_delete("./repo")

        print("Models loaded. Ready for ingestion.")

    def _cleanup_repo(self, repo_path="./repo"):
        """Only delete the cloned repo folder."""
        if self.vectorstore is not None:
            self.vectorstore = None

        self.current_repo_url = None
        gc.collect()

        if os.path.exists(repo_path):
            try:
                r = Repo(repo_path)
                r.close()
                del r
            except Exception:
                pass
            gc.collect()
            time.sleep(0.5)
            safe_delete(repo_path)

        print("Cleanup complete.")

    def _get_code_files(self, repo_path):
        code_files = []
        for root, dirs, files in os.walk(repo_path):
            if any(x in root for x in [".git", "__pycache__", "node_modules"]):
                continue
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in LANGUAGE_MAP:
                    code_files.append(os.path.join(root, file))
        return code_files

    def _read_files(self, file_paths):
        documents = []
        for path in file_paths:
            ext = os.path.splitext(path)[1].lower()
            try:
                with open(path, "r", encoding="utf-8") as f:
                    documents.append({
                        "path":     path,
                        "content":  f.read(),
                        "language": LANGUAGE_MAP[ext]
                    })
            except Exception as e:
                print(f"Error reading {path}: {e}")
        return documents

    def _split_documents(self, documents, repo_url):
        all_docs = []
        for doc in documents:
            splitter = RecursiveCharacterTextSplitter.from_language(
                language=doc["language"],
                chunk_size=1500,
                chunk_overlap=200
            )
            chunks = splitter.create_documents(
                texts=[doc["content"]],
                metadatas=[{
                    "file_path": doc["path"].replace("\\", "/"),
                    "filename":  os.path.basename(doc["path"]),
                    "language":  str(doc["language"]),
                    "repo_url":  repo_url,
                }]
            )
            all_docs.extend(chunks)
        return all_docs

    def _rerank(self, query, docs, top_n=3):
        pairs = [[query, doc.page_content] for doc in docs]
        scores = self.reranker.predict(pairs)
        scored_docs = list(zip(scores, docs))
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        return scored_docs[:top_n]

    def _build_prompt(self, query, reranked_docs):
        context_parts = []
        for score, doc in reranked_docs:
            context_parts.append(
                f"FILE: {doc.metadata['file_path']}\n"
                f"CODE:\n{doc.page_content}"
            )
        context = "\n\n---\n\n".join(context_parts)

        return (
            "You are RepoGPT, a senior software engineer helping developers understand a repository.\n\n"
            "You are given retrieved code snippets from a GitHub repository.\n\n"
            "Your job:\n"
            "- Explain the code clearly\n"
            "- Be concise but technical\n"
            "- Use markdown formatting\n"
            "- Use headings and bullet points\n"
            "- When showing code ALWAYS use fenced markdown code blocks with the language specified\n"
            "- Explain WHY the code exists and HOW it works\n"
            "- Mention filenames using backticks\n"
            "- Only show the relevant code snippets\n"
            "- If the answer is not present in the context, say: Not found in the provided code.\n\n"
            f"CODE CONTEXT:\n{context}\n\n"
            f"QUESTION:\n{query}\n\n"
            "ANSWER:"
        )

    def _generate(self, prompt):
        models = [
            "openai/gpt-4o-mini"
        ]
        for model in models:
            try:
                response = self.llm_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.choices[0].message.content.strip(), model
            except Exception as e:
                print(f"{model} failed: {e}")
                continue
        return "All models unavailable.", "none"

    def ingest(self, repo_url: str, repo_path="./repo"):

        # Clean old repo and reset vectorstore
        self._cleanup_repo(repo_path)

        # Extra safety
        if os.path.exists(repo_path):
            safe_delete(repo_path)
            time.sleep(1)

        if os.path.exists(repo_path):
            raise Exception(
                "Could not delete old repo folder. "
                "Please close any terminals inside the repo folder."
            )

        # Clone
        print(f"Cloning {repo_url}...")
        Repo.clone_from(repo_url, repo_path)
        print("Cloned successfully")

        # Process
        code_files = self._get_code_files(repo_path)
        documents = self._read_files(code_files)
        all_docs = self._split_documents(documents, repo_url)
        print(f"Processed {len(documents)} files into {len(all_docs)} chunks")

        # Use EphemeralClient — in memory, no tenant issues ever
        collection_name = f"code_rag_{uuid.uuid4().hex[:8]}"
        ephemeral_client = chromadb.EphemeralClient()

        self.vectorstore = Chroma.from_documents(
            documents=all_docs,
            embedding=self.embeddings,
            client=ephemeral_client,
            collection_name=collection_name
        )
        self.current_repo_url = repo_url

        print(f"Stored {self.vectorstore._collection.count()} chunks in memory")

        return {
            "status":   "ready",
            "repo_url": repo_url,
            "files":    len(documents),
            "chunks":   self.vectorstore._collection.count()
        }

    def query(self, question: str):
        if self.vectorstore is None:
            return {"error": "No repository ingested yet. Please load a repo first."}

        retriever = self.vectorstore.as_retriever(search_kwargs={"k": 10})
        retrieved = retriever.invoke(question)
        reranked = self._rerank(question, retrieved, top_n=3)
        prompt = self._build_prompt(question, reranked)
        answer, model_used = self._generate(prompt)

        sources = []
        for score, doc in reranked:
            sources.append({
                "file_path":    doc.metadata["file_path"],
                "filename":     doc.metadata["filename"],
                "language":     doc.metadata["language"],
                "rerank_score": round(float(score), 4),
                "preview":      doc.page_content[:200]
            })

        return {
            "question":   question,
            "answer":     answer,
            "sources":    sources,
            "model_used": model_used
        }

    def status(self):
        if self.vectorstore is None:
            return {"ready": False, "repo_url": None, "chunks": 0}
        return {
            "ready":    True,
            "repo_url": self.current_repo_url,
            "chunks":   self.vectorstore._collection.count()
        }