import json
import os

from backend.app.agents.verifier import BANK_REGISTRY
from backend.app.core.pidgin_normalizer import PidginNormalizer
from memory.store.db import KnowledgeBaseStore
from memory.store.embeddings import EmbeddingService

store = KnowledgeBaseStore()
embedder = EmbeddingService()

with open("data/seed_posts.json", "r", encoding="utf-8") as f:
    posts = json.load(f)

with open("evals/benchmark_results.json", "r", encoding="utf-8") as f:
    bench_data = json.load(f)

openai_eval = bench_data["openai_evaluation"]["grounded_multi_agent_run"]["detailed_results"]
bench_item_map = {it["id"]: it for it in openai_eval}

print("================================================================================")
print("PART 1.1: QUERY VARIANT RETRIEVAL COMPARISON ON ALL 23 VERIFIABLE ITEMS")
print("================================================================================\n")

print(f"{'Item ID':<8} | {'Raw Post Rank':<14} | {'Norm Query Rank':<16} | {'Pipeline Rank in Log':<20} | {'Gold Doc Target':<40}")
print("-" * 105)

raw_ranks = []
norm_ranks = []
pipeline_ranks = []

for p in posts:
    gold_docs = p.get("linked_kb_docs", [])
    if not gold_docs:
        continue
    pid = p["id"]
    text = p["text"]
    norm_text, _ = PidginNormalizer.normalize(text)
    
    # Check bank
    target_bank = None
    for canonical, aliases in BANK_REGISTRY.items():
        if any(alias in text.lower() for alias in aliases):
            target_bank = canonical
            break

    # 1. Raw text search
    qvec_raw = embedder.embed_texts([text])[0]
    chunks_raw = store.hybrid_search(text, qvec_raw, top_k=20, target_institution=target_bank)
    rank_raw = "not in top 20"
    for idx, c in enumerate(chunks_raw):
        if any(g.lower() in c["url"].lower() for g in gold_docs):
            rank_raw = str(idx + 1)
            break

    # 2. Normalized query search
    qvec_norm = embedder.embed_texts([norm_text])[0]
    chunks_norm = store.hybrid_search(norm_text, qvec_norm, top_k=20, target_institution=target_bank)
    rank_norm = "not in top 20"
    for idx, c in enumerate(chunks_norm):
        if any(g.lower() in c["url"].lower() for g in gold_docs):
            rank_norm = str(idx + 1)
            break

    bench_item = bench_item_map.get(pid, {})
    p_rank = bench_item.get("gold_retrieval_rank", "N/A")

    raw_ranks.append(rank_raw)
    norm_ranks.append(rank_norm)
    pipeline_ranks.append(p_rank)

    print(f"{pid:<8} | {rank_raw:<14} | {rank_norm:<16} | {p_rank:<20} | {os.path.basename(gold_docs[0])[:40]:<40}")

raw_r1 = sum(1 for r in raw_ranks if r == "1")
norm_r1 = sum(1 for r in norm_ranks if r == "1")
pipe_r1 = sum(1 for r in pipeline_ranks if r == "1")

raw_top20 = sum(1 for r in raw_ranks if r != "not in top 20")
norm_top20 = sum(1 for r in norm_ranks if r != "not in top 20")
pipe_top20 = sum(1 for r in pipeline_ranks if r != "not in top 20")

print("-" * 105)
print(f"Recall@1: Raw Post = {raw_r1}/23 ({raw_r1/23*100:.1f}%) | Norm Query = {norm_r1}/23 ({norm_r1/23*100:.1f}%) | Pipeline Log = {pipe_r1}/23 ({pipe_r1/23*100:.1f}%)")
print(f"In Top 20: Raw Post = {raw_top20}/23 ({raw_top20/23*100:.1f}%) | Norm Query = {norm_top20}/23 ({norm_top20/23*100:.1f}%) | Pipeline Log = {pipe_top20}/23 ({pipe_top20/23*100:.1f}%)")
