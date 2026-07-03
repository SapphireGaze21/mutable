# Mutable ISRP Work Summary

This document summarizes all the modifications, additions, and tools built during the course of the internship working on the `mutable` database engine repository. The primary focus of the work was instrumenting the query optimizer for dynamic programming (DP) algorithms and building comprehensive TPC-DS benchmarking pipelines.

---

## 1. Core Engine Instrumentation (`src/IR/PlanEnumerator.cpp`)
To analyze the completeness vs. pruning trade-offs of various Join-Order Enumeration algorithms (such as `DPsize`, `DPsub`, and `DPccp`), the core C++ optimizer was instrumented to expose runtime metrics:
- **`EvaluatedCounter` & `CCPCounter`:** Added globally accessible counters to track the exact number of candidate plans (Subproblems and Connected Subgraphs) evaluated across O(3ⁿ) search spaces.
- **`PlanningTime_us`:** Integrated high-precision timers to profile the microsecond-level execution wall-clock time spent purely in the plan enumeration phase.
- **Outcome:** This allowed for direct comparisons between theoretical pair evaluations and actual wall-clock processing overhead for different DP algorithms.

## 2. Bug Fixes
- **`Interpreter.hpp`:** Fixed a compilation syntax error involving `const_cast` inside the `at()` method to ensure smooth builds and execution across the engine.

## 3. TPC-DS Benchmarking Framework (`benchmark/tpcds/`)
A complete, automated benchmarking pipeline was constructed to evaluate the database engine against complex, real-world query topologies:
- **Query Templates & Flat Queries:** Adapted TPC-DS SQL queries into a "flat" format (simplifying unsupported features like CTEs) to test the engine's core flat `SELECT-FROM-WHERE-GROUP BY` capabilities.
- **Data Loaders:** Created utilities and schemas to easily generate and load TPC-DS CSV data into the engine.
- **Benchmarking Scripts (`run_benchmark.py`):** Built Python automation to run queries across different DP algorithms, capture the exposed metrics (`CCPCounter`, `PlanningTime_us`, `Cost`), and automatically compare performance disparities (e.g., discovering the high subset-generation overhead in `DPsub` compared to `DPccp`).

## 4. SQL Feature Compatibility Scanner (`benchmark/tpcds_error_scanner.py`)
To systematically identify why certain TPC-DS queries were failing during evaluation, an automated SQL compatibility scanner was engineered:
- **Feature Probing:** Tests 59 distinct SQL features (like `LEFT JOIN`, `BETWEEN`, Window Functions) individually against the engine in a rapid `--dryrun` mode.
- **Automated Logging:** Captures `stderr` and determines exactly which features trigger parser errors, semantic failures (e.g., correlated subquery crashes), or missing schema components.
- **`mutable_error_log.md`:** Auto-generated a clean, Markdown-formatted error log detailing exactly what is supported (e.g., inner comma joins, basic aggregates) and what is unsupported, acting as a roadmap for future SQL parser enhancements.

---

### Key Takeaway
The combination of core C++ metric instrumentation and automated Python testing pipelines exposed critical insights into `mutable`'s optimizer performance and current SQL feature limitations, establishing a robust foundation for future query optimization research on the engine.
