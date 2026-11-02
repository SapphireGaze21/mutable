#!/usr/bin/env python3
"""
Generate a mutable_schema.sql and clean CSVs retaining ALL columns natively.
"""
import re
import csv as csv_mod
import glob
import os

QUERY_DIR = "benchmark/tpcds/query_templates_flat"
TARGET_QUERIES = [
    "query12.sql", "query15.sql",
    "query36.sql", "query27.sql",
    "query23.sql", "query25.sql", "query77.sql"
]

used_tables = set()
for qf in TARGET_QUERIES:
    if not os.path.exists(f"{QUERY_DIR}/{qf}"):
        continue
    with open(f"{QUERY_DIR}/{qf}") as f:
        sql = f.read().upper()
    from_part = re.search(r'FROM\s+(.*?)\s+WHERE', sql, re.DOTALL)
    if not from_part:
        from_part = re.search(r'FROM\s+(.*?)\s*;', sql, re.DOTALL)
    if not from_part:
        continue
    for ref in from_part.group(1).split(','):
        tname = ref.strip().split()[0].lower()
        used_tables.add(tname)

print(f"Tables used in queries: {sorted(used_tables)}")

with open("benchmark/tpcds/data/csvs/schema.sql") as f:
    orig_schema = f.read()

def map_mutable_type(ctype):
    ctype = ctype.strip().upper()
    if 'INT' in ctype:
        return 'INT(4)', 'int'
    if 'DECIMAL' in ctype or 'NUMERIC' in ctype:
        m = re.search(r'\((\d+),\s*(\d+)\)', ctype)
        if m:
            return f"DECIMAL({m.group(1)}, {m.group(2)})", 'decimal'
        return 'DECIMAL(10, 2)', 'decimal'
    if 'CHAR' in ctype:
        return 'VARCHAR(255)', 'string'
    if ctype == 'DATE':
        return 'DATE', 'date'
    if 'TIME' in ctype:
        return 'DATETIME', 'date'
    return 'INT(4)', 'int'

table_schemas = {}
for match in re.finditer(r'CREATE TABLE (\w+)\s*\(([^)]+)\)', orig_schema, re.DOTALL):
    tname = match.group(1).lower()
    cols_str = match.group(2)
    cols = {}
    for col_match in re.finditer(r'\b([a-zA-Z_]\w*)\s+([a-zA-Z_][\w(),\s]+?)(?=(?:,|\n|$))', cols_str):
        cname = col_match.group(1).lower()
        ctype = col_match.group(2).strip()
        if cname not in ('primary', 'unique', 'foreign', 'key', 'constraint', 'not', 'null', 'default'):
            # only add if not already in cols
            if cname not in cols:
                cols[cname] = ctype
    table_schemas[tname] = cols

ddl_lines = ["CREATE DATABASE tpcds_eval;", "USE tpcds_eval;", ""]
import_lines = []

for tname in sorted(used_tables):
    if tname not in table_schemas:
        print(f"  WARNING: {tname} not in schema")
        continue

    orig_cols = table_schemas[tname]
    csv_path = f"benchmark/tpcds/data/csvs/{tname}.csv"
    if not os.path.exists(csv_path):
        continue

    with open(csv_path, 'r', newline='') as fin:
        reader = csv_mod.reader(fin)
        full_header = [h.strip().lower() for h in next(reader)]

    # Map columns based on CSV header
    mapped_cols = []
    col_types = []
    for cname in full_header:
        if cname in orig_cols:
            m_type, type_class = map_mutable_type(orig_cols[cname])
            mapped_cols.append(f"{cname} {m_type}")
            col_types.append(type_class)
        else:
            mapped_cols.append(f"{cname} VARCHAR(255)")
            col_types.append('string')

    lean_csv = f"benchmark/tpcds/data/csvs/lean_{tname}.csv"
    with open(csv_path, 'r', newline='') as fin, open(lean_csv, 'w', newline='') as fout:
        reader = csv_mod.reader(fin)
        next(reader)  # skip original header
        writer = csv_mod.writer(fout, lineterminator='\n')
        writer.writerow(full_header)
        for row_num, row in enumerate(reader):
            if row_num >= 10000:
                break
            lean_row = []
            for idx, v in enumerate(row):
                v = v.strip()
                tclass = col_types[idx]
                if not v:
                    if tclass == 'int': lean_row.append('0')
                    elif tclass == 'decimal': lean_row.append('0.0')
                    elif tclass == 'string': lean_row.append('')
                    elif tclass == 'date': lean_row.append('1970-01-01')
                    else: lean_row.append('0')
                else:
                    if tclass == 'date':
                        # mutable expects YYYY-MM-DD
                        lean_row.append(v)
                    else:
                        lean_row.append(v)
            writer.writerow(lean_row)

    col_defs = ', '.join(mapped_cols)
    ddl_lines.append(f"CREATE TABLE {tname}({col_defs});")
    import_lines.append(
        f'IMPORT INTO {tname} DSV "benchmark/tpcds/data/csvs/lean_{tname}.csv" DELIMITER "," HAS HEADER SKIP HEADER;'
    )
    print(f"  {tname}: {len(mapped_cols)} cols")

final_sql = "\n".join(ddl_lines) + "\n\n" + "\n".join(import_lines)
with open("benchmark/tpcds/data/csvs/mutable_schema.sql", "w") as f:
    f.write(final_sql)

print(f"\nWrote mutable_schema.sql  ({len(import_lines)} tables)")
