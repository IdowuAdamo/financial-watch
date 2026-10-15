import json

with open("evals/benchmark_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

openai_eval = data["openai_evaluation"]["grounded_multi_agent_run"]["detailed_results"]
item_map = {it["id"]: it for it in openai_eval}

with open("data/seed_posts.json", "r", encoding="utf-8") as f:
    seed_posts = json.load(f)
seed_map = {s["id"]: s for s in seed_posts}

rank1_items = ["seed_01", "seed_02", "seed_07", "seed_08", "seed_18", "seed_24"]
correct_answered_items = ["seed_04", "seed_05", "seed_06", "seed_09", "seed_10", "seed_11", "seed_20", "seed_21", "seed_25"]

print("================================================================================")
print("PART 1.1: INVERSION INVESTIGATION - 6 ITEMS WITH GOLD AT RANK 1 (FALSE ABSTENTIONS)")
print("================================================================================\n")

for iid in rank1_items:
    it = item_map[iid]
    seed = seed_map[iid]
    print(f"[{iid}] Category: {it['category_type']} | Expected: {it['expected_verdict']} -> Pred: {it['verdict']}")
    print(f"  Raw Post: {seed['text']}")
    print(f"  Gold Docs: {seed.get('linked_kb_docs')}")
    print(f"  Extracted Claims: {it.get('claims')}")
    print(f"  Gold Rank: {it.get('gold_retrieval_rank')} | Gold Title-Only: {it.get('gold_is_title_only')}")
    print(f"  Cited Chunk IDs: {it.get('cited_chunk_ids')}")
    print(f"  Evidence Type: {it.get('evidence_type')} | Entailment: {it.get('entailment_status')}")
    print(f"  Quoted Spans: {it.get('quoted_spans')}")
    print(f"  Confidence: {it.get('confidence')}")
    print()

print("================================================================================")
print("PART 1.1: INVERSION INVESTIGATION - 9 CORRECT ANSWERED ITEMS (GOLD NOT IN TOP 20)")
print("================================================================================\n")

for iid in correct_answered_items:
    it = item_map[iid]
    seed = seed_map[iid]
    print(f"[{iid}] Category: {it['category_type']} | Expected: {it['expected_verdict']} -> Pred: {it['verdict']}")
    print(f"  Raw Post: {seed['text']}")
    print(f"  Gold Docs: {seed.get('linked_kb_docs')}")
    print(f"  Extracted Claims: {it.get('claims')}")
    print(f"  Gold Rank: {it.get('gold_retrieval_rank')} | Gold Title-Only: {it.get('gold_is_title_only')}")
    print(f"  Cited Chunk IDs: {it.get('cited_chunk_ids')}")
    print(f"  Evidence Type: {it.get('evidence_type')} | Entailment: {it.get('entailment_status')}")
    print(f"  Quoted Spans: {it.get('quoted_spans')}")
    print(f"  Confidence: {it.get('confidence')}")
    print()
