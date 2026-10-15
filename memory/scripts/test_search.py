"""
Test hybrid search across indexed chunks.
"""
from memory.store.db import KnowledgeBaseStore
from memory.store.embeddings import EmbeddingService


def test_queries():
    store = KnowledgeBaseStore()
    embedder = EmbeddingService()

    queries = [
        "Heritage Bank license revocation",
        "Apex Horizon Example Bank deposits and capital",
        "BVN expiration date renewal fee",
        "Meridian Mock Bank core banking maintenance"
    ]

    for q in queries:
        print("\n==========================================")
        print(f"QUERY: '{q}'")
        emb = embedder.embed_query(q)
        results = store.hybrid_search(q, emb, top_k=2)
        print(f"Retrieved {len(results)} matches:")
        for r in results:
            sim_flag = "[SIMULATED]" if r["is_simulated"] else "[REAL]"
            title_flag = "[TITLE-ONLY]" if r["is_title_only"] else "[FULL-TEXT]"
            print(f"- Score: {r['score']} | {sim_flag} {title_flag} | Source: {r['source']}")
            print(f"  URL: {r['url']}")
            print(f"  Content: {r['content'][:150]}...")

if __name__ == "__main__":
    test_queries()
