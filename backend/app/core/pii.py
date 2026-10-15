"""
PII Redaction Service.
Safely masks Nigerian telephone numbers, Bank Verification Numbers (BVN), NUBAN account numbers, and emails.
Corrects the regex collision between 11-digit BVNs and 11-digit Nigerian mobile numbers (0803...).
"""
import re

# Nigerian telecom mobile prefix check: starts with 070, 080, 081, 090, 091 followed by 8 digits
PHONE_LOCAL_REGEX = re.compile(r"\b(0[789][01]\d{8})\b")
PHONE_INTL_REGEX = re.compile(r"\b(?:\+234|234)[-\s]?([789][01]\d{8})\b")

# Contextual BVN: 11 digits preceded by BVN-related keywords
BVN_CONTEXT_REGEX = re.compile(r"(?i)\b(?:bvn|bank\s+verification\s+number|verification\s+no|bvn\s+is|bvn\s*:)\s*[:#-]?\s*(\d{11})\b")

# Generic 11-digit numbers that DO NOT begin with Nigerian telecom prefixes (070, 080, 081, 090, 091)
BVN_NON_PHONE_REGEX = re.compile(r"\b([1-9]\d{10})\b")

# Contextual NUBAN account numbers: 10 digits preceded by banking account keywords
NUBAN_CONTEXT_REGEX = re.compile(r"(?i)\b(?:acct|account|nuban|acc|acct\s+no|account\s+number)\s*[:#-]?\s*(\d{10})\b")

# Email regex
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")

class PIIRedactor:
    """
    Sanitizes untrusted text to protect personally identifiable information.
    """
    @staticmethod
    def redact(text: str) -> tuple[str, dict]:
        redacted = text
        stats = {"bvn_count": 0, "phone_count": 0, "nuban_count": 0, "email_count": 0}

        # 1. First, catch contextual BVN to ensure explicit BVN labels are redacted as BVN
        def replace_bvn_context(match):
            stats["bvn_count"] += 1
            full = match.group(0)
            digits = match.group(1)
            return full.replace(digits, "[REDACTED_BVN]")

        redacted = BVN_CONTEXT_REGEX.sub(replace_bvn_context, redacted)

        # 2. Mask Nigerian international phone numbers (+234 803 123 4567)
        def replace_phone_intl(match):
            stats["phone_count"] += 1
            return "[REDACTED_PHONE]"

        redacted = PHONE_INTL_REGEX.sub(replace_phone_intl, redacted)

        # 3. Mask Nigerian local phone numbers (0803 123 4567)
        def replace_phone_local(match):
            stats["phone_count"] += 1
            return "[REDACTED_PHONE]"

        redacted = PHONE_LOCAL_REGEX.sub(replace_phone_local, redacted)

        # 4. Mask remaining 11-digit numbers not matching phone format as potential BVN
        def replace_bvn_raw(match):
            stats["bvn_count"] += 1
            return "[REDACTED_BVN]"

        redacted = BVN_NON_PHONE_REGEX.sub(replace_bvn_raw, redacted)

        # 5. Mask contextual NUBAN account numbers (10 digits)
        def replace_nuban(match):
            stats["nuban_count"] += 1
            full = match.group(0)
            digits = match.group(1)
            return full.replace(digits, "[REDACTED_NUBAN]")

        redacted = NUBAN_CONTEXT_REGEX.sub(replace_nuban, redacted)

        # 6. Mask emails
        def replace_email(match):
            stats["email_count"] += 1
            return "[REDACTED_EMAIL]"

        redacted = EMAIL_REGEX.sub(replace_email, redacted)

        return redacted, stats
