import json
import pytest
import os
from app.extract import extract_indicators, normalize_text

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
