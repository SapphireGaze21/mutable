#!/usr/bin/env python3
import sys
import os
import argparse
import yaml
import subprocess
import re
import graphviz

# Distinct, premium, Picasso-like color palette for different operator types
COLOR_SCHEME = {
    # Logical Operators
    'ProjectionOperator':          {'fill': '#E1BEE7', 'color': '#8E44AD', 'fontcolor': '#4A148C'},  # Light Purple
    'JoinOperator':                {'fill': '#FFE0B2', 'color': '#E67E22', 'fontcolor': '#D35400'},  # Peach/Orange
    'FilterOperator':              {'fill': '#C8E6C9', 'color': '#2ECC71', 'fontcolor': '#1B5E20'},  # Green
    'DisjunctiveFilterOperator':   {'fill': '#C8E6C9', 'color': '#27AE60', 'fontcolor': '#1B5E20'},  # Green
    'ScanOperator':                {'fill': '#D0E1F9', 'color': '#2980B9', 'fontcolor': '#1B365D'},  # Blue

    # Physical Operators
    'PrintOperator':               {'fill': '#CFD8DC', 'color': '#78909C', 'fontcolor': '#37474F'},  # Grey
    'wasm::Print':                 {'fill': '#CFD8DC', 'color': '#78909C', 'fontcolor': '#37474F'},  # Grey
    'wasm::Projection':            {'fill': '#E1BEE7', 'color': '#8E44AD', 'fontcolor': '#4A148C'},  # Light Purple
    'wasm::SimpleHashJoin':        {'fill': '#FFE0B2', 'color': '#E67E22', 'fontcolor': '#D35400'},  # Peach/Orange (Hash Join)
    'wasm::NestedLoopsJoin':       {'fill': '#FFCDD2', 'color': '#E74C3C', 'fontcolor': '#B71C1C'},  # Red/Pink (Nested Loops Join)
    'wasm::SortMergeJoin':         {'fill': '#D1C4E9', 'color': '#673AB7', 'fontcolor': '#311B92'},  # Deep Purple (Sort Merge Join)
    'wasm::BranchingFilter':       {'fill': '#C8E6C9', 'color': '#2ECC71', 'fontcolor': '#1B5E20'},  # Green (Filter)
    'wasm::LazyDisjunctiveFilter': {'fill': '#C8E6C9', 'color': '#27AE60', 'fontcolor': '#1B5E20'},  # Green (Filter)
    'wasm::Scan':                  {'fill': '#D0E1F9', 'color': '#2980B9', 'fontcolor': '#1B365D'},  # Blue (Table Scan)
}

def parse_plan(plan_lines, is_physical=False):
    nodes = []
    stack = []
    node_count = 0
    pending_edge_label = None

    for line in plan_lines:
        if not line.strip():
            continue
        
        # Get indentation prefix and clean content
        m_prefix = re.match(r'^([\s`|]*)', line)
        prefix = m_prefix.group(1) if m_prefix else ""
        content = line[len(prefix):].strip()
        
        if not content:
            continue
            
        depth = len(prefix)
        
        # Check if this is an edge label line in physical plan
        if is_physical and content in ['probe input', 'build input', '0. input', '1. input', 'probe', 'build']:
            pending_edge_label = content
            continue
        
        # Determine operator name and details
        op_name = ""
        details = content
        
        # Try to find operator name matching known types or general patterns
        m_op = re.match(r'^([A-Za-z0-9_:]+Operator|wasm::[A-Za-z0-9_]+|interpreter::[A-Za-z0-9_]+)', content)
        if m_op:
            op_name = m_op.group(1)
            details = content[len(op_name):].strip()
        else:
            # Fallback to the first word
            m_first = re.match(r'^([^\s{(<]+)', content)
            if m_first:
                op_name = m_first.group(1)
                details = content[len(op_name):].strip()
        
        # Extract cardinality: e.g. <3.84e+10> or <200>
        cardinality = None
        m_card = re.search(r'<([0-9.e+-]+)>', content)
        if m_card:
            cardinality = m_card.group(1)
            
        # Extract cost: e.g. (cumulative cost 506366)
        cost = None
        m_cost = re.search(r'\(cumulative cost\s+([0-9.e+-]+)\)', content, re.IGNORECASE)
        if m_cost:
            cost = m_cost.group(1)
            
        # Clean details: remove cardinality, cost, and schema list {[ ... ]}
        clean_details = details
        if cardinality:
            clean_details = clean_details.replace(f"<{cardinality}>", "")
        # Remove schema list {[ ... ]}
        clean_details = re.sub(r'\{\[[^\]]*\]\}', '', clean_details)
        # Remove cost description
        if cost:
            clean_details = re.sub(r'\(cumulative cost\s+[0-9.e+-]+\)', '', clean_details, flags=re.IGNORECASE)
        
        clean_details = clean_details.strip()
        
        node_id = f"node_{node_count}"
        node_count += 1
        
        node = {
            'id': node_id,
            'depth': depth,
            'op': op_name,
            'details': clean_details,
            'cardinality': cardinality,
            'cost': cost,
            'edge_label': pending_edge_label,
            'parent': None
        }
        
        # Reset pending label
        pending_edge_label = None
        
        # Pop from stack until we find the parent (depth < current depth)
        while stack and stack[-1]['depth'] >= depth:
            stack.pop()
            
        if stack:
            parent = stack[-1]
            node['parent'] = parent['id']
            
        nodes.append(node)
        stack.append(node)
        
    return nodes

def render_graph(nodes, filename, title, is_physical=False):
    # Set up Graphviz digraph with high-resolution output and clean styles
    dot = graphviz.Digraph(comment=title, format='png')
    dot.attr(rankdir='TB', size='12,12', dpi='300')
    dot.attr('node', shape='none', fontname='Helvetica,Arial,sans-serif')
    dot.attr('edge', fontname='Helvetica,Arial,sans-serif', fontsize='10', color='#7F8C8D')
    
    # Add title label
    dot.attr(label=f"\n{title}\n\n", labelloc='t', fontsize='16', fontname='Helvetica-Bold')

    for node in nodes:
        op = node['op']
        style_info = COLOR_SCHEME.get(op, {'fill': '#ECEFF1', 'color': '#B0BEC5', 'fontcolor': '#37474F'})
        
        # Build clean HTML table
        label_html = f'''<
        <table border="0" cellborder="1" cellspacing="0" cellpadding="6" style="ROUNDED">
          <tr><td bgcolor="{style_info['fill']}" border="1" color="{style_info['color']}"><font color="{style_info['fontcolor']}"><b>{op}</b></font></td></tr>
        '''
        
        if node['details']:
            clean_details = node['details'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
            if len(clean_details) > 80:
                clean_details = clean_details[:77] + "..."
            label_html += f'  <tr><td border="1" color="{style_info["color"]}"><font point-size="10" color="#555555">{clean_details}</font></td></tr>\n'
            
        if node['cardinality']:
            label_html += f'  <tr><td border="1" color="{style_info["color"]}"><font point-size="10"><b>Cardinality:</b> {node["cardinality"]}</font></td></tr>\n'
            
        if is_physical and node['cost']:
            label_html += f'  <tr><td border="1" color="{style_info["color"]}"><font point-size="10"><b>Cost:</b> {node["cost"]}</font></td></tr>\n'
            
        label_html += '</table>>'
        
        dot.node(node['id'], label=label_html)
        
        if node['parent']:
            edge_args = {}
            if node['edge_label']:
                edge_args['label'] = f" {node['edge_label']} "
            dot.edge(node['parent'], node['id'], **edge_args)
            
    # Add Color Code Guide (Legend)
    legend_html = '''<
    <table border="0" cellborder="1" cellspacing="0" cellpadding="5" style="ROUNDED">
      <tr><td bgcolor="#34495E" colspan="2"><font color="white"><b>Color Code Guide</b></font></td></tr>
    '''
    
    if not is_physical:
        legend_items = [
            ('ProjectionOperator', 'Projection / Print'),
            ('JoinOperator', 'Join Operations'),
            ('FilterOperator', 'Filters / Selections'),
            ('ScanOperator', 'Scans / Table Access')
        ]
    else:
        legend_items = [
            ('wasm::Print', 'Print Result Set'),
            ('wasm::Projection', 'Projection / Mapping'),
            ('wasm::SimpleHashJoin', 'Hash Join'),
            ('wasm::NestedLoopsJoin', 'Nested Loops Join'),
            ('wasm::SortMergeJoin', 'Sort-Merge Join'),
            ('wasm::BranchingFilter', 'Branch / Lazy Filter'),
            ('wasm::Scan', 'Table Scan')
        ]
        
    for op, desc in legend_items:
        style = COLOR_SCHEME.get(op, {'fill': '#ECEFF1', 'color': '#B0BEC5'})
        legend_html += f'  <tr><td bgcolor="{style["fill"]}" color="{style["color"]}" width="30"></td><td><font point-size="10">{desc}</font></td></tr>\n'
        
    legend_html += '</table>>'
    dot.node('legend_node', label=legend_html, shape='none')
    
    output_path = dot.render(filename, cleanup=True)
    return output_path

def extract_plans_from_text(text):
    lines = text.splitlines()
    logical_lines = []
    physical_lines = []
    
    has_logical = any(op in line for line in lines for op in ['Operator'])
    has_physical = any(term in line for line in lines for term in ['wasm::', 'interpreter::'])
    
    if has_logical and has_physical:
        # Both are present, split them at the first physical plan marker
        phys_start_idx = -1
        for i, line in enumerate(lines):
            if any(term in line for term in ['wasm::', 'interpreter::']):
                phys_start_idx = i
                break
        
        for line in lines[:phys_start_idx]:
            if any(op in line for op in ['Operator']) or line.strip().startswith('`'):
                if not any(term in line for term in ['Created At', 'Created database', 'Created table', 'Using database', 'Counter =', 'PlanningTime_us']):
                    logical_lines.append(line)
        for line in lines[phys_start_idx:]:
            if any(term in line for term in ['wasm::', 'interpreter::', 'probe input', 'build input', '0. input', '1. input']) or line.strip().startswith('`'):
                physical_lines.append(line)
    elif has_logical:
        for line in lines:
            if any(op in line for op in ['Operator']) or line.strip().startswith('`'):
                if not any(term in line for term in ['Created At', 'Created database', 'Created table', 'Using database', 'Counter =', 'PlanningTime_us']):
                    logical_lines.append(line)
    elif has_physical:
        for line in lines:
            if any(term in line for term in ['wasm::', 'interpreter::', 'probe input', 'build input', '0. input', '1. input']) or line.strip().startswith('`'):
                physical_lines.append(line)
                
    return logical_lines, physical_lines

def main():
    parser = argparse.ArgumentParser(description='Generate Picasso plan tree diagram images for logical/physical plans.')
    parser.add_argument('path', help='Path to a .yml experiment file, a text log file, or "-" to read from stdin')
    parser.add_argument('-b', '--builddir', help='Path to build directory (defaults to \'build/release-v8\')',
                        default=os.path.join('build', 'release-v8'), type=str)
    parser.add_argument('--case', dest='case', default='a', help='Query case (defaults to a)')
    parser.add_argument('--plan-enumerator', dest='plan_enumerator', default='DPccp', help='Override plan enumerator (e.g. DPccp, DPsize)')
    parser.add_argument('-o', '--output-dir', dest='output_dir', default='.', help='Output directory for saving PNGs')
    args = parser.parse_args()

    logical_lines = []
    physical_lines = []

    # Read inputs
    if args.path == '-':
        print("Reading plan dumps from stdin...")
        raw_text = sys.stdin.read()
        logical_lines, physical_lines = extract_plans_from_text(raw_text)
    elif os.path.isfile(args.path) and not args.path.endswith('.yml'):
        print(f"Reading plan dumps from text file: {args.path}")
        with open(args.path, 'r', encoding='utf-8') as f:
            raw_text = f.read()
        logical_lines, physical_lines = extract_plans_from_text(raw_text)
    elif os.path.isfile(args.path) and args.path.endswith('.yml'):
        # Load yaml and run query
        print(f"Executing query from YAML file: {args.path} to fetch plan dumps...")
        with open(args.path, 'r') as yml_file:
            yml = yaml.safe_load(yml_file)
            
        # Point to data2 directory
        if 'data' in yml:
            for table_name, table in yml['data'].items():
                if 'file' in table:
                    table['file'] = table['file'].replace('/data/', '/data2/')

        suite = yml.get('suite')
        path_to_data = os.path.join('benchmark', suite, 'data2')
        
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from database_connectors import mutable
        
        path_to_binary = os.path.join(args.builddir, 'bin', 'shell')
        if not os.path.isfile(path_to_binary):
            print(f"Error: mutable binary not found at '{path_to_binary}'")
            sys.exit(1)
            
        conn = mutable.Mutable({'path_to_binary': path_to_binary})
        imports = conn.get_setup_statements(suite, path_to_data, yml.get('data'), args.case)
        import_str = '\n'.join(imports)
        
        query = yml.get('systems', {}).get('mutable', {}).get('cases', {}).get(args.case)
        if not query:
            print(f"Error: case '{args.case}' not found in {args.path}")
            sys.exit(1)
            
        query_str = import_str + '\n' + query + '\n'
        
        # Build binary command
        command = [path_to_binary, '--backend', 'WasmV8', '--data-layout', 'PAX4M',
                   '--plan-enumerator', args.plan_enumerator, '--plan', '--physplan', '--dryrun', '-']
        
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        proc_out, proc_err = process.communicate(query_str.encode('utf-8'))
        raw_text = proc_out.decode('utf-8', errors='replace')
        
        logical_lines, physical_lines = extract_plans_from_text(raw_text)
    else:
        print(f"Error: Invalid file path or format: '{args.path}'")
        sys.exit(1)

    logical_saved = None
    physical_saved = None

    # Render logical plan
    if logical_lines:
        print(f"Found logical plan ({len(logical_lines)} lines). Parsing...")
        logical_nodes = parse_plan(logical_lines, is_physical=False)
        out_path = os.path.join(args.output_dir, 'logical_plan')
        logical_saved = render_graph(logical_nodes, out_path, "Logical Query Plan", is_physical=False)
        print(f"Logical plan tree successfully saved to: {logical_saved}")
    else:
        print("No logical plan lines found.")

    # Render physical plan
    if physical_lines:
        print(f"Found physical plan ({len(physical_lines)} lines). Parsing...")
        physical_nodes = parse_plan(physical_lines, is_physical=True)
        out_path = os.path.join(args.output_dir, 'physical_plan')
        physical_saved = render_graph(physical_nodes, out_path, "Physical Execution Plan", is_physical=True)
        print(f"Physical plan tree successfully saved to: {physical_saved}")
    else:
        print("No physical plan lines found.")

    # Display interactive matplotlib popup window
    if logical_saved or physical_saved:
        import matplotlib.pyplot as plt
        import matplotlib.image as mpimg

        if logical_saved and physical_saved:
            fig, axes = plt.subplots(1, 2, figsize=(18, 9))
            fig.canvas.manager.set_window_title('Picasso Query Plan Trees')
            
            # Load and display logical plan
            img_log = mpimg.imread(logical_saved)
            axes[0].imshow(img_log)
            axes[0].axis('off')
            axes[0].set_title('Logical Query Plan', fontsize=14, fontweight='bold')
            
            # Load and display physical plan
            img_phys = mpimg.imread(physical_saved)
            axes[1].imshow(img_phys)
            axes[1].axis('off')
            axes[1].set_title('Physical Execution Plan', fontsize=14, fontweight='bold')
            
            plt.tight_layout()
        else:
            path = logical_saved or physical_saved
            title = 'Logical Query Plan' if logical_saved else 'Physical Execution Plan'
            
            fig, ax = plt.subplots(figsize=(10, 8))
            fig.canvas.manager.set_window_title(f'Picasso {title}')
            
            img = mpimg.imread(path)
            ax.imshow(img)
            ax.axis('off')
            ax.set_title(title, fontsize=14, fontweight='bold')
            
            plt.tight_layout()
            
        print("Displaying interactive matplotlib popup window. Close the window to exit.")
        plt.show()

if __name__ == '__main__':
    main()
