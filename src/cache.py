# Semantic cache - stores query-answer pairs
import logging
import json
import hashlib
import math
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

def _hash_embedding(text: str, dim: int = 128) -> list:
    hash_obj = hashlib.sha256(text.encode())
    hash_hex = hash_obj.hexdigest()
    vec = [int(hash_hex[i:i+2], 16) / 255.0 for i in range(0, min(dim, len(hash_hex)), 2)]
    while len(vec) < dim:
        vec.extend([0.0] * (dim - len(vec)))
    return vec[:dim]

def _cosine_similarity(vec1: list, vec2: list) -> float:
    dot = sum(a * b for a, b in zip(vec1, vec2))
    mag1 = math.sqrt(sum(a * a for a in vec1))
    mag2 = math.sqrt(sum(a * a for a in vec2))
    return dot / (mag1 * mag2) if mag1 > 0 and mag2 > 0 else 0.0

class SemanticCache:
    
    def __init__(self, cache_dir: Path, similarity_threshold: float = 0.85):
        from config import CACHE_ENABLED
        
        self.cache_dir = cache_dir
        self.similarity_threshold = similarity_threshold
        self.enabled = CACHE_ENABLED
        self.cache_file = cache_dir / "cache.json"
        self.cache_data = {}
        
        if self.enabled:
            self._load_cache()
    
    def _load_cache(self):
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    self.cache_data = json.load(f)
            logger.info(f"Loaded {len(self.cache_data)} cached entries")
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
            self.cache_data = {}
    
    def _save_cache(self):
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def _get_query_hash(self, query: str) -> str:
        return hashlib.md5(" ".join(query.lower().strip().split()).encode()).hexdigest()
    
    def get(self, query: str) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None
        
        query_hash = self._get_query_hash(query)
        if query_hash in self.cache_data:
            logger.info("Cache hit (exact match)")
            return self.cache_data[query_hash]
        
        query_embedding = _hash_embedding(query)
        best_match = None
        best_similarity = 0.0
        
        for cached_entry in self.cache_data.values():
            if "embedding" in cached_entry:
                similarity = _cosine_similarity(query_embedding, cached_entry["embedding"])
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = cached_entry
        
        if best_similarity >= self.similarity_threshold and best_match:
            logger.info(f"Cache hit (semantic similarity: {best_similarity:.2f})")
            return best_match
        
        return None
    
    def set(self, query: str, answer: str, metadata: Optional[Dict] = None):
        if not self.enabled:
            return
        
        self.cache_data[self._get_query_hash(query)] = {
            "query": query,
            "answer": answer,
            "embedding": _hash_embedding(query),
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        }
        self._save_cache()
        logger.info(f"Cached answer for query: {query[:50]}...")
    
    def clear(self):
        self.cache_data = {}
        if self.cache_file.exists():
            self.cache_file.unlink()
        logger.info("Cache cleared")
