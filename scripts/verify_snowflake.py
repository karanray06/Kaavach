#!/usr/bin/env python3
"""
scripts/verify_snowflake.py
Runs one scan end to end against real Snowflake, queries the rows back,
prints table counts, and cleans up only its own test rows.
"""

import os
import sys
import uuid
import logging
from dotenv import load_dotenv

# Ensure repo root is on PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.snow import (
    get_snowflake_connection,
    insert_scan,
    insert_indicators,
    insert_or_update_campaign
)
from app.extract import hash_ioc

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("verify_snowflake")

def main():
    load_dotenv()
    conn = get_snowflake_connection()
    if not conn:
        logger.error("Unable to establish Snowflake connection. Check .env settings.")
        sys.exit(1)

    test_uuid = str(uuid.uuid4())
    test_scan_id = f"test-scan-{test_uuid[:8]}"
    test_camp_id = f"C-TEST-{test_uuid[:8]}"
    test_phone = "+919876543210"
    test_ioc_hash = hash_ioc(test_phone)

    logger.info("Starting end-to-end Snowflake verification test...")
    logger.info(f"Target Scan ID: {test_scan_id}")
    logger.info(f"Target Campaign ID: {test_camp_id}")
    logger.info(f"Target IOC Hash (64-char): {test_ioc_hash}")

    # 1. Insert Scan
    scan_payload = {
        "scan_id": test_scan_id,
        "lang": "en",
        "input_type": "text",
        "channel": "sms",
        "verdict": "LIKELY_SCAM",
        "risk_score": 0.92,
        "tactics": [{"code": "FAKE_KYC"}],
        "campaign": {"id": test_camp_id}
    }
    inserted_scan = insert_scan(scan_payload)
    logger.info(f"insert_scan result: {inserted_scan}")
    assert inserted_scan, "Failed to insert scan"

    # 2. Insert Indicators
    indicators_payload = [
        {
            "scan_id": test_scan_id,
            "ioc_type": "phone",
            "ioc_hash": test_ioc_hash,
            "ioc_display": "+91***",
            "tld": None
        }
    ]
    inserted_ind = insert_indicators(indicators_payload)
    logger.info(f"insert_indicators result: {inserted_ind}")
    assert inserted_ind, "Failed to insert indicators"

    # 3. Insert or Update Campaign
    campaign_payload = {
        "id": test_camp_id,
        "primary_tactic": "FAKE_KYC",
        "variant_no": 1,
        "centroid_simhash": 42424242
    }
    merged_camp = insert_or_update_campaign(campaign_payload)
    logger.info(f"insert_or_update_campaign result: {merged_camp}")
    assert merged_camp, "Failed to merge campaign"

    # 4. Query back the rows
    cur = conn.cursor()
    try:
        cur.execute("SELECT scan_id, verdict, risk_score, primary_tactic, is_demo FROM SCANS WHERE scan_id = %s", (test_scan_id,))
        scan_row = cur.fetchone()
        logger.info(f"Queried SCANS row: {scan_row}")
        assert scan_row is not None, "Test scan row not found in SCANS!"
        assert scan_row[4] is False, f"Expected is_demo = False, got {scan_row[4]}"

        cur.execute("SELECT scan_id, ioc_type, ioc_hash, is_demo FROM INDICATORS WHERE scan_id = %s", (test_scan_id,))
        ind_row = cur.fetchone()
        logger.info(f"Queried INDICATORS row: {ind_row}")
        assert ind_row is not None, "Test indicator row not found in INDICATORS!"
        assert len(ind_row[2]) == 64, f"IOC hash length was {len(ind_row[2])}, expected 64"
        assert ind_row[3] is False, f"Expected is_demo = False, got {ind_row[3]}"

        cur.execute("SELECT campaign_id, primary_tactic, variant_count FROM CAMPAIGNS WHERE campaign_id = %s", (test_camp_id,))
        camp_row = cur.fetchone()
        logger.info(f"Queried CAMPAIGNS row: {camp_row}")
        assert camp_row is not None, "Test campaign row not found in CAMPAIGNS!"

        # Query overall table counts
        cur.execute("SELECT COUNT(*) FROM SCANS WHERE is_demo = FALSE")
        real_scans_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM INDICATORS WHERE is_demo = FALSE")
        real_ind_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM CAMPAIGNS")
        total_camp_count = cur.fetchone()[0]

        logger.info("=========================================")
        logger.info("SNOWFLAKE ACTIVE VERIFICATION COUNTS:")
        logger.info(f"  Real Non-Demo SCANS:      {real_scans_count}")
        logger.info(f"  Real Non-Demo INDICATORS: {real_ind_count}")
        logger.info(f"  Total CAMPAIGNS:          {total_camp_count}")
        logger.info("=========================================")

    finally:
        # 5. Clean up ONLY our own test rows
        logger.info("Cleaning up verification test rows...")
        cur.execute("DELETE FROM SCANS WHERE scan_id = %s", (test_scan_id,))
        cur.execute("DELETE FROM INDICATORS WHERE scan_id = %s", (test_scan_id,))
        cur.execute("DELETE FROM CAMPAIGNS WHERE campaign_id = %s", (test_camp_id,))
        conn.commit()
        cur.close()
        logger.info("Cleanup complete. Verified successfully!")

if __name__ == "__main__":
    main()
