import re
import yaml
import sys

def parse_sql(file_path):
    with open(file_path, 'r') as f:
        content = f.read()

    # Find all CREATE TABLE blocks
    tables = {}
    blocks = re.findall(r'(?i)create table\s+(\w+)\s*\((.*?)\);', content, re.DOTALL)
    for t_name, t_cols in blocks:
        t_name = t_name.strip().lower()
        cols = {}
        for line in t_cols.split('\n'):
            line = line.strip()
            if not line or line.startswith('--') or line.startswith('primary key'):
                continue
            # Some lines end with commas
            line = line.rstrip(',')
            parts = [p for p in line.split() if p]
            if len(parts) >= 2:
                c_name = parts[0]
                c_type = parts[1]
                # convert type to mutable format
                # e.g., integer -> INT, char(x) -> CHAR x, decimal(x,y) -> DECIMAL x y, date -> DATE
                c_type_upper = c_type.upper()
                if 'INTEGER' in c_type_upper or 'INT' in c_type_upper:
                    mut_type = 'BIGINT' # following graph_mutable.yml convention where sks are BIGINT
                elif 'DECIMAL' in c_type_upper:
                    m = re.match(r'DECIMAL\((\d+),(\d+)\)', c_type_upper)
                    if m:
                        mut_type = f'DECIMAL {m.group(1)} {m.group(2)}'
                    else:
                        mut_type = 'DECIMAL 7 2'
                elif 'CHAR' in c_type_upper or 'VARCHAR' in c_type_upper:
                    mut_type = 'CHAR 255'
                elif 'DATE' in c_type_upper:
                    mut_type = 'DATE'
                else:
                    mut_type = 'CHAR 255' # fallback
                
                cols[c_name] = mut_type
        tables[t_name] = {'attributes': cols}
    return tables

tables = parse_sql('tpcds queries/tpcds-kit/tools/tpcds.sql')

existing_tables = ['store_sales', 'customer', 'date_dim', 'item', 'store', 'promotion']
missing = {}
for t, spec in tables.items():
    if t not in existing_tables:
        missing[t] = spec

print(yaml.dump(missing, sort_keys=False))

