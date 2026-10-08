import hashlib

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

def assign_campaign(normalized_text: str, primary_tactic: str, store_campaigns: dict) -> dict:
    """
    Assigns the scan to a campaign or creates a new one.
    Returns {"id": campaign_id, "variant_no": variant_no, "first_seen": ..., "variants": count}
    """
    h = simhash(normalized_text)
    
    best_campaign = None
    best_dist = float('inf')
    
    # Simple nearest-neighbor search
    for cid, c_data in store_campaigns.items():
        if c_data.get("primary_tactic") == primary_tactic:
            dist = hamming_distance(h, c_data.get("centroid_simhash", 0))
            if dist <= 12 and dist < best_dist:
                best_dist = dist
                best_campaign = cid
                
    if best_campaign:
        # Join existing
        c_data = store_campaigns[best_campaign]
        c_data["variant_count"] += 1
        return {
            "id": best_campaign,
            "variant_no": c_data["variant_count"],
            "first_seen": c_data["first_seen"],
            "variants": c_data["variant_count"]
        }
    else:
        # Create new
        new_id = f"C-{len(store_campaigns) + 1:04d}"
        import datetime
        now_str = datetime.datetime.now().isoformat()
        store_campaigns[new_id] = {
            "primary_tactic": primary_tactic,
            "centroid_simhash": h,
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
