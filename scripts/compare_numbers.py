import urllib.request
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.snow import get_snowflake_connection

def main():
    # 1. API numbers
    req = urllib.request.Request("http://127.0.0.1:8000/api/trends")
    with urllib.request.urlopen(req) as resp:
        api_res = json.loads(resp.read().decode())

    print("=== API /api/trends TELEMETRY ===")
    print(f"Source: {api_res['source']}")
    print(f"Updated At: {api_res['updated_at']}")
    print(f"Total Scans (7d): {api_res['total_scans']}")
    print(f"AI Unavailable (7d): {api_res['ai_unavailable_count']}")
    print("Tactics Breakdown:")
    for t in api_res["trends"]:
        print(f"  - {t['tactic']}: count={t['count']}, share={t['share_pct']}%, prev={t['prev_count']}, change={t['change_pct']}, is_new={t['is_new']}")

    # 2. Direct Snowflake query
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

    cur.execute("""
    SELECT primary_tactic, COUNT(*) 
    FROM KAVACH.CORE.SCANS 
    WHERE is_demo = FALSE AND primary_tactic IS NOT NULL AND primary_tactic NOT IN ('UNKNOWN', '') AND ts >= DATEADD(day, -7, CURRENT_TIMESTAMP())
    GROUP BY primary_tactic 
    ORDER BY COUNT(*) DESC
    """)
    sf_rows = cur.fetchall()
    cur.close()

    print("\n=== DIRECT SNOWFLAKE QUERY ===")
    print(f"Snowflake Total Scans (7d): {tot_row[0]}")
    print(f"Snowflake AI Unavailable (7d): {tot_row[1]}")
    print("Snowflake Tactics Breakdown:")
    for r in sf_rows:
        print(f"  - {r[0]}: count={r[1]}")

    print("\n=== EXACT COMPARISON RESULTS ===")
    print(f"Total Scans: API={api_res['total_scans']} | Snowflake={tot_row[0]} -> MATCH: {api_res['total_scans'] == tot_row[0]}")
    print(f"AI Unavailable: API={api_res['ai_unavailable_count']} | Snowflake={tot_row[1]} -> MATCH: {api_res['ai_unavailable_count'] == tot_row[1]}")

    api_map = {t["tactic"]: t["count"] for t in api_res["trends"]}
    sf_map = {r[0]: r[1] for r in sf_rows}

    all_matched = True
    for tac, cnt in sf_map.items():
        api_cnt = api_map.get(tac)
        matched = (api_cnt == cnt)
        if not matched:
            all_matched = False
        print(f"Tactic '{tac}': API={api_cnt} | Snowflake={cnt} -> MATCH: {matched}")

    assert all_matched, "Some tactic counts did not match!"
    print("\n>>> ALL API NUMBERS MATCH DIRECT SNOWFLAKE QUERIES 100% <<<")

if __name__ == "__main__":
    main()
