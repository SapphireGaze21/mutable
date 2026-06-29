#!/usr/bin/env python3
import yaml
import os
import subprocess
import glob
import re

# Extract topology from statistics
def extract_topology(stdout):
    csg = 0
    ccp = 0
    for line in stdout.split('\n'):
        if "CSGs" in line and "CCPs" in line:
            m = re.search(r'(\d+)\s+CSGs,\s+(\d+)\s+CCPs', line)
            if m:
                csg = int(m.group(1))
                ccp = int(m.group(2))
    return csg, ccp

def parse_metrics(stdout):
    cost = None
    time_taken = None
    evals = None
    ccp_evals = None
    planning_us = None
    
    for line in stdout.split('\n'):
        if "Est. total cost:" in line:
            cost = float(line.split(":")[1].strip())
        elif "Execute query:" in line:
            time_taken = float(line.split(":")[1].strip())
        elif "EvaluatedCounter =" in line:
            evals = int(line.split("=")[1].strip())
        elif "CCPCounter =" in line:
            ccp_evals = int(line.split("=")[1].strip())
        elif "PlanningTime_us =" in line:
            planning_us = int(line.split("=")[1].strip())
            
    return cost, time_taken, evals, ccp_evals, planning_us

def extract_join_plan(stdout):
    plan_lines = []
    in_plan = False
    
    for line in stdout.split('\n'):
        if "ProjectionOperator" in line:
            in_plan = True
            
        if in_plan:
            if line.strip() == "0 rows" or "Construct the query graph" in line or line.startswith("Est. total cost"):
                break
                
            clean_line = re.sub(r'\s*\{\[.*?\]\}\s*<\d+>', '', line)
            clean_line = clean_line.rstrip()
            if clean_line:
                plan_lines.append(clean_line)
                
    return "\n".join(plan_lines)

def run_query(ddl, query, enumerator):
    full_query = f"{ddl} {query}"
    
    with open("temp_eval_query.sql", "w") as f:
        f.write(full_query)
        
    cmd = [
        "build/debug_shared/bin/shell",
        "--benchmark",
        "--quiet",
        "--statistics",
        "--plan",
        "--backend", "Interpreter",
        "--plan-enumerator", enumerator,
        "--cardinality-estimator", "CartesianProduct",
        "--dryrun",
        "temp_eval_query.sql"
    ]
    
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = process.communicate(timeout=120)
    
    if process.returncode != 0:
        return False, out + "\nSTDERR:\n" + err
        
    return True, out + "\nSTDERR:\n" + err

def run_all_queries_once(ddl, queries_by_algo):
    """
    Build one SQL file with:
      1. DDL + IMPORT (once)
      2. For each (query, algo): USE db; SET enumerator; run query
    Parse output by splitting on markers we inject via SELECT statements.
    Instead run separately per algo but reuse the same import data by
    combining all queries for each algo into one shell call.
    """
    results = {}  # (query_name, algo) -> (ok, output)
    
    algorithms = list(queries_by_algo.keys())
    query_names = list(list(queries_by_algo.values())[0].keys())
    
    for algo in algorithms:
        # One SQL file: import once, run all queries for this algo
        lines = [ddl]
        markers = []
        for qname, qsql in queries_by_algo[algo].items():
            lines.append(qsql)
            markers.append(qname)
        
        combined_sql = "\n".join(lines)
        with open("temp_eval_query.sql", "w") as f:
            f.write(combined_sql)
        
        print(f"  -> Running {algo} (all queries in one pass)...", flush=True)
        
        cmd = [
            "build/debug_shared/bin/shell",
            "--benchmark",
            "--quiet",
            "--statistics",
            "--plan",
            "--backend", "Interpreter",
            "--plan-enumerator", algo,
            "--cardinality-estimator", "CartesianProduct",
            "--dryrun",
            "temp_eval_query.sql"
        ]
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, err = process.communicate(timeout=600)
        ok = (process.returncode == 0)
        
        # Split combined output into per-query blocks.
        # Our PlanEnumerator instrumentation emits exactly one "EvaluatedCounter =" per query.
        # Split on "Est. total cost:" — one per query in the combined output.
        parts = re.split(r'(Est\. total cost:[^\n]*\n)', out)
        # parts = [before_q1_cost, q1_cost_line, between, q2_cost_line, ...]
        # Pair each cost line with the plan text before it and stats after it
        plan_blocks = []
        i = 0
        while i < len(parts):
            if re.match(r'Est\. total cost:', parts[i]):
                # parts[i] = cost line, parts[i-1] = plan before it, parts[i+1] = stats after
                plan_before = parts[i-1] if i > 0 else ''
                stats_after = parts[i+1] if i+1 < len(parts) else ''
                # Only take stats up to the next plan (next ProjectionOperator)
                next_plan = re.search(r'ProjectionOperator', stats_after)
                if next_plan:
                    stats_after = stats_after[:next_plan.start()]
                plan_blocks.append(plan_before + parts[i] + stats_after)
                i += 2
            else:
                i += 1
        
        for i, qname in enumerate(markers):
            if not ok:
                results[(qname, algo)] = (False, out + "\nSTDERR:\n" + err)
            elif i < len(plan_blocks):
                results[(qname, algo)] = (True, plan_blocks[i] + "\nSTDERR:\n" + err)
            else:
                results[(qname, algo)] = (False, f"No output block for query {qname} (got {len(plan_blocks)} blocks for {len(markers)} queries)\nFull output:\n{out[:500]}\nSTDERR:\n" + err)
    
    return results

def main():
    target_queries = [
        "query12.sql", "query15.sql",   # Chain
        "query36.sql", "query27.sql",   # Star
        "query23.sql", "query25.sql", "query77.sql"  # Complex/Cyclic
    ]
    
    query_dir = "benchmark/tpcds/query_templates_flat"
    
    # Read the real schema which has the IMPORT CSV statements
    with open("benchmark/tpcds/data/csvs/mutable_schema.sql", "r") as f:
        ddl = f.read()

    algorithms = ["DPsize", "DPsizeOpt", "DPsub", "DPccp"]
    
    print("Evaluating 7 Target TPCDS Queries with Real Data...\n")
    
    # Load query SQL
    query_sqls = {}
    for qf in target_queries:
        with open(f"{query_dir}/{qf}") as f:
            query_sqls[qf] = f.read().strip()
    
    # Build queries_by_algo structure
    queries_by_algo = {algo: {qf: query_sqls[qf] for qf in target_queries} for algo in algorithms}
    
    # Run all queries for each algo in one shell pass
    all_results = run_all_queries_once(ddl, queries_by_algo)
    
    topologies = {}
    
    for qf in target_queries:
        query = query_sqls[qf]
        tables = query.upper().split("WHERE")[0].split("FROM")[1].split(",")
        num_tables = len(tables)
        
        print(f"\n[{qf}] {num_tables} tables")
        
        results = {}
        success_all = True
        
        for algo in algorithms:
            ok, out = all_results.get((qf, algo), (False, "No result"))
            cost, time_val, evals, ccp_evals, planning_us = parse_metrics(out)
            
            if not ok or cost is None:
                print(f"  FAILED for {algo}: {out[:200]}")
                success_all = False
                break
            
            csg, ccp = extract_topology(out)
            plan = extract_join_plan(out)
            results[algo] = {
                "cost": cost, "time": time_val,
                "evals": evals, "ccp_evals": ccp_evals,
                "planning_us": planning_us,
                "csg": csg, "ccp": ccp, "plan": plan
            }
        
        if not success_all:
            continue
        
        costs = [res["cost"] for res in results.values()]
        same_cost = all(c == costs[0] for c in costs)
        plans = [res["plan"] for res in results.values()]
        same_plan = all(p == plans[0] for p in plans)
        
        ref = results["DPsub"]
        topo_key = (num_tables, ref["csg"], ref["ccp"])
        if topo_key not in topologies:
            topologies[topo_key] = []
        topologies[topo_key].append({
            "query": qf, "results": results,
            "same_cost": same_cost, "same_plan": same_plan
        })
    
    # Output Results
    print("\n" + "="*80)
    print("TOPOLOGY REPORT AND EVALUATION WITH REAL TPCDS DATA")
    print("="*80)
    
    for topo_key, qs in topologies.items():
        n, csg, ccp = topo_key
        topo_name = "Complex/Cyclic"
        if csg == (n * (n+1) // 2):
            topo_name = "Chain"
        elif csg == (2**(n-1) + n - 1):
            topo_name = "Star"
        elif csg == (2**n - 1):
            topo_name = "Clique"
        
        print(f"\n--- {topo_name}: {n} Tables, {csg} CSGs, {ccp} CCPs ---")
        
        for q in qs:
            print(f"\n  Query: {q['query']}")
            print(f"  Cost equality across all DP algos: {'YES' if q['same_cost'] else 'NO'}")
            print(f"  Plan structure equality:           {'YES' if q['same_plan'] else 'NO'}")
            print("  Algorithm Performance:")
            res = q['results']
            for algo in algorithms:
                r = res[algo]
                eval_str = f", Evaluated={r['evals']}, CCP_Evaluated={r['ccp_evals']}" if r['evals'] is not None else ""
                plan_t = f", PlanningTime={r['planning_us']}µs" if r.get('planning_us') is not None else ""
                print(f"    - {algo:<10}: Cost = {r['cost']:<20}{eval_str}{plan_t}")
            
            if res["DPsizeOpt"]["evals"] and res["DPsize"]["evals"]:
                saved = res["DPsize"]["evals"] - res["DPsizeOpt"]["evals"]
                print(f"  -> DPsizeOpt saved {saved} pair evaluations vs DPsize")
            
            print(f"\n  Join Plan (DPsize):")
            for line in res["DPsize"]["plan"].split("\n"):
                if line.strip():
                    # Clean up the schema noise — just show operator structure
                    clean = re.sub(r'\{.*?\}', '', line)
                    clean = re.sub(r'<[\d.e+]+>', '', clean).rstrip()
                    if clean.strip():
                        print(f"  {clean}")

if __name__ == "__main__":
    main()
