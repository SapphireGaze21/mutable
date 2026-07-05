#!/usr/bin/env python3
import sys
import os
import argparse
import yaml
import subprocess
import re
import numpy as np

# Set matplotlib backend to Agg to work on headless terminal environments
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Add the benchmark directory to python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database_connectors import mutable

# Target queries sorted by table count
TARGET_QUERIES = [
    # (query_name, table_count)
    ('q3', 4),
    ('q1', 5),
    ('q32', 6),
    ('q8', 7),
    ('q25', 9),
    ('q19', 10),
    ('q22', 11),
    ('q24', 12),
    ('q33', 14)
]

ALGORITHMS = ['DPsize', 'DPsub', 'DPccp', 'DPsizeOpt']

def run_query_on_mutable(builddir: str, yml: dict, suite: str, path_to_data: str, config_name: str, config: dict, case_name: str, query: str, plan_enumerator: str) -> dict:
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

    # Replace plan enumerator argument
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
    command.append('-')
    
    counters = {'EvaluatedCounter': 0, 'CCPCounter': 0}
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=os.getcwd())
    try:
        proc_out, proc_err = process.communicate(query_str.encode('latin-1'), timeout=180)
        output_str = proc_out.decode('latin-1')
        
        for line in output_str.splitlines():
            if 'EvaluatedCounter =' in line:
                counters['EvaluatedCounter'] = int(line.split('=')[1].strip())
            elif 'CCPCounter =' in line:
                counters['CCPCounter'] = int(line.split('=')[1].strip())
    except subprocess.TimeoutExpired:
        print(f"Error: Query {plan_enumerator} timed out after 180 seconds")
        process.terminate()
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            process.kill()
            
    return counters

def main():
    parser = argparse.ArgumentParser(description='Run specific JOB queries on mutable and plot their join-pair counters.')
    parser.add_argument('-b', '--builddir', help='path to the build directory (defaults to \'build/release-v8\')',
                        default=os.path.join('build', 'release-v8'), type=str, metavar='PATH')
    parser.add_argument('--case', dest='case', default='a', help='run only a specific case (defaults to case a)')
    args = parser.parse_args()

    results = {}  # query -> { algo -> counter_value }

    for q_name, tbl_count in TARGET_QUERIES:
        file_path = os.path.join('benchmark', 'job', f"{q_name}.yml")
        if not os.path.isfile(file_path):
            print(f"File {file_path} not found. Skipping...")
            continue
            
        print(f"\n================ Running Query {q_name} ({tbl_count} tables) ================")
        with open(file_path, 'r') as yml_file:
            yml = yaml.safe_load(yml_file)
            
        if 'data' in yml:
            for table_name, table in yml['data'].items():
                if 'file' in table:
                    table['file'] = table['file'].replace('/data/', '/data2/')

        suite = yml.get('suite')
        path_to_data = os.path.join('benchmark', suite, 'data2')
        
        systems_dict = yml.get('systems', {})
        if 'mutable' not in systems_dict:
            print(f"Warning: mutable system config not found in {q_name}.yml. Skipping...")
            continue
            
        sys_config = systems_dict['mutable']
        cases = sys_config.get('cases', {})
        configs = sys_config.get('configurations', {})
        if not configs:
            configs = {'default': {}}
            
        config_name = list(configs.keys())[0]
        config = configs[config_name]
        
        query = cases.get(args.case)
        if not query:
            print(f"Warning: Case {args.case} not found in {q_name}.yml. Skipping...")
            continue
            
        results[q_name] = {}
        for algo in ALGORITHMS:
            print(f"Running {algo}...")
            cnt = run_query_on_mutable(args.builddir, yml, suite, path_to_data, config_name, config, args.case, query, algo)
            
            # Select counter: CCPCounter for DPccp, EvaluatedCounter for others
            if algo == 'DPccp':
                val = cnt.get('CCPCounter', 0)
            else:
                val = cnt.get('EvaluatedCounter', 0)
                
            results[q_name][algo] = val
            print(f"  > Counter: {val}")

    # Plot results
    print("\nGenerating plot...")
    
    # Data extraction
    x_labels = [f"{q_name}\n({tbl_count} tables)" for q_name, tbl_count in TARGET_QUERIES]
    num_queries = len(TARGET_QUERIES)
    
    # Prepare bars data
    bars_data = {algo: [] for algo in ALGORITHMS}
    for q_name, _ in TARGET_QUERIES:
        for algo in ALGORITHMS:
            val = results.get(q_name, {}).get(algo, 0)
            # Clip 0 values to 1 for logarithmic scale visualization
            bars_data[algo].append(max(1, val))
            
    # Set up matplotlib figure
    x = np.arange(num_queries)
    width = 0.2  # Width of each bar
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Distinct, premium color palette
    colors = {
        'DPsize': '#3A86C8',     # Premium Blue
        'DPsub': '#F0A202',      # Amber Orange
        'DPccp': '#4CAF50',      # Emerald Green
        'DPsizeOpt': '#E94F37'   # Red Coral
    }
    
    # Plot grouped bars
    rects1 = ax.bar(x - 1.5 * width, bars_data['DPsize'], width, label='DPsize (EvaluatedCounter)', color=colors['DPsize'])
    rects2 = ax.bar(x - 0.5 * width, bars_data['DPsub'], width, label='DPsub (EvaluatedCounter)', color=colors['DPsub'])
    rects3 = ax.bar(x + 0.5 * width, bars_data['DPccp'], width, label='DPccp (CCPCounter)', color=colors['DPccp'])
    rects4 = ax.bar(x + 1.5 * width, bars_data['DPsizeOpt'], width, label='DPsizeOpt (EvaluatedCounter)', color=colors['DPsizeOpt'])
    
    # Customise axes
    ax.set_ylabel('Join-Pair Counter (Log Scale)', fontsize=12, fontweight='bold')
    ax.set_xlabel('Query (Number of Tables Joined)', fontsize=12, fontweight='bold')
    ax.set_title('Join-Pair Counter across Plan Enumerator Algorithms (JOB Queries)', fontsize=14, fontweight='bold', pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, rotation=0, ha='center', fontsize=10)
    
    # Use logarithmic scale as requested
    ax.set_yscale('log')
    ax.grid(True, which="both", ls="--", alpha=0.5)
    
    # Legend at the bottom
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=4, frameon=True, fontsize=10)
    
    # Save the plot
    plot_path = 'join_pair_counters.png'
    plt.tight_layout()
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    print(f"Plot saved successfully to: {os.path.abspath(plot_path)}")
    
    # Also print a summary text table in terminal
    print("\n" + "="*80)
    print(f"{'Query (Tables)':<20} | {'DPsize':<12} | {'DPsub':<12} | {'DPccp':<12} | {'DPsizeOpt':<12}")
    print("="*80)
    for q_name, tbl_count in TARGET_QUERIES:
        lbl = f"{q_name} ({tbl_count})"
        v_size = results.get(q_name, {}).get('DPsize', '-')
        v_sub = results.get(q_name, {}).get('DPsub', '-')
        v_ccp = results.get(q_name, {}).get('DPccp', '-')
        v_opt = results.get(q_name, {}).get('DPsizeOpt', '-')
        print(f"{lbl:<20} | {v_size:<12} | {v_sub:<12} | {v_ccp:<12} | {v_opt:<12}")
    print("="*80)

if __name__ == '__main__':
    main()
