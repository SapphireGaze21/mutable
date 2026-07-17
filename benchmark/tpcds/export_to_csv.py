import duckdb
import os

# Connect to database
con = duckdb.connect("tpcds.db")

# Create output directory
output_dir = "tpcds_csv"
os.makedirs(output_dir, exist_ok=True)

# Get all tables
tables = con.execute("""
SELECT table_name
FROM information_schema.tables
WHERE table_schema='main'
ORDER BY table_name
""").fetchall()

# Export each table
for (table,) in tables:
    csv_path = os.path.join(output_dir, f"{table}.csv")

    con.execute(f"""
    COPY "{table}"
    TO '{csv_path}'
    (HEADER, DELIMITER ',');
    """)

    print(f"Exported {table} -> {csv_path}")

print("Done!")