import json
import pytest
import os
from unittest.mock import patch
from app.rules import compute_rule_score
from app.pipeline import run_scan

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

def test_task_job_review_scam_rules():
    phrases = [
        "Please write Google reviews for our business",
        "Each review pays $10 instantly",
        "$50 per review for simple feedback",
        "Earn per task from home",
        "Join our Telegram job channel today",
        "Must send deposit to unlock tasks and withdraw"
    ]
    for p in phrases:
        score, hits = compute_rule_score(p)
        hit_ids = [h["id"] for h in hits]
        assert "R013" in hit_ids, f"Expected R013 to match '{p}'"
        assert score > 0.4

def test_ai_high_likelihood_forces_likely_scam_verdict():
    text = "We are Big Mover Company LLC. Your role is to write Google reviews for us. Each review pays $10. Can I share the links to the Google Doc with you?"
    
    mock_gemma_json = json.dumps({
        "is_scam_likelihood": 0.88,
        "tactics": [{"code": "TASK_SCAM", "evidence": "write Google reviews"}],
        "impersonated_entity_type": "employer",
        "channel_guess": "sms",
        "reasoning_short": "Task scam offering payment for fraudulent reviews.",
        "actions": ["Do not accept task offers from strangers", "Do not pay any deposit"]
    })

    with patch("app.pipeline.classify_text_and_image", return_value=mock_gemma_json):
        result = run_scan(text=text)
        assert result["verdict"] == "LIKELY_SCAM"
        assert result["confidence"] == 0.88
        assert result["ai_available"] is True

def test_ai_high_likelihood_forces_likely_scam_even_zero_rules():
    text = "An innocuous sounding text"
    mock_gemma_json = json.dumps({
        "is_scam_likelihood": 0.86,
        "tactics": [{"code": "SUSPICIOUS_LINK", "evidence": "link"}],
        "impersonated_entity_type": "unknown",
        "channel_guess": "unknown",
        "reasoning_short": "High probability scam",
        "actions": []
    })

    with patch("app.pipeline.compute_rule_score", return_value=(0.0, [])):
        with patch("app.pipeline.classify_text_and_image", return_value=mock_gemma_json):
            result = run_scan(text=text)
            assert result["verdict"] == "LIKELY_SCAM"
