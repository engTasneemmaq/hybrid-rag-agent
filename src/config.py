# Configuration file - paths and settings
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
PDF_DIR = DATA_DIR / "pdfs"
DB_PATH = DATA_DIR / "finance.db"
VECTOR_STORE_PATH = DATA_DIR / "vector_store"
CACHE_DIR = DATA_DIR / "cache"

PDF_DIR.mkdir(parents=True, exist_ok=True)
VECTOR_STORE_PATH.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "ollama")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3.1:8b")
MODEL_BASE_URL = os.getenv("MODEL_BASE_URL", "http://localhost:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")

TOP_K_VECTOR = int(os.getenv("TOP_K_VECTOR", "5"))
TOP_K_BM25 = int(os.getenv("TOP_K_BM25", "5"))
TOP_K_FINAL = int(os.getenv("TOP_K_FINAL", "5"))
USE_RERANKER = os.getenv("USE_RERANKER", "false").lower() == "true"

SQL_MAX_ROWS = int(os.getenv("SQL_MAX_ROWS", "100"))

CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
CACHE_SIMILARITY_THRESHOLD = float(os.getenv("CACHE_SIMILARITY_THRESHOLD", "0.85"))

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
