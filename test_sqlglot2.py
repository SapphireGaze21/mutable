import sys
import os
import sqlglot
import sqlglot.expressions as exp
import re

sys.path.append('benchmark')
import tpl_parser

TPCDS_TABLES = {
    'store_sales', 'store_returns', 'catalog_sales', 'catalog_returns',
    'web_sales', 'web_returns', 'inventory',
    'customer', 'customer_address', 'customer_demographics',
    'household_demographics', 'date_dim', 'time_dim', 'item', 'store',
    'promotion', 'warehouse', 'ship_mode', 'call_center',
    'catalog_page', 'web_site', 'web_page', 'income_band', 'reason',
}

def flatten_query(sql):
    sql = re.sub(r'\[.*?\]', '1', sql) # Handle any leftover template vars
    
    ast = sqlglot.parse_one(sql, dialect="postgres")
    
    # 1. Extract all physical tables
    tables_dict = {}
    for table in ast.find_all(exp.Table):
        name = table.name.lower()
        if name in TPCDS_TABLES:
            alias = table.alias or name
            tables_dict[alias] = name
            
    if not tables_dict:
        return None
        
    from_clause = ", ".join([f"{name} {alias}" if name != alias else name for alias, name in tables_dict.items()])
    
    # 2. Extract conditions from WHERE and ON clauses
    conditions = []
    
    def extract_simple_conditions(node):
        if not node: return
        # If it's an AND, traverse children
        if isinstance(node, exp.And):
            extract_simple_conditions(node.left)
            extract_simple_conditions(node.right)
            return
            
        # For individual conditions, verify no subqueries or aggregations
        if any(node.find_all(exp.Select)) or any(node.find_all(exp.Subquery)) or any(node.find_all(exp.AggFunc)):
            return
            
        # verify no CASE
        if any(node.find_all(exp.Case)):
            return
            
        # We also need to map bare columns to aliases if possible, or just keep the sql
        conditions.append(node.sql(dialect="postgres"))

    # Find WHERE
    for where in ast.find_all(exp.Where):
        extract_simple_conditions(where.this)
        
    # Find JOIN ON
    for join in ast.find_all(exp.Join):
        if join.args.get("on"):
            extract_simple_conditions(join.args["on"])

    where_clause = " AND ".join(conditions)
    if where_clause:
        return f"SELECT * FROM {from_clause} WHERE {where_clause};"
    else:
        return f"SELECT * FROM {from_clause};"

sql = tpl_parser.parse_tpl('benchmark/tpcds/query_templates/query16.tpl')
print(flatten_query(sql))
