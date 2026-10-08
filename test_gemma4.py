import os
import json
import pytest
from unittest.mock import MagicMock, patch
from pydantic import BaseModel

class VerificationSchema(BaseModel):
    is_scam: bool
    explanation: str

def test_model_check_mocked():
    """
    Tests model check with mocked google.genai so no test hits the network.
    """
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "is_scam": True,
        "explanation": "Mocked scam detection"
    })

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-mock-api-key"}):
        with patch("google.genai.Client", return_value=mock_client):
            from google import genai
            from google.genai import types

            client = genai.Client(api_key="test-mock-api-key")
            response = client.models.generate_content(
                model="gemma-4-31b-it",
                contents=["Analyze this image. Is it a scam?"],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=VerificationSchema,
                    temperature=0.0
                )
            )
            data = json.loads(response.text)
            assert data["is_scam"] is True
            assert data["explanation"] == "Mocked scam detection"
