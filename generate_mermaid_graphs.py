import os
import re
import glob
from collections import defaultdict
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
        
    edges = set()
    for eq in ast.find_all(exp.EQ):
        cols = list(eq.find_all(exp.Column))
        if len(cols) == 2:
            t1 = cols[0].table.lower() if cols[0].table else map_column_to_table(cols[0].name.lower(), tables_list)
            t2 = cols[1].table.lower() if cols[1].table else map_column_to_table(cols[1].name.lower(), tables_list)
            
            if t1 in tables: t1 = tables[t1]
            if t2 in tables: t2 = tables[t2]
            
            if t1 and t2 and t1 != t2:
                pair = tuple(sorted([t1, t2]))
                edges.add(pair)
                
    return set(tables_list), list(edges)

def classify_graph(nodes, edges):
    if len(nodes) <= 1:
        return "Single Table"
    if not edges:
        return "Disconnected"
        
    # Build adjacency
    adj = defaultdict(set)
    for u, v in edges:
        adj[u].add(v)
        adj[v].add(u)
        
    # Check connected
    visited = set()
    start = list(nodes)[0]
    stack = [start]
    while stack:
        curr = stack.pop()
        if curr not in visited:
            visited.add(curr)
            stack.extend(adj[curr] - visited)
            
    if len(visited) < len(nodes):
        return "Disconnected / Cartesian"

    degrees = [len(adj[n]) for n in nodes]
    degrees.sort()
    
    n = len(nodes)
    e = len(edges)
    
    if e == n - 1:
        if degrees[-1] == n - 1:
            return "Star"
        if degrees.count(1) == 2 and all(d == 2 for d in degrees[2:]):
            return "Chain"
        return "Tree"
        
    if e == n * (n - 1) // 2:
        return "Clique / Complete"
        
    return "Cyclic / Web"

def main():
    files = sorted(glob.glob("benchmark/tpcds/query_templates_flat/*.sql"))
    
    md = []
    md.append("# TPC-DS Join Graphs and Topologies\n")
    md.append("This artifact details the exact Mermaid diagram join graph and structural topology classification (Star, Chain, Tree, etc.) for each flat query.\n")
    
    for f in files:
        basename = os.path.basename(f)
        query_name = basename.replace(".sql", "")
        res = analyze_query(f)
        if not res:
            continue
            
        nodes, edges = res
        if len(nodes) <= 1:
            continue
            
        topology = classify_graph(nodes, edges)
        
        md.append(f"### {query_name}")
        md.append(f"- **Tables:** {len(nodes)}")
        md.append(f"- **Structure:** {topology}")
        md.append("")
        
        if edges:
            md.append("```mermaid")
            md.append("graph TD;")
            for u, v in edges:
                # remove quotes to prevent mermaid syntax issues if any
                u_clean = u.replace("'", "").replace('"', '')
                v_clean = v.replace("'", "").replace('"', '')
                md.append(f"  {u_clean} --- {v_clean}")
            md.append("```")
            md.append("")
            
    with open("visual_graphs.md", "w") as out:
        out.write("\n".join(md))
        
if __name__ == "__main__":
    main()
