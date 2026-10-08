import json
import re
import os
from typing import Dict, List, Tuple

RULES_FILE = os.path.join(os.path.dirname(__file__), "rules_data.json")

def load_rules():
    with open(RULES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# Precompile regexes
RULES = load_rules()
for rule in RULES:
    rule["regex"] = re.compile(rule["pattern"], re.IGNORECASE)

def compute_rule_score(text: str) -> Tuple[float, List[Dict]]:
    """
    Computes a rule score (0 to 1) and returns a list of rule hits.
    """
    score = 0.0
    hits = []
    
    for rule in RULES:
        if rule["regex"].search(text):
            score += rule["weight"]
            hits.append({
                "id": rule["id"],
                "name": rule["name"],
                "description": rule["description"]
            })
            
    # Cap score at 1.0
    final_score = min(score, 1.0)
    
    return final_score, hits
