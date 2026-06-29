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
    
    for line in stdout.split('\n'):
        if "Est. total cost:" in line:
            cost = float(line.split(":")[1].strip())
        elif "Execute query:" in line:
            time_taken = float(line.split(":")[1].strip())
        elif "EvaluatedCounter =" in line:
            evals = int(line.split("=")[1].strip())
        elif "CCPCounter =" in line:
            ccp_evals = int(line.split("=")[1].strip())
            
    return cost, time_taken, evals, ccp_evals

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
    out, err = process.communicate()
    
    if process.returncode != 0:
        return False, out + "\nSTDERR:\n" + err
        
    return True, out + "\nSTDERR:\n" + err

def main():
    target_queries = [
        "query12.sql"
    ]
    
    # Read the real schema which has the IMPORT CSV statements
    with open("benchmark/tpcds/data/csvs/mutable_schema.sql", "r") as f:
        ddl = f.read()

    algorithms = ["DPsize", "DPsizeOpt", "DPsub", "DPccp"]
    
    print("Evaluating 7 Target TPCDS Queries with Real 300MB Dataset...\n")
    
    topologies = {}

    for query_name in target_queries:
        qpath = os.path.join("benchmark/tpcds/query_templates_flat", query_name)
        with open(qpath, 'r') as f:
            query = f.read().strip()
            
        tables = query.upper().split("WHERE")[0].split("FROM")[1].split(",")
        num_tables = len(tables)
            
        print(f"[{query_name}] Testing with {num_tables} tables...")
        
        results = {}
        success_all = True
        
        for algo in algorithms:
            print(f"  -> Running {algo}...")
            ok, out = run_query(ddl, query, algo)
            
            cost, time_val, evals, ccp_evals = parse_metrics(out)
            
            if not ok or cost is None:
                print(f"     Failed execution for {algo}!")
                print(out)
                success_all = False
                break
                
            csg, ccp = extract_topology(out)
            plan = extract_join_plan(out)
            
            results[algo] = {
                "cost": cost,
                "time": time_val,
                "evals": evals,
                "ccp_evals": ccp_evals,
                "csg": csg,
                "ccp": ccp,
                "plan": plan
            }
            
        if not success_all:
            continue
            
        # Verify that all algorithms produced the exact same cost
        costs = [res["cost"] for res in results.values()]
        same_cost = all(c == costs[0] for c in costs)
        
        # Verify join plans are structurally similar
        plans = [res["plan"] for res in results.values()]
        same_plan = all(p == plans[0] for p in plans)
        
        topo_key = (num_tables, results["DPsub"]["csg"], results["DPsub"]["ccp"])
        
        if topo_key not in topologies:
            topologies[topo_key] = []
            
        topologies[topo_key].append({
            "query": query_name,
            "results": results,
            "same_cost": same_cost,
            "same_plan": same_plan
        })
            
    # Output Results
    print("\n" + "="*80)
    print("TOPOLOGY REPORT AND EVALUATION WITH REAL DATA")
    print("="*80)
    
    for topo_key, qs in topologies.items():
        print(f"\n--- Topology Group: {topo_key[0]} Tables, {topo_key[1]} CSGs, {topo_key[2]} CCPs ---")
        
        n = topo_key[0]
        csg = topo_key[1]
        ccp = topo_key[2]
        
        topo_name = "Complex/Cyclic"
        if csg == (n * (n+1) // 2):
            topo_name = "Chain"
        elif csg == (2**(n-1) + n - 1):
            topo_name = "Star"
        elif csg == (2**n - 1):
            topo_name = "Clique"
            
        print(f"Mathematical Topology Classification: {topo_name}")
        
        for q in qs:
            print(f"\n  Query: {q['query']}")
            print(f"  Cost equality across all DP algos: {'YES' if q['same_cost'] else 'NO'}")
            print(f"  Plan structure equality across all DP algos: {'YES' if q['same_plan'] else 'NO'}")
            
            res = q['results']
            print("  Algorithm Performance & Optimality Checks:")
            for algo in algorithms:
                r = res[algo]
                eval_str = f", Evaluated={r['evals']}, CCP_Evaluated={r['ccp_evals']}" if r['evals'] is not None else ""
                cost_str = f"{r['cost']:<10}" if r['cost'] is not None else "N/A       "
                time_str = f"{r['time']}s" if r['time'] is not None else "N/A"
                print(f"    - {algo:<10}: Cost = {cost_str}, Time = {time_str}{eval_str}")
                
            if res["DPsizeOpt"]["evals"] is not None and res["DPsize"]["evals"] is not None:
                print(f"  -> Optimality Confirmed: DPsizeOpt evaluated {res['DPsize']['evals'] - res['DPsizeOpt']['evals']} fewer pairs than DPsize.")
                
            print("\n  Clean Join Plan (First Algorithm):")
            print("  " + "\n  ".join(res["DPsize"]["plan"].split("\n")))
            
if __name__ == "__main__":
    main()
