"""
Knowledge Base Snapshot Manager.
Exports and restores compact, deterministic snapshots of documents, chunks, and embeddings.
Pre-caches gold query embeddings for offline benchmarking.
"""
import gzip
import json
import logging
import os

from memory.store.db import KnowledgeBaseStore
from memory.store.embeddings import EmbeddingService

logger = logging.getLogger("financial_watch.memory.snapshot")

SNAPSHOT_DIR = os.path.join(os.path.dirname(__file__))
SNAPSHOT_FILE = os.path.join(SNAPSHOT_DIR, "kb_snapshot.json.gz")
QUERY_CACHE_FILE = os.path.join(SNAPSHOT_DIR, "query_embeddings_cache.json")

class SnapshotManager:
    def __init__(self, store: KnowledgeBaseStore | None = None):
        self.store = store or KnowledgeBaseStore()

    def export_snapshot(self, output_path: str | None = None) -> str:
        """
        Exports all database documents and chunks (including vectors) to a compact gzip archive.
        """
        output_path = output_path or SNAPSHOT_FILE
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        logger.info("Exporting Knowledge Base snapshot from PostgreSQL...")
        with self.store.get_connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT * FROM documents ORDER BY id;")
            docs = cur.fetchall()

            cur.execute(
                """
                    SELECT id, document_id, chunk_index, content, cleaned_content,
                           token_count, tier, source, url, publish_date,
                           is_simulated, institution_tags, embedding
                    FROM document_chunks
                    ORDER BY id;
                    """
            )
            raw_chunks = cur.fetchall()

        # Format chunks with serializable embeddings
        chunks = []
        for c in raw_chunks:
            emb = c["embedding"]
            if emb is not None:
                if hasattr(emb, "to_numpy"):
                    emb = emb.to_numpy().tolist()
                elif hasattr(emb, "tolist"):
                    emb = emb.tolist()
                elif isinstance(emb, str):
                    emb = json.loads(emb)
                else:
                    emb = [float(x) for x in emb]
            chunks.append({
                "id": c["id"],
                "document_id": c["document_id"],
                "chunk_index": c["chunk_index"],
                "content": c["content"],
                "cleaned_content": c["cleaned_content"],
                "token_count": c["token_count"],
                "tier": c["tier"],
                "source": c["source"],
                "url": c["url"],
                "publish_date": c["publish_date"],
                "is_simulated": c["is_simulated"],
                "institution_tags": c["institution_tags"],
                "embedding": emb,
            })

        snapshot_payload = {
            "version": "1.0",
            "document_count": len(docs),
            "chunk_count": len(chunks),
            "documents": [dict(d) for d in docs],
            "chunks": chunks,
        }

        json_bytes = json.dumps(snapshot_payload, default=str).encode("utf-8")
        with gzip.open(output_path, "wb") as f:
            f.write(json_bytes)

        byte_size = os.path.getsize(output_path)
        logger.info(f"Snapshot exported successfully to {output_path} ({byte_size / 1024:.1f} KB).")
        return output_path

    def load_snapshot(self, snapshot_path: str | None = None):
        """
        Restores documents and chunks from a snapshot into PostgreSQL.
        Runs CREATE EXTENSION vector and creates tables if needed.
        """
        snapshot_path = snapshot_path or SNAPSHOT_FILE
        if not os.path.exists(snapshot_path):
            raise FileNotFoundError(f"Snapshot file not found at {snapshot_path}")

        logger.info(f"Loading Knowledge Base snapshot from {snapshot_path}...")
        self.store.init_schema()

        with gzip.open(snapshot_path, "rb") as f:
            data = json.loads(f.read().decode("utf-8"))

        docs = data.get("documents", [])
        chunks = data.get("chunks", [])

        for d in docs:
            self.store.insert_document(d)

        self.store.insert_chunks(chunks)
        logger.info(f"Loaded {len(docs)} documents and {len(chunks)} chunks into PostgreSQL.")

    def precompute_query_embeddings(self, queries: list[str], embedder: EmbeddingService | None = None) -> str:
        """
        Pre-computes and caches query embeddings for gold benchmark questions.
        Enables 100% offline retrieval evaluation.
        """
        embedder = embedder or EmbeddingService()
        cache = {}
        if os.path.exists(QUERY_CACHE_FILE):
            with open(QUERY_CACHE_FILE, "r", encoding="utf-8") as f:
                try:
                    cache = json.load(f)
                except Exception:
                    cache = {}

        for q in queries:
            if q not in cache:
                cache[q] = embedder.embed_query(q)

        with open(QUERY_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f)

        logger.info(f"Cached {len(cache)} query embeddings to {QUERY_CACHE_FILE}.")
        return QUERY_CACHE_FILE

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    manager = SnapshotManager()
    path = manager.export_snapshot()
    print("Exported snapshot to:", path)
