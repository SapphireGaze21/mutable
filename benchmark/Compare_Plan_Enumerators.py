#!/usr/bin/env python3
import sys
import os
import argparse
import glob
import yaml
import subprocess
import re

# Add the directory containing this script to the python path to allow importing local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_connectors import mutable, postgresql, hyper, duckdb, connector
from database_connectors.connector import *
from benchmark_utils import *

try:
    import yamale
    HAS_YAMALE = True
except ImportError:
    HAS_YAMALE = False

try:
    from typeguard import typechecked
except ImportError:
    def typechecked(func):
        return func

YML_SCHEMA: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_schema.yml')

def validate_schema(path_to_file: str, path_to_schema: str) -> bool:
    if not HAS_YAMALE:
        return True
    if not os.path.exists(path_to_schema):
        return True
    schema = yamale.make_schema(path_to_schema)
    data = yamale.make_data(path_to_file)
    try:
        yamale.validate(schema, data)
    except ValueError as e:
        errors = '\n'.join([f'  - {err.strip()}' for err in str(e).split('\n')[1:]])
        print(f'Benchmark file "{path_to_file}" violates schema:\n{errors}')
        return False
    return True

def print_simplified_join_order(output_str: str) -> None:
    lines = output_str.splitlines()
    nodes = []
    op_pattern = re.compile(r'^([\s`|]*)([A-Za-z]+Operator)(.*)')
    for line in lines:
        m = op_pattern.match(line)
        if m:
            prefix, op, details = m.groups()
            depth = len(prefix)
            table_name = None
            if op == 'ScanOperator':
                m_table = re.search(r'\(([^) ]+)', details)
                if m_table:
                    table_name = m_table.group(1)
            nodes.append({
                'depth': depth,
                'op': op,
                'table': table_name,
                'children': []
            })
            
    if not nodes:
        return
        
    stack = []
    root = None
    for node in nodes:
        while stack and stack[-1]['depth'] >= node['depth']:
            stack.pop()
        if stack:
            stack[-1]['children'].append(node)
        else:
            root = node
        stack.append(node)
        
    if not root:
        return
        
    tables = []
    def collect_tables(n):
        if n['op'] == 'ScanOperator' and n['table']:
            if n['table'] not in tables:
                tables.append(n['table'])
        for child in n['children']:
            collect_tables(child)
            
    collect_tables(root)
    if not tables:
        return
        
    table_letters = {t: chr(ord('A') + i) for i, t in enumerate(tables)}
    
    def format_join_order(n, mapping):
        if n['op'] == 'ScanOperator':
            return mapping.get(n['table'], n['table'])
        elif n['op'] == 'JoinOperator':
            if len(n['children']) == 2:
                left = format_join_order(n['children'][0], mapping)
                right = format_join_order(n['children'][1], mapping)
                return f"({left} ⋈ {right})"
            elif len(n['children']) == 1:
                return format_join_order(n['children'][0], mapping)
            else:
                return "Join"
        else:
            if len(n['children']) == 1:
                return format_join_order(n['children'][0], mapping)
            elif len(n['children']) > 1:
                parts = [format_join_order(c, mapping) for c in n['children']]
                return ", ".join(parts)
            else:
                return ""
                
    join_order_names = format_join_order(root, {})
    join_order_letters = format_join_order(root, table_letters)
    
    print("--- SIMPLIFIED JOIN ORDER ---")
    print("Table Mapping:")
    for t, letter in table_letters.items():
        print(f"  {letter}: {t}")
    print("\nJoin Order:")
    print(f"  {join_order_letters}")

    # Parse and display costs if present
    cost_pattern = re.compile(r'\(cumulative cost\s+([0-9.e+-]+)\)', re.IGNORECASE)
    all_costs = [float(c) for c in cost_pattern.findall(output_str)]
    if all_costs:
        plan_cost = max(all_costs)
        join_costs = [float(c) for c in re.findall(r'wasm::\w*Join.*\(cumulative cost\s+([0-9.e+-]+)\)', output_str, re.IGNORECASE)]
        
        def format_cost(val: float) -> str:
            if val.is_integer():
                return str(int(val))
            return f"{val:g}"
            
        print(f"\nPlan Cost: {format_cost(plan_cost)}")
        if join_costs:
            print(f"Join Cost: {format_cost(max(join_costs))}")

    print("-----------------------------")

def run_query_on_mutable(builddir: str, yml: dict, suite: str, path_to_data: str, config_name: str, config: dict, case_name: str, query: str, join_implementations: str = None, times: bool = False, plan_enumerator: str = None) -> dict:
    path_to_binary = os.path.join(builddir, 'bin', 'shell')
    if not os.path.isfile(path_to_binary):
        print(f"Error: mutable binary not found at '{path_to_binary}'")
        return {}

    conn = mutable.Mutable({'path_to_binary': path_to_binary})
    imports = conn.get_setup_statements(suite, path_to_data, yml.get('data'), case_name)
    import_str = '\n'.join(imports)
    query_str = import_str + '\n' + query + '\n'
    
    command = [path_to_binary]
    
    binargs = yml.get('binargs', None)
    supplementary_args = yml.get('args', None)
    
    if binargs:
        command.extend(binargs.split(' '))
    if supplementary_args:
        command.extend(supplementary_args.split(' '))
    if config and 'args' in config:
        command.extend(config['args'].split(' '))
        
    filtered_command = []
    for arg in command:
        if arg not in ['--benchmark', '--times', '-t', '--quiet', '-q']:
            filtered_command.append(arg)
    command = filtered_command

    if plan_enumerator:
        new_command = []
        skip_next = False
        for arg in command:
            if skip_next:
                skip_next = False
                continue
            if arg == '--plan-enumerator':
                skip_next = True
                continue
            if arg.startswith('--plan-enumerator='):
                continue
            new_command.append(arg)
        command = new_command
        command.extend(['--plan-enumerator', plan_enumerator])

    if join_implementations:
        command.extend(['--join-implementations', join_implementations])
    if times:
        command.append('--times')
    
    command.append('-')
    
    counters = {'EvaluatedCounter': '-', 'CCPCounter': '-', 'PlanningTime_us': '-'}
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=os.getcwd())
    try:
        proc_out, proc_err = process.communicate(query_str.encode('latin-1'), timeout=120)
        output_str = proc_out.decode('latin-1')
        
        print_simplified_join_order(output_str)
        
        for line in output_str.splitlines():
            if any(term in line for term in ['EvaluatedCounter =', 'CCPCounter =', 'PlanningTime_us =']):
                print(line)
                if 'EvaluatedCounter =' in line:
                    counters['EvaluatedCounter'] = line.split('=')[1].strip()
                elif 'CCPCounter =' in line:
                    counters['CCPCounter'] = line.split('=')[1].strip()
                elif 'PlanningTime_us =' in line:
                    counters['PlanningTime_us'] = line.split('=')[1].strip()
                
        if proc_err:
            err_str = proc_err.decode('latin-1')
            if 'Exception' in err_str or 'error' in err_str.lower() or 'terminate called' in err_str:
                print("--- STDERR ---")
                print(err_str)
    except subprocess.TimeoutExpired:
        print("Error: Query timed out after 120 seconds")
        process.terminate()
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            process.kill()
    return counters

def main():
    parser = argparse.ArgumentParser(description='Compare plan enumerator strategies and output simplified join order and counters.')
    parser.add_argument('path', nargs='*', help='directory path of a benchmark suite or path to single experiment to be run')
    parser.add_argument('-b', '--builddir', help='path to the build directory (defaults to \'build/release\')',
                        default=os.path.join('build', 'release'), type=str, metavar='PATH')
    parser.add_argument('--config', dest='config', default=None, help='run only a specific configuration (if the system has configurations)')
    parser.add_argument('--case', dest='case', default=None, help='run only a specific case')
    parser.add_argument('--join-implementations', dest='join_implementations', default=None, help='join implementations to consider (NestedLoops, SimpleHash, SortMerge)')
    parser.add_argument('-t', '--times', dest='times', action='store_true', help='output plan and execution timings')
    args = parser.parse_args()

    if not args.path:
        benchmark_files = sorted(glob.glob(os.path.join('benchmark', '**', '[!_]*.yml'), recursive=True))
    else:
        benchmark_files = []
        for path in sorted(set(args.path)):
            if os.path.isfile(path):
                benchmark_files.append(path)
            else:
                benchmark_files.extend(glob.glob(os.path.join(path, '**', '[!_]*.yml'), recursive=True))
    benchmark_files = sorted(list(set(benchmark_files)))

    if not benchmark_files:
        print("No experiment (.yml) files found.")
        sys.exit(1)

    for path_to_file in benchmark_files:
        if not validate_schema(path_to_file, YML_SCHEMA):
            continue

        with open(path_to_file, 'r') as yml_file:
            yml = yaml.safe_load(yml_file)

        suite = yml.get('suite')
        path_to_data = os.path.join('benchmark', suite, 'data')
        
        info_data = yml.get('data')
        if info_data:
            for table_name, table in info_data.items():
                p = table.get('file', os.path.join(path_to_data, f"{table_name}.csv"))
                if os.path.isfile(p):
                    if 'lines_in_file' not in table:
                        if 'lines_in_file' in yml:
                            table['lines_in_file'] = yml['lines_in_file']
                        else:
                            table['lines_in_file'] = int(os.popen(f"wc -l < {p}").read())

        systems_dict = yml.get('systems', {})
        if 'mutable' not in systems_dict:
            continue

        sys_config = systems_dict['mutable']
        cases = sys_config.get('cases', {})
        
        if 'script' in cases:
            continue

        configs = sys_config.get('configurations', {})
        if not configs:
            configs = {'default': {}}
        
        for config_name, config in configs.items():
            if args.config and config_name != args.config:
                continue
            
            for case_name, query in cases.items():
                if args.case and str(case_name) != args.case:
                    continue
                
                results = []
                enumerators = ['DPsize', 'DPsub', 'DPccp', 'DPsizeOpt']
                for enum in enumerators:
                    print(f"=== {enum} ===")
                    cnt = run_query_on_mutable(args.builddir, yml, suite, path_to_data, config_name, config, str(case_name), query,
                                               join_implementations=args.join_implementations, times=args.times, plan_enumerator=enum)
                    results.append((enum, cnt))
                    print()
                
                # Print summary table
                print("=== Summary of Plan Enumerators ===")
                headers = ["Algorithm", "EvaluatedCounter", "CCPCounter", "PlanningTime_us"]
                col_widths = [15, 18, 12, 16]
                
                # ASCII separator line
                sep = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
                print(sep)
                
                # Print Header
                header_str = "|" + "|".join(f" {h:<{col_widths[i]}} " for i, h in enumerate(headers)) + "|"
                print(header_str)
                print(sep)
                
                # Print Rows
                for enum, cnt in results:
                    row_data = [
                        enum,
                        cnt.get('EvaluatedCounter', '-'),
                        cnt.get('CCPCounter', '-'),
                        cnt.get('PlanningTime_us', '-')
                    ]
                    row_str = "|" + "|".join(f" {str(val):<{col_widths[i]}} " for i, val in enumerate(row_data)) + "|"
                    print(row_str)
                print(sep)
                print()

if __name__ == '__main__':
    main()
