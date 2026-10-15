import json
import os

with open("evals/benchmark_results.json", "r", encoding="utf-8") as f:
    bench_data = json.load(f)

openai_eval = bench_data["openai_evaluation"]["grounded_multi_agent_run"]["detailed_results"]
item_map = {it["id"]: it for it in openai_eval}

target_15 = [
    "seed_01", "seed_02", "seed_07", "seed_08", "seed_18", "seed_24",
    "seed_04", "seed_05", "seed_06", "seed_09", "seed_10", "seed_11", "seed_20", "seed_21", "seed_25"
]

print("=== DEEP GATE AND ENTAILMENT INSPECTION ON 15 ITEMS ===")
for iid in target_15:
    it = item_map[iid]
    print(f"ID: {iid} ({it['category_type']}) | Exp: {it['expected_verdict']} | Pred: {it['verdict']}")
    print(f"  Claims: {it['claims']}")
    print(f"  Cited: {it['cited_chunk_ids']}")
    print(f"  Evidence Type: {it['evidence_type']}")
    print(f"  Entailment: {it['entailment_status']}")
    print(f"  Quoted Spans: {it['quoted_spans']}")
    print(f"  Confidence: {it['confidence']}")
    print(f"  Gold Rank in Pipeline: {it['gold_retrieval_rank']}")
    print()

# Check log file for errors/timeouts
log_file = "C:/Users/Hp/.gemini/antigravity-ide/brain/2e96845c-f16d-4bc7-bc57-22c35fce6e70/.system_generated/tasks/task-1371.log"
if os.path.exists(log_file):
    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
        log_content = f.read()
    print("=== LOG SCAN (TASK-1371) ===")
    print("Total characters in log:", len(log_content))
    error_lines = [line for line in log_content.splitlines() if any(w in line.lower() for w in ["error", "warning", "fallback", "timed out", "retry"])]
    print(f"Warning/Error lines found in log: {len(error_lines)}")
    for l in error_lines[:15]:
        print("  *", l)
else:
    print("Task 1371 log not found on disk.")
