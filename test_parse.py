import re
import sys

def parse_tpl(file_path):
    with open(file_path, 'r') as f:
        content = f.read()

    # Find all defines
    defines = re.findall(r'(?i)define\s+(\w+)\s*=\s*(.*?);', content)
    
    # Simple substitution map
    substitutions = {}
    for var, expr in defines:
        expr = expr.strip()
        if expr.lower().startswith('random('):
            # random(1998,2002, uniform)
            m = re.match(r'(?i)random\(\s*([0-9]+)\s*,', expr)
            if m:
                substitutions[var] = m.group(1)
        elif expr.lower().startswith('text('):
            # text({"1001-5000",1},{">10000",1})
            m = re.match(r'(?i)text\(\s*\{\s*["\']([^"\']+)["\']', expr)
            if m:
                substitutions[var] = m.group(1)
        else:
            # Maybe just an assignment: define _END = "";
            # define _LIMITA = "";
            # define LIMITA = text({"1001-5000",1});
            m = re.match(r'["\']([^"\']*)["\']', expr)
            if m:
                substitutions[var] = m.group(1)
            else:
                substitutions[var] = expr

    # Now strip out all lines starting with define
    lines = content.split('\n')
    query_lines = []
    for line in lines:
        if re.match(r'(?i)^\s*define\s+', line):
            continue
        query_lines.append(line)
        
    query = '\n'.join(query_lines)

    # Substitute
    for var, val in substitutions.items():
        query = query.replace(f'[{var}]', val)
        
    print(query)

parse_tpl('tpcds queries/tpcds-kit/query_templates/query91.tpl')
