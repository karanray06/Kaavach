import os
import pytest
from dotenv import load_dotenv
load_dotenv()
from app.gemma import classify_text_and_image

def test_gemma_classification_skips_if_no_key():
    if not os.environ.get("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set")
    
    result = classify_text_and_image(text="URGENT: Your SBI account will be blocked. Click here to update KYC: http://sbi-kyc.com")
    assert "is_scam_likelihood" in result
    assert "tactics" in result
