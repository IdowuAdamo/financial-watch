"""
Retrieval evaluation harness.
Measures Recall@k (k=1, 3, 5), Abstention Coverage, and Confident-Wrong rate.
Reports metrics separately for regulator-level (real KB) vs bank-specific (simulated client) queries.
Supports 100% offline benchmarking via pre-cached query embeddings.
"""
import json
import logging
import os
from typing import Any

from memory.snapshot.snapshot_manager import QUERY_CACHE_FILE
from memory.store.db import KnowledgeBaseStore
from memory.store.embeddings import EmbeddingService

logger = logging.getLogger("financial_watch.memory.evals")

# Benchmark test cases with expected targets
BENCHMARK_CASES = [
    # --- REGULATOR-LEVEL QUERIES (Target: Real KB evidence) ---
    {
        "id": "q_reg_01",
        "category": "regulator_level",
        "query": "Central Bank of Nigeria BVN expiry date policy",
        "expected_doc_substring": "BVN Issued in Nigeria Has No Expiry Date",
        "expect_abstention": False,
    },
    {
        "id": "q_reg_02",
        "category": "regulator_level",
        "query": "Heritage Bank operating licence revocation CBN announcement",
        "expected_doc_substring": "Heritage Bank",
        "expect_abstention": False,
    },
    {
        "id": "q_reg_03",
        "category": "regulator_level",
        "query": "Central Bank of Nigeria circular on cybersecurity levy withdrawal",
        "expected_doc_substring": "Cybersecurity Levy",
        "expect_abstention": False,
    },
    {
        "id": "q_reg_04",
        "category": "regulator_level",
        "query": "Fake crypto grant distribution purportedly signed by Governor Cardoso",
        "expected_doc_substring": "Fraudulent",
        "expect_abstention": False,
    },

    # --- BANK-SPECIFIC QUERIES (Target: Simulated Client Docs) ---
    {
        "id": "q_sim_01",
        "category": "bank_specific",
        "query": "Apex Horizon Example Bank customer deposit growth and liquidity position",
        "expected_doc_substring": "Apex Horizon Example Bank",
        "expect_abstention": False,
    },
    {
        "id": "q_sim_02",
        "category": "bank_specific",
        "query": "Meridian Mock Bank core banking Sunday maintenance window",
        "expected_doc_substring": "Meridian Mock Bank",
        "expect_abstention": False,
    },
    {
        "id": "q_sim_03",
        "category": "bank_specific",
        "query": "Northbridge Example Bank recruitment fees and interview charges policy",
        "expected_doc_substring": "Northbridge Example Bank",
        "expect_abstention": False,
    },

    # --- ABSTENTION TEST CASES (No matching evidence exists; system must abstain) ---
    {
        "id": "q_abs_01",
        "category": "bank_specific",
        "query": "Kreston Test Bank vault explosion and total deposit wipeout in Kano",
        "expected_doc_substring": None, # Intentionally no document exists
        "expect_abstention": True,
    },
    {
        "id": "q_abs_02",
        "category": "regulator_level",
        "query": "CBN secret decree mandating 75% tax deduction on all personal savings accounts",
        "expected_doc_substring": None, # Intentionally no document exists
        "expect_abstention": True,
    },
]

class RetrievalEvaluator:
    def __init__(self, store: KnowledgeBaseStore | None = None, embedder: EmbeddingService | None = None):
        self.store = store or KnowledgeBaseStore()
        self.embedder = embedder or EmbeddingService()
        self.query_cache: dict[str, list[float]] = {}
        if os.path.exists(QUERY_CACHE_FILE):
            try:
                with open(QUERY_CACHE_FILE, "r", encoding="utf-8") as f:
                    self.query_cache = json.load(f)
            except Exception:
                pass

    def get_query_embedding(self, query: str) -> list[float]:
        if query in self.query_cache:
            return self.query_cache[query]
        emb = self.embedder.embed_query(query)
        self.query_cache[query] = emb
        return emb

    def evaluate(self, k_values: list[int] = [1, 3, 5], abstention_threshold: float = 0.20) -> dict[str, Any]:
        """
        Runs retrieval evaluation across benchmark cases and computes:
        - Recall@k for k in {1, 3, 5}
        - Abstention Coverage (correct abstention rate when expected)
        - Confident-Wrong Rate (asserted false match with score >= threshold)
        Reports separately for regulator-level vs bank-specific items.
        """
        results_by_cat = {
            "regulator_level": {"total": 0, "abstention_expected": 0, "correct_abstention": 0, "confident_wrong": 0, "hits": {k: 0 for k in k_values}},
            "bank_specific": {"total": 0, "abstention_expected": 0, "correct_abstention": 0, "confident_wrong": 0, "hits": {k: 0 for k in k_values}},
        }

        detailed_logs = []

        for case in BENCHMARK_CASES:
            cat = case["category"]
            query = case["query"]
            expected = case["expected_doc_substring"]
            expect_abstention = case["expect_abstention"]

            stats = results_by_cat[cat]
            stats["total"] += 1

            emb = self.get_query_embedding(query)
            max_k = max(k_values)
            retrieved = self.store.hybrid_search(query, emb, top_k=max_k)

            # Check abstention
            top_score = retrieved[0]["score"] if retrieved else 0.0
            is_abstained = (len(retrieved) == 0) or (top_score < abstention_threshold)

            hit_at_k = {k: False for k in k_values}

            if expect_abstention:
                stats["abstention_expected"] += 1
                if is_abstained:
                    stats["correct_abstention"] += 1
                else:
                    # Confident wrong: Retrieved irrelevant passage with high confidence score
                    stats["confident_wrong"] += 1
            else:
                # Evidence expected
                for k in k_values:
                    top_k_chunks = retrieved[:k]
                    hit = any(expected.lower() in (c["content"] + " " + c["url"]).lower() for c in top_k_chunks)
                    if hit:
                        hit_at_k[k] = True
                        stats["hits"][k] += 1

                # If missed evidence entirely and claimed high confidence on wrong doc
                if not hit_at_k[1] and top_score >= 0.50:
                    stats["confident_wrong"] += 1

            detailed_logs.append({
                "id": case["id"],
                "category": cat,
                "query": query,
                "expected": expected,
                "expect_abstention": expect_abstention,
                "top_score": top_score,
                "is_abstained": is_abstained,
                "hit_at_k": hit_at_k,
                "retrieved_top1": retrieved[0]["content"][:100] if retrieved else None,
            })

        # Calculate percentages
        summary = {}
        for cat, data in results_by_cat.items():
            ev_count = data["total"] - data["abstention_expected"]
            recall_scores = {}
            for k in k_values:
                recall_scores[f"recall@{k}"] = round(data["hits"][k] / ev_count, 4) if ev_count > 0 else 1.0

            abs_cov = round(data["correct_abstention"] / data["abstention_expected"], 4) if data["abstention_expected"] > 0 else 1.0
            conf_wrong = round(data["confident_wrong"] / data["total"], 4) if data["total"] > 0 else 0.0

            summary[cat] = {
                "total_queries": data["total"],
                "evidence_queries": ev_count,
                "abstention_queries": data["abstention_expected"],
                **recall_scores,
                "abstention_coverage": abs_cov,
                "confident_wrong_rate": conf_wrong,
            }

        return {
            "summary": summary,
            "detailed_logs": detailed_logs,
        }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    evaluator = RetrievalEvaluator()
    res = evaluator.evaluate()
    print("\nRetrieval Evaluation Report:")
    print(json.dumps(res["summary"], indent=2))
