"""
HTML Parser for regulatory circulars, news articles, and fact-check reports.
Cleans navigation, headers, footers, scripts, and extracts main semantic body.
"""
import re
from typing import Any

from bs4 import BeautifulSoup


class HTMLDocumentParser:
    """
    Cleans raw HTML into normalized plain text while extracting metadata.
    """
    @staticmethod
    def parse(html_content: str, base_url: str = "") -> dict[str, Any]:
        soup = BeautifulSoup(html_content, "html.parser")

        # Strip scripts, styles, iframes, nav, footer, headers
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "form"]):
            tag.decompose()

        # Extract title
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        elif soup.find("h1"):
            title = soup.find("h1").get_text().strip()

        # Extract meta description or date
        publish_date = None
        date_meta = soup.find("meta", property="article:published_time") or soup.find("meta", attrs={"name": "date"})
        if date_meta and date_meta.get("content"):
            publish_date = date_meta["content"].strip()

        # Extract main text
        main_content = soup.find("main") or soup.find("article") or soup.find("div", class_=re.compile(r"content|entry|post|body", re.IGNORECASE)) or soup.body
        
        if main_content:
            raw_text = main_content.get_text(separator="\n")
        else:
            raw_text = soup.get_text(separator="\n")

        # Clean text
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        cleaned_text = "\n\n".join(lines)

        return {
            "title": title or "Untitled Document",
            "publish_date": publish_date,
            "text": cleaned_text,
            "raw_length": len(html_content),
            "cleaned_length": len(cleaned_text),
        }
