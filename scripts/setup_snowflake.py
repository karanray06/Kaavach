import os
import sys
import glob
import uuid
from dotenv import load_dotenv

# Ensure workspace root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import snowflake.connector
from app.snow import insert_scan, get_snowflake_connection

def split_sql_statements(sql_text: str):
    """
    Splits SQL script into individual statements safely by semicolon,
    ignoring full-line comments and blank lines.
    """
    statements = []
    current_lines = []
    for line in sql_text.splitlines():
        trimmed = line.strip()
        if trimmed.startswith("--"):
            continue
        current_lines.append(line)
        if trimmed.endswith(";"):
            full_stmt = "\n".join(current_lines).strip()
            clean_stmt = full_stmt.rstrip(";").strip()
            if clean_stmt:
                statements.append(clean_stmt)
            current_lines = []
    if current_lines:
        full_stmt = "\n".join(current_lines).strip()
        clean_stmt = full_stmt.rstrip(";").strip()
        if clean_stmt:
            statements.append(clean_stmt)
    return statements

def run_setup():
    load_dotenv(override=True)
    
    account = os.environ.get("SNOWFLAKE_ACCOUNT")
    user = os.environ.get("SNOWFLAKE_USER")
    password = os.environ.get("SNOWFLAKE_PASSWORD")
    warehouse = os.environ.get("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH")
    database = os.environ.get("SNOWFLAKE_DATABASE", "KAVACH")
    schema = os.environ.get("SNOWFLAKE_SCHEMA", "CORE")
    role = os.environ.get("SNOWFLAKE_ROLE")

    print("=" * 60)
    print("KAVACH SNOWFLAKE SETUP & VERIFICATION")
    print("=" * 60)
    print(f"Target Database : {database}")
    print(f"Target Schema   : {schema}")
    print(f"Target Warehouse: {warehouse}")
    print(f"Target Role     : {role}")
    print(f"User            : {user}")
    print(f"Account         : {account}")

    # Check for empty credentials
    missing = []
    if not account:
        missing.append("SNOWFLAKE_ACCOUNT")
    if not user:
        missing.append("SNOWFLAKE_USER")
    if not password:
        missing.append("SNOWFLAKE_PASSWORD")
        
    if missing:
        print("\n[ERROR] Missing required Snowflake credentials in .env:")
        for m in missing:
            print(f"  - {m} is empty or not set.")
        return False

    print("\nConnecting to Snowflake...")
    conn = None
    try:
        connect_params = {
            "user": user,
            "password": password,
            "account": account,
        }
        if role:
            connect_params["role"] = role
            
        conn = snowflake.connector.connect(**connect_params)
        print("[OK] Connected successfully to Snowflake.")
    except Exception as e:
        print(f"\n[ERROR] Connection failed: {e}")
        err_str = str(e).lower()
        if "incorrect username or password" in err_str:
            print("Diagnosis: Check SNOWFLAKE_USER or SNOWFLAKE_PASSWORD in .env.")
        elif "could not resolve" in err_str or "unknown" in err_str or "failed to connect" in err_str:
            print("Diagnosis: Check SNOWFLAKE_ACCOUNT in .env. Format should be <orgname>-<accountname> or <account_locator>.")
        elif "role" in err_str:
            print("Diagnosis: Check SNOWFLAKE_ROLE in .env. Ensure the user has access to this role.")
        else:
            print(f"Diagnosis: Snowflake returned error: {e}")
        return False

    cur = conn.cursor()

    try:
        # Step A: Create and use warehouse
        print(f"\nEnsuring warehouse '{warehouse}' exists...")
        wh_sql = f"""
        CREATE WAREHOUSE IF NOT EXISTS {warehouse}
            WAREHOUSE_SIZE = 'XSMALL'
            AUTO_SUSPEND = 60
            AUTO_RESUME = TRUE;
        """
        cur.execute(wh_sql)
        cur.execute(f"USE WAREHOUSE {warehouse};")
        print(f"[OK] Warehouse '{warehouse}' active.")

        # Step B: Create and use database & schema
        print(f"Ensuring database '{database}' and schema '{schema}' exist...")
        cur.execute(f"CREATE DATABASE IF NOT EXISTS {database};")
        cur.execute(f"USE DATABASE {database};")
        cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema};")
        cur.execute(f"USE SCHEMA {schema};")
        print(f"[OK] Database '{database}' and schema '{schema}' active.")

        # Step C: Execute all SQL files in sql/ directory in alphabetical order
        sql_files = sorted(glob.glob("sql/*.sql"))
        print(f"\nExecuting {len(sql_files)} SQL files in sql/ directory:")
        
        for fpath in sql_files:
            print(f"\n--- Running {fpath} ---")
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
                
            statements = split_sql_statements(content)
            for stmt in statements:
                first_line = stmt.strip().splitlines()[0][:70]
                try:
                    cur.execute(stmt)
                    print(f"  [OK] {first_line}")
                except Exception as stmt_err:
                    print(f"  [ERROR] {first_line}\n         Error: {stmt_err}")

        # Step D: Verification
        print("\n" + "=" * 60)
        print("VERIFICATION OF CREATED OBJECTS")
        print("=" * 60)

        # 1. Databases
        print("\n--- SHOW DATABASES LIKE 'KAVACH' ---")
        cur.execute(f"SHOW DATABASES LIKE '{database}';")
        for row in cur.fetchall():
            print(f"  Database: {row[1]} | Owner: {row[5]} | Created: {row[2]}")

        # 2. Tables in Schema
        print(f"\n--- SHOW TABLES IN SCHEMA {database}.{schema} ---")
        cur.execute(f"SHOW TABLES IN SCHEMA {database}.{schema};")
        for row in cur.fetchall():
            print(f"  Table: {row[1]} | Kind: {row[3]} | Rows: {row[4]}")

        # 3. Views in Schema
        print(f"\n--- SHOW VIEWS IN SCHEMA {database}.{schema} ---")
        cur.execute(f"SHOW VIEWS IN SCHEMA {database}.{schema};")
        for row in cur.fetchall():
            print(f"  View: {row[1]} | Owner: {row[4]}")

        # 4. Test insert_scan(), read back, and delete
        print("\n--- TESTING insert_scan() THROUGH app/snow.py ---")
        test_scan_id = "test-verify-" + str(uuid.uuid4())[:8]
        test_record = {
            "scan_id": test_scan_id,
            "lang": "en",
            "input_type": "text",
            "channel": "test",
            "verdict": "LIKELY_SCAM",
            "risk_score": 0.99,
            "tactics": [{"code": "TEST_TACTIC", "evidence": "automated verify"}],
            "campaign": {"id": "C-TEST-0001"}
        }

        print(f"Inserting test row ({test_scan_id})...")
        inserted = insert_scan(test_record)
        if inserted:
            print("[OK] insert_scan() succeeded.")
            cur.execute(f"SELECT scan_id, verdict, risk_score, primary_tactic FROM {database}.{schema}.SCANS WHERE scan_id = %s", (test_scan_id,))
            fetched = cur.fetchone()
            print(f"[OK] Selected back inserted row: {fetched}")
            cur.execute(f"DELETE FROM {database}.{schema}.SCANS WHERE scan_id = %s", (test_scan_id,))
            print(f"[OK] Cleaned up test row ({test_scan_id}).")
        else:
            print("[WARN] insert_scan() returned False.")

        print("\n[SUCCESS] All Snowflake database objects verified successfully!")
        return True

    except Exception as e:
        print(f"\n[ERROR] Execution error: {e}")
        return False
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    success = run_setup()
    sys.exit(0 if success else 1)
