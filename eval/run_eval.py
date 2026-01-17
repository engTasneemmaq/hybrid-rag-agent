# Evaluation script
import json
import sys
import time
import logging
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent_graph import create_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def evaluate_context_precision(question: str, answer: str, sources: list) -> float:
    if not sources:
        return 0.0
    source_companies = {s.get("company", "") for s in sources if s.get("type") == "pdf"}
    answer_lower = answer.lower()
    score = 0.5
    for company in source_companies:
        if company.lower() in answer_lower:
            score += 0.3
            break
    return min(1.0, score)


def evaluate_faithfulness(question: str, answer: str, sources: list) -> float:
    answer_lower = answer.lower()
    if any(flag in answer_lower for flag in ["i don't know", "i cannot", "error", "failed"]):
        return 0.3
    if len(answer) < 20:
        return 0.4
    if sources and len(answer) > 50:
        return 0.8
    return 0.5


def run_evaluation():
    print("Starting Evaluation Run...")
    
    dataset_path = Path(__file__).parent.parent / "golden_dataset.json"
    with open(dataset_path, 'r', encoding='utf-8') as f:
        dataset = json.load(f)
    
    print("Initializing agent...")
    agent, _ = create_agent()
    
    results = []
    for item in dataset:
        q_id = item['id']
        question = item['question']
        category = item['category']
        
        print(f"\nProcessing Q{q_id}: {question[:60]}...")
        
        start_time = time.time()
        try:
            response = agent.invoke(question, stream=False)
            success = True
            answer = response.get("answer", "")
            route = response.get("route", "")
            sources = response.get("sources", [])
            sql_query = response.get("sql_query", "")
            sql_valid = response.get("sql_valid", None)
        except Exception as e:
            logger.error(f"Error processing Q{q_id}: {e}")
            answer = f"ERROR: {str(e)}"
            route = "ERROR"
            sources = []
            sql_query = ""
            sql_valid = False
            success = False
        
        duration = time.time() - start_time
        context_precision = evaluate_context_precision(question, answer, sources)
        faithfulness = evaluate_faithfulness(question, answer, sources)
        
        results.append({
            "id": q_id,
            "category": category,
            "question": question,
            "route": route,
            "answer": answer,
            "sources": json.dumps(sources),
            "sql_query": sql_query if sql_query else "",
            "sql_valid": sql_valid if sql_valid is not None else "",
            "context_precision": round(context_precision, 2),
            "faithfulness": round(faithfulness, 2),
            "duration_sec": round(duration, 2),
            "error": not success
        })
    
    df = pd.DataFrame(results)
    output_path = Path(__file__).parent.parent / "eval_results.csv"
    df.to_csv(output_path, index=False)
    
    print(f"\nEvaluation Complete. Results saved to {output_path}")
    print("\nSummary:")
    print(df[['id', 'category', 'route', 'sql_valid', 'context_precision', 'faithfulness', 'duration_sec']].to_string())
    print(f"\nAverage Context Precision: {df['context_precision'].mean():.2f}")
    print(f"Average Faithfulness: {df['faithfulness'].mean():.2f}")
    print(f"Average Duration: {df['duration_sec'].mean():.2f}s")


if __name__ == "__main__":
    run_evaluation()
