import pytest
import datetime
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.pipeline import MEMORY_STORE, MEMORY_STORE_LOCK
from app.trends import (
    calculate_trend_metrics,
    get_cached_trends,
    set_cached_trends,
    invalidate_trends_cache
)


def test_calculate_trend_metrics_normal():
    curr = {"TASK_SCAM": 10, "JOB_SCAM": 6}
    prev = {"TASK_SCAM": 8, "JOB_SCAM": 8}
    res = calculate_trend_metrics(curr, prev, total_scans=16, ai_unavailable_count=0, source="snowflake")

    assert res["source"] == "snowflake"
    assert res["total_scans"] == 16
    assert res["ai_unavailable_count"] == 0
    assert len(res["trends"]) == 2

    task = next(t for t in res["trends"] if t["tactic"] == "TASK_SCAM")
    job = next(t for t in res["trends"] if t["tactic"] == "JOB_SCAM")

    # TASK_SCAM: (10 - 8) / 8 * 100 = +25.0%
    assert task["count"] == 10
    assert task["prev_count"] == 8
    assert task["change_pct"] == 25.0
    assert task["is_new"] is False
    assert task["flag"] is None
    assert task["share_pct"] == 62.5

    # JOB_SCAM: (6 - 8) / 8 * 100 = -25.0%
    assert job["count"] == 6
    assert job["prev_count"] == 8
    assert job["change_pct"] == -25.0
    assert job["is_new"] is False
    assert job["flag"] is None
    assert job["share_pct"] == 37.5


def test_calculate_trend_metrics_prev_count_zero():
    curr = {"NEW_THREAT": 5}
    prev = {}
    res = calculate_trend_metrics(curr, prev, total_scans=5, ai_unavailable_count=0)

    assert len(res["trends"]) == 1
    t = res["trends"][0]
    assert t["tactic"] == "NEW_THREAT"
    assert t["count"] == 5
    assert t["prev_count"] == 0
    assert t["change_pct"] is None
    assert t["is_new"] is True
    assert t["flag"] == "new"
    assert t["share_pct"] == 100.0


def test_calculate_trend_metrics_no_scans():
    res = calculate_trend_metrics({}, {}, total_scans=0, ai_unavailable_count=0)
    assert res["total_scans"] == 0
    assert res["ai_unavailable_count"] == 0
    assert res["trends"] == []


def test_calculate_trend_metrics_only_ai_unavailable():
    res = calculate_trend_metrics({}, {}, total_scans=3, ai_unavailable_count=3)
    assert res["total_scans"] == 3
    assert res["ai_unavailable_count"] == 3
    assert res["trends"] == []


def test_calculate_trend_metrics_share_pct_sums_to_about_100():
    curr = {"A": 17, "B": 23, "C": 41, "D": 9, "E": 12}
    total = sum(curr.values())
    res = calculate_trend_metrics(curr, {}, total_scans=total, ai_unavailable_count=0)

    shares = [t["share_pct"] for t in res["trends"]]
    total_share = sum(shares)
    assert 99.0 <= total_share <= 101.0


def test_memory_fallback_excludes_demo_and_matches_logic():
    invalidate_trends_cache()
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    with MEMORY_STORE_LOCK:
        MEMORY_STORE["scans"].clear()
        # Demo scan should be excluded
        MEMORY_STORE["scans"]["s-demo"] = {
            "is_demo": True,
            "ts": now_iso,
            "primary_tactic": "DEMO_TACTIC",
            "verdict": "LIKELY_SCAM",
            "ai_available": True
        }
        # Real scans
        MEMORY_STORE["scans"]["s-real1"] = {
            "is_demo": False,
            "ts": now_iso,
            "primary_tactic": "LOTTERY",
            "verdict": "LIKELY_SCAM",
            "ai_available": True
        }
        MEMORY_STORE["scans"]["s-real2"] = {
            "is_demo": False,
            "ts": now_iso,
            "primary_tactic": "LOTTERY",
            "verdict": "LIKELY_SCAM",
            "ai_available": True
        }
        MEMORY_STORE["scans"]["s-real3"] = {
            "is_demo": False,
            "ts": now_iso,
            "primary_tactic": "UNKNOWN",
            "verdict": "UNCERTAIN",
            "ai_available": False
        }

    client = TestClient(app)
    with patch("app.main.get_trending_tactics", return_value=None):
        r = client.get("/api/trends")
        assert r.status_code == 200
        data = r.json()
        assert data["source"] == "memory"
        assert data["total_scans"] == 3
        assert data["ai_unavailable_count"] == 1
        tactics = [t["tactic"] for t in data["trends"]]
        assert "DEMO_TACTIC" not in tactics
        assert "UNKNOWN" not in tactics
        assert "LOTTERY" in tactics
        lottery = next(t for t in data["trends"] if t["tactic"] == "LOTTERY")
        assert lottery["count"] == 2
        assert lottery["share_pct"] == 100.0


def test_api_trends_key_parity():
    client = TestClient(app)
    expected_root_keys = {"source", "updated_at", "total_scans", "ai_unavailable_count", "trends"}
    expected_item_keys = {"tactic", "count", "share_pct", "prev_count", "change_pct", "is_new", "flag"}

    # 1. Snowflake path mocked
    mock_snow = {
        "source": "snowflake",
        "updated_at": "12:00",
        "total_scans": 10,
        "ai_unavailable_count": 1,
        "trends": [
            {
                "tactic": "FAKE_KYC",
                "count": 9,
                "share_pct": 100.0,
                "prev_count": 5,
                "change_pct": 80.0,
                "is_new": False,
                "flag": None
            }
        ]
    }
    invalidate_trends_cache()
    with patch("app.main.get_trending_tactics", return_value=mock_snow):
        r_snow = client.get("/api/trends")
        data_snow = r_snow.json()
        assert set(data_snow.keys()) == expected_root_keys
        assert set(data_snow["trends"][0].keys()) == expected_item_keys

    # 2. Memory path
    invalidate_trends_cache()
    with patch("app.main.get_trending_tactics", return_value=None):
        r_mem = client.get("/api/trends")
        data_mem = r_mem.json()
        assert set(data_mem.keys()) == expected_root_keys
        if data_mem["trends"]:
            assert set(data_mem["trends"][0].keys()) == expected_item_keys


def test_trends_cache_and_invalidation():
    invalidate_trends_cache()
    assert get_cached_trends() is None

    test_data = {"source": "test", "trends": []}
    set_cached_trends(test_data)
    assert get_cached_trends() == test_data

    invalidate_trends_cache()
    assert get_cached_trends() is None


def test_api_campaigns_excludes_demo():
    client = TestClient(app)
    with MEMORY_STORE_LOCK:
        MEMORY_STORE["campaigns"].clear()
        MEMORY_STORE["campaigns"]["C-DEMO01"] = {
            "variant_count": 5,
            "primary_tactic": "DEMO_TAC",
            "first_seen": "demo",
            "last_seen": "demo"
        }
        MEMORY_STORE["campaigns"]["C-0001"] = {
            "variant_count": 3,
            "primary_tactic": "IMPERSONATION",
            "first_seen": "2026-10-08T00:00:00",
            "last_seen": "2026-10-08T01:00:00"
        }

    with patch("app.main.get_recent_campaigns", return_value=None):
        r = client.get("/api/campaigns")
        assert r.status_code == 200
        data = r.json()
        assert data["source"] == "memory"
        c_ids = [c["campaign_id"] for c in data["campaigns"]]
        assert "C-DEMO01" not in c_ids
        assert "C-0001" in c_ids
        c = data["campaigns"][0]
        assert c["variant_count"] == 3
        assert c["top_tactic"] == "IMPERSONATION"
