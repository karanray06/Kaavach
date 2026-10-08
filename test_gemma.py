import os
import pytest
from dotenv import load_dotenv
load_dotenv()
from app.gemma import classify_text_and_image

def test_gemma_classification_skips_if_no_key():
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key or key.startswith("=") or key == "your_gemini_api_key_here":
        pytest.skip("GEMINI_API_KEY not set or placeholder")
    
    try:
        result = classify_text_and_image(text="URGENT: Your SBI account will be blocked. Click here to update KYC: http://sbi-kyc.com")
        assert "is_scam_likelihood" in result
        assert "tactics" in result
    except Exception as e:
        if "API_KEY_INVALID" in str(e) or "400" in str(e) or "INVALID_ARGUMENT" in str(e):
            pytest.skip(f"GEMINI_API_KEY could not authenticate: {e}")
        raise
