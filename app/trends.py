import datetime
import threading
import time
from typing import Dict, List, Optional, Any

_TRENDS_CACHE: Dict[str, Any] = {
    "data": None,
    "cached_at": 0.0
}
_CACHE_LOCK = threading.Lock()


def get_cached_trends() -> Optional[dict]:
    with _CACHE_LOCK:
        if _TRENDS_CACHE["data"] is not None and (time.time() - _TRENDS_CACHE["cached_at"]) < 60:
            return _TRENDS_CACHE["data"]
        return None


def set_cached_trends(data: dict) -> None:
    with _CACHE_LOCK:
        _TRENDS_CACHE["data"] = data
        _TRENDS_CACHE["cached_at"] = time.time()


def invalidate_trends_cache() -> None:
    with _CACHE_LOCK:
        _TRENDS_CACHE["data"] = None
        _TRENDS_CACHE["cached_at"] = 0.0


def calculate_trend_metrics(
    curr_tactics: Dict[str, int],
    prev_tactics: Dict[str, int],
    total_scans: int,
    ai_unavailable_count: int,
    source: str = "snowflake"
) -> dict:
    """
    Computes dynamic telemetry trend metrics across a 7-day current vs 7-day prior window.
    Filters out UNKNOWN / empty tactics from trends list while accounting for total_scans
    and ai_unavailable_count.
    """
    # Exclude UNKNOWN and empty tactics from tactic breakdown
    valid_curr = {k: v for k, v in curr_tactics.items() if k and k not in ("UNKNOWN", "") and v > 0}
    total_mentions = sum(valid_curr.values())

    trends_list: List[dict] = []
    # Sort descending by current count, then ascending by tactic name
    sorted_tactics = sorted(valid_curr.items(), key=lambda x: (-x[1], x[0]))

    for tactic, count in sorted_tactics:
        prev = int(prev_tactics.get(tactic, 0))
        share_pct = round((count / total_mentions) * 100, 1) if total_mentions > 0 else 0.0

        is_new = (prev == 0 and count > 0)
        if prev > 0:
            change_pct = round(((count - prev) / prev) * 100, 1)
        elif is_new:
            change_pct = None
        else:
            change_pct = None

        trends_list.append({
            "tactic": tactic,
            "count": int(count),
            "share_pct": share_pct,
            "prev_count": prev,
            "change_pct": change_pct,
            "is_new": is_new,
            "flag": "new" if is_new else None
        })

    return {
        "source": source,
        "updated_at": datetime.datetime.now().strftime("%H:%M"),
        "total_scans": int(total_scans),
        "ai_unavailable_count": int(ai_unavailable_count),
        "trends": trends_list
    }
