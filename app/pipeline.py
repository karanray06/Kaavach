import time
import uuid
import json
from typing import Dict, Any, Optional
from app.extract import extract_indicators, normalize_text
from app.rules import compute_rule_score
from app.gemma import classify_text_and_image
from app.dna import assign_campaign

# In-memory stores for fallback
MEMORY_STORE = {
    "scans": [],
    "indicators": {},
    "campaigns": {}
}

def get_seen_count(indicator_value: str) -> int:
    return MEMORY_STORE["indicators"].get(indicator_value, 0)

def increment_seen_count(indicator_value: str):
    MEMORY_STORE["indicators"][indicator_value] = MEMORY_STORE["indicators"].get(indicator_value, 0) + 1

def run_scan(text: str, image_bytes: Optional[bytes] = None, lang: str = "en") -> Dict[str, Any]:
    timings = {}
    
    # 1. Ingest
    t0 = time.time()
    # Image decoding is stubbed here if we had actual decoding, currently just passing bytes
    timings["ingest"] = int((time.time() - t0) * 1000)
    
    # 2. Extract
    t1 = time.time()
    indicators = extract_indicators(text)
    timings["extract"] = int((time.time() - t1) * 1000)
    
    # 3. Rules
    t2 = time.time()
    rule_score, rule_hits = compute_rule_score(text)
    timings["rules"] = int((time.time() - t2) * 1000)
    
    # 4. Classify & 6. Explain
    t3 = time.time()
    try:
        gemma_result_str = classify_text_and_image(text=text, image_bytes=image_bytes)
        gemma_result = json.loads(gemma_result_str)
        gemma_confidence = float(gemma_result.get("is_scam_likelihood", 0.0))
        tactics = gemma_result.get("tactics", [])
        explanation = gemma_result.get("reasoning_short", "No reasoning provided.")
    except Exception as e:
        gemma_confidence = 0.0
        tactics = []
        explanation = f"Error calling Gemma: {str(e)}"
    
    t_classify = time.time()
    timings["classify"] = int((t_classify - t3) * 1000)
    timings["explain"] = int((time.time() - t_classify) * 1000) # Actually explain happens in the same call in this design
    
    # 5. Blend
    seen_penalty = 0.0
    for k, v_list in indicators.items():
        for v in v_list:
            seen_count = get_seen_count(v)
            if seen_count > 0:
                seen_penalty += 0.05 * seen_count
                
    risk_score = 0.4 * rule_score + 0.6 * gemma_confidence + seen_penalty
    risk_score = min(risk_score, 1.0)
    
    if risk_score < 0.35:
        verdict = "NO_RED_FLAGS"
    elif risk_score < 0.65:
        verdict = "SUSPICIOUS"
    else:
        verdict = "LIKELY_SCAM"
        
    # 7. DNA
    t_dna = time.time()
    norm_text = normalize_text(text)
    # Determine primary tactic for campaign clustering
    primary_tactic = "UNKNOWN"
    if tactics and isinstance(tactics, list) and len(tactics) > 0:
        if isinstance(tactics[0], dict):
            primary_tactic = tactics[0].get("code", "UNKNOWN")
    campaign_info = assign_campaign(norm_text, primary_tactic, MEMORY_STORE["campaigns"])
    campaign_id = campaign_info["id"]
    variant_no = campaign_info["variant_no"]
    
    # 8. Redact and store
    t_store = time.time()
    scan_id = str(uuid.uuid4())
    
    # Update memory store
    for k, v_list in indicators.items():
        for v in v_list:
            increment_seen_count(v)
            
    timings["store"] = int((time.time() - t_store) * 1000)
    
    # Formatting output indicators
    out_indicators = []
    for k, v_list in indicators.items():
        for v in v_list:
            out_indicators.append({
                "type": k,
                "display": (v[:3] + "***") if len(v) > 3 else "***",
                "seen_before": get_seen_count(v)
            })
            
    return {
        "scan_id": scan_id,
        "verdict": verdict,
        "risk_score": risk_score,
        "confidence": gemma_confidence,
        "tactics": tactics,
        "indicators": out_indicators,
        "explanation": explanation,
        "actions": ["Do not click links.", "Report to bank.", "Block sender."],
        "campaign": {"id": campaign_id, "variant_no": variant_no, "first_seen": campaign_info.get("first_seen", "unknown"), "variants": campaign_info.get("variants", 1)},
        "lang": lang,
        "timings_ms": timings,
        "model": "gemini-3.1-pro-preview"
    }
