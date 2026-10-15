"""
Unit tests for Nigerian Pidgin normalizer and bank alias resolution.
"""
from backend.app.core.pidgin_normalizer import PidginNormalizer


def test_pidgin_normalization_translations():
    pidgin_text = "Make una go withdraw all una money from Apex Bank! CBN don revoke their license sharp sharp!"
    normalized, has_pidgin = PidginNormalizer.normalize(pidgin_text)

    assert has_pidgin is True
    assert "urging depositors to withdraw funds" in normalized
    assert "has revoked" in normalized
    assert "immediately" in normalized
    # Check bank alias resolution
    assert "Apex Horizon Example Bank" in normalized

def test_code_mixed_entity_resolution():
    mixed_text = "Meridian Bank app no dey work since morning. Wahala dey!"
    normalized, has_pidgin = PidginNormalizer.normalize(mixed_text)

    assert has_pidgin is True
    assert "Meridian Mock Bank" in normalized
    assert "is experiencing an operational outage" in normalized
    assert "financial distress or insolvency" in normalized

def test_standard_english_preserved():
    standard_text = "The Central Bank of Nigeria published guidelines on recapitalization."
    normalized, has_pidgin = PidginNormalizer.normalize(standard_text)

    assert has_pidgin is False
    assert "Central Bank of Nigeria" in normalized
