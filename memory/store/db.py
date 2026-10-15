"""
PostgreSQL 16 + pgvector storage layer for FinancialWatch Knowledge Base.
Supports vector similarity search, tsvector full-text search, and document management.
"""
import json
import logging
import os
from typing import Any

import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row

load_dotenv()

logger = logging.getLogger("financial_watch.memory.store")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5433/financial_watch"
)

class KnowledgeBaseStore:
    """
    Manages persistence and vector indexing for documents and document chunks.
    """
    def __init__(self, db_url: str | None = None):
        self.db_url = db_url or DATABASE_URL

    def get_connection(self):
        conn = psycopg.connect(self.db_url, row_factory=dict_row)
        register_vector(conn)
        return conn

    def init_schema(self, sql_path: str | None = None):
        """Ensures vector extension and schema exist."""
        if not sql_path:
            sql_path = os.path.join(os.path.dirname(__file__), "..", "sql", "init.sql")
        
        with open(sql_path, "r", encoding="utf-8") as f:
            sql = f.read()

        with psycopg.connect(self.db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
        logger.info("Knowledge Base database schema initialized successfully.")

    def insert_document(self, doc: dict[str, Any]):
        """Inserts a parent document record."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO documents (
                        id, source, tier, title, url, publish_date, 
                        content_type, sha256, is_simulated, metadata_json
                    ) VALUES (
                        %(id)s, %(source)s, %(tier)s, %(title)s, %(url)s, %(publish_date)s,
                        %(content_type)s, %(sha256)s, %(is_simulated)s, %(metadata_json)s
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        title = EXCLUDED.title,
                        url = EXCLUDED.url,
                        sha256 = EXCLUDED.sha256,
                        metadata_json = EXCLUDED.metadata_json;
                    """,
                    {
                        "id": doc["id"],
                        "source": doc["source"],
                        "tier": doc.get("tier", 1),
                        "title": doc["title"],
                        "url": doc["url"],
                        "publish_date": doc.get("publish_date"),
                        "content_type": doc.get("content_type", "text"),
                        "sha256": doc["sha256"],
                        "is_simulated": doc.get("is_simulated", False),
                        "metadata_json": json.dumps(doc.get("metadata", {})),
                    }
                )
            conn.commit()

    def insert_chunks(self, chunks: list[dict[str, Any]]):
        """Bulk inserts chunks with dense vector embeddings and metadata."""
        if not chunks:
            return

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                for c in chunks:
                    cur.execute(
                        """
                        INSERT INTO document_chunks (
                            id, document_id, chunk_index, content, cleaned_content,
                            token_count, tier, source, url, publish_date,
                            is_simulated, institution_tags, embedding
                        ) VALUES (
                            %(id)s, %(document_id)s, %(chunk_index)s, %(content)s, %(cleaned_content)s,
                            %(token_count)s, %(tier)s, %(source)s, %(url)s, %(publish_date)s,
                            %(is_simulated)s, %(institution_tags)s, %(embedding)s
                        )
                        ON CONFLICT (id) DO UPDATE SET
                            content = EXCLUDED.content,
                            cleaned_content = EXCLUDED.cleaned_content,
                            tier = EXCLUDED.tier,
                            embedding = EXCLUDED.embedding,
                            institution_tags = EXCLUDED.institution_tags;
                        """,
                        {
                            "id": c["id"],
                            "document_id": c["document_id"],
                            "chunk_index": c.get("chunk_index", 0),
                            "content": c["content"],
                            "cleaned_content": c.get("cleaned_content", c["content"]),
                            "token_count": c.get("token_count", 0),
                            "tier": c.get("tier", 1),
                            "source": c["source"],
                            "url": c["url"],
                            "publish_date": c.get("publish_date"),
                            "is_simulated": c.get("is_simulated", False),
                            "institution_tags": json.dumps(c.get("institution_tags", [])),
                            "embedding": c.get("embedding"), # list of floats or pgvector type
                        }
                    )
            conn.commit()
        logger.info(f"Inserted {len(chunks)} chunks into PostgreSQL.")

    def hybrid_search(
        self,
        query_text: str,
        query_embedding: list[float] | None,
        top_k: int = 5,
        filter_source: str | None = None,
        filter_simulated: bool | None = None,
        target_institution: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Executes hybrid dense vector similarity + sparse tsvector full-text search.
        Formula:
          Combined = 0.45 * (1 - cosine_dist) + 0.40 * normalized_fts_rank + 0.10 * tier_weight + institution_boost
          Title-only penalty is enforced downstream in the verifier confidence gate,
          preserving discovery during candidate retrieval.
        """
        tier_weights = {1: 1.0, 2: 0.8, 3: 0.5}

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Dense vector candidates if embedding available (top 100 for high recall)
                vector_results: dict[str, tuple[float, dict[str, Any]]] = {}
                if query_embedding:
                    cur.execute(
                        """
                        SELECT id, document_id, chunk_index, content, tier, source, url,
                               publish_date, is_simulated, institution_tags,
                               1 - (embedding <=> %(qvec)s::vector) AS vector_similarity
                        FROM document_chunks
                        WHERE embedding IS NOT NULL
                        ORDER BY embedding <=> %(qvec)s::vector ASC
                        LIMIT 100;
                        """,
                        {"qvec": query_embedding}
                    )
                    for row in cur.fetchall():
                        vector_results[row["id"]] = (float(row["vector_similarity"]), row)

                # Sparse keyword full-text search
                fts_results: dict[str, tuple[float, dict[str, Any]]] = {}
                try:
                    cur.execute(
                        """
                        SELECT id, document_id, chunk_index, content, tier, source, url,
                               publish_date, is_simulated, institution_tags,
                               ts_rank_cd(tsv, websearch_to_tsquery('english', %(qtext)s)) AS fts_rank
                        FROM document_chunks
                        WHERE tsv @@ websearch_to_tsquery('english', %(qtext)s)
                        ORDER BY fts_rank DESC
                        LIMIT 100;
                        """,
                        {"qtext": query_text}
                    )
                    for row in cur.fetchall():
                        fts_results[row["id"]] = (float(row["fts_rank"]), row)
                except Exception:
                    # Fallback to plainto_tsquery if websearch syntax fails
                    conn.rollback()
                    cur.execute(
                        """
                        SELECT id, document_id, chunk_index, content, tier, source, url,
                               publish_date, is_simulated, institution_tags,
                               ts_rank_cd(tsv, plainto_tsquery('english', %(qtext)s)) AS fts_rank
                        FROM document_chunks
                        WHERE tsv @@ plainto_tsquery('english', %(qtext)s)
                        ORDER BY fts_rank DESC
                        LIMIT 100;
                        """,
                        {"qtext": query_text}
                    )
                    for row in cur.fetchall():
                        fts_results[row["id"]] = (float(row["fts_rank"]), row)

                # Merge candidate IDs
                all_ids = set(vector_results.keys()) | set(fts_results.keys())
                scored_results = []

                # Max FTS rank for normalization
                max_fts = max([r[0] for r in fts_results.values()], default=1.0)
                if max_fts <= 0:
                    max_fts = 1.0

                for chunk_id in all_ids:
                    vec_sim = vector_results[chunk_id][0] if chunk_id in vector_results else 0.0
                    fts_rank = fts_results[chunk_id][0] if chunk_id in fts_results else 0.0
                    norm_fts = fts_rank / max_fts

                    raw_row = vector_results[chunk_id][1] if chunk_id in vector_results else fts_results[chunk_id][1]
                    tier = raw_row.get("tier", 1)
                    tier_weight = tier_weights.get(tier, 0.5)
                    
                    is_simulated = raw_row.get("is_simulated", False)
                    # Filter simulated if specified
                    if filter_simulated is not None and is_simulated != filter_simulated:
                        continue

                    content = raw_row.get("content", "")
                    is_title_only = "[TITLE-ONLY EVIDENCE]" in content or raw_row.get("document_id", "").startswith("doc_cbn_title_")

                    # Institution tag matching boost for targeted banking queries
                    inst_tags = raw_row.get("institution_tags") or []
                    if isinstance(inst_tags, str):
                        try:
                            inst_tags = json.loads(inst_tags)
                        except Exception:
                            inst_tags = []
                    
                    inst_boost = 0.0
                    if target_institution:
                        if any(target_institution.lower() in t.lower() or t.lower() in target_institution.lower() for t in inst_tags):
                            inst_boost = 0.25
                        elif target_institution.lower() in content.lower():
                            inst_boost = 0.15

                    # Combined score
                    score = (0.45 * max(0.0, vec_sim)) + (0.40 * norm_fts) + (0.10 * tier_weight) + inst_boost + 0.05

                    scored_results.append({
                        "id": chunk_id,
                        "document_id": raw_row["document_id"],
                        "chunk_index": raw_row["chunk_index"],
                        "content": content,
                        "source": raw_row["source"],
                        "tier": tier,
                        "url": raw_row["url"],
                        "publish_date": raw_row["publish_date"],
                        "is_simulated": is_simulated,
                        "is_title_only": is_title_only,
                        "institution_tags": inst_tags,
                        "score": round(score, 4),
                        "vector_similarity": round(vec_sim, 4),
                        "fts_rank": round(fts_rank, 4),
                    })

                # Sort descending by final hybrid score
                scored_results.sort(key=lambda x: x["score"], reverse=True)
                return scored_results[:top_k]


    def get_stats(self) -> dict[str, Any]:
        """Returns database counts and health metrics."""
        with self.get_connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS doc_count FROM documents;")
            doc_count = cur.fetchone()["doc_count"]

            cur.execute("SELECT COUNT(*) AS chunk_count FROM document_chunks;")
            chunk_count = cur.fetchone()["chunk_count"]

            cur.execute("SELECT source, COUNT(*) AS count FROM documents GROUP BY source;")
            by_source = {row["source"]: row["count"] for row in cur.fetchall()}

        return {
            "total_documents": doc_count,
            "total_chunks": chunk_count,
            "documents_by_source": by_source,
        }

    def save_approval_item(self, post_id: str, payload: dict[str, Any], approval_status: str = "pending") -> None:
        """Persists or updates an analyzed post in the approval queue."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO approval_queue (post_id, payload, approval_status, updated_at)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (post_id) DO UPDATE SET
                        payload = EXCLUDED.payload,
                        approval_status = EXCLUDED.approval_status,
                        updated_at = CURRENT_TIMESTAMP;
                    """,
                    (post_id, json.dumps(payload), approval_status)
                )
            conn.commit()

    def list_approval_items(self, status: str | None = None) -> list[dict[str, Any]]:
        """Retrieves items from the approval queue table, ordered by newest first."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                if status:
                    cur.execute(
                        "SELECT payload, approval_status, rejection_reason, editor_notes FROM approval_queue WHERE approval_status = %s ORDER BY created_at DESC;",
                        (status,)
                    )
                else:
                    cur.execute(
                        "SELECT payload, approval_status, rejection_reason, editor_notes FROM approval_queue ORDER BY created_at DESC;"
                    )
                rows = cur.fetchall()

        items = []
        for r in rows:
            raw_payload = r["payload"]
            payload = json.loads(raw_payload) if isinstance(raw_payload, str) else dict(raw_payload)
            payload["approval_status"] = r["approval_status"]
            if r["rejection_reason"]:
                payload["rejection_reason"] = r["rejection_reason"]
            if r["editor_notes"]:
                payload["editor_notes"] = r["editor_notes"]
            items.append(payload)
        return items

    def update_approval_status(
        self,
        post_id: str,
        status: str,
        rejection_reason: str | None = None,
        editor_notes: str | None = None,
        edited_formal: str | None = None,
        edited_pidgin: str | None = None
    ) -> dict[str, Any] | None:
        """Updates the status and optional notes or edits of a staged post in the approval queue."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT payload FROM approval_queue WHERE post_id = %s FOR UPDATE;", (post_id,))
                row = cur.fetchone()
                if not row:
                    return None

                raw_payload = row["payload"]
                payload = json.loads(raw_payload) if isinstance(raw_payload, str) else dict(raw_payload)
                payload["approval_status"] = status
                if rejection_reason is not None:
                    payload["rejection_reason"] = rejection_reason
                if editor_notes is not None:
                    payload["editor_notes"] = editor_notes
                if edited_formal is not None:
                    if "response_draft" not in payload:
                        payload["response_draft"] = {}
                    payload["response_draft"]["formal_response"] = edited_formal
                if edited_pidgin is not None:
                    if "response_draft" not in payload:
                        payload["response_draft"] = {}
                    payload["response_draft"]["pidgin_response"] = edited_pidgin

                cur.execute(
                    """
                    UPDATE approval_queue
                    SET payload = %s,
                        approval_status = %s,
                        rejection_reason = COALESCE(%s, rejection_reason),
                        editor_notes = COALESCE(%s, editor_notes),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE post_id = %s;
                    """,
                    (json.dumps(payload), status, rejection_reason, editor_notes, post_id)
                )
            conn.commit()
        return payload

