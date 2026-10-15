"""
Inspect CBN and FactCheckHub for live downloadable documents.
"""

import httpx
from bs4 import BeautifulSoup

USER_AGENT = "FinancialWatchBot/1.0 (+https://github.com/financial-watch/compliance-bot)"

def inspect_cbn():
    print("--- Inspecting CBN ---")
    with httpx.Client(timeout=20.0, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
        # Check allDocs.html
        resp = client.get("https://www.cbn.gov.ng/Documents/allDocs.html")
        print("allDocs status:", resp.status_code, "len:", len(resp.text))
        
        # Check what iframes or scripts exist
        soup = BeautifulSoup(resp.text, "html.parser")
        iframes = [i.get("src") for i in soup.find_all("iframe") if i.get("src")]
        scripts = [s.get("src") for s in soup.find_all("script") if s.get("src")]
        print("allDocs iframes:", iframes)
        print("allDocs scripts:", scripts[:5])

        # Also check circulars page
        resp_circ = client.get("https://www.cbn.gov.ng/Documents/circulars.html")
        soup_circ = BeautifulSoup(resp_circ.text, "html.parser")
        iframes_circ = [i.get("src") for i in soup_circ.find_all("iframe") if i.get("src")]
        print("circulars iframes:", iframes_circ)

        # Check home page press releases/news
        resp_home = client.get("https://www.cbn.gov.ng/")
        soup_home = BeautifulSoup(resp_home.text, "html.parser")
        news_links = []
        for a in soup_home.find_all("a"):
            href = a.get("href", "")
            text = a.get_text().strip()
            if any(k in href.lower() or k in text.lower() for k in ["circular", "press", "statement", "bank", "notice"]):
                if len(text) > 10:
                    news_links.append((text, href))
        print(f"CBN home news links found ({len(news_links)}):")
        for t, h in news_links[:10]:
            print(f"  {t[:60]} -> {h}")

def inspect_factcheckhub():
    print("\n--- Inspecting FactCheckHub ---")
    with httpx.Client(timeout=20.0, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
        # Check post-sitemap.xml
        resp = client.get("https://factcheckhub.com/post-sitemap.xml")
        print("post-sitemap status:", resp.status_code)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            locs = [loc.get_text().strip() for loc in soup.find_all("loc")]
            print(f"Total post URLs in post-sitemap: {len(locs)}")
            # Filter for banking / CBN / finance fact checks
            finance_checks = [u for u in locs if any(k in u.lower() for k in ["cbn", "bank", "naira", "ndic", "fraud", "scam", "grant", "account", "fund"])]
            print(f"Matching banking/finance fact checks ({len(finance_checks)}):")
            for u in finance_checks[:15]:
                print(f"  {u}")

if __name__ == "__main__":
    inspect_cbn()
    inspect_factcheckhub()
