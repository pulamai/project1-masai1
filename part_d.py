import os
import glob
import json
import time
import sqlite3
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from mock_llm import chat

# Chunk policies
def chunk_text(text, chunk_size=40, overlap=10):
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += (chunk_size - overlap)
    return chunks

class PolicyRAG:
    def __init__(self, policy_dir="data/policies"):
        self.chunks = []
        for path in glob.glob(os.path.join(policy_dir, "*.txt")):
            filename = os.path.basename(path)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            for c in chunk_text(content):
                self.chunks.append({"source": filename, "text": c})

        self.vectorizer = TfidfVectorizer()
        self.tfidf_matrix = self.vectorizer.fit_transform([ch["text"] for ch in self.chunks])

    def retrieve(self, query, k=3):
        q_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(q_vec, self.tfidf_matrix).flatten()
        top_idx = scores.argsort()[::-1][:k]
        results = []
        for idx in top_idx:
            results.append({
                "source": self.chunks[idx]["source"],
                "score": float(scores[idx]),
                "text": self.chunks[idx]["text"]
            })
        return results

# Tools implementation
def get_order(order_id):
    conn = sqlite3.connect("data/instamart.db")
    cursor = conn.cursor()
    cursor.execute("SELECT order_id, status, order_amount, delivery_minutes FROM orders WHERE order_id = ?", (order_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return {"error": "order not found"}
    return {"order_id": row[0], "status": row[1], "order_amount": row[2], "delivery_minutes": row[3]}

rag_instance = PolicyRAG()
def search_policy(query):
    return {"results": rag_instance.retrieve(query)}

def calculate_refund(order_amount, delivery_minutes):
    if delivery_minutes is None or delivery_minutes > 45:
        return {"refund_inr": float(order_amount)}
    return {"refund_inr": 0.0}

def issue_refund(order_id, refund_inr):
    os.makedirs("outputs", exist_ok=True)
    with open("outputs/refund_ledger.jsonl", "a") as f:
        f.write(json.dumps({"timestamp": time.time(), "tool": "issue_refund", "order_id": order_id, "amount": refund_inr}) + "\n")
    return {"refund_inr": refund_inr}

def escalate_to_human(order_id, refund_inr):
    os.makedirs("outputs", exist_ok=True)
    with open("outputs/refund_ledger.jsonl", "a") as f:
        f.write(json.dumps({"timestamp": time.time(), "tool": "escalate_to_human", "order_id": order_id, "amount": refund_inr}) + "\n")
    return {"refund_inr": refund_inr}

TOOL_MAP = {
    "get_order": get_order,
    "search_policy": search_policy,
    "calculate_refund": calculate_refund,
    "issue_refund": issue_refund,
    "escalate_to_human": escalate_to_human
}

def run_agent(user_message, scenario_id, max_iterations=6, token_limit=6000, time_limit_seconds=10, run_id="run_default"):
    start_time = time.monotonic()
    messages = [
        {"role": "system", "content": "AGENT. You are a helpful refund assistant."},
        {"role": "user", "content": user_message}
    ]

    tokens_used = 0
    steps = []
    tools_executed = []

    os.makedirs("state", exist_ok=True)

    for iteration in range(max_iterations):
        if (time.monotonic() - start_time) >= time_limit_seconds:
            return {"status": "FALLBACK_TIMEOUT", "final_answer": "Timeout reached", "steps": steps, "tokens_used": tokens_used}

        resp = chat(messages)
        tokens_used += resp.usage.total_tokens

        if tokens_used > token_limit:
            return {"status": "FALLBACK_TOKEN_LIMIT", "final_answer": "Token limit exceeded", "steps": steps, "tokens_used": tokens_used}

        msg = resp.choices[0].message
        if not msg.tool_calls:
            final_content = msg.content
            status = final_content.split(":")[0] if ":" in final_content else "DENIED"
            return {"status": status, "final_answer": final_content, "steps": steps, "tokens_used": tokens_used}

        # Append assistant message with tool calls
        tool_calls_raw = [{"id": tc.id, "name": tc.name, "arguments": tc.arguments} for tc in msg.tool_calls]
        messages.append({"role": "assistant", "content": None, "tool_calls": tool_calls_raw})

        for tc in msg.tool_calls:
            t_name = tc.name
            t_args = tc.arguments

            func = TOOL_MAP.get(t_name)
            obs = func(**t_args)
            tools_executed.append(t_name)

            steps.append({"tool": t_name, "arguments": t_args, "observation": obs})
            messages.append({"role": "tool", "tool_call_id": tc.id, "name": t_name, "content": json.dumps(obs)})

            # Save Checkpoint after each tool execution
            checkpoint = {
                "run_id": run_id, "scenario_id": scenario_id, "messages": messages,
                "tokens_used": tokens_used, "step_number": len(steps), "tools_executed": tools_executed
            }
            with open(os.path.join("state", f"{run_id}.json"), "w") as cf:
                json.dump(checkpoint, cf)

    return {"status": "FALLBACK_MAX_ITERATIONS", "final_answer": "Max iterations reached", "steps": steps, "tokens_used": tokens_used}

def run_part_d():
    scenarios = pd.read_csv("data/raw/agent_scenarios.csv")
    os.makedirs("outputs", exist_ok=True)

    results = []
    for idx, row in scenarios.iterrows():
        res = run_agent(row['message'], row['scenario_id'], run_id=f"run_{row['scenario_id']}")
        results.append({
            "scenario_id": row['scenario_id'], "status": res['status'],
            "final_answer": res['final_answer'], "llm_calls": len(res['steps']) + 1, "tokens_used": res['tokens_used']
        })
        with open("outputs/agent_runs.jsonl", "a") as f:
            f.write(json.dumps({"scenario_id": row['scenario_id'], **res}) + "\n")

    print("Part D completed successfully.")

if __name__ == "__main__":
    run_part_d()
