import os
import snowflake.connector
from dotenv import load_dotenv

load_dotenv()

def run_script(conn, file_path):
    print(f"Running {file_path}...")
    with open(file_path, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    # Simple split by ';' to execute statements sequentially
    statements = [s.strip() for s in sql.split(';') if s.strip()]
    cur = conn.cursor()
    for stmt in statements:
        try:
            cur.execute(stmt)
        except Exception as e:
            print(f"Error executing statement:\n{stmt}\nError: {e}")
    cur.close()
    print(f"Finished {file_path}")

def main():
    conn = snowflake.connector.connect(
        user=os.environ.get("SNOWFLAKE_USER"),
        password=os.environ.get("SNOWFLAKE_PASSWORD"),
        account=os.environ.get("SNOWFLAKE_ACCOUNT"),
        role=os.environ.get("SNOWFLAKE_ROLE")
    )
    
    try:
        run_script(conn, "sql/01_schema.sql")
        run_script(conn, "sql/02_views.sql")
        run_script(conn, "sql/03_seed_demo.sql")
        print("Database seeded successfully!")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
