import duckdb

print("DuckDB version:", duckdb.__version__)

con = duckdb.connect("tpcds.db")

con.execute("INSTALL tpcds")
con.execute("LOAD tpcds")

con.execute("CALL dsdgen(sf=1)")

tables = con.execute("SHOW TABLES").fetchall()

print("Number of tables:", len(tables))
print(tables[:10])