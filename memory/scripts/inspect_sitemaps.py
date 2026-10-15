"""
Script to inspect live sitemaps and derive actual section allowlists and discover real official documents.
Uses our compliance gate User-Agent.
"""
import asyncio
from collections import Counter
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

USER_AGENT = "FinancialWatchBot/1.0 (+https://github.com/financial-watch/compliance-bot)"

async def inspect_sitemap(url: str, label: str):
    print("\n==========================================")
    print(f"Inspecting {label} at {url}...")
    headers = {"User-Agent": USER_AGENT, "Accept": "application/xml,text/xml,*/*"}
    
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            print(f"Status Code: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"Failed to fetch {url}: HTTP {resp.status_code}")
                return []

            content = resp.text
            soup = BeautifulSoup(content, "html.parser") # or xml
            locs = [loc.get_text().strip() for loc in soup.find_all("loc")]
            print(f"Found {len(locs)} total URLs in sitemap.")

            # Analyze path prefixes
            prefixes = Counter()
            for loc in locs:
                parsed = urlparse(loc)
                parts = [p for p in parsed.path.split("/") if p]
                if parts:
                    prefixes[f"/{parts[0]}/"] += 1
                    if len(parts) > 1:
                        prefixes[f"/{parts[0]}/{parts[1]}/"] += 1

            print(f"Top URL path prefixes found in {label}:")
            for prefix, count in prefixes.most_common(15):
                print(f"  {prefix:<30} : {count} URLs")

            sample_urls = locs[:10]
            print("Sample URLs:")
            for s in sample_urls:
                print(f"  {s}")

            return locs
    except Exception as e:
        print(f"Error inspecting {label}: {e}")
        return []

async def main():
    cbn_urls = await inspect_sitemap("https://www.cbn.gov.ng/sitemap.xml", "CBN")
    ndic_urls = await inspect_sitemap("https://ndic.gov.ng/sitemap.xml", "NDIC")
    fch_urls = await inspect_sitemap("https://factcheckhub.com/sitemap_index.xml", "FactCheckHub")

if __name__ == "__main__":
    asyncio.run(main())
