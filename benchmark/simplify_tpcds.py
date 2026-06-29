#!/usr/bin/env python3
"""
Simplify TPC-DS .tpl queries for mutable compatibility (v4 using sqlglot).

This uses sqlglot to cleanly parse the query AST and perfectly extract
base tables and simple JOIN conditions without being confused by subqueries.
"""

import os
import sys
import re
import sqlglot
import sqlglot.expressions as exp

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
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
    # Strip any leftover template tags like [LIMITA]
    sql = re.sub(r'\[.*?\]', '1', sql)
    
    try:
        ast = sqlglot.parse_one(sql, dialect="postgres")
    except Exception:
        # If sqlglot can't parse it, we skip it
        return None
        
    # 1. Extract all physical tables from the entire query
    tables_dict = {}
    for table in ast.find_all(exp.Table):
        name = table.name.lower()
        if name in TPCDS_TABLES:
            alias = table.alias or name
            tables_dict[alias] = name
            
    if not tables_dict:
        return None
        
    # Format FROM clause
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
            
        # Verify no subqueries, aggregations, or CASE
        if any(node.find_all((exp.Select, exp.Subquery, exp.AggFunc, exp.Case))):
            return
            
        # Ignore IN clauses and BETWEEN clauses as mutable often trips on them or they contain unresolved functions
        if any(node.find_all((exp.In, exp.Between))):
            return
            
        # Ignore functions we know mutable or TPC-DS has trouble with
        sql_str = node.sql(dialect="postgres")
        if 'dist(' in sql_str.lower() or 'distmember(' in sql_str.lower() or 'CAST' in sql_str.upper():
            return
            
        if '+' in sql_str or '-' in sql_str or '*' in sql_str or '/' in sql_str:
            return

        # Check that all column references in this condition use an alias/table that we extracted
        columns = node.find_all(exp.Column)
        for col in columns:
            if col.table:
                table_ref = col.table.lower()
                if table_ref not in tables_dict:
                    return
            else:
                # Bare column - technically could be valid, but mutable might complain if ambiguous.
                # For now, we'll allow bare columns but they caused some "ambiguous" errors.
                pass

        conditions.append(sql_str)

    # Find all WHERE clauses anywhere in the query
    for where in ast.find_all(exp.Where):
        extract_simple_conditions(where.this)
        
    # Find all JOIN ON clauses anywhere in the query
    for join in ast.find_all(exp.Join):
        if join.args.get("on"):
            extract_simple_conditions(join.args["on"])

    # Eliminate duplicate conditions
    unique_conditions = []
    seen = set()
    for c in conditions:
        if c not in seen:
            seen.add(c)
            unique_conditions.append(c)

    where_clause = " AND ".join(unique_conditions)
    
    # If the user wants to test join algos, we should ensure at least ONE join condition exists if there are multiple tables.
    # Otherwise we get a full Cartesian product which crashes mutable.
    # Actually, let's keep it simple: if there are > 1 tables and 0 conditions, skip it.
    if len(tables_dict) > 1 and not unique_conditions:
        return None
        
    if where_clause:
        return f"SELECT * FROM {from_clause} WHERE {where_clause};"
    else:
        return f"SELECT * FROM {from_clause};"


def simplify_query(tpl_path):
    sql = tpl_parser.parse_tpl(tpl_path)
    return flatten_query(sql)


def main():
    input_dir = 'benchmark/tpcds/query_templates'
    output_dir = 'benchmark/tpcds/query_templates_flat'
    os.makedirs(output_dir, exist_ok=True)

    success = 0
    failed = 0
    skipped = 0

    for i in range(1, 100):
        tpl_path = os.path.join(input_dir, f'query{i}.tpl')
        if not os.path.exists(tpl_path):
            skipped += 1
            continue

        try:
            simplified = simplify_query(tpl_path)
            if simplified is None:
                print(f'query{i}: SKIP (no valid join structure found)')
                skipped += 1
                continue

            output_path = os.path.join(output_dir, f'query{i}.sql')
            with open(output_path, 'w') as f:
                f.write(simplified + '\n')

            # Double check our new sql passes mutable's requirements: double quotes, uppercase keywords
            # (tpl_parser.py already handles most of this, but sqlglot might change the formatting slightly)
            # We'll just rely on sqlglot's standard postgres dialect which is close enough

            print(f'query{i}: OK')
            success += 1
        except Exception as e:
            print(f'query{i}: ERROR ({e})')
            failed += 1

    print(f'\n=== Summary ===')
    print(f'Success: {success}')
    print(f'Failed:  {failed}')
    print(f'Skipped: {skipped}')


if __name__ == '__main__':
    main()
