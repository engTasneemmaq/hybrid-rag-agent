# Agent orchestration - routes queries and coordinates tools
import logging
import json
from typing import Dict, Any, List, Optional
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)

class RouteType(Enum):
    SQL_ONLY = "SQL_ONLY"
    PDF_ONLY = "PDF_ONLY"
    BOTH = "BOTH"
    CLARIFY = "CLARIFY"
    REFUSE = "REFUSE"


def create_agent():
    """Create and return initialized agent - shared function"""
    from config import MODEL_NAME, MODEL_BASE_URL, DB_PATH, DATA_DIR, CACHE_DIR, CACHE_SIMILARITY_THRESHOLD
    from tools_sql import SQLTool
    from retriever import VectorStore, HybridRetriever
    from cache import SemanticCache
    
    llm_client = LLMClient(MODEL_NAME, MODEL_BASE_URL)
    sql_tool = SQLTool(DB_PATH)
    vector_store = VectorStore()
    
    chunks_file = DATA_DIR / "chunks.json"
    chunks = []
    if chunks_file.exists():
        with open(chunks_file, 'r') as f:
            chunks = json.load(f)
    
    retriever = HybridRetriever(vector_store, chunks)
    cache = SemanticCache(CACHE_DIR, CACHE_SIMILARITY_THRESHOLD)
    
    return AgentGraph(llm_client, sql_tool, retriever, cache, None), chunks


class AgentGraph:
    
    def __init__(self, llm_client, sql_tool, retriever, cache, prompts):
        self.llm_client = llm_client
        self.sql_tool = sql_tool
        self.retriever = retriever
        self.cache = cache
    
    def invoke(self, question: str, stream: bool = False) -> Dict[str, Any]:
        cached = self.cache.get(question)
        if cached:
            return {
                "answer": cached["answer"],
                "sources": cached.get("metadata", {}).get("sources", []),
                "route": cached.get("metadata", {}).get("route", "CACHED"),
                "cached": True
            }
        
        route = self._route_query(question)
        logger.info(f"Query routed to: {route.value}")
        
        if route == RouteType.REFUSE:
            return {
                "answer": self._handle_refusal(question),
                "route": route.value,
                "sources": []
            }
        
        if route == RouteType.CLARIFY:
            return {
                "answer": self._handle_clarification(question),
                "route": route.value,
                "sources": []
            }
        
        sql_results = self._execute_sql(question) if route in [RouteType.SQL_ONLY, RouteType.BOTH] else None
        pdf_results = self._retrieve_pdfs(question) if route in [RouteType.PDF_ONLY, RouteType.BOTH] else []
        
        answer = self._synthesize_answer(question, sql_results, pdf_results)
        sources = self._format_sources(sql_results, pdf_results)
        self.cache.set(question, answer, metadata={"sources": sources, "route": route.value})
        
        return {
            "answer": answer,
            "sources": sources,
            "route": route.value,
            "sql_query": sql_results.get("query") if sql_results else None,
            "sql_valid": sql_results.get("success") if sql_results else None
        }
    
    def _route_query(self, question: str) -> RouteType:
        from prompts import get_router_prompt
        
        prompt = get_router_prompt(question)
        response = self.llm_client.generate(prompt, max_tokens=10)
        route_str = response.strip().upper()
        
        try:
            return RouteType(route_str)
        except ValueError:
            q = question.lower()
            if any(w in q for w in ["drop", "delete", "insert", "update"]):
                return RouteType.REFUSE
            if any(w in q for w in ["price", "volume", "close", "open", "stock"]):
                return RouteType.BOTH if any(w in q for w in ["risk", "report", "10-k", "annual"]) else RouteType.SQL_ONLY
            if any(w in q for w in ["risk", "revenue", "sales", "table", "report"]):
                return RouteType.PDF_ONLY
            return RouteType.CLARIFY
    
    def _execute_sql(self, question: str) -> Optional[Dict]:
        from prompts import get_sql_prompt
        
        schema = self.sql_tool.get_schema_string()
        prompt = get_sql_prompt(question, schema)
        sql_query = self.llm_client.generate(prompt, max_tokens=200)
        logger.info(f"Generated SQL: {sql_query}")
        return self.sql_tool.execute_query(sql_query)
    
    def _retrieve_pdfs(self, question: str) -> List[Dict]:
        from config import TOP_K_VECTOR, TOP_K_BM25, TOP_K_FINAL
        results = self.retriever.search(question, top_k_vector=TOP_K_VECTOR, top_k_bm25=TOP_K_BM25, top_k_final=TOP_K_FINAL)
        logger.info(f"Retrieved {len(results)} PDF chunks")
        return results
    
    def _synthesize_answer(self, question: str, sql_results: Optional[Dict], pdf_results: List[Dict]) -> str:
        from prompts import get_answer_prompt
        
        context_parts = [f"[{r.get('metadata', {}).get('company', 'Unknown')} {r.get('metadata', {}).get('year', '')} 10-K, page {r.get('metadata', {}).get('page', '?')}]\n{r['content'][:500]}..." 
                        for r in pdf_results]
        context = "\n\n".join(context_parts)
        sql_summary = sql_results.get("summary", "") if sql_results and sql_results.get("success") else ""
        
        prompt = get_answer_prompt(question, context, sql_summary)
        return self.llm_client.generate(prompt, max_tokens=500)
    
    def _format_sources(self, sql_results: Optional[Dict], pdf_results: List[Dict]) -> List[Dict]:
        sources = []
        if sql_results and sql_results.get("success"):
            sources.append({"type": "sql", "query": sql_results.get("query"), "row_count": sql_results.get("row_count", 0)})
        for r in pdf_results:
            m = r.get("metadata", {})
            sources.append({"type": "pdf", "company": m.get("company", ""), "year": m.get("year", ""), 
                          "page": m.get("page", ""), "pdf_filename": m.get("pdf_filename", ""), "chunk_type": m.get("chunk_type", "text")})
        return sources
    
    def _handle_refusal(self, question: str) -> str:
        from prompts import get_refusal_prompt
        return self.llm_client.generate(get_refusal_prompt("Contains potentially dangerous SQL commands or injection attempts"), max_tokens=100)
    
    def _handle_clarification(self, question: str) -> str:
        from prompts import get_clarification_prompt
        q = question.lower()
        missing = []
        if not any(t in q for t in ["aapl", "msft", "tsla", "apple", "microsoft", "tesla"]):
            missing.append("company name")
        if not any(w in q for w in ["2023", "2022", "2024", "q1", "q2", "q3", "q4"]):
            missing.append("timeframe/date")
        return self.llm_client.generate(get_clarification_prompt(question, ", ".join(missing) if missing else "specific details"), max_tokens=100)


class LLMClient:
    def __init__(self, model_name: str, base_url: str):
        self.model_name = model_name
        self.base_url = base_url
    
    def generate(self, prompt: str, max_tokens: int = 500, stream: bool = False):
        try:
            import requests
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model_name, "prompt": prompt, "stream": stream, 
                      "options": {"num_predict": max_tokens, "temperature": 0.7}},
                timeout=120, stream=stream
            )
            if stream:
                for line in response.iter_lines():
                    if line:
                        data = json.loads(line)
                        if "response" in data:
                            yield data["response"]
                        if data.get("done", False):
                            break
            else:
                if response.status_code == 200:
                    return response.json().get("response", "")
                logger.error(f"LLM API error: {response.status_code}")
                return "Error: Failed to generate response"
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return f"Error: {str(e)}"
