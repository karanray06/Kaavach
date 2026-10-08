import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_MODEL_ID = os.environ.get("GEMINI_MODEL_ID", "gemini-3.8-flash")
