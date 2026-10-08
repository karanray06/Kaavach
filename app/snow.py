import os
import snowflake.connector
from dotenv import load_dotenv

load_dotenv()

def get_snowflake_connection():
    try:
        conn = snowflake.connector.connect(
            user=os.environ.get("SNOWFLAKE_USER"),
            password=os.environ.get("SNOWFLAKE_PASSWORD"),
            account=os.environ.get("SNOWFLAKE_ACCOUNT"),
            warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE"),
            database=os.environ.get("SNOWFLAKE_DATABASE"),
            schema=os.environ.get("SNOWFLAKE_SCHEMA"),
            role=os.environ.get("SNOWFLAKE_ROLE")
        )
        return conn
    except Exception as e:
        print(f"Snowflake connection failed: {e}")
        return None

def check_health():
    conn = get_snowflake_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
            return "ok"
        except Exception:
            return "error"
        finally:
            conn.close()
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
        # Get primary tactic
        tactics = scan_data.get("tactics", [])
        primary_tactic = tactics[0].get("code") if tactics and isinstance(tactics[0], dict) else "UNKNOWN"
        
        cur.execute(query, (
            scan_data["scan_id"],
            scan_data["lang"],
            'text', # input_type
            'unknown', # channel
            scan_data["verdict"],
            float(scan_data["risk_score"]),
            primary_tactic,
            scan_data.get("campaign", {}).get("id")
        ))
        cur.close()
        return True
    except Exception as e:
        print(f"Error inserting scan: {e}")
        return False
    finally:
        conn.close()
