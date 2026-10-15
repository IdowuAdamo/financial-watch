"""
Filter CBN official documents from GetAllDocuments for banking stability, circulars, and license lists.
"""
import json

import httpx

USER_AGENT = "FinancialWatchBot/1.0 (+https://github.com/financial-watch/compliance-bot)"

def search_cbn_docs():
    with httpx.Client(timeout=30.0, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
        resp = client.get("https://www.cbn.gov.ng/api/GetAllDocuments")
        if resp.status_code != 200:
            print("Failed with status:", resp.status_code)
            return

        docs = resp.json()
        print(f"Total CBN official documents retrieved: {len(docs)}")

        # Print fields of the first document
        if docs:
            print("Sample doc keys:", list(docs[0].keys()))
            print("Sample doc:", json.dumps(docs[0], indent=2))

        # Look for documents with keywords: bank, license, stability, revocation, fraud, circular
        keywords = ["stability", "license", "licence", "revocation", "fraud", "deposit", "safe", "scam"]
        matches = []
        for d in docs:
            title = (d.get("title") or "").lower()
            desc = (d.get("description") or "").lower()
            ref = (d.get("refNo") or "").lower()
            if any(k in title or k in desc or k in ref for k in keywords):
                matches.append(d)

        print(f"\nMatching regulatory documents found: {len(matches)}")
        for m in matches[:15]:
            print(f"- ID: {m.get('id')} | Ref: {m.get('refNo')} | Date: {m.get('docDate') or m.get('dateCreated')} | Title: {m.get('title')}")
            if "docPath" in m or "fileName" in m or "link" in m:
                path = m.get("docPath") or m.get("fileName") or m.get("link")
                print(f"  Path: {path}")

if __name__ == "__main__":
    search_cbn_docs()
