import json
import pytest
import os
from app.rules import compute_rule_score

@pytest.fixture
def fixtures():
    with open(os.path.join(os.path.dirname(__file__), "fixtures", "messages.json"), "r", encoding="utf-8") as f:
        return json.load(f)

def test_rules(fixtures):
    for fix in fixtures:
        score, hits = compute_rule_score(fix["text"])
        
        if fix["id"] == "scam_en_1":
            assert score > 0
            hit_ids = [h["id"] for h in hits]
            assert "R001" in hit_ids # urgency
        
        if fix["id"] == "benign_en_2":
            assert score == 0.0 # Lunch meeting shouldn't trigger rules

def test_shortened_url_without_protocol():
    text = "Suspicious login detected. Click tinyurl.com/bank-sec to unlock account"
    score, hits = compute_rule_score(text)
    hit_ids = [h["id"] for h in hits]
    assert "R006" in hit_ids
    assert score > 0.25

def test_otp_theft_and_kyc_rule():
    text = "Do not share your OTP 482910 with anyone. Bank executive calling for KYC verification"
    score, hits = compute_rule_score(text)
    hit_ids = [h["id"] for h in hits]
    assert "R003" in hit_ids
    assert score >= 0.40

def test_electricity_disconnection_rule():
    text = "Your electricity will be disconnected tonight. Call officer at 9876543210"
    score, hits = compute_rule_score(text)
    hit_ids = [h["id"] for h in hits]
    assert "R002" in hit_ids
    assert score >= 0.40
