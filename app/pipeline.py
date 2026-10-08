import time
import uuid
import json
import logging
import threading
from collections import OrderedDict
from typing import Dict, Any, Optional, List
from fastapi import BackgroundTasks

from app.config import GEMINI_MODEL_ID
from app.extract import extract_indicators, normalize_text, hash_ioc
from app.rules import compute_rule_score
from app.gemma import classify_text_and_image
from app.dna import assign_campaign
from app.snow import insert_scan, insert_indicators

logger = logging.getLogger("kavach.pipeline")

# In-memory stores for fallback with LRU caps and thread safety
MEMORY_STORE_LOCK = threading.Lock()
MAX_MEMORY_SCANS = 10000
MAX_MEMORY_INDICATORS = 50000

MEMORY_STORE = {
    "scans": OrderedDict(),
    "indicators": OrderedDict(),
    "campaigns": {}
}

def get_seen_count(indicator_hash: str) -> int:
    with MEMORY_STORE_LOCK:
        return MEMORY_STORE["indicators"].get(indicator_hash, 0)

def increment_seen_count(indicator_hash: str):
    with MEMORY_STORE_LOCK:
        count = MEMORY_STORE["indicators"].get(indicator_hash, 0) + 1
        MEMORY_STORE["indicators"][indicator_hash] = count
        if len(MEMORY_STORE["indicators"]) > MAX_MEMORY_INDICATORS:
            MEMORY_STORE["indicators"].popitem(last=False)

def record_scan_in_memory(scan_id: str, scan_record: dict):
    with MEMORY_STORE_LOCK:
        MEMORY_STORE["scans"][scan_id] = scan_record
        if len(MEMORY_STORE["scans"]) > MAX_MEMORY_SCANS:
            MEMORY_STORE["scans"].popitem(last=False)

def sync_persist_to_snowflake(scan_record: dict, snowflake_indicators: List[dict]):
    """
    Persists scan and hashed indicators to Snowflake. Must never raise or crash the caller.
    """
    try:
        insert_scan(scan_record)
        if snowflake_indicators:
            insert_indicators(snowflake_indicators)
    except Exception as e:
        logger.warning("Snowflake background persistence failed: %s", e)

def run_scan(
    text: str,
    image_bytes: Optional[bytes] = None,
    mime_type: str = "image/png",
    lang: str = "en",
    background_tasks: Optional[BackgroundTasks] = None
) -> Dict[str, Any]:
    timings = {}
    
    # 1. Ingest
    t0 = time.time()
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
        gemma_result_str = classify_text_and_image(text=text, image_bytes=image_bytes, mime_type=mime_type)
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
    timings["explain"] = int((time.time() - t_classify) * 1000)
    
    # 5. Blend: Score calculation based on hashed IOC lookups
    seen_penalty = 0.0
    for k, v_list in indicators.items():
        if k in ("url", "phone", "upi", "email", "crypto", "domain"):
            for v in v_list:
                h = hash_ioc(v)
                seen_count = get_seen_count(h)
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
    primary_tactic = "UNKNOWN"
    if tactics and isinstance(tactics, list) and len(tactics) > 0:
        if isinstance(tactics[0], dict):
            primary_tactic = tactics[0].get("code", "UNKNOWN")
    campaign_info = assign_campaign(norm_text, primary_tactic, MEMORY_STORE["campaigns"])
    campaign_id = campaign_info["id"]
    variant_no = campaign_info["variant_no"]
    timings["dna"] = int((time.time() - t_dna) * 1000)
    
    # 8. Redact and store (Only hashed values enter memory store & Snowflake)
    t_store = time.time()
    scan_id = str(uuid.uuid4())
    
    out_indicators = []
    snowflake_indicators = []
    for k, v_list in indicators.items():
        for v in v_list:
            if k in ("url", "phone", "upi", "email", "crypto", "domain"):
                h = hash_ioc(v)
                increment_seen_count(h)
                seen_count = get_seen_count(h)
                masked_display = (v[:3] + "***") if len(v) > 3 else "***"
                out_indicators.append({
                    "type": k,
                    "display": masked_display,
                    "seen_before": seen_count
                })
                snowflake_indicators.append({
                    "scan_id": scan_id,
                    "ioc_type": k,
                    "ioc_hash": h,
                    "ioc_display": masked_display,
                    "tld": None
                })
            else:
                out_indicators.append({
                    "type": k,
                    "display": v,
                    "seen_before": 0
                })
            
    timings["store"] = int((time.time() - t_store) * 1000)
    
    scan_record = {
        "scan_id": scan_id,
        "verdict": verdict,
        "risk_score": risk_score,
        "confidence": gemma_confidence,
        "tactics": tactics,
        "indicators": out_indicators,
        "explanation": explanation,
        "actions": ["Do not click links.", "Report to bank.", "Block sender."],
        "campaign": {
            "id": campaign_id,
            "variant_no": variant_no,
            "first_seen": campaign_info.get("first_seen", "unknown"),
            "variants": campaign_info.get("variants", 1)
        },
        "lang": lang,
        "timings_ms": timings,
        "model": GEMINI_MODEL_ID
    }
    
    record_scan_in_memory(scan_id, scan_record)
    
    # Snowflake Persistence via BackgroundTasks
    if background_tasks:
        background_tasks.add_task(sync_persist_to_snowflake, scan_record, snowflake_indicators)
    else:
        sync_persist_to_snowflake(scan_record, snowflake_indicators)
        
    return scan_record
