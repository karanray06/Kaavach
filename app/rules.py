import json
import re
import os
import math
import unicodedata
from typing import Dict, List, Tuple

RULES_FILE = os.path.join(os.path.dirname(__file__), "rules_data.json")

def load_rules():
    with open(RULES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# Precompile regexes
RULES = load_rules()
for rule in RULES:
    rule["regex"] = re.compile(rule["pattern"], re.IGNORECASE)

def normalize_input(text: str) -> str:
    """Normalize text before rule matching: NFKC, strip zero-width, collapse spaced digits."""
    # Unicode NFKC normalization
    text = unicodedata.normalize("NFKC", text)
    # Strip zero-width characters
    text = re.sub(r'[\u200b\u200c\u200d\u200e\u200f\ufeff]', '', text)
    # Collapse spaced digits: "9 8 7 6" -> "9876"
    text = re.sub(r'(\d)\s+(?=\d)', r'\1', text)
    return text

def compute_rule_score(text: str) -> Tuple[float, List[Dict]]:
    """
    Computes a rule score (0 to 1) and returns a list of rule hits.
    Uses tanh saturation for gentler scoring.
    """
    text = normalize_input(text)
    raw_score = 0.0
    hits = []
    
    for rule in RULES:
        if rule["regex"].search(text):
            raw_score += rule["weight"]
            hits.append({
                "id": rule["id"],
                "name": rule["name"],
                "description": rule["description"]
            })
            
    # Saturate with tanh for smoother growth
    final_score = math.tanh(raw_score / 1.5)
    
    return final_score, hits
