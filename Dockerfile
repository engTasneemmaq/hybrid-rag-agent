# Dockerfile for Hybrid RAG Agent
# Sets up environment and model weights automatically

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama (for local LLM)
RUN curl -fsSL https://ollama.com/install.sh | sh

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p data/pdfs data/cache data/vector_store

# Expose API port
EXPOSE 8000

# Default command: start API server
# Note: In production, you'd want to start Ollama separately or use a different model service
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
