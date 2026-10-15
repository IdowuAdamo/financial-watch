"""
Knowledge Base Command Line Interface.
Supports ECS scheduled tasks, local setup, and snapshot export/load.
Usage:
  python -m memory.cli ingest
  python -m memory.cli load-snapshot
  python -m memory.cli export-snapshot
  python -m memory.cli status
"""
import json
import logging
import sys

from memory.ingestion import IngestionPipeline
from memory.snapshot.snapshot_manager import SnapshotManager
from memory.store.db import KnowledgeBaseStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("financial_watch.memory.cli")

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m memory.cli [ingest|load-snapshot|export-snapshot|status]")
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "ingest":
        logger.info("Executing full ingestion pipeline (ECS task / local)...")
        pipeline = IngestionPipeline()
        stats = pipeline.run_full_ingestion()
        print("\nIngestion Completed:")
        print(json.dumps(stats, indent=2))

    elif cmd == "load-snapshot":
        logger.info("Loading Knowledge Base snapshot into PostgreSQL...")
        manager = SnapshotManager()
        manager.load_snapshot()
        stats = KnowledgeBaseStore().get_stats()
        print("\nSnapshot Loaded Successfully:")
        print(json.dumps(stats, indent=2))

    elif cmd == "export-snapshot":
        logger.info("Exporting Knowledge Base snapshot from PostgreSQL...")
        manager = SnapshotManager()
        path = manager.export_snapshot()
        print(f"\nSnapshot exported to {path}")

    elif cmd == "status":
        stats = KnowledgeBaseStore().get_stats()
        print("\nKnowledge Base Database Status:")
        print(json.dumps(stats, indent=2))

    else:
        print(f"Unknown command: '{cmd}'. Supported: ingest, load-snapshot, export-snapshot, status")
        sys.exit(1)

if __name__ == "__main__":
    main()
