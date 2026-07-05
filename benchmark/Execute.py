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

def run_query_on_mutable(builddir: str, yml: dict, suite: str, path_to_data: str, config_name: str, config: dict, case_name: str, query: str, join_implementations: str = None, times: bool = False, plan_enumerator: str = None) -> None:
    path_to_binary = os.path.join(builddir, 'bin', 'shell')
    if not os.path.isfile(path_to_binary):
        print(f"Error: mutable binary not found at '{path_to_binary}'")
        return

    # Initialize connector to reuse DDL/import generator
    conn = mutable.Mutable({'path_to_binary': path_to_binary})
    
    # Generate setup DDL + COPY/IMPORT statements
    imports = conn.get_setup_statements(suite, path_to_data, yml.get('data'), case_name)
    import_str = '\n'.join(imports)
    query_str = import_str + '\n' + query + '\n'
    
    # Build command
    command = [path_to_binary]
    
    # Extract config args
    binargs = yml.get('binargs', None)
    supplementary_args = yml.get('args', None)
    
    if binargs:
        command.extend(binargs.split(' '))
    if supplementary_args:
        command.extend(supplementary_args.split(' '))
    if config and 'args' in config:
        command.extend(config['args'].split(' '))
        
    # Strip timing/benchmark/quiet flags to ensure query outputs are shown
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
    
    print(f"Executing: {' '.join(command)}")
    print(f"--- QUERY SQL ---")
    print(query.strip())
    print("-----------------")
    print("--- OUTPUT ---")
    
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=os.getcwd())
    try:
        proc_out, proc_err = process.communicate(query_str.encode('latin-1'), timeout=120)
        output_str = proc_out.decode('latin-1')
        print(output_str)
        print_simplified_join_order(output_str)
        if proc_err:
            print("--- STDERR ---")
            print(proc_err.decode('latin-1'))
    except subprocess.TimeoutExpired:
        print("Error: Query timed out after 120 seconds")
        process.terminate()
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            process.kill()
    print("========================================================================\n")

def run_query_on_duckdb(yml: dict, config_name: str, case_name: str, query: str) -> None:
    duckdb_cli = 'benchmark/database_connectors/duckdb'
    if not os.path.isfile(duckdb_cli):
        duckdb_cli = 'duckdb'  # fallback to system path
        
    tmp_db = 'tmp.duckdb'
    if os.path.exists(tmp_db):
        os.remove(tmp_db)
        
    conn = duckdb.DuckDB({'path_to_binary': duckdb_cli})
    
    try:
        complete_tables, actual_tables = conn.generate_create_table_stmts(yml.get('data', {}))
        
        # Build statements list
        statements = []
        statements.extend(complete_tables)
        statements.extend(actual_tables)
        
        # Fill actual tables from complete tables with scale factor
        for table_name, table in yml.get('data', {}).items():
            statements.append(f'DELETE FROM "{table_name}";')
            drop_indexes = conn.generate_drop_index_stmts(table.get('indexes', {}))
            statements.extend(drop_indexes)
            
            sf = 1
            if 'scale_factors' in table:
                scale_factors = table['scale_factors']
                if isinstance(scale_factors, (float, int)):
                    sf = scale_factors
                elif case_name in scale_factors:
                    sf = scale_factors[case_name]
            
            header = int(table.get('header', 0))
            num_rows = round((table['lines_in_file'] - header) * sf)
            statements.append(f'INSERT INTO "{table_name}" SELECT * FROM "{table_name}_complete" LIMIT {num_rows};')
            create_indexes = conn.generate_create_index_stmts(table_name, table.get('indexes', {}))
            statements.extend(create_indexes)
            
        statements.append(query)
        combined_query = '\n'.join(statements) + '\n'
        
        command = [duckdb_cli, tmp_db]
        
        print(f"Executing: {' '.join(command)}")
        print(f"--- QUERY SQL ---")
        print(query.strip())
        print("-----------------")
        print("--- OUTPUT ---")
        
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=os.getcwd())
        proc_out, proc_err = process.communicate(combined_query.encode('utf-8'), timeout=120)
        print(proc_out.decode('utf-8'))
        if proc_err:
            print("--- STDERR ---")
            print(proc_err.decode('utf-8'))
    except Exception as e:
        print(f"Error running DuckDB: {e}")
    finally:
        if os.path.exists(tmp_db):
            os.remove(tmp_db)
    print("========================================================================\n")

def run_query_on_postgresql(yml: dict, case_name: str, query: str) -> None:
    db_options = {'dbname': 'benchmark_tmp', 'user': 'postgres'}
    
    conn = postgresql.PostgreSQL({})
    
    print(f"Connecting to PostgreSQL (db={db_options['dbname']}, user={db_options['user']})...")
    print(f"--- QUERY SQL ---")
    print(query.strip())
    print("-----------------")
    print("--- OUTPUT ---")
    
    # We will attempt to run it using psql CLI
    tmp_sql_file = 'tmp.sql'
    try:
        # Create database setup statements
        statements = []
        statements.append(f"DROP DATABASE IF EXISTS {db_options['dbname']};")
        statements.append(f"CREATE DATABASE {db_options['dbname']};")
        
        # We need to run drop/create database first
        # Since psql cannot run CREATE DATABASE in a transaction block, we run it on default 'postgres' database
        setup_cmd = f"psql -U {db_options['user']} -d postgres -c \"DROP DATABASE IF EXISTS {db_options['dbname']}; CREATE DATABASE {db_options['dbname']};\""
        subprocess.run(setup_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Now create tables in the new database
        conn_tables = []
        for table_name, table in yml.get('data', {}).items():
            columns = Connector.parse_attributes(conn.POSTGRESQL_TYPE_PARSER, table['attributes'])
            complete_table_name = table_name + "_complete"
            conn_tables.append(f"CREATE UNLOGGED TABLE \"{complete_table_name}\" {columns};")
            
            # Copy data
            abs_path = os.path.abspath(table['file'])
            copy_stmt = f"COPY \"{complete_table_name}\" FROM '{abs_path}'"
            if 'delimiter' in table:
                delim = table['delimiter'].replace("'", "")
                copy_stmt += f" WITH DELIMITER '{delim}'"
            if 'format' in table:
                copy_stmt += f" {table['format'].upper()}"
            if 'header' in table:
                copy_stmt += ' HEADER' if table['header'] == 1 else ''
            copy_stmt += ";"
            conn_tables.append(copy_stmt)
            
            # Actual table
            conn_tables.append(f"CREATE UNLOGGED TABLE \"{table_name}\" {columns};")
            
            # Fill with scale factor
            sf = 1
            if 'scale_factors' in table:
                scale_factors = table['scale_factors']
                if isinstance(scale_factors, (float, int)):
                    sf = scale_factors
                elif case_name in scale_factors:
                    sf = scale_factors[case_name]
            header = int(table.get('header', 0))
            num_rows = round((table['lines_in_file'] - header) * sf)
            conn_tables.append(f"INSERT INTO \"{table_name}\" SELECT * FROM \"{complete_table_name}\" LIMIT {num_rows};")
            
            if 'indexes' in table:
                create_indexes = conn.generate_create_index_stmts(table_name, table['indexes'])
                conn_tables.extend(create_indexes)
                
        conn_tables.append(query)
        
        with open(tmp_sql_file, 'w') as f:
            f.write('\n'.join(conn_tables) + '\n')
            
        cmd = f"psql -U {db_options['user']} -d {db_options['dbname']} -f {tmp_sql_file}"
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        proc_out, proc_err = process.communicate(timeout=120)
        
        print(proc_out.decode('utf-8'))
        if proc_err:
            print("--- STDERR ---")
            print(proc_err.decode('utf-8'))
            
    except Exception as e:
        print(f"Error running PostgreSQL: {e}")
    finally:
        if os.path.exists(tmp_sql_file):
            os.remove(tmp_sql_file)
            
        # Clean up database
        cleanup_cmd = f"psql -U {db_options['user']} -d postgres -c \"DROP DATABASE IF EXISTS {db_options['dbname']};\""
        subprocess.run(cleanup_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
    print("========================================================================\n")

def run_query_on_hyper(yml: dict, case_name: str, query: str) -> None:
    print("HyPer execution not directly supported for outputting query results.")
    print("Here is the query that would be run:")
    print(query.strip())
    print("========================================================================\n")

def main():
    parser = argparse.ArgumentParser(description='Run .yml queries and print the results.')
    parser.add_argument('path', nargs='*', help='directory path of a benchmark suite or path to single experiment to be run')
    parser.add_argument('-s', '--system', dest='system', default='mutable', choices=['mutable', 'DuckDB', 'PostgreSQL', 'HyPer'],
                        help='database system to run the query on')
    parser.add_argument('-b', '--builddir', help='path to the build directory (defaults to \'build/release\')',
                        default=os.path.join('build', 'release'), type=str, metavar='PATH')
    parser.add_argument('--config', dest='config', default=None, help='run only a specific configuration (if the system has configurations)')
    parser.add_argument('--case', dest='case', default=None, help='run only a specific case')
    parser.add_argument('--join-implementations', dest='join_implementations', default=None, help='join implementations to consider (NestedLoops, SimpleHash, SortMerge)')
    parser.add_argument('-t', '--times', dest='times', action='store_true', help='output plan and execution timings')
    parser.add_argument('--plan-enumerator', dest='plan_enumerator', default=None, help='override plan enumerator (e.g. DPsize, DPsub)')
    args = parser.parse_args()

    # Determine files to process
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
        print(f"Processing experiment file: {path_to_file}")
        if not validate_schema(path_to_file, YML_SCHEMA):
            continue

        with open(path_to_file, 'r') as yml_file:
            yml = yaml.safe_load(yml_file)

        suite = yml.get('suite')
        path_to_data = os.path.join('benchmark', suite, 'data')
        
        # Populate lines_in_file in yml table structure if missing
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
                else:
                    print(f"Warning: Table file '{p}' not found.")

        # Check if the requested system is defined in this experiment
        systems_dict = yml.get('systems', {})
        if args.system not in systems_dict:
            print(f"System '{args.system}' not configured in '{path_to_file}'. Skipping.")
            continue

        sys_config = systems_dict[args.system]
        cases = sys_config.get('cases', {})
        
        # Check if this is a repeat script rather than simple cases
        if 'script' in cases:
            print(f"Repeat scripts are not standard SQL query cases. Running bash script:")
            # For repeat, it's a script executed multiple times
            script = cases['script']
            configs = sys_config.get('configurations', {'default': {}})
            for config_name, config in configs.items():
                if args.config and config_name != args.config:
                    continue
                variables = [f'{key}={value}' for key, value in config.get('variables', {}).items()]
                cmd = ['env', 'N=1', 'RANDOM=42'] + variables + ['/bin/bash']
                print(f"Running script under config '{config_name}':")
                process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                proc_out, proc_err = process.communicate(script.encode('utf-8'))
                print(proc_out.decode('utf-8'))
                if proc_err:
                    print("--- STDERR ---")
                    print(proc_err.decode('utf-8'))
            continue

        # Iterate configurations and cases
        if args.system == 'mutable':
            configs = sys_config.get('configurations', {})
            if not configs:
                # If no configurations defined, run with empty default
                configs = {'default': {}}
            
            for config_name, config in configs.items():
                if args.config and config_name != args.config:
                    continue
                
                for case_name, query in cases.items():
                    if args.case and str(case_name) != args.case:
                        continue
                    
                    print(f"=== System: {args.system} | Config: {config_name} | Case: {case_name} ===")
                    run_query_on_mutable(args.builddir, yml, suite, path_to_data, config_name, config, str(case_name), query,
                                         join_implementations=args.join_implementations, times=args.times, plan_enumerator=args.plan_enumerator)
        else:
            # DuckDB, PostgreSQL, HyPer do not have configurations in systems yml
            for case_name, query in cases.items():
                if args.case and str(case_name) != args.case:
                    continue
                
                print(f"=== System: {args.system} | Case: {case_name} ===")
                if args.system == 'DuckDB':
                    run_query_on_duckdb(yml, 'default', str(case_name), query)
                elif args.system == 'PostgreSQL':
                    run_query_on_postgresql(yml, str(case_name), query)
                elif args.system == 'HyPer':
                    run_query_on_hyper(yml, str(case_name), query)

if __name__ == '__main__':
    main()
