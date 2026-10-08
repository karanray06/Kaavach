import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel

load_dotenv(override=True)

class TestSchema(BaseModel):
    is_scam: bool
    explanation: str

def test_model(model_id):
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    print(f"Testing {model_id}...")
    try:
        response = client.models.generate_content(
            model=model_id,
            contents=["Analyze this image. Is it a scam?", types.Part.from_bytes(data=b"fakeimagebytes", mime_type="image/png")],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=TestSchema,
                temperature=0.0
            )
        )
        print(f"Success! {response.text}")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test_model("gemma-4-31b-it")
    test_model("gemma-4-26b-a4b-it")
