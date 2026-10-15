"""
Unit and integration tests for snapshot export and load.
"""
import os
import tempfile

from memory.snapshot.snapshot_manager import SnapshotManager


def test_snapshot_export_and_content():
    manager = SnapshotManager()
    with tempfile.NamedTemporaryFile(suffix=".json.gz", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        exported_path = manager.export_snapshot(tmp_path)
        assert os.path.exists(exported_path)
        assert os.path.getsize(exported_path) > 1000 # Must contain data
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
