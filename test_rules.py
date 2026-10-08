import json
import pytest
import os
from app.rules import compute_rule_score

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
