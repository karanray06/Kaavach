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
        
        cur.execute(query, (
            scan_data.get("scan_id"),
            scan_data.get("lang", "en"),
            scan_data.get("input_type", "text"),
            scan_data.get("channel", "unknown"),
            scan_data.get("verdict"),
            float(scan_data.get("risk_score", 0.0)),
            primary_tactic,
            scan_data.get("campaign", {}).get("id")
        ))
        cur.close()
        return True
    except Exception as e:
        logger.warning("Error inserting scan to Snowflake: %s", e)
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
        cur.close()
        return True
    except Exception as e:
        logger.warning("Error inserting indicators to Snowflake: %s", e)
        return False

def get_trending_tactics():
    """
    Queries V_TRENDING_TACTICS view from Snowflake.
    """
    conn = get_snowflake_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT primary_tactic, current_count, delta_vs_prior FROM V_TRENDING_TACTICS ORDER BY current_count DESC LIMIT 5")
        rows = cur.fetchall()
        cur.close()
        return [{"tactic": r[0], "count": r[1], "delta": r[2]} for r in rows]
    except Exception as e:
        logger.warning("Error querying trending tactics: %s", e)
        return None

def get_recent_campaigns():
    """
    Queries CAMPAIGNS table from Snowflake.
    """
    conn = get_snowflake_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT campaign_id, variant_count, primary_tactic, first_seen, last_seen FROM CAMPAIGNS ORDER BY last_seen DESC LIMIT 5")
        rows = cur.fetchall()
        cur.close()
        return [{"campaign_id": r[0], "variant_count": r[1], "primary_tactic": r[2], "first_seen": str(r[3]), "last_seen": str(r[4])} for r in rows]
    except Exception as e:
        logger.warning("Error querying recent campaigns: %s", e)
        return None
