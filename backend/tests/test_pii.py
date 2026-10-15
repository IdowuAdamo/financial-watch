"""
Unit tests for PII redaction and collision resolution.
Ensures 11-digit Nigerian mobile numbers (0803...) are NOT misclassified as BVN.
"""
from backend.app.core.pii import PIIRedactor


def test_nigerian_phone_number_redaction():
    text = "Please call customer support on 08031234567 or international line +2348029876543."
    redacted, stats = PIIRedactor.redact(text)
    
    assert "08031234567" not in redacted
    assert "+2348029876543" not in redacted
    assert "[REDACTED_PHONE]" in redacted
    assert stats["phone_count"] == 2
    assert stats["bvn_count"] == 0 # Crucial: Local phone numbers must NOT be counted as BVN!

def test_contextual_bvn_redaction():
    text = "Send your BVN: 22233344455 and email to agent@scam.ng to link your account."
    redacted, stats = PIIRedactor.redact(text)
    
    assert "22233344455" not in redacted
    assert "[REDACTED_BVN]" in redacted
    assert "[REDACTED_EMAIL]" in redacted
    assert stats["bvn_count"] == 1
    assert stats["email_count"] == 1

def test_nuban_redaction():
    text = "Transfer N50,000 to account 0123456789 at First Bank."
    redacted, stats = PIIRedactor.redact(text)
    
    assert "0123456789" not in redacted
    assert "[REDACTED_NUBAN]" in redacted
    assert stats["nuban_count"] == 1
