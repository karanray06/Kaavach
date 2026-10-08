import time
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.snow import get_snowflake_connection
from app.trends import invalidate_trends_cache

def main():
    client = TestClient(app)

    print("=== RUNNING 3 LIVE SCANS ===")
    s1 = client.post("/api/scan", data={"text": "URGENT: Your SBI account will be suspended today. Click http://update-kyc-bank.in immediately."})
    print("Scan 1:", s1.status_code, "Tactic:", s1.json().get("tactics", [{}])[0].get("code"))

    s2 = client.post("/api/scan", data={"text": "Congratulations! You won 25,00,000 INR in Kaun Banega Crorepati lucky draw lottery. Call 9876543210."})
    print("Scan 2:", s2.status_code, "Tactic:", s2.json().get("tactics", [{}])[0].get("code"))

    s3 = client.post("/api/scan", data={"text": "Part time job offer: Earn 5000 daily by liking YouTube videos and Telegram rating tasks."})
    print("Scan 3:", s3.status_code, "Tactic:", s3.json().get("tactics", [{}])[0].get("code"))

    # Wait for background tasks to commit to Snowflake
    print("\nWaiting for Snowflake background persistence...")
    time.sleep(5)
    invalidate_trends_cache()

    # Query /api/trends
    api_res = client.get("/api/trends").json()
    print("\n=== API /api/trends RESPONSE ===")
    print("Source:", api_res["source"])
    print("Updated At:", api_res["updated_at"])
    print("Total Scans:", api_res["total_scans"])
    print("AI Unavailable Count:", api_res["ai_unavailable_count"])
    print("Tactics Breakdown:")
    for t in api_res["trends"]:
        print(f"  - {t['tactic']}: count={t['count']}, share={t['share_pct']}%, prev={t['prev_count']}, change={t['change_pct']}, is_new={t['is_new']}")

    # Direct query to Snowflake
    conn = get_snowflake_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT 
        COUNT(*),
        COUNT(CASE WHEN verdict = 'UNCERTAIN' OR primary_tactic IS NULL OR primary_tactic IN ('UNKNOWN', '') THEN 1 END)
    FROM KAVACH.CORE.SCANS
    WHERE is_demo = FALSE AND ts >= DATEADD(day, -7, CURRENT_TIMESTAMP())
    """)
    tot_row = cur.fetchone()
    print("\n=== DIRECT SNOWFLAKE QUERY ===")
    print("Direct Snowflake Total Scans:", tot_row[0])
    print("Direct Snowflake AI Unavailable:", tot_row[1])

    cur.execute("""
    SELECT primary_tactic, COUNT(*) 
    FROM KAVACH.CORE.SCANS 
    WHERE is_demo = FALSE AND primary_tactic IS NOT NULL AND primary_tactic NOT IN ('UNKNOWN', '') AND ts >= DATEADD(day, -7, CURRENT_TIMESTAMP())
    GROUP BY primary_tactic 
    ORDER BY COUNT(*) DESC
    """)
    sf_rows = cur.fetchall()
    print("Direct Snowflake Tactics Breakdown:")
    for r in sf_rows:
        print(f"  - {r[0]}: count={r[1]}")

    api_tactics_map = {t["tactic"]: t["count"] for t in api_res["trends"]}
    sf_tactics_map = {r[0]: r[1] for r in sf_rows}

    assert api_res["total_scans"] == tot_row[0], f"Mismatch total: {api_res['total_scans']} vs {tot_row[0]}"
    assert api_res["ai_unavailable_count"] == tot_row[1], f"Mismatch unavail: {api_res['ai_unavailable_count']} vs {tot_row[1]}"
    for tac, cnt in sf_tactics_map.items():
        assert api_tactics_map.get(tac) == cnt, f"Mismatch for {tac}: {api_tactics_map.get(tac)} vs {cnt}"

    print("\n>>> VERIFICATION SUCCESS: All API counts match direct Snowflake query EXACTLY! <<<")

if __name__ == "__main__":
    main()
