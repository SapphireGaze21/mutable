#!/usr/bin/env python3
import sys
import os
import yaml
import duckdb
import time

def print_table(headers, rows):
    if not rows:
        print("Empty result set (0 rows).")
        return
    # Find max width of each column
    col_widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(val if val is not None else "NULL")))
            
    # Print header
    header_str = " | ".join(f"{str(h).ljust(col_widths[i])}" for i, h in enumerate(headers))
    print(header_str)
    print("-" * len(header_str))
    
    # Print rows
    for row in rows:
        row_str = " | ".join(f"{str(val if val is not None else 'NULL').ljust(col_widths[i])}" for i, val in enumerate(row))
        print(row_str)

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 RunTPCDS.py <path_to_qXX.yml> [case_number]")
        print("Example: python3 RunTPCDS.py tpcds/q01.yml 1")
        sys.exit(1)
        
    yml_path = sys.argv[1]
    case_name = sys.argv[2] if len(sys.argv) > 2 else "1"
    
    if not os.path.exists(yml_path):
        print(f"Error: File not found '{yml_path}'")
        sys.exit(1)
        
    with open(yml_path, 'r') as f:
        yml = yaml.safe_load(f)
        
    # Get the DuckDB query
    systems = yml.get('systems', {})
    duckdb_config = systems.get('DuckDB', {})
    cases = duckdb_config.get('cases', {})
    
    # Check if case exists (can be int or str in yml)
    query = cases.get(case_name) or cases.get(int(case_name) if case_name.isdigit() else None)
    
    if not query:
        print(f"Error: Case '{case_name}' for system 'DuckDB' not found in '{yml_path}'")
        print(f"Available cases: {list(cases.keys())}")
        sys.exit(1)
        
    db_path = os.path.join(os.path.dirname(__file__), 'tpcds', 'tpcds.db')
    if not os.path.exists(db_path):
        print(f"Error: DuckDB database not found at '{db_path}'")
        sys.exit(1)
        
    print(f"Connecting to DuckDB database: {db_path}")
    con = duckdb.connect(db_path)
    
    print("\n--- QUERY SQL ---")
    print(query.strip())
    print("-----------------\n")
    
    print("Executing query...")
    start_time = time.time()
    try:
        res = con.execute(query)
        rows = res.fetchall()
        elapsed = time.time() - start_time
        
        headers = [desc[0] for desc in res.description]
        print(f"--- OUTPUT (rows: {len(rows)}, time: {elapsed:.3f}s) ---")
        print_table(headers, rows)
    except Exception as e:
        print(f"Error executing query: {e}")
        sys.exit(1)
    finally:
        con.close()
        
    print("========================================================================\n")

if __name__ == '__main__':
    main()
