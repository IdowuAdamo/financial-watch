"""
Search and list specific key official circulars in the CBN document repository.
"""

import httpx

USER_AGENT = "FinancialWatchBot/1.0 (+https://github.com/financial-watch/compliance-bot)"

def find_stability_and_license_docs():
    with httpx.Client(timeout=30.0, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
        resp = client.get("https://www.cbn.gov.ng/api/GetAllDocuments")
        docs = resp.json()
        print(f"Total docs: {len(docs)}")

        targets = []
        for d in docs:
            title = (d.get("title") or "")
            desc = (d.get("description") or "")
            ref = (d.get("refNo") or "")
            full = f"{title} {desc} {ref}".lower()
            
            # Check for high-relevance regulatory documents
            if any(term in full for term in [
                "recapitalization", "banking system remains safe", "heritage bank",
                "revocation of licence", "revocation of license", "stability of the banking",
                "customer service", "unauthorised debit", "cybersecurity levy",
                "scam", "fraudulent", "bvn", "unlicensed", "phishing"
            ]):
                targets.append(d)

        print(f"Found {len(targets)} highly relevant target circulars/press releases:")
        for t in targets[:25]:
            print(f"- ID: {t.get('id')} | Date: {t.get('documentDate')} | Title: {t.get('title')}")
            print(f"  Link: {t.get('link')}")

if __name__ == "__main__":
    find_stability_and_license_docs()
