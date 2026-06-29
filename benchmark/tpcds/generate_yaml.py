import re
import yaml

with open('benchmark/dataset_for_graph/data/schema.sql', 'r') as f:
    sql = f.read()

tables_to_extract = ['store_sales', 'customer', 'date_dim', 'item', 'store', 'promotion']

data = {}

for table in tables_to_extract:
    match = re.search(f'CREATE TABLE {table}\\((.*?)\\);', sql, re.IGNORECASE)
    if match:
        columns = match.group(1).split(', ')
        attributes = {}
        for col in columns:
            parts = col.strip().split(' ')
            col_name = parts[0]
            col_type = parts[1]
            # Convert DuckDB types to string suitable for YAML
            attributes[col_name] = col_type
        
        data[table] = {
            'attributes': attributes
        }

with open('benchmark/dataset_for_graph/data_tpcds.yml', 'w') as f:
    yaml.dump({'data': data}, f, sort_keys=False)
