@echo off
REM CI script for Windows: Ensures database exists, builds index if missing, runs evaluation.

echo 🔧 CI Pipeline Starting...

REM Check if database exists
if not exist "data\finance.db" (
    echo 📊 Generating database...
    python setup_data.py
) else (
    echo ✅ Database exists
)

REM Check if chunks exist
if not exist "data\chunks.json" (
    echo 📄 Building vector index...
    python -m src.ingest
) else (
    echo ✅ Chunks exist
)

REM Run evaluation
echo 🧪 Running evaluation...
python eval\run_eval.py

echo ✅ CI Pipeline Complete
