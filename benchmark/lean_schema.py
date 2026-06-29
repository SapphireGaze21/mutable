#!/usr/bin/env python3
"""
Generate a lean Mutable schema with ALL integer columns per table
(dropping CHAR/VARCHAR columns which cause StackMachine misaligned-store crash).
Only emit tables that are actually used by the target queries.
"""
import re
import csv as csv_mod
import glob

QUERY_DIR = "benchmark/tpcds/query_templates_flat"
TARGET_QUERIES = [
    "query12.sql", "query15.sql",
    "query36.sql", "query27.sql",
    "query23.sql", "query25.sql", "query77.sql"
]

# Collect all tables referenced in target queries
used_tables = set()
for qf in TARGET_QUERIES:
    with open(f"{QUERY_DIR}/{qf}") as f:
        sql = f.read().upper()
    from_part = re.search(r'FROM\s+(.*?)\s+WHERE', sql, re.DOTALL)
    if not from_part:
        continue
    for ref in from_part.group(1).split(','):
        tname = ref.strip().split()[0].lower()
        used_tables.add(tname)

print(f"Tables used in queries: {sorted(used_tables)}")

# Read original schema
with open("benchmark/tpcds/data/csvs/schema.sql") as f:
    orig_schema = f.read()

def is_char_type(col_type):
    col_type = col_type.strip().upper()
    return 'VARCHAR' in col_type or ('CHAR' in col_type and 'DECIMAL' not in col_type)

# Parse original schema
table_schemas = {}
for match in re.finditer(r'CREATE TABLE (\w+)\s*\(([^)]+)\)', orig_schema, re.DOTALL):
    tname = match.group(1).lower()
    cols_str = match.group(2)
    cols = {}
    for col_match in re.finditer(r'\b(\w+)\s+([\w()]+)', cols_str):
        cname = col_match.group(1).lower()
        ctype = col_match.group(2)
        if cname not in ('primary', 'unique', 'foreign', 'key', 'constraint', 'not', 'null', 'default'):
            cols[cname] = ctype
    table_schemas[tname] = cols

# Build schema DDL + lean CSVs
ddl_lines = ["CREATE DATABASE tpcds_eval;", "USE tpcds_eval;", ""]
import_lines = []

for tname in sorted(used_tables):
    if tname not in table_schemas:
        print(f"  WARNING: {tname} not in schema")
        continue

    orig_cols = table_schemas[tname]
    csv_path = f"benchmark/tpcds/data/csvs/{tname}.csv"

    # Read CSV header to know available columns
    with open(csv_path, 'r', newline='') as fin:
        reader = csv_mod.reader(fin)
        full_header = [h.strip().lower() for h in next(reader)]

    # Keep only integer columns (those that exist in both schema and CSV)
    int_cols = []  # (col_name, csv_idx)
    for cname, ctype in orig_cols.items():
        if not is_char_type(ctype) and cname in full_header:
            int_cols.append((cname, full_header.index(cname)))

    if not int_cols:
        print(f"  Skipping {tname} — no integer columns found")
        continue

    # Write lean CSV with only integer columns
    lean_csv = f"benchmark/tpcds/data/csvs/lean_{tname}.csv"
    lean_header = [c for c, _ in int_cols]
    lean_indices = [i for _, i in int_cols]

    with open(csv_path, 'r', newline='') as fin, open(lean_csv, 'w', newline='') as fout:
        reader = csv_mod.reader(fin)
        next(reader)  # skip original header
        writer = csv_mod.writer(fout, lineterminator='\n')
        writer.writerow(lean_header)
        for row in reader:
            lean_row = []
            for idx in lean_indices:
                v = row[idx].strip() if idx < len(row) else ''
                if not v:
                    lean_row.append('0')
                else:
                    try:
                        lean_row.append(str(abs(int(float(v)))))
                    except ValueError:
                        lean_row.append('0')
            writer.writerow(lean_row)

    col_defs = ', '.join(f"{c} INT(4)" for c in lean_header)
    ddl_lines.append(f"CREATE TABLE {tname}({col_defs});")
    import_lines.append(
        f'IMPORT INTO {tname} DSV "benchmark/tpcds/data/csvs/lean_{tname}.csv" DELIMITER "," HAS HEADER SKIP HEADER;'
    )
    print(f"  {tname}: {len(lean_header)} int cols")

final_sql = "\n".join(ddl_lines) + "\n\n" + "\n".join(import_lines)
with open("benchmark/tpcds/data/csvs/mutable_schema.sql", "w") as f:
    f.write(final_sql)

print(f"\nWrote mutable_schema.sql  ({len(import_lines)} tables)")
