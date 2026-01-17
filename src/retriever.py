# Hybrid retrieval - BM25 + vector search
import logging
import hashlib
from typing import List, Dict, Optional
from pathlib import Path

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None
    logging.warning("rank_bm25 not installed. BM25 search will be disabled.")

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    chromadb = None
    logging.warning("chromadb not installed. Vector search will be disabled.")

logger = logging.getLogger(__name__)

def _fallback_embedding(text: str, dim: int = 384) -> List[float]:
    hash_obj = hashlib.md5(text.encode())
    hash_hex = hash_obj.hexdigest()
    vec = [int(hash_hex[i:i+2], 16) / 255.0 for i in range(0, min(dim, len(hash_hex)), 2)]
    while len(vec) < dim:
        vec.extend([0.0] * (dim - len(vec)))
    return vec[:dim]

class VectorStore:
    
    def __init__(self, persist_dir: Optional[Path] = None):
        from config import VECTOR_STORE_PATH, EMBEDDING_MODEL, MODEL_BASE_URL
        
        self.persist_dir = persist_dir or VECTOR_STORE_PATH
        self.embedding_model = EMBEDDING_MODEL
        self.model_base_url = MODEL_BASE_URL
        self.client = None
        self.collection = None
        self._init_client()
    
    def _init_client(self):
        if chromadb is None:
            logger.warning("ChromaDB not available. Using fallback.")
            return
        
        try:
            self.client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=Settings(anonymized_telemetry=False)
            )
            try:
                self.collection = self.client.get_collection(name="financial_docs")
                logger.info("Loaded existing vector store collection")
            except:
                self.collection = self.client.create_collection(
                    name="financial_docs",
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info("Created new vector store collection")
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
    
    def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        try:
            import requests
            embeddings = []
            for text in texts:
                response = requests.post(
                    f"{self.model_base_url}/api/embeddings",
                    json={"model": self.embedding_model, "prompt": text},
                    timeout=30
                )
                if response.status_code == 200:
                    embeddings.append(response.json()["embedding"])
                else:
                    logger.warning("Ollama embedding failed, using fallback")
                    embeddings.append(_fallback_embedding(text))
            return embeddings
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return [_fallback_embedding(t) for t in texts]
    
    def add_chunks(self, chunks: List[Dict]):
        if not self.collection:
            logger.error("Vector store not initialized")
            return
        
        texts = [chunk["content"] for chunk in chunks]
        embeddings = self._get_embeddings(texts)
        
        self.collection.add(
            ids=[f"chunk_{i}" for i in range(len(chunks))],
            embeddings=embeddings,
            documents=texts,
            metadatas=[{
                "company": chunk.get("company", ""),
                "year": chunk.get("year", ""),
                "page": str(chunk.get("page", "")),
                "chunk_type": chunk.get("chunk_type", "text"),
                "pdf_filename": chunk.get("pdf_filename", "")
            } for chunk in chunks]
        )
        
        logger.info(f"Added {len(chunks)} chunks to vector store")
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        if not self.collection:
            return []
        
        try:
            query_embedding = self._get_embeddings([query])[0]
            results = self.collection.query(query_embeddings=[query_embedding], n_results=top_k)
            
            if not results["documents"] or not results["documents"][0]:
                return []
            
            return [{
                "content": doc,
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "score": 1.0 - results["distances"][0][i] if results["distances"] else 0.0
            } for i, doc in enumerate(results["documents"][0])]
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    def save(self):
        pass


class BM25Retriever:
    
    def __init__(self, chunks: List[Dict]):
        self.chunks = chunks
        self.bm25 = None
        if BM25Okapi and chunks:
            texts = [chunk["content"] for chunk in chunks]
            self.bm25 = BM25Okapi([text.lower().split() for text in texts])
            logger.info("BM25 index built")
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        if not self.bm25:
            return []
        
        query_tokens = query.lower().split()
        scores = self.bm25.get_scores(query_tokens)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        
        return [{
            "content": self.chunks[idx]["content"],
            "metadata": {k: v for k, v in self.chunks[idx].items() if k != "content"},
            "score": float(scores[idx])
        } for idx in top_indices if scores[idx] > 0]


class HybridRetriever:
    def __init__(self, vector_store: VectorStore, chunks: List[Dict]):
        from config import USE_RERANKER
        self.vector_store = vector_store
        self.chunks = chunks
        self.use_reranker = USE_RERANKER
        self.bm25 = BM25Retriever(chunks) if chunks else None
        if not chunks:
            logger.warning("No chunks provided to HybridRetriever. BM25 search will be disabled.")
    
    def search(self, query: str, top_k_vector: int = 5, top_k_bm25: int = 5, top_k_final: int = 5) -> List[Dict]:
        vector_results = self.vector_store.search(query, top_k=top_k_vector)
        bm25_results = self.bm25.search(query, top_k=top_k_bm25) if self.bm25 else []
        
        seen = set()
        merged = []
        for result in vector_results:
            h = hash(result["content"][:100])
            if h not in seen:
                result["score"] = result.get("score", 0.0) * 1.2
                merged.append(result)
                seen.add(h)
        
        for result in bm25_results:
            h = hash(result["content"][:100])
            if h not in seen:
                merged.append(result)
                seen.add(h)
        
        merged.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        
        if self.use_reranker:
            query_words = set(query.lower().split())
            for result in merged:
                content_words = set(result["content"].lower().split())
                overlap = len(query_words & content_words) / max(len(query_words), 1)
                result["score"] = result.get("score", 0.0) + overlap * 0.1
            merged.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        
        return merged[:top_k_final]
