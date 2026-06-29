import sys
import os
import sqlglot
import sqlglot.expressions as exp

sys.path.append('benchmark')
import tpl_parser

sql = tpl_parser.parse_tpl('benchmark/tpcds/query_templates/query16.tpl')
# Clean up any leftover square brackets (like [LIMITA]) just in case
import re
sql = re.sub(r'\[.*?\]', '1', sql)

try:
    # Dialect postgres or something
    ast = sqlglot.parse_one(sql, dialect="postgres")
    
    tables = []
    aliases = set()
    for table in ast.find_all(exp.Table):
        name = table.name
        alias = table.alias or name
        tables.append(f"{name} {alias}" if alias != name else name)
        aliases.add(alias)
        
    print("Tables:", tables)
    
    # Extract conditions
    conditions = []
    for node in ast.find_all(exp.Condition):
        # We only want top-level conditions in WHERE or ON, but for now let's just look at EQ
        if isinstance(node, exp.EQ):
            conditions.append(node.sql())
            
    print("EQ conditions:", conditions)

except Exception as e:
    print("Parse error:", e)

