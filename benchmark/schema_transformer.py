import re

with open("benchmark/tpcds/data/csvs/schema.sql", "r") as f:
    schema = f.read()

# Replace types - use INT(4) not INT(8) to avoid StackMachine misaligned-store crash
schema = schema.replace("BIGINT", "INT(4)")
schema = schema.replace("INTEGER", "INT(4)")
schema = schema.replace("VARCHAR", "CHAR(255)")
schema = schema.replace("DATE", "INT(4)")
schema = re.sub(r"DECIMAL\(\d+,\d+\)", "INT(4)", schema)
schema = schema.replace(";;", ";")

# Append dummy_col CHAR(255) to every table
schema = schema.replace(");", ", dummy_col CHAR(255));")

# Find table names and generate IMPORT statements
table_names = re.findall(r"CREATE TABLE ([a-zA-Z0-9_]+)", schema)

import_statements = []
for t in table_names:
    import_statements.append(f"IMPORT INTO {t} DSV \"benchmark/tpcds/data/csvs/{t}.csv\" DELIMITER \",\" HAS HEADER SKIP HEADER;")

final_schema = "CREATE DATABASE tpcds_eval;\nUSE tpcds_eval;\n\n" + schema + "\n\n" + "\n".join(import_statements)

with open("benchmark/tpcds/data/csvs/mutable_schema.sql", "w") as f:
    f.write(final_schema)
