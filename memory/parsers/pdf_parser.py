"""
PDF Parser for official regulatory circulars, bank annual reports, and directives.
Uses pypdf to extract text page by page with metadata extraction.
"""
import io
from typing import Any

import pypdf


class PDFDocumentParser:
    """
    Parses PDF bytes into normalized text and page metadata.
    """
    @staticmethod
    def parse(pdf_bytes: bytes) -> dict[str, Any]:
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        num_pages = len(reader.pages)
        
        extracted_pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                extracted_pages.append(f"--- Page {i+1} ---\n" + text.strip())

        full_text = "\n\n".join(extracted_pages)
        
        # Extract metadata
        meta = reader.metadata or {}
        title = meta.get("/Title") or ""
        creator = meta.get("/Creator") or ""
        creation_date = str(meta.get("/CreationDate", ""))

        return {
            "title": str(title) if title else "Official Regulatory Document",
            "publish_date": creation_date if creation_date else None,
            "creator": str(creator),
            "num_pages": num_pages,
            "text": full_text,
            "raw_length": len(pdf_bytes),
            "cleaned_length": len(full_text),
        }
