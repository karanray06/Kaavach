import os
import json
import pytest
from unittest.mock import MagicMock, patch
from dotenv import load_dotenv

load_dotenv()
from app.gemma import classify_text_and_image

def test_gemma_classification_mocked():
    """
    Tests classify_text_and_image with mocked google.genai so no test hits the network.
    """
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "is_scam_likelihood": 0.95,
        "tactics": [{"code": "FAKE_KYC", "evidence": "urgent verification"}],
        "impersonated_entity_type": "bank",
        "channel_guess": "sms",
        "reasoning_short": "This message threatens bank blockage to steal credentials.",
        "actions": ["Do not click the link", "Contact your bank branch directly"]
    })

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-mock-api-key"}):
        with patch("google.genai.Client", return_value=mock_client) as mock_client_cls:
            result_str = classify_text_and_image(
                text="URGENT: Your SBI account will be blocked. Click here to update KYC: http://sbi-kyc.com",
                lang="en"
            )
            result = json.loads(result_str)
            assert result["is_scam_likelihood"] == 0.95
            assert result["tactics"][0]["code"] == "FAKE_KYC"
            assert "reasoning_short" in result
            mock_client.models.generate_content.assert_called_once()
            call_kwargs = mock_client.models.generate_content.call_args[1]
            contents = call_kwargs["contents"]
            assert "<UNTRUSTED_CONTENT>" in contents[0]
            assert "URGENT: Your SBI account will be blocked" in contents[0]
