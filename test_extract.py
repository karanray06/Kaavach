import json
import pytest
import os
import hmac
import hashlib
from app.extract import extract_indicators, normalize_text, hash_ioc

@pytest.fixture
def fixtures():
    with open(os.path.join(os.path.dirname(__file__), "fixtures", "messages.json"), "r", encoding="utf-8") as f:
        return json.load(f)

def test_extract_indicators(fixtures):
    for fix in fixtures:
        inds = extract_indicators(fix["text"])
        
        if fix["id"] == "scam_en_1":
            assert "sbi-kyc-update.example.invalid" in inds.get("domain", [])
            assert "9876543210" in inds.get("phone", [])
            
        elif fix["id"] == "scam_en_2":
            assert "customs-india@fakeupi" in inds.get("upi", [])
            
        elif fix["id"] == "scam_en_3":
            assert "+919999988888" in inds.get("phone", [])

def test_normalize_text(fixtures):
    for fix in fixtures:
        norm = normalize_text(fix["text"])
        if fix["id"] == "scam_en_1":
            assert "<URL>" in norm
            assert "<PHONE>" in norm
        elif fix["id"] == "scam_en_2":
            assert "<UPI>" in norm
            assert "<AMT>" in norm

def test_hash_ioc():
    h1 = hash_ioc("  +919876543210  ")
    h2 = hash_ioc("+919876543210")
    h3 = hash_ioc("+919876543211")
    
    assert len(h1) == 64
    assert h1 == h2  # Strips and lowercases
    assert h1 != h3  # Different IOC has different hash
    assert hash_ioc("") == ""

def test_phone_normalization_boundary():
    # Exactly 10 digits
    text_10 = "call me at 9876543210 now"
    assert "<PHONE>" in normalize_text(text_10)
    
    # Less than 10 digits (e.g. 6-digit OTP code)
    text_6 = "your verification code is 123456"
    norm_6 = normalize_text(text_6)
    assert "<PHONE>" not in norm_6
    assert "<N>" in norm_6  # Caught by digit run, not phone
