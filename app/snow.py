import os
import logging
import snowflake.connector
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("kavach.snow")

_SNOW_CONN = None

def get_snowflake_connection():
    """
    Reuses module-level Snowflake connection, reconnecting if disconnected or closed.
    """
    global _SNOW_CONN
    if _SNOW_CONN is not None:
        try:
            if not _SNOW_CONN.is_closed():
                return _SNOW_CONN
        except Exception:
            _SNOW_CONN = None

    account = os.environ.get("SNOWFLAKE_ACCOUNT")
    user = os.environ.get("SNOWFLAKE_USER")
    if not account or not user:
        return None

    try:
        _SNOW_CONN = snowflake.connector.connect(
            user=user,
            password=os.environ.get("SNOWFLAKE_PASSWORD"),
            account=account,
            warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
            database=os.environ.get("SNOWFLAKE_DATABASE", "KAVACH"),
            schema=os.environ.get("SNOWFLAKE_SCHEMA", "CORE"),
            role=os.environ.get("SNOWFLAKE_ROLE")
        )
        return _SNOW_CONN
    except Exception as e:
        logger.warning("Snowflake connection failed: %s", e)
        _SNOW_CONN = None
        return None

def check_health():
    conn = get_snowflake_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
            return "ok"
        except Exception as e:
            logger.warning("Snowflake health check query failed: %s", e)
            return "error"
    return "down"

def insert_scan(scan_data: dict):
    conn = get_snowflake_connection()
    if not conn:
        return False
        
    try:
        cur = conn.cursor()
        query = """
        INSERT INTO SCANS (scan_id, ts, lang, input_type, channel, verdict, risk_score, primary_tactic, campaign_id, is_demo)
        VALUES (%s, CURRENT_TIMESTAMP(), %s, %s, %s, %s, %s, %s, %s, FALSE)
        """
        tactics = scan_data.get("tactics", [])
        primary_tactic = tactics[0].get("code") if tactics and isinstance(tactics[0], dict) else "UNKNOWN"
        campaign = scan_data.get("campaign")
        campaign_id = campaign.get("id") if isinstance(campaign, dict) else None
        
        cur.execute(query, (
            scan_data.get("scan_id"),
            scan_data.get("lang", "en"),
            scan_data.get("input_type", "text"),
            scan_data.get("channel", "unknown"),
            scan_data.get("verdict"),
            float(scan_data.get("risk_score", 0.0)),
            primary_tactic,
            campaign_id
        ))
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        logger.error("Error inserting scan to Snowflake: %s", e, exc_info=True)
        return False

def insert_indicators(indicators_data: list):
    """
    Writes only hashed IOC values (ioc_hash) and redacted display values to INDICATORS table.
    """
    if not indicators_data:
        return True
    conn = get_snowflake_connection()
    if not conn:
        return False
        
    try:
        cur = conn.cursor()
        query = """
        INSERT INTO INDICATORS (scan_id, ioc_type, ioc_hash, ioc_display, tld, ts, is_demo)
        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP(), FALSE)
        """
        params = [
            (
                item.get("scan_id"),
                item.get("ioc_type"),
                item.get("ioc_hash"),
                item.get("ioc_display", "***"),
                item.get("tld")
            )
            for item in indicators_data
        ]
        cur.executemany(query, params)
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        logger.error("Error inserting indicators to Snowflake: %s", e, exc_info=True)
        return False

def insert_or_update_campaign(campaign_data: dict):
    """
    MERGE into KAVACH.CORE.CAMPAIGNS to update variant_count, last_seen, and centroid_simhash.
    """
    if not campaign_data or not campaign_data.get("id"):
        return False
    conn = get_snowflake_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        query = """
        MERGE INTO CAMPAIGNS target
        USING (SELECT %s AS campaign_id, %s AS primary_tactic, %s AS variant_count, %s AS centroid_simhash) source
        ON target.campaign_id = source.campaign_id
        WHEN MATCHED THEN
            UPDATE SET 
                last_seen = CURRENT_TIMESTAMP(),
                variant_count = source.variant_count,
                centroid_simhash = source.centroid_simhash,
                primary_tactic = source.primary_tactic
        WHEN NOT MATCHED THEN
            INSERT (campaign_id, first_seen, last_seen, variant_count, primary_tactic, centroid_simhash)
            VALUES (source.campaign_id, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP(), source.variant_count, source.primary_tactic, source.centroid_simhash);
        """
        cur.execute(query, (
            campaign_data.get("id"),
            campaign_data.get("primary_tactic", "UNKNOWN"),
            int(campaign_data.get("variant_no", 1)),
            int(campaign_data.get("centroid_simhash", 0))
        ))
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        logger.error("Error merging campaign to Snowflake: %s", e, exc_info=True)
        return False

def get_trending_tactics():
    """
    Queries KAVACH.CORE.SCANS (is_demo = FALSE) for 7-day current and 7-day prior windows
    using DATEADD. Computes share percentages, week-over-week changes, total_scans,
    and ai_unavailable_count.
    """
    conn = get_snowflake_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        # 1. Total scans and AI-unavailable count for the last 7 days
        totals_query = """
        SELECT 
            COUNT(*) as total_scans,
            COUNT(CASE WHEN verdict = 'UNCERTAIN' OR primary_tactic IS NULL OR primary_tactic IN ('UNKNOWN', '') THEN 1 END) as ai_unavail
        FROM KAVACH.CORE.SCANS
        WHERE is_demo = FALSE AND ts >= DATEADD(day, -7, CURRENT_TIMESTAMP())
        """
        cur.execute(totals_query)
        tot_row = cur.fetchone()
        total_scans = tot_row[0] if tot_row and tot_row[0] is not None else 0
        ai_unavailable_count = tot_row[1] if tot_row and tot_row[1] is not None else 0

        # 2. Tactic counts for current 7 days and prior 7 days
        tactics_query = """
        SELECT 
            primary_tactic,
            COUNT(CASE WHEN ts >= DATEADD(day, -7, CURRENT_TIMESTAMP()) THEN 1 END) as curr_cnt,
            COUNT(CASE WHEN ts >= DATEADD(day, -14, CURRENT_TIMESTAMP()) AND ts < DATEADD(day, -7, CURRENT_TIMESTAMP()) THEN 1 END) as prev_cnt
        FROM KAVACH.CORE.SCANS
        WHERE is_demo = FALSE 
          AND primary_tactic IS NOT NULL 
          AND primary_tactic NOT IN ('UNKNOWN', '')
          AND ts >= DATEADD(day, -14, CURRENT_TIMESTAMP())
        GROUP BY primary_tactic
        HAVING curr_cnt > 0
        ORDER BY curr_cnt DESC
        """
        cur.execute(tactics_query)
        rows = cur.fetchall()
        cur.close()

        curr_tactics = {r[0]: int(r[1]) for r in rows}
        prev_tactics = {r[0]: int(r[2]) for r in rows}

        from app.trends import calculate_trend_metrics
        return calculate_trend_metrics(
            curr_tactics=curr_tactics,
            prev_tactics=prev_tactics,
            total_scans=total_scans,
            ai_unavailable_count=ai_unavailable_count,
            source="snowflake"
        )
    except Exception as e:
        logger.warning("Error querying trending tactics: %s", e)
        return None

def get_recent_campaigns():
    """
    Queries CAMPAIGNS table from Snowflake, excluding demo campaigns.
    """
    conn = get_snowflake_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT campaign_id, variant_count, primary_tactic, first_seen, last_seen 
            FROM CAMPAIGNS 
            WHERE campaign_id NOT LIKE 'C-DEMO%' 
            ORDER BY last_seen DESC 
            LIMIT 5
        """)
        rows = cur.fetchall()
        cur.close()
        return [
            {
                "campaign_id": r[0],
                "variant_count": int(r[1]) if r[1] is not None else 1,
                "top_tactic": r[2] or "UNKNOWN",
                "primary_tactic": r[2] or "UNKNOWN",
                "first_seen": str(r[3]),
                "last_seen": str(r[4])
            }
            for r in rows
        ]
    except Exception as e:
        logger.warning("Error querying recent campaigns: %s", e)
        return None
