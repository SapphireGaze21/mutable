import os
import re
import glob
import sqlglot
import sqlglot.expressions as exp

TPCDS_TABLES = [
    'store_sales', 'store_returns', 'catalog_sales', 'catalog_returns',
    'web_sales', 'web_returns', 'inventory',
    'customer', 'customer_address', 'customer_demographics',
    'household_demographics', 'date_dim', 'time_dim', 'item', 'store',
    'promotion', 'warehouse', 'ship_mode', 'call_center',
    'catalog_page', 'web_site', 'web_page', 'income_band', 'reason',
]

def map_column_to_table(col_name, tables_in_query):
    # Mapping of common TPC-DS prefixes
    prefix_map = {
        'ss_': 'store_sales', 'sr_': 'store_returns',
        'cs_': 'catalog_sales', 'cr_': 'catalog_returns',
        'ws_': 'web_sales', 'wr_': 'web_returns',
        'inv_': 'inventory',
        'c_': 'customer', 'ca_': 'customer_address', 'cd_': 'customer_demographics',
        'hd_': 'household_demographics', 'd_': 'date_dim', 't_': 'time_dim',
        'i_': 'item', 's_': 'store', 'p_': 'promotion', 'w_': 'warehouse',
        'sm_': 'ship_mode', 'cc_': 'call_center', 'cp_': 'catalog_page',
        'web_': 'web_site', 'wp_': 'web_page', 'ib_': 'income_band', 'r_': 'reason'
    }
    for prefix, table in prefix_map.items():
        if col_name.startswith(prefix) and table in tables_in_query:
            return table
    return None

def analyze_query(filepath):
    with open(filepath, 'r') as f:
        sql = f.read()
        
    try:
        ast = sqlglot.parse_one(sql, dialect="postgres")
    except Exception:
        return None
        
    tables = {}
    tables_list = []
    for t in ast.find_all(exp.Table):
        name = t.name.lower()
        alias = t.alias_or_name.lower()
        tables[alias] = name
        tables_list.append(name)
        
    joins = set()
    # Find all EQ conditions
    for eq in ast.find_all(exp.EQ):
        cols = list(eq.find_all(exp.Column))
        if len(cols) == 2:
            t1 = cols[0].table.lower() if cols[0].table else map_column_to_table(cols[0].name.lower(), tables_list)
            t2 = cols[1].table.lower() if cols[1].table else map_column_to_table(cols[1].name.lower(), tables_list)
            
            if t1 in tables: t1 = tables[t1]
            if t2 in tables: t2 = tables[t2]
            
            if t1 and t2 and t1 != t2:
                # order alphabetically so a=b is same as b=a
                pair = tuple(sorted([t1, t2]))
                joins.add(f"{pair[0]} -- {pair[1]}")
                
    return len(tables_list), sorted(list(joins))

def main():
    files = sorted(glob.glob("benchmark/tpcds/query_templates_flat/*.sql"))
    
    md = []
    md.append("# TPC-DS Flat Queries Join Structures\n")
    md.append("This document outlines the join graphs for the perfectly flattened TPC-DS queries.\n")
    
    for f in files:
        basename = os.path.basename(f)
        query_name = basename.replace(".sql", "")
        res = analyze_query(f)
        if res:
            n_tables, joins = res
            md.append(f"### {query_name} ({n_tables} tables)")
            if joins:
                md.append("- **Join Graph:**")
                for j in joins:
                    md.append(f"  - `{j}`")
            else:
                md.append("- *No equi-joins detected in AST*")
            md.append("")
            
    with open("query_graphs.md", "w") as out:
        out.write("\n".join(md))
        
if __name__ == "__main__":
    main()
