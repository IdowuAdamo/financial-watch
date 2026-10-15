"""
Inspection script for the 11 Pre-Fix Confident-Wrong Benchmark Items:
seed_01, 03, 10, 13, 14, 15, 19, 25, 26, 27, 28
Prints the claim, retrieved chunks, verdict, confidence, rationale, and failure analysis.
"""
import json
import os

from memory.store.db import KnowledgeBaseStore


def inspect_confident_wrong():
    seed_file = os.path.join(os.path.dirname(__file__), "..", "data", "seed_posts.json")
    results_file = os.path.join(os.path.dirname(__file__), "benchmark_results.json")

    with open(seed_file, "r", encoding="utf-8") as f:
        posts = {p["id"]: p for p in json.load(f)}

    with open(results_file, "r", encoding="utf-8") as f:
        results = json.load(f)

    target_ids = ["seed_01", "seed_03", "seed_10", "seed_13", "seed_14", "seed_15", "seed_19", "seed_25", "seed_26", "seed_27", "seed_28"]
    
    prefix_items = {}
    if "prefix_baseline_run" in results and "detailed_results" in results["prefix_baseline_run"]:
        prefix_items = {i["id"]: i for i in results["prefix_baseline_run"]["detailed_results"]}

    postfix_items = {i["id"]: i for i in results["grounded_multi_agent_run"]["detailed_results"]}

    store = KnowledgeBaseStore()
    with store.get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, url, source, tier, institution_tags FROM document_chunks;")
        chunk_meta = {row["id"]: row for row in cur.fetchall()}

    print("\n" + "=" * 105)
    print("           DETAILED AUDIT OF THE 11 PRE-FIX CONFIDENT-WRONG BENCHMARK ITEMS            ")
    print("=" * 105)

    for item_id in target_ids:
        post = posts.get(item_id, {})
        post_fix = postfix_items.get(item_id, {})
        pre_fix = prefix_items.get(item_id, {})

        print(f"\n[ITEM ID: {item_id}] Category: {post.get('category_type')} | Language: {post.get('language')}")
        print(f"Post Text: \"{post.get('text')}\"")
        print(f"Extracted Claim(s): {post_fix.get('claims', ['N/A'])}")
        print(f"Target Expected Verdict: {post.get('expected_verdict')} (Gold Label: {post.get('gold_label')})")
        print(f"Linked Gold KB Doc(s)  : {post.get('linked_kb_docs')}")
        print("-" * 105)
        
        # Pre-fix outcome
        pre_verdict = pre_fix.get("predicted_verdict", "supported/contradicted")
        print(f"Pre-Fix Baseline Result : Verdict = '{pre_verdict}' | Status = CONFIDENT-WRONG")
        
        # Post-fix outcome
        post_verdict = post_fix.get("verdict")
        post_conf = post_fix.get("confidence")
        post_cited = post_fix.get("cited_chunk_ids", [])
        post_spans = post_fix.get("quoted_spans", [])
        post_ev_type = post_fix.get("evidence_type")
        post_cw = post_fix.get("is_confident_wrong")
        
        print(f"Post-Fix Grounded Result: Verdict = '{post_verdict}' (Confidence: {post_conf:.2f}, Evidence: {post_ev_type}) | Confident-Wrong: {post_cw}")
        print(f"Cited Chunk IDs         : {post_cited if post_cited else '[] (Properly Abstained)'}")
        print(f"Validated Quoted Spans  : {post_spans if post_spans else 'None'}")
        
        # Retrieved chunks
        print("Retrieved Chunks in Session:")
        for cid in post_fix.get("cited_chunk_ids", []) or post_fix.get("retrieved_chunk_ids", [])[:3]:
            meta = chunk_meta.get(cid, {})
            print(f"  * {cid}: {meta.get('source', 'Unknown')} | {meta.get('url', 'N/A')}")

        print(f"Design Rationale        : {post.get('rationale')}")
        print("=" * 105)

if __name__ == "__main__":
    inspect_confident_wrong()
