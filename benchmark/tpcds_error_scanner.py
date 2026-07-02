#!/usr/bin/env python3
"""
Test all TPC-DS simplified queries and individual SQL features against mutable.
Produces a compatibility error log.
"""

import os
import re
import subprocess
import sys

SHELL = "build/debug_shared/bin/shell"
SCHEMA = "/tmp/schema_no_import.sql"
FLAT_DIR = "benchmark/tpcds/query_templates_flat"

def test_query(sql, schema_path):
    with open(schema_path) as f:
        schema = f.read()
    full_sql = f"{schema}\n{sql}"
    with open("/tmp/mutable_test.sql", "w") as f:
        f.write(full_sql)
    cmd = [
        SHELL, "--quiet", "--dryrun",
        "--plan-enumerator", "DPsize",
        "--cardinality-estimator", "CartesianProduct",
        "/tmp/mutable_test.sql"
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"
    except Exception as e:
        return -2, "", str(e)

def has_error(stderr):
    """Check if stderr indicates a failure."""
    for line in stderr.split('\n'):
        l = line.strip()
        if not l:
            continue
        if 'error' in l.lower() or "failed" in l.lower() or 'Condition' in l:
            return True
    return False

def first_error(stderr):
    for line in stderr.split('\n'):
        l = line.strip()
        if l and ('error' in l.lower() or 'Error' in l or 'failed' in l.lower() or 'Condition' in l):
            return l[:120]
    return stderr.strip().split('\n')[-1][:120] if stderr.strip() else "unknown"

# ========== PHASE 1: Flat query tests ==========
print("=" * 80)
print("MUTABLE TPC-DS COMPATIBILITY ERROR LOG")
print("=" * 80)
print("\n### PHASE 1: Testing Simplified Flat Queries ###\n")

flat_results = {}
for fname in sorted(os.listdir(FLAT_DIR)):
    if not fname.endswith('.sql'):
        continue
    qid = int(re.search(r'(\d+)', fname).group(1))
    with open(os.path.join(FLAT_DIR, fname)) as f:
        sql = f.read().strip()
    rc, out, err = test_query(sql, SCHEMA)
    if rc != -1 and not has_error(err):
        flat_results[qid] = ("OK", None, None)
        print(f"  query{qid:>2}: OK")
    elif rc == -1:
        flat_results[qid] = ("TIMEOUT", "TIMEOUT", "Timed out")
        print(f"  query{qid:>2}: TIMEOUT")
    else:
        e = first_error(err)
        flat_results[qid] = ("FAIL", e, err[:300])
        print(f"  query{qid:>2}: FAIL — {e}")

ok = sum(1 for v in flat_results.values() if v[0] == "OK")
fail = sum(1 for v in flat_results.values() if v[0] == "FAIL")
to = sum(1 for v in flat_results.values() if v[0] == "TIMEOUT")
print(f"\n  Summary: {ok} OK, {fail} FAIL, {to} TIMEOUT out of {len(flat_results)}")

# ========== PHASE 2: Direct feature tests ==========
print("\n\n### PHASE 2: Direct SQL Feature Support Tests ###\n")

features = [
    # Basic queries
    ("Simple SELECT *",                  "SELECT * FROM date_dim;"),
    ("WHERE equality (int)",             "SELECT * FROM date_dim WHERE d_year = 1998;"),
    ("WHERE AND",                        "SELECT * FROM date_dim WHERE d_year = 1998 AND d_moy = 1;"),
    ("WHERE OR",                         "SELECT * FROM date_dim WHERE d_year = 1998 OR d_moy = 1;"),
    ("WHERE != / <>",                    "SELECT * FROM date_dim WHERE d_year != 1998;"),
    ("WHERE < > <= >=",                  "SELECT * FROM date_dim WHERE d_year >= 1998 AND d_year <= 2000;"),
    ("WHERE BETWEEN",                    "SELECT * FROM date_dim WHERE d_year BETWEEN 1998 AND 2000;"),
    ("WHERE IN (list)",                  "SELECT * FROM date_dim WHERE d_year IN (1998, 1999, 2000);"),
    ("WHERE IS NULL",                    "SELECT * FROM date_dim WHERE d_year IS NULL;"),
    ("WHERE IS NOT NULL",                "SELECT * FROM date_dim WHERE d_year IS NOT NULL;"),
    ("WHERE LIKE",                       "SELECT * FROM date_dim WHERE d_year LIKE 1998;"),
    ("WHERE NOT IN (list)",              "SELECT * FROM date_dim WHERE d_year NOT IN (1998, 1999);"),
    # Joins
    ("Multi-table JOIN (comma)",         "SELECT * FROM store_sales, date_dim WHERE ss_sold_date_sk = d_date_sk;"),
    ("INNER JOIN ... ON",                "SELECT * FROM store_sales JOIN date_dim ON ss_sold_date_sk = d_date_sk;"),
    ("LEFT OUTER JOIN",                  "SELECT * FROM store_sales LEFT JOIN date_dim ON ss_sold_date_sk = d_date_sk;"),
    ("RIGHT OUTER JOIN",                 "SELECT * FROM store_sales RIGHT JOIN date_dim ON ss_sold_date_sk = d_date_sk;"),
    ("FULL OUTER JOIN",                  "SELECT * FROM store_sales FULL OUTER JOIN date_dim ON ss_sold_date_sk = d_date_sk;"),
    ("CROSS JOIN",                       "SELECT * FROM store_sales CROSS JOIN date_dim;"),
    ("Self-join with alias",             "SELECT * FROM date_dim d1, date_dim d2 WHERE d1.d_year = d2.d_year;"),
    # Aliases
    ("Table alias (AS)",                 "SELECT * FROM date_dim AS d WHERE d.d_year = 1998;"),
    ("Column alias (AS)",                "SELECT d_year AS yr FROM date_dim;"),
    # Aggregations
    ("COUNT(*)",                         "SELECT COUNT(*) FROM date_dim;"),
    ("SUM()",                            "SELECT SUM(d_year) FROM date_dim;"),
    ("AVG()",                            "SELECT AVG(d_year) FROM date_dim;"),
    ("MIN()",                            "SELECT MIN(d_year) FROM date_dim;"),
    ("MAX()",                            "SELECT MAX(d_year) FROM date_dim;"),
    ("DISTINCT",                         "SELECT DISTINCT d_year FROM date_dim;"),
    ("COUNT(DISTINCT col)",              "SELECT COUNT(DISTINCT d_year) FROM date_dim;"),
    # Grouping
    ("GROUP BY",                         "SELECT d_year, COUNT(*) FROM date_dim GROUP BY d_year;"),
    ("GROUP BY + HAVING",                "SELECT d_year, COUNT(*) FROM date_dim GROUP BY d_year HAVING COUNT(*) > 10;"),
    ("ROLLUP",                           "SELECT d_year, d_moy, COUNT(*) FROM date_dim GROUP BY ROLLUP(d_year, d_moy);"),
    ("CUBE",                             "SELECT d_year, d_moy, COUNT(*) FROM date_dim GROUP BY CUBE(d_year, d_moy);"),
    ("GROUPING SETS",                    "SELECT d_year, d_moy, COUNT(*) FROM date_dim GROUP BY GROUPING SETS((d_year), (d_moy));"),
    # Ordering & Limiting
    ("ORDER BY",                         "SELECT * FROM date_dim ORDER BY d_year;"),
    ("ORDER BY DESC",                    "SELECT * FROM date_dim ORDER BY d_year DESC;"),
    ("LIMIT",                            "SELECT * FROM date_dim LIMIT 10;"),
    ("ORDER BY + LIMIT",                 "SELECT * FROM date_dim ORDER BY d_year LIMIT 10;"),
    # Set operations
    ("UNION ALL",                        "SELECT d_year FROM date_dim UNION ALL SELECT d_year FROM date_dim;"),
    ("UNION (dedup)",                    "SELECT d_year FROM date_dim UNION SELECT d_year FROM date_dim;"),
    ("INTERSECT",                        "SELECT d_year FROM date_dim INTERSECT SELECT d_year FROM date_dim;"),
    ("EXCEPT",                           "SELECT d_year FROM date_dim EXCEPT SELECT d_year FROM date_dim;"),
    # Subqueries
    ("Subquery in WHERE (IN)",           "SELECT * FROM date_dim WHERE d_year IN (SELECT d_year FROM date_dim);"),
    ("Subquery in FROM",                 "SELECT * FROM (SELECT d_year FROM date_dim) AS sub;"),
    ("Scalar subquery",                  "SELECT * FROM date_dim WHERE d_year = (SELECT MAX(d_year) FROM date_dim);"),
    ("EXISTS",                           "SELECT * FROM date_dim WHERE EXISTS (SELECT 1 FROM store_sales);"),
    ("NOT EXISTS",                       "SELECT * FROM date_dim WHERE NOT EXISTS (SELECT 1 FROM store_sales);"),
    ("Correlated subquery",              "SELECT * FROM date_dim d1 WHERE d1.d_year = (SELECT MAX(d2.d_year) FROM date_dim d2 WHERE d2.d_moy = d1.d_moy);"),
    # CTEs
    ("CTE (WITH ... AS)",               "WITH cte AS (SELECT d_year FROM date_dim) SELECT * FROM cte;"),
    # Expressions
    ("CASE WHEN",                        "SELECT CASE WHEN d_year = 1998 THEN 1 ELSE 0 END FROM date_dim;"),
    ("CAST()",                           "SELECT CAST(d_year AS INT) FROM date_dim;"),
    ("COALESCE()",                       "SELECT COALESCE(d_year, 0) FROM date_dim;"),
    ("Arithmetic in SELECT",             "SELECT d_year + 1 FROM date_dim;"),
    ("Arithmetic in WHERE",              "SELECT * FROM date_dim WHERE d_year + 1 = 1999;"),
    # Window functions
    ("WINDOW / OVER",                    "SELECT d_year, COUNT(*) OVER (PARTITION BY d_moy) FROM date_dim;"),
    ("RANK() OVER",                      "SELECT d_year, RANK() OVER (ORDER BY d_year) FROM date_dim;"),
    ("ROW_NUMBER() OVER",                "SELECT d_year, ROW_NUMBER() OVER (ORDER BY d_year) FROM date_dim;"),
    # Misc
    ("String literal in WHERE",          "SELECT * FROM date_dim WHERE d_year = 'test';"),
    ("Multiple statements",              "SELECT * FROM date_dim; SELECT * FROM store_sales;"),
    ("Nested parentheses",               "SELECT * FROM date_dim WHERE (d_year = 1998 AND (d_moy = 1 OR d_moy = 2));"),
]

supported = []
unsupported = []

for name, sql in features:
    rc, out, err = test_query(sql, SCHEMA)
    if rc != -1 and not has_error(err):
        supported.append(name)
        print(f"  {name:<35}: SUPPORTED")
    elif rc == -1:
        unsupported.append((name, "TIMEOUT"))
        print(f"  {name:<35}: UNSUPPORTED [TIMEOUT]")
    else:
        e = first_error(err)
        unsupported.append((name, e))
        print(f"  {name:<35}: UNSUPPORTED — {e}")

print(f"\n  Summary: {len(supported)} supported, {len(unsupported)} unsupported out of {len(features)}")
print(f"\n  Supported features:   {supported}")
print(f"\n  Unsupported features:")
for name, err in unsupported:
    print(f"    - {name}: {err}")
