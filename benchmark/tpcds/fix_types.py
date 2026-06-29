import yaml

with open('benchmark/dataset_for_graph/graph_mutable.yml', 'r') as f:
    graph = yaml.safe_load(f)

for table_name, table in graph['data'].items():
    for col_name, col_type in table['attributes'].items():
        if col_type == 'VARCHAR':
            table['attributes'][col_name] = 'CHAR 255'
        elif col_type == 'INTEGER':
            table['attributes'][col_name] = 'INT'
        elif col_type.startswith('DECIMAL'):
            # DECIMAL(7,2) -> DECIMAL 7 2
            inner = col_type.replace('DECIMAL(', '').replace(')', '')
            parts = inner.split(',')
            table['attributes'][col_name] = f"DECIMAL {parts[0]} {parts[1]}"

with open('benchmark/dataset_for_graph/graph_mutable.yml', 'w') as f:
    yaml.dump(graph, f, sort_keys=False)
