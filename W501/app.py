"""
FastAPI Web Application for LangChain RAG
基于 FastAPI 的 RAG Web 服务
"""

import os
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import tempfile
import shutil

from langchain_rag import LangChainRAG, create_rag

# Initialize FastAPI app
app = FastAPI(
    title="LangChain RAG API",
    description="PDF 问答 RAG 服务",
    version="1.0.0"
)

# Initialize RAG system
# Use OpenAI in production (AWS), Ollama for local development
USE_OLLAMA = os.getenv("USE_OLLAMA", "true").lower() == "true"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

rag = None


def get_rag():
    """Get or create RAG instance"""
    global rag
    if rag is None:
        if USE_OLLAMA:
            rag = create_rag(use_ollama=True, persist_directory="./faiss_index")
        else:
            rag = create_rag(use_ollama=False, persist_directory="./faiss_index")
    return rag


# Request/Response models
class QueryRequest(BaseModel):
    question: str
    top_k: Optional[int] = 4


class QueryResponse(BaseModel):
    answer: str
    sources: List[dict]


class HealthResponse(BaseModel):
    status: str
    documents: int


class IngestResponse(BaseModel):
    message: str
    chunks: int


@app.on_event("startup")
async def startup_event():
    """Initialize RAG on startup"""
    get_rag()
    print("✓ RAG system initialized")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    rag_instance = get_rag()
    return HealthResponse(
        status="healthy",
        documents=rag_instance.get_document_count()
    )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "LangChain RAG API",
        "version": "1.0.0",
        "endpoints": {
            "/health": "Health check",
            "/query": "POST - Ask a question",
            "/upload": "POST - Upload PDF",
            "/search": "POST - Similarity search"
        }
    }


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Query the RAG system
    向 RAG 系统提问
    """
    rag_instance = get_rag()
    
    if rag_instance.get_document_count() == 0:
        raise HTTPException(
            status_code=400,
            detail="No documents loaded. Please upload a PDF first."
        )
    
    try:
        result = rag_instance.query(request.question)
        
        # Format sources
        sources = []
        for doc in result.get("source_documents", []):
            sources.append({
                "content": doc.page_content[:200] + "...",
                "source": doc.metadata.get("source", "Unknown"),
                "page": doc.metadata.get("page", "N/A")
            })
        
        return QueryResponse(
            answer=result["answer"],
            sources=sources
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload", response_model=IngestResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload and process a PDF file
    上传并处理 PDF 文件
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    rag_instance = get_rag()
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        
        # Process the PDF
        chunks = rag_instance.load_pdf(tmp_path)
        rag_instance.add_documents(chunks)
        
        # Clean up
        os.unlink(tmp_path)
        
        return IngestResponse(
            message=f"Successfully processed {file.filename}",
            chunks=len(chunks)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search")
async def similarity_search(request: QueryRequest):
    """
    Perform similarity search without LLM
    执行相似度搜索（不使用 LLM）
    """
    rag_instance = get_rag()
    
    if rag_instance.get_document_count() == 0:
        raise HTTPException(
            status_code=400,
            detail="No documents loaded. Please upload a PDF first."
        )
    
    try:
        docs = rag_instance.similarity_search(request.question, k=request.top_k)
        
        results = []
        for doc in docs:
            results.append({
                "content": doc.page_content,
                "source": doc.metadata.get("source", "Unknown"),
                "page": doc.metadata.get("page", "N/A")
            })
        
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/clear")
async def clear_database():
    """
    Clear the vector database
    清空向量数据库
    """
    rag_instance = get_rag()
    rag_instance.clear_database()
    return {"message": "Database cleared"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)

