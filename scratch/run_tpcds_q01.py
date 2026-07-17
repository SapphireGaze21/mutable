import os
import sys
import yaml
import subprocess

# Add benchmark directory to path to import mutable/Execute
sys.path.append(os.path.abspath('benchmark'))
import Execute
import database_connectors.mutable as mutable

def main():
    yml_path = 'benchmark/tpcds/q01.yml'
    with open(yml_path, 'r') as f:
        yml = yaml.safe_load(f)
    
    suite = 'TPC-DS'
    path_to_data = 'benchmark/tpcds/data'
    
    # Get the mutable SQL query
    cases = yml.get('systems', {}).get('mutable', {}).get('cases', {})
    query = cases.get(1)
    
    path_to_binary = 'build/release-v8/bin/shell'
    conn = mutable.Mutable({'path_to_binary': path_to_binary})
    
    imports = conn.get_setup_statements(suite, path_to_data, yml.get('data'), '1')
    import_str = '\n'.join(imports)
    query_str = import_str + '\n' + query + '\n'
    
    # Write the full SQL to a temporary file
    sql_file = 'scratch/q01_run.sql'
    os.makedirs(os.path.dirname(sql_file), exist_ok=True)
    with open(sql_file, 'w') as f:
        f.write(query_str)
        
    print(f"SQL file written to {sql_file}")
    
    command = [
        path_to_binary,
        '--backend', 'WasmV8',
        '--data-layout', 'PAX4M',
        '--join-implementations', 'SimpleHash',
        '--times',
        '-'
    ]
    
    print(f"Running command: {' '.join(command)}")
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc_out, proc_err = process.communicate(query_str.encode('latin-1'))
    
    print("--- STDOUT ---")
    print(proc_out.decode('latin-1'))
    print("--- STDERR ---")
    print(proc_err.decode('latin-1'))

if __name__ == '__main__':
    main()
