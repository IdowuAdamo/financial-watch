"""
Nigerian Pidgin to Standard English Normalizer and Entity Resolution Engine.
Translates conversational Pidgin and code-mixed expressions into search-optimized terms
for hybrid knowledge base retrieval while preserving the original verbatim text for display.
"""
import re

# Nigerian Pidgin translation dictionary for financial topics
PIDGIN_NORMALIZATION_MAP = {
    # Actions & verbs
    r"\bdon\s+revoke\b": "has revoked",
    r"\bdon\s+withdraw\b": "has withdrawn",
    r"\bdon\s+close\b": "has closed",
    r"\bdon\s+cast\b": "has collapsed or failed",
    r"\be\s+don\s+cast\b": "it has collapsed or failed",
    r"\bmake\s+una\s+(?:go\s+)?withdraw\b": "urging depositors to withdraw funds",
    r"\bmake\s+una\s+sharp\s+sharp\b": "urgently and immediately",
    r"\bsharp\s+sharp\b": "immediately",
    r"\bwahala\s+dey\b": "there is financial distress or insolvency",
    r"\bno\s+dey\s+work\b": "is experiencing an operational outage",
    r"\bdem\s+say\b": "rumours allege that",
    r"\bdey\s+hold\b": "is withholding",
    r"\bdey\s+chop\s+money\b": "is misappropriating customer funds",
    r"\bno\s+fit\b": "is unable to",
    r"\bna\s+scam\b": "is a fraudulent scheme",
    r"\buna\s+go\s+lose\b": "depositors will lose",
    r"\bwetin\s+dey\s+happen\b": "what is happening with",
    r"\bno\s+leave\s+your\s+money\b": "do not leave your deposits",
    
    # Financial terms & vernacular
    r"\bkudi\b": "money",
    r"\bowo\b": "money",
    r"\begunje\b": "bribe or illegal fee",
    r"\brank\s+and\s+file\b": "general public",
    r"\bajebutter\b": "wealthy",
}

# Bank and regulator entity mappings
ENTITY_ALIAS_MAP = {
    r"\bapex\s+bank\b": "Apex Horizon Example Bank",
    r"\bapex\s+horizon\b": "Apex Horizon Example Bank",
    r"\bmeridian\s+bank\b": "Meridian Mock Bank",
    r"\bmeridian\s+mock\b": "Meridian Mock Bank",
    r"\bnorthbridge\s+bank\b": "Northbridge Example Bank",
    r"\bnorthbridge\s+example\b": "Northbridge Example Bank",
    r"\bkreston\s+bank\b": "Kreston Test Bank",
    r"\bgtb\b": "Guaranty Trust Bank",
    r"\bgtbank\b": "Guaranty Trust Bank",
    r"\bzenith\b": "Zenith Bank",
    r"\baccess\b": "Access Bank",
    r"\bcbn\b": "Central Bank of Nigeria",
    r"\bndic\b": "Nigeria Deposit Insurance Corporation",
}

class PidginNormalizer:
    """
    Normalizes Nigerian Pidgin expressions and resolves institution aliases.
    """
    @staticmethod
    def normalize(text: str) -> tuple[str, bool]:
        """
        Translates Pidgin tokens and entity aliases into normalized search query text.
        Returns: (normalized_text, has_pidgin_tokens: bool)
        """
        normalized = text
        pidgin_detected = False

        # Apply Pidgin vocabulary replacements
        for pattern, replacement in PIDGIN_NORMALIZATION_MAP.items():
            if re.search(pattern, normalized, re.IGNORECASE):
                pidgin_detected = True
                normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)

        # Apply Entity Alias replacements
        for pattern, replacement in ENTITY_ALIAS_MAP.items():
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)

        # Clean multiple spaces
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized, pidgin_detected
