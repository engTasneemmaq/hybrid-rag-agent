# FastAPI endpoint
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import json

from config import MODEL_NAME, DB_PATH, PDF_DIR, VECTOR_STORE_PATH
from agent_graph import create_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Hybrid RAG Agent API", version="1.0.0")

agent = None
chunks_cache = []


class QueryRequest(BaseModel):
    question: str
    stream: bool = False


class QueryResponse(BaseModel):
    answer: str
    sources: list
    route: str
    sql_query: Optional[str] = None
    sql_valid: Optional[bool] = None
    cached: bool = False


def initialize_agent():
    global agent, chunks_cache
    logger.info("Initializing agent...")
    agent, chunks_cache = create_agent()
    logger.info("Agent initialized successfully")


@app.on_event("startup")
async def startup_event():
    initialize_agent()


@app.get("/")
async def root():
    return {"status": "ok", "service": "Hybrid RAG Agent", "model": MODEL_NAME}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "db_exists": DB_PATH.exists(),
        "pdf_dir_exists": PDF_DIR.exists(),
        "vector_store_exists": VECTOR_STORE_PATH.exists(),
        "chunks_loaded": len(chunks_cache)
    }


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    if request.stream:
        return StreamingResponse(stream_query(request.question), media_type="text/event-stream")
    else:
        return QueryResponse(**agent.invoke(request.question, stream=False))


def stream_query(question: str):
    if not agent:
        yield f"data: {json.dumps({'error': 'Agent not initialized'})}\n\n"
        return
    
    result = agent.invoke(question, stream=False)
    answer = result.get("answer", "")
    words = answer.split()
    
    for i in range(0, len(words), 3):
        chunk = " ".join(words[i:i+3]) + (" " if i + 3 < len(words) else "")
        yield f"data: {json.dumps({'chunk': chunk, 'done': False})}\n\n"
    
    yield f"data: {json.dumps({'chunk': '', 'done': True, 'answer': answer, 'sources': result.get('sources', []), 'route': result.get('route', '')})}\n\n"


if __name__ == "__main__":
    import uvicorn
    from config import API_HOST, API_PORT
    uvicorn.run(app, host=API_HOST, port=API_PORT)
