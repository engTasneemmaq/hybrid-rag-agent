import json
import pandas as pd
import time
from typing import List, Dict

# --- INSTRUCTIONS FOR CANDIDATE ---
# 1. Import your agent's main query function below.
# 2. Run this script to generate your score report.
# 3. Submit the 'eval_results.csv' file.

# from my_agent import query_pipeline as my_agent_function
def my_agent_function(prompt: str) -> str:
    """
    PLACEHOLDER: Replace this with your actual agent call.
    Example: return agent_graph.invoke({"question": prompt})['answer']
    """
    return "I am a placeholder agent. I don't know the answer yet."

def load_golden_dataset(filepath: str):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def run_evaluation():
    print("🚀 Starting Evaluation Run...")
    dataset = load_golden_dataset("golden_dataset.json")
    results = []

    for item in dataset:
        q_id = item['id']
        question = item['question']
        category = item['category']
        
        print(f"Processing Q{q_id}: {question[:50]}...")
        
        start_time = time.time()
        try:
            # CALL CANDIDATE AGENT
            response = my_agent_function(question)
            success = True
        except Exception as e:
            response = f"ERROR: {str(e)}"
            success = False
        duration = time.time() - start_time
        
        # Simple Keyword Check (In a real scenario, use LLM-as-a-judge here)
        # This is just for the candidate's quick feedback.
        keywords = item.get('expected_answer_keywords', [])
        hit = any(k.lower() in response.lower() for k in keywords) if keywords else "N/A"

        results.append({
            "id": q_id,
            "category": category,
            "question": question,
            "agent_response": response,
            "duration_sec": round(duration, 2),
            "keyword_hit": hit,
            "error": not success
        })

    # Save Results
    df = pd.DataFrame(results)
    df.to_csv("eval_results.csv", index=False)
    print("\n✅ Evaluation Complete. Results saved to eval_results.csv")
    print(df[['id', 'category', 'keyword_hit', 'duration_sec']])

if __name__ == "__main__":
    run_evaluation()