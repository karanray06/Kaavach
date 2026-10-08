import hashlib
import datetime
import threading
from typing import Dict, Any, List

_DNA_LOCK = threading.Lock()

def simhash(text: str) -> int:
    """
    Computes a 64-bit simhash over 3-grams of words in the normalized text.
    """
    words = text.split()
    if not words:
        return 0
        
    # Generate 3-grams
    ngrams = []
    for i in range(max(1, len(words) - 2)):
        ngram = " ".join(words[i:i+3])
        ngrams.append(ngram)
        
    v = [0] * 64
    for ngram in ngrams:
        # Hash each ngram to a 64-bit int
        h = int(hashlib.md5(ngram.encode('utf-8')).hexdigest()[:16], 16)
        for i in range(64):
            bit = (h >> i) & 1
            if bit:
                v[i] += 1
            else:
                v[i] -= 1
                
    fingerprint = 0
    for i in range(64):
        if v[i] > 0:
            fingerprint |= (1 << i)
            
    return fingerprint

def hamming_distance(h1: int, h2: int) -> int:
    """
    Computes the Hamming distance between two 64-bit integers.
    """
    x = (h1 ^ h2) & ((1 << 64) - 1)
    return bin(x).count('1')

def compute_centroid_simhash(hashes: List[int]) -> int:
    """
    Recomputes the centroid simhash by bitwise majority vote over recent variants.
    """
    if not hashes:
        return 0
    v = [0] * 64
    for h in hashes:
        for i in range(64):
            if (h >> i) & 1:
                v[i] += 1
            else:
                v[i] -= 1
    centroid = 0
    for i in range(64):
        if v[i] >= 0:
            centroid |= (1 << i)
    return centroid

def assign_campaign(normalized_text: str, primary_tactic: str, store_campaigns: dict) -> dict:
    """
    Assigns the scan to a campaign or creates a new one with thread-safety and drift mitigation.
    Returns {"id": campaign_id, "variant_no": variant_no, "first_seen": ..., "variants": count}
    """
    h = simhash(normalized_text)
    
    with _DNA_LOCK:
        best_campaign = None
        best_dist = float('inf')
        
        # Match against centroid or any recent variant simhash to handle adversarial drift
        for cid, c_data in store_campaigns.items():
            if c_data.get("primary_tactic") == primary_tactic:
                centroid_dist = hamming_distance(h, c_data.get("centroid_simhash", 0))
                recent = c_data.get("recent_simhashes", [c_data.get("centroid_simhash", 0)])
                min_recent_dist = min(hamming_distance(h, r_h) for r_h in recent) if recent else centroid_dist
                effective_dist = min(centroid_dist, min_recent_dist)
                
                if effective_dist <= 12 and effective_dist < best_dist:
                    best_dist = effective_dist
                    best_campaign = cid
                    
        now_str = datetime.datetime.now().isoformat()

        if best_campaign:
            # Join existing campaign and update centroid via majority vote
            c_data = store_campaigns[best_campaign]
            c_data["variant_count"] += 1
            c_data["last_seen"] = now_str
            
            recent = c_data.setdefault("recent_simhashes", [c_data.get("centroid_simhash", h)])
            recent.append(h)
            if len(recent) > 20:
                recent.pop(0)
                
            c_data["centroid_simhash"] = compute_centroid_simhash(recent)
            
            return {
                "id": best_campaign,
                "variant_no": c_data["variant_count"],
                "first_seen": c_data["first_seen"],
                "variants": c_data["variant_count"]
            }
        else:
            # Create new campaign
            new_id = f"C-{len(store_campaigns) + 1:04d}"
            store_campaigns[new_id] = {
                "primary_tactic": primary_tactic,
                "centroid_simhash": h,
                "recent_simhashes": [h],
                "variant_count": 1,
                "first_seen": now_str,
                "last_seen": now_str
            }
            return {
                "id": new_id,
                "variant_no": 1,
                "first_seen": now_str,
                "variants": 1
            }
