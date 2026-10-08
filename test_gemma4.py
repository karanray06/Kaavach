import os
import pytest
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel

load_dotenv(override=True)

class VerificationSchema(BaseModel):
    is_scam: bool
    explanation: str

def run_model_check(model_id):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or api_key.startswith("="):
        print(f"Skipping {model_id} check: GEMINI_API_KEY not configured.")
        return
    client = genai.Client(api_key=api_key)
    print(f"Testing {model_id}...")
    try:
        response = client.models.generate_content(
            model=model_id,
            contents=["Analyze this image. Is it a scam?", types.Part.from_bytes(data=b"fakeimagebytes", mime_type="image/png")],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=VerificationSchema,
                temperature=0.0
            )
        )
        print(f"Success! {response.text}")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    run_model_check("gemma-4-31b-it")
    run_model_check("gemma-4-26b-a4b-it")
