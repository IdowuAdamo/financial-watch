# Repository Cleanup Manifest (Staged for Review)

> [!IMPORTANT]
> **Status: PENDING USER APPROVAL**  
> In accordance with project governance rules, no files listed below have been deleted or moved. This manifest itemizes all temporary artifacts, exploratory scratch scripts, superseded ingestors, and cache directories staged for cleanup.

---

## 1. Scratch & Diagnostic Scripts
These scripts were created to inspect local binaries, test parsers, and diagnose raw web endpoints:

| File Path | Purpose / Category | Status | Proposed Action |
|---|---|---|---|
| `scratch/inspect_manual_files.py` | One-off PDF parser and byte inspector for manual uploads | Standalone Scratch | Delete upon approval |
| `scratch/test_ndic_parse.py` | Diagnostic test script for JS string literal unescaping | Standalone Scratch | Delete upon approval |
| `scratch/test_ndic_ingest.py` | Diagnostic text and unicode extraction script | Standalone Scratch | Delete upon approval |

---

## 2. Superseded & Legacy Network Scripts
These early development scripts either bypassed `ComplianceGate.fetch_url` using unmanaged `httpx.Client()` or have been completely superseded by `memory/ingestion.py`:

| File Path | Reason for Removal | Replacement |
|---|---|---|
| `memory/scripts/search_cbn_docs.py` | Unrouted HTTP client; exploratory title search | `memory/ingestion.py` (`ingest_cbn_title_only_evidence`) |
| `memory/scripts/find_stability_circulars.py` | Unrouted HTTP client; exploratory circular search | `memory/ingestion.py` |
| `memory/scripts/find_cbn_docs.py` | Unrouted HTTP client; raw document discovery | `memory/ingestion.py` |
| `memory/scripts/inspect_sitemaps.py` | One-off sitemap probe | `memory/compliance/robots.py` |
| `memory/scripts/run_phase1_ingestion.py` | Early procedural pipeline script | Unified CLI `python -m memory.cli ingest` |
| `memory/scripts/test_search.py` | Standalone hybrid search debug script | `tests/test_store.py` (`test_hybrid_search_scoring`) |

---

## 3. Temporary Probe & Discovery Artifacts

| File Path | Description | Proposed Action |
|---|---|---|
| `memory/manual/_phase1_download_results.json` | Network probe results from preliminary crawl attempts | Delete upon approval |
| `memory/manual/_probe_run_results.json` | Crawl status codes and bot-challenge diagnostics | Delete upon approval |

---

## 4. Build Caches & Test Runtime Artifacts
Handled via `.gitignore`:
- `.pytest_cache/`
- `**/__pycache__/`
- `frontend/.next/`
- `frontend/out/`

---

## Approval Checklist
- [ ] User approves deletion of Section 1 (Scratch scripts)
- [ ] User approves deletion of Section 2 (Superseded network scripts)
- [ ] User approves deletion of Section 3 (Temporary probe JSONs)
