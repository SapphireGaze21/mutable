# Mutable Database Engine — SQL Compatibility Error Log

> Tested against mutable (debug build) using TPC-DS schema with 59 individual SQL feature probes and 67 simplified TPC-DS queries.

---

## Summary

| Category | Count |
|---|---|
| **SQL Features Supported** | 26 / 59 (44%) |
| **SQL Features Unsupported** | 33 / 59 (56%) |
| **Simplified TPC-DS Queries Passing** | 35 / 67 (52%) |
| **Simplified TPC-DS Queries Failing** | 32 / 67 (48%) |
| **Original TPC-DS Queries Simplifiable** | 67 / 99 (68%) |
| **Original TPC-DS Queries Not Simplifiable** | 32 / 99 — contain only subqueries, UNION, EXISTS, etc. |

---

## ✅ Supported SQL Features (26)

| # | Feature | Example |
|---|---|---|
| 1 | `SELECT *` | `SELECT * FROM t;` |
| 2 | `WHERE =` (int equality) | `WHERE d_year = 1998` |
| 3 | `WHERE AND` | `WHERE d_year = 1998 AND d_moy = 1` |
| 4 | `WHERE OR` | `WHERE d_year = 1998 OR d_moy = 1` |
| 5 | `WHERE != / <>` | `WHERE d_year != 1998` |
| 6 | `WHERE < > <= >=` | `WHERE d_year >= 1998 AND d_year <= 2000` |
| 7 | Multi-table JOIN (comma syntax) | `FROM a, b WHERE a.x = b.x` |
| 8 | Self-join with alias | `FROM t d1, t d2 WHERE d1.x = d2.x` |
| 9 | Table alias (`AS`) | `FROM date_dim AS d` |
| 10 | Column alias (`AS`) | `SELECT d_year AS yr` |
| 11 | `COUNT(*)` | `SELECT COUNT(*) FROM t` |
| 12 | `SUM()` | `SELECT SUM(col) FROM t` |
| 13 | `AVG()` | `SELECT AVG(col) FROM t` |
| 14 | `MIN()` | `SELECT MIN(col) FROM t` |
| 15 | `MAX()` | `SELECT MAX(col) FROM t` |
| 16 | `GROUP BY` | `GROUP BY d_year` |
| 17 | `GROUP BY` + `HAVING` | `GROUP BY d_year HAVING COUNT(*) > 10` |
| 18 | `ORDER BY` | `ORDER BY d_year` |
| 19 | `ORDER BY DESC` | `ORDER BY d_year DESC` |
| 20 | `LIMIT` | `LIMIT 10` |
| 21 | `ORDER BY` + `LIMIT` | `ORDER BY d_year LIMIT 10` |
| 22 | Subquery in `FROM` | `FROM (SELECT ...) AS sub` |
| 23 | Arithmetic in `SELECT` | `SELECT d_year + 1` |
| 24 | Arithmetic in `WHERE` | `WHERE d_year + 1 = 1999` |
| 25 | Multiple statements | `SELECT ...; SELECT ...;` |
| 26 | Nested parentheses | `WHERE (x = 1 AND (y = 2 OR y = 3))` |

---

## ❌ Unsupported SQL Features (33)

### Parser-Level Failures (keyword not recognized by the lexer/parser)

| Feature | Error | Notes |
|---|---|---|
| `BETWEEN` | `expected TK_SEMICOL, got BETWEEN` | Parser doesn't recognize BETWEEN keyword |
| `IN (list)` | `expected TK_SEMICOL, got IN` | Parser doesn't recognize IN keyword |
| `NOT IN (list)` | `Function IN is not defined` | Treated as function call |
| `IS NULL` | `expected TK_SEMICOL, got IS` | Parser doesn't recognize IS NULL |
| `IS NOT NULL` | `expected TK_SEMICOL, got IS` | Same as above |
| `LIKE` | `operands must be character sequences` | Only works on CHAR types, not INT |
| `JOIN ... ON` | `expected TK_SEMICOL, got date_dim` | ANSI JOIN syntax not supported |
| `LEFT JOIN` | `expected TK_SEMICOL, got JOIN` | Outer joins not recognized |
| `RIGHT JOIN` | `expected TK_SEMICOL, got JOIN` | Outer joins not recognized |
| `FULL OUTER JOIN` | `expected TK_SEMICOL, got OUTER` | Outer joins not recognized |
| `CROSS JOIN` | `expected TK_SEMICOL, got JOIN` | CROSS JOIN not recognized |
| `DISTINCT` | `Attribute DISTINCT not found` | Parser treats DISTINCT as column name |
| `COUNT(DISTINCT col)` | `expected TK_RPAR, got d_year` | No DISTINCT inside aggregates |
| `UNION ALL` | `expected TK_SEMICOL, got ALL` | Set operations not implemented |
| `UNION` | `expected TK_SEMICOL, got SELECT` | Set operations not implemented |
| `INTERSECT` | `expected TK_SEMICOL, got SELECT` | Set operations not implemented |
| `EXCEPT` | `expected TK_SEMICOL, got SELECT` | Set operations not implemented |
| `EXISTS` | `expected expression, got EXISTS` | EXISTS predicate not recognized |
| `NOT EXISTS` | `expected expression, got EXISTS` | Same as above |
| `WITH ... AS` (CTE) | `expected a statement, got WITH` | CTEs not implemented |
| `CASE WHEN` | `expected TK_SEMICOL, got d_year` | CASE expressions not recognized |
| `CAST()` | `expected TK_RPAR, got AS` | Type casting not supported |
| `COALESCE()` | `Function COALESCE is not defined` | Not a built-in function |
| `ROLLUP` | `Function ROLLUP is not defined` | Advanced grouping not supported |
| `CUBE` | `Function CUBE is not defined` | Advanced grouping not supported |
| `GROUPING SETS` | `expected TK_SEMICOL, got (` | Advanced grouping not supported |
| `WINDOW / OVER` | `expected TK_SEMICOL, got (` | Window functions not implemented |
| `RANK() OVER` | `expected TK_SEMICOL, got (` | Window functions not implemented |
| `ROW_NUMBER() OVER` | `expected TK_SEMICOL, got (` | Window functions not implemented |
| String literals in WHERE | `illegal character '` | Single-quoted strings not fully supported |

### Semantic-Level Failures (parses but fails during semantic analysis)

| Feature | Error | Notes |
|---|---|---|
| Subquery in `WHERE (IN)` | `expected TK_SEMICOL, got IN` | Subquery + IN combo fails |
| Scalar subquery in `WHERE` | `Table name already in use` | Cannot reuse table name in subquery |
| Correlated subquery | `Condition 'it != named_sources_.end()' failed` | **Assertion failure / crash** — outer reference not resolved |

---

## TPC-DS Flat Query Failures (32 out of 67)

### Missing Tables in Our Lean Schema (not a mutable bug)

These queries reference tables we excluded from our lean INT-only schema:

| Missing Table | Affected Queries |
|---|---|
| `household_demographics` | query34, query73, query79, query84, query88, query90, query96 |
| `inventory` | query21, query22, query37, query39, query72, query82 |
| `promotion` | query7, query26, query61, query80 |
| `warehouse` | query40, query62, query66, query99 |
| `call_center` | query91 |
| `reason` | query85, query93 |

### Missing Columns in Our Lean Schema (not a mutable bug)

These queries reference CHAR/VARCHAR columns we stripped when creating INT-only CSVs:

| Missing Column | Affected Queries |
|---|---|
| `i_manufact_id` (VARCHAR) | query3, query32, query92 |
| `i_manager_id` (VARCHAR) | query42, query52, query55 |
| `d_quarter_name` (VARCHAR) | query17 |
| `ss_net_profit` (DECIMAL) | query49 |

---

## Impact on TPC-DS Benchmark Coverage

```
99 original TPC-DS queries
 └─ 67 could be simplified to flat SELECT-FROM-WHERE (68%)
 └─ 32 could NOT be simplified — require UNION, EXISTS, CTE, correlated subqueries (32%)

Of the 67 simplified queries:
 └─ 35 pass mutable successfully (52%)
 └─ 32 fail due to missing tables/columns in our lean schema (48%)
      └─ 0 fail due to actual mutable SQL bugs

Key takeaway: ALL failures on simplified queries are due to our lean schema
              missing tables/columns, NOT due to mutable SQL limitations.
              Mutable handles all flat SELECT-FROM-WHERE-GROUP BY queries correctly.
```

---

## Workaround Summary

| Unsupported Feature | Workaround Used in Our Pipeline |
|---|---|
| `JOIN ... ON` syntax | Rewrite as comma-joins with `WHERE` conditions |
| `BETWEEN x AND y` | Rewrite as `col >= x AND col <= y` |
| `IN (a, b, c)` | Rewrite as `col = a OR col = b OR col = c` |
| `IS NULL` / `IS NOT NULL` | Dropped from conditions |
| `DISTINCT` | Dropped from queries |
| `CASE WHEN` | Dropped from conditions |
| `CAST()` | Dropped — used INT-only schema |
| Subqueries in WHERE | Flattened into additional FROM tables |
| `UNION` / `INTERSECT` / `EXCEPT` | Query skipped entirely |
| `EXISTS` / `NOT EXISTS` | Query skipped entirely |
| `WITH ... AS` (CTE) | Query skipped entirely |
| Window functions | Query skipped entirely |
| String literals (`'...'`) | Used INT-only columns to avoid string handling |
