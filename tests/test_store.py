"""
Integration tests for PostgreSQL 16 + pgvector storage and hybrid retrieval.
"""
import pytest

from memory.store.db import KnowledgeBaseStore
from memory.store.embeddings import EmbeddingService


def test_store_connection_and_stats():
    store = KnowledgeBaseStore()
    stats = store.get_stats()
    assert "total_documents" in stats
    assert "total_chunks" in stats
    assert stats["total_documents"] >= 4
    assert stats["total_chunks"] >= 200

def test_hybrid_search_scoring():
    store = KnowledgeBaseStore()
    embedder = EmbeddingService()

    query = "Apex Horizon Example Bank customer deposits"
    emb = embedder.embed_query(query)
    results = store.hybrid_search(query, emb, top_k=3)

    assert len(results) > 0
    top_result = results[0]
    assert top_result["score"] > 0
    assert "Apex Horizon Example Bank" in top_result["content"]
    assert top_result["is_simulated"] is True

def test_title_only_evidence_penalty():
    store = KnowledgeBaseStore()
    embedder = EmbeddingService()

    query = "Heritage Bank licence revocation"
    emb = embedder.embed_query(query)
    results = store.hybrid_search(query, emb, top_k=3)

    assert len(results) > 0
    title_chunks = [r for r in results if r["is_title_only"]]
    assert len(title_chunks) > 0
    for tc in title_chunks:
        assert "[TITLE-ONLY EVIDENCE]" in tc["content"]

def test_approval_queue_persistence():
    store = KnowledgeBaseStore()
    test_id = "test_post_audit_persist_001"
    payload = {
        "post_id": test_id,
        "text": "Apex Horizon Example Bank customer notice verification test.",
        "approval_status": "pending",
        "response_draft": {
            "formal_response": "Draft response text."
        }
    }

    # Save item
    store.save_approval_item(post_id=test_id, payload=payload, approval_status="pending")

    # List items
    items = store.list_approval_items(status="pending")
    matching = [i for i in items if i.get("post_id") == test_id]
    assert len(matching) == 1
    assert matching[0]["approval_status"] == "pending"

    # Update item
    updated = store.update_approval_status(
        post_id=test_id,
        status="approved",
        edited_formal="Approved and edited response text.",
        editor_notes="Reviewed and approved by test auditor."
    )
    assert updated is not None
    assert updated["approval_status"] == "approved"
    assert updated["response_draft"]["formal_response"] == "Approved and edited response text."
    assert updated["editor_notes"] == "Reviewed and approved by test auditor."

def test_approval_queue_db_failure_fallback_visibility():
    """Verifies that DB failure raises connection error caught by API layer fallback."""
    unreachable_store = KnowledgeBaseStore(db_url="postgresql://invalid:invalid@127.0.0.1:59999/nonexistent")
    with pytest.raises(Exception):
        unreachable_store.list_approval_items(status="pending")

