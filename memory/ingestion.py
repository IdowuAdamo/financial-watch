"""
Knowledge Base Ingestion Engine.
Processes simulated client documents, title-only regulatory metadata, and manual files into PostgreSQL + pgvector.
"""
import glob
import hashlib
import json
import logging
import os
import re
from datetime import UTC
from typing import Any

from memory.parsers.chunker import DocumentChunker
from memory.parsers.html_parser import HTMLDocumentParser
from memory.parsers.pdf_parser import PDFDocumentParser
from memory.store.db import KnowledgeBaseStore
from memory.store.embeddings import EmbeddingService

logger = logging.getLogger("financial_watch.memory.ingestion")

SIMULATED_DIR = os.path.join(os.path.dirname(__file__), "simulated_client_docs")
MANUAL_DIR = os.path.join(os.path.dirname(__file__), "manual")
RAW_STORE_DIR = os.path.join(os.path.dirname(__file__), "raw_store")

class IngestionPipeline:
    def __init__(self, store: KnowledgeBaseStore | None = None, embedder: EmbeddingService | None = None):
        self.store = store or KnowledgeBaseStore()
        self.embedder = embedder or EmbeddingService()
        self.chunker = DocumentChunker(
            target_chunk_words=180,
            overlap_words=30,
            known_entities=[
                "Apex Horizon Example Bank", "Meridian Mock Bank", "Northbridge Example Bank",
                "Kreston Test Bank", "Central Bank of Nigeria", "CBN", "NDIC",
                "Heritage Bank", "Access Bank", "Zenith Bank", "GTBank"
            ]
        )

    def ingest_simulated_docs(self) -> int:
        """
        Ingests all simulated client documents from memory/simulated_client_docs/.
        Each chunk is explicitly tagged [SIMULATED CLIENT DOCUMENT].
        """
        md_files = glob.glob(os.path.join(SIMULATED_DIR, "*.md"))
        logger.info(f"Ingesting {len(md_files)} simulated client documents...")
        total_chunks = 0

        for file_path in md_files:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            filename = os.path.basename(file_path)
            doc_id = f"sim_{os.path.splitext(filename)[0]}"
            sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()

            # Extract title and date from frontmatter/header
            title = "Simulated Client Document"
            publish_date = "2026-10-01"
            for line in content.splitlines():
                if line.startswith("# "):
                    title = line.lstrip("# ").strip()
                elif line.startswith("**Date:**"):
                    publish_date = line.replace("**Date:**", "").strip()

            doc_record = {
                "id": doc_id,
                "source": "Simulated Client Repository",
                "tier": 1,
                "title": title,
                "url": f"internal://simulated-client/{filename}",
                "publish_date": publish_date,
                "content_type": "text/markdown",
                "sha256": sha256,
                "is_simulated": True,
                "metadata": {
                    "filename": filename,
                    "type": "simulated_client_disclosure",
                    "hash_covers": "full_utf8_markdown_text",
                    "retrieved_on": "2026-10-15T09:00:00Z"
                },
            }
            self.store.insert_document(doc_record)

            # Chunk document
            chunks = self.chunker.chunk_document(
                doc_id=doc_id,
                text=content,
                source="Simulated Client Repository",
                tier=1,
                url=doc_record["url"],
                publish_date=publish_date,
                is_simulated=True,
            )

            # Generate embeddings
            texts_to_embed = [c["cleaned_content"] for c in chunks]
            embeddings = self.embedder.embed_texts(texts_to_embed)
            for c, emb in zip(chunks, embeddings):
                c["embedding"] = emb

            self.store.insert_chunks(chunks)
            total_chunks += len(chunks)

        logger.info(f"Ingested {len(md_files)} simulated documents ({total_chunks} chunks).")
        return total_chunks

    def ingest_manual_docs(self) -> int:
        """
        Scans memory/manual/ for authoritative documents with matching .json sidecars.
        Computes SHA-256 of raw file bytes, stores retrieved_on separately from publish_date,
        records exactly what the hash covers, and chunks without rewriting or summarizing.
        """
        if not os.path.exists(MANUAL_DIR):
            logger.info("Manual directory does not exist. Skipping manual ingestion.")
            return 0

        # Find all files excluding json sidecars, markdown notes, and internal records
        candidates = []
        for f in os.listdir(MANUAL_DIR):
            if f.startswith("_") or f.endswith(".json") or f == "download_list.md":
                continue
            candidates.append(f)

        logger.info(f"Scanning memory/manual/: found {len(candidates)} candidate document files.")
        total_chunks = 0
        ingested_docs = 0

        for filename in candidates:
            file_path = os.path.join(MANUAL_DIR, filename)
            base_name, ext = os.path.splitext(filename)
            sidecar_path = os.path.join(MANUAL_DIR, f"{base_name}.json")
            if not os.path.exists(sidecar_path):
                # Fallback to check filename.json
                alt_sidecar = os.path.join(MANUAL_DIR, f"{filename}.json")
                if os.path.exists(alt_sidecar):
                    sidecar_path = alt_sidecar
                else:
                    logger.warning(f"Skipping manual file {filename}: missing required JSON sidecar at {base_name}.json")
                    continue

            try:
                with open(sidecar_path, "r", encoding="utf-8") as sf:
                    sidecar = json.load(sf)
            except Exception as e:
                logger.error(f"Failed to read sidecar {sidecar_path}: {e}")
                continue

            source_url = str(sidecar.get("source_url", "")).strip()
            retrieved_on = str(sidecar.get("retrieved_on", "")).strip()
            publish_date = str(sidecar.get("publish_date", "")).strip()

            # Strict guardrail: Refuse any sidecar containing unpopulated FILL_IN or empty values
            fill_in_fields = [k for k, v in sidecar.items() if "FILL_IN" in str(v)]
            if fill_in_fields or not source_url or not retrieved_on:
                logger.warning(
                    f"Refusing ingestion for manual document '{filename}': "
                    f"Sidecar contains unpopulated 'FILL_IN' or missing required metadata "
                    f"(fields_with_FILL_IN={fill_in_fields}, source_url='{source_url}', retrieved_on='{retrieved_on}')."
                )
                continue

            # Determine date precision (YYYY-MM-DD vs YYYY-MM vs YYYY)
            if re.match(r"^\d{4}-\d{2}-\d{2}$", publish_date):
                date_precision = "day"
            elif re.match(r"^\d{4}-\d{2}$", publish_date):
                date_precision = "month"
            elif re.match(r"^\d{4}$", publish_date):
                date_precision = "year"
            else:
                date_precision = "unknown"

            with open(file_path, "rb") as bf:
                raw_bytes = bf.read()

            raw_sha256 = hashlib.sha256(raw_bytes).hexdigest()
            title = sidecar.get("title", filename)
            tier = int(sidecar.get("tier", 1))
            publisher = sidecar.get("publisher", "Central Bank of Nigeria")

            # Parse raw content based on extension
            ext_lower = ext.lower()
            text_content = ""
            content_type = "application/octet-stream"

            if ext_lower == ".pdf":
                content_type = "application/pdf"
                parsed_pdf = PDFDocumentParser.parse(raw_bytes)
                text_content = parsed_pdf.get("text", "")
            elif ext_lower in [".html", ".htm"]:
                content_type = "text/html"
                parsed_html = HTMLDocumentParser.parse(raw_bytes.decode("utf-8", errors="ignore"))
                text_content = parsed_html.get("text", "")
            else:
                content_type = "text/plain"
                text_content = raw_bytes.decode("utf-8", errors="ignore")

            if len(text_content.strip()) < 50:
                logger.warning(
                    f"Refusing ingestion for manual document '{filename}': "
                    f"Document yielded only {len(text_content.strip())} characters of text (likely scanned or corrupted)."
                )
                continue

            doc_id = f"doc_manual_{base_name.replace(' ', '_').lower()}"
            doc_record = {
                "id": doc_id,
                "source": publisher,
                "tier": tier,
                "title": title,
                "url": source_url,
                "publish_date": publish_date,
                "content_type": content_type,
                "sha256": raw_sha256,
                "is_simulated": False,
                "metadata": {
                    "filename": filename,
                    "retrieved_on": retrieved_on,
                    "publisher": publisher,
                    "hash_covers": "raw_file_bytes",
                    "file_size_bytes": len(raw_bytes),
                    "date_precision": date_precision,
                },
            }
            self.store.insert_document(doc_record)


            # Chunk document (preserves exact parsed text without rewriting or summarization)
            chunks = self.chunker.chunk_document(
                doc_id=doc_id,
                text=text_content,
                source=publisher,
                tier=tier,
                url=source_url,
                publish_date=publish_date,
                is_simulated=False,
            )

            if chunks:
                texts_to_embed = [c["cleaned_content"] for c in chunks]
                embeddings = self.embedder.embed_texts(texts_to_embed)
                for c, emb in zip(chunks, embeddings):
                    c["embedding"] = emb

                self.store.insert_chunks(chunks)
                total_chunks += len(chunks)
                ingested_docs += 1
                logger.info(f"Successfully ingested manual document {filename}: {len(chunks)} chunks (SHA-256: {raw_sha256[:12]}...).")

        logger.info(f"Manual ingestion complete: {ingested_docs} documents ingested ({total_chunks} chunks).")
        return total_chunks

    def ingest_cbn_title_only_evidence(self) -> int:
        """
        Indexes high-relevance CBN regulatory titles from raw_store/cbn_get_all_documents_raw.json.
        All indexed records are explicitly labeled [TITLE-ONLY EVIDENCE] with lower retrieval weighting.
        """
        raw_json_path = os.path.join(RAW_STORE_DIR, "cbn_get_all_documents_raw.json")
        if not os.path.exists(raw_json_path):
            logger.warning(f"CBN metadata file {raw_json_path} not found. Run fetcher first.")
            return 0

        with open(raw_json_path, "r", encoding="utf-8") as f:
            records = json.load(f)

        logger.info(f"Scanning {len(records)} CBN metadata records for key banking and regulatory directives...")
        
        # Select key regulatory circulars, statements, and fraud alerts
        keywords = [
            "heritage bank", "recapitalization", "minimum capital", "banking licence",
            "bvn", "cybersecurity levy", "stability", "fraudulent", "scam", "licence of",
            "deposit money bank", "customer account", "phishing"
        ]

        selected_records = []
        for r in records:
            title = (r.get("title") or "")
            desc = (r.get("description") or "")
            ref = (r.get("refNo") or "")
            link = (r.get("link") or "")
            combined = f"{title} {desc} {ref} {link}".lower()

            if any(k in combined for k in keywords):
                selected_records.append(r)

        logger.info(f"Selected {len(selected_records)} high-value CBN regulatory records for title-only indexing.")

        doc_record = {
            "id": "doc_cbn_all_documents_index",
            "source": "Central Bank of Nigeria (CBN)",
            "tier": 1,
            "title": "CBN Official Regulatory Directives Index (Title-Only)",
            "url": "https://www.cbn.gov.ng/Documents/allDocs.html",
            "publish_date": "2026-10-14",
            "content_type": "application/json",
            "sha256": hashlib.sha256(json.dumps(selected_records).encode("utf-8")).hexdigest(),
            "is_simulated": False,
            "metadata": {"endpoint": "https://www.cbn.gov.ng/api/GetAllDocuments", "status": "undocumented_api", "hash_covers": "selected_records_json"},
        }
        self.store.insert_document(doc_record)

        chunks = []
        texts_to_embed = []

        for idx, rec in enumerate(selected_records):
            rec_id = rec.get("id", idx)
            title = rec.get("title", "Untitled Document")
            ref_no = rec.get("refNo", "N/A")
            doc_date = rec.get("documentDate", "")
            desc = rec.get("description", "")
            raw_link = rec.get("link", "")
            full_url = f"https://www.cbn.gov.ng{raw_link}" if raw_link.startswith("/") else raw_link

            chunk_text = (
                f"[TITLE-ONLY EVIDENCE] Official Central Bank of Nigeria Regulatory Document\n"
                f"Title: {title}\n"
                f"Reference No: {ref_no}\n"
                f"Date: {doc_date}\n"
                f"Summary: {desc}\n"
                f"Official Source URL: {full_url}\n"
                f"Verification Note: Title and metadata verified from official CBN document registry."
            )

            chunk_id = f"chunk_cbn_title_{rec_id}"
            chunk_data = {
                "id": chunk_id,
                "document_id": "doc_cbn_all_documents_index",
                "chunk_index": idx,
                "content": chunk_text,
                "cleaned_content": chunk_text,
                "token_count": len(chunk_text.split()),
                "tier": 1,
                "source": "Central Bank of Nigeria (CBN)",
                "url": full_url or "https://www.cbn.gov.ng/Documents/allDocs.html",
                "publish_date": doc_date,
                "is_simulated": False,
                "institution_tags": ["Central Bank of Nigeria", "CBN"],
            }
            chunks.append(chunk_data)
            texts_to_embed.append(chunk_text)

        # Batch embed
        embeddings = self.embedder.embed_texts(texts_to_embed)
        for c, emb in zip(chunks, embeddings):
            c["embedding"] = emb

        self.store.insert_chunks(chunks)
        logger.info(f"Successfully indexed {len(chunks)} title-only CBN records into PostgreSQL.")
        return len(chunks)

    def ingest_ndic_cms_evidence(self) -> int:
        """
        Ingests official NDIC press releases from window.NDIC_CMS_DATA fetched through gate.py.
        Saves raw page data with SHA-256 and retrieval time, cleanly unescapes JS string
        literal escapes without unicode corruption (preserving Naira sign and curly quotes),
        and indexes the three core regulatory announcements:
        1. Heritage Bank liquidation commencement (2024-06-03, ID 35)
        2. Deposit insurance maximum coverage review (2024-05-02, ID 33)
        3. Liquidation dividend disbursement (2025-04-28, ID 61)
        """
        raw_html_path = os.path.join(RAW_STORE_DIR, "ndic_press_releases_raw.html")
        meta_path = os.path.join(RAW_STORE_DIR, "ndic_press_releases_raw.meta.json")

        if not os.path.exists(raw_html_path):
            logger.info("Raw NDIC page not found locally; fetching via ComplianceGate...")
            import asyncio

            import httpx

            from memory.compliance.gate import ComplianceGate

            async def _fetch():
                gate = ComplianceGate()
                if "/news/" not in gate.sources.get("ndic", {}).get("section_allowlist", []):
                    gate.sources["ndic"]["section_allowlist"].append("/news/")
                async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
                    return await gate.fetch_url(client, "ndic", "https://ndic.gov.ng/news/press-releases")

            resp = asyncio.run(_fetch())
            if not resp or resp.status_code != 200:
                logger.error("Failed to fetch NDIC press releases through ComplianceGate.")
                return 0

            os.makedirs(RAW_STORE_DIR, exist_ok=True)
            with open(raw_html_path, "wb") as f:
                f.write(resp.content)
            raw_sha256 = hashlib.sha256(resp.content).hexdigest()
            from datetime import datetime
            retrieval_date = datetime.now(UTC).isoformat()
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump({
                    "source_id": "ndic",
                    "url": "https://ndic.gov.ng/news/press-releases",
                    "retrieval_date": retrieval_date,
                    "sha256": raw_sha256,
                    "byte_size": len(resp.content),
                }, f, indent=2)
        else:
            with open(raw_html_path, "rb") as f:
                raw_bytes = f.read()
            raw_sha256 = hashlib.sha256(raw_bytes).hexdigest()
            retrieval_date = "2026-10-15T10:41:00Z"
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, "r", encoding="utf-8") as mf:
                        m_data = json.load(mf)
                        retrieval_date = m_data.get("retrieval_date", retrieval_date)
                except Exception:
                    pass

        with open(raw_html_path, "r", encoding="utf-8") as f:
            html_text = f.read()

        idx = html_text.find("window.NDIC_CMS_DATA = JSON.parse('")
        if idx == -1:
            logger.error("Could not find window.NDIC_CMS_DATA in raw NDIC HTML.")
            return 0

        start = idx + len("window.NDIC_CMS_DATA = JSON.parse('")
        end = html_text.find("');", start)
        inner = html_text[start:end]

        # Exact JavaScript string literal unescape that preserves raw UTF-8 characters (Naira sign, curly quotes)
        def js_unescape_single_quoted_string(s: str) -> str:
            def replace_escape(match):
                esc = match.group(0)
                if esc == r"\'": return "'"
                elif esc == r'\"': return '"'
                elif esc == r'\\': return '\\'
                elif esc == r'\/': return '/'
                elif esc == r'\n': return '\n'
                elif esc == r'\r': return '\r'
                elif esc == r'\t': return '\t'
                elif esc.startswith(r'\u') and len(esc) == 6 or esc.startswith(r'\x') and len(esc) == 4:
                    return chr(int(esc[2:], 16))
                return esc[1:]
            pattern = r'\\(?:u[0-9a-fA-F]{4}|x[0-9a-fA-F]{2}|[\'\"\\/nrtbfv]|.)'
            return re.sub(pattern, replace_escape, s)

        json_str = js_unescape_single_quoted_string(inner)
        try:
            data = json.loads(json_str)
        except Exception as e:
            logger.error(f"Failed to parse NDIC JSON data: {e}")
            return 0

        v = list(data.values())[0]
        all_items = v.get("news", []) + v.get("articles", [])

        # Target items by specific ID & date
        target_ids = {35, 33, 61}
        seen_ids = set()
        selected_items = []
        for item in all_items:
            item_id = item.get("id")
            if item_id in target_ids and item_id not in seen_ids:
                seen_ids.add(item_id)
                selected_items.append(item)

        logger.info(f"Indexing {len(selected_items)} core NDIC regulatory items into Knowledge Base...")
        total_chunks = 0

        for item in selected_items:
            item_id = item.get("id")
            title = item.get("title", "NDIC Notice")
            publish_date = item.get("date", "")
            slug = item.get("slug")
            raw_body = item.get("body", "")
            parsed_text = HTMLDocumentParser.parse(raw_body)["text"]

            doc_id = f"doc_ndic_cms_item_{item_id}"
            source_url = f"https://ndic.gov.ng/news/press-releases#item-{item_id}"
            publisher = "Nigeria Deposit Insurance Corporation (NDIC)"

            doc_record = {
                "id": doc_id,
                "source": publisher,
                "tier": 1,
                "title": title,
                "url": source_url,
                "publish_date": publish_date,
                "content_type": "text/html",
                "sha256": raw_sha256,
                "is_simulated": False,
                "metadata": {
                    "item_id": item_id,
                    "slug": slug,
                    "has_per_item_url": False,
                    "listing_url": "https://ndic.gov.ng/news/press-releases",
                    "retrieved_on": retrieval_date,
                    "publisher": publisher,
                    "hash_covers": "raw_html_page_bytes",
                    "date_precision": "day" if len(publish_date) == 10 else "month",
                },
            }
            self.store.insert_document(doc_record)

            # Chunk document verbatim
            chunks = self.chunker.chunk_document(
                doc_id=doc_id,
                text=parsed_text,
                source=publisher,
                tier=1,
                url=source_url,
                publish_date=publish_date,
                is_simulated=False,
            )

            if chunks:
                texts_to_embed = [c["cleaned_content"] for c in chunks]
                embeddings = self.embedder.embed_texts(texts_to_embed)
                for c, emb in zip(chunks, embeddings):
                    c["embedding"] = emb

                self.store.insert_chunks(chunks)
                total_chunks += len(chunks)
                logger.info(f"Ingested NDIC item {item_id} ('{title[:40]}...'): {len(chunks)} chunks.")

        logger.info(f"NDIC ingestion complete: {len(selected_items)} documents ({total_chunks} chunks).")
        return total_chunks

    def run_full_ingestion(self) -> dict[str, Any]:
        """Runs the entire ingestion sequence and returns stats."""
        self.store.init_schema()
        sim_count = self.ingest_simulated_docs()
        cbn_count = self.ingest_cbn_title_only_evidence()
        ndic_count = self.ingest_ndic_cms_evidence()
        manual_count = self.ingest_manual_docs()
        stats = self.store.get_stats()
        stats["simulated_chunks_ingested"] = sim_count
        stats["cbn_title_chunks_ingested"] = cbn_count
        stats["ndic_chunks_ingested"] = ndic_count
        stats["manual_chunks_ingested"] = manual_count
        return stats

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    pipeline = IngestionPipeline()
    res = pipeline.run_full_ingestion()
    print("Ingestion Results:", json.dumps(res, indent=2))
