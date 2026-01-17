#!/bin/bash
# CI script: Ensures database exists, builds index if missing, runs evaluation.

set -e

echo "🔧 CI Pipeline Starting..."

# Check if database exists
if [ ! -f "data/finance.db" ]; then
    echo "📊 Generating database..."
    python setup_data.py
else
    echo "✅ Database exists"
fi

# Check if chunks exist
if [ ! -f "data/chunks.json" ]; then
    echo "📄 Building vector index..."
    python -m src.ingest
else
    echo "✅ Chunks exist"
fi

# Run evaluation
echo "🧪 Running evaluation..."
python eval/run_eval.py

echo "✅ CI Pipeline Complete"
