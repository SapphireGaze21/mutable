import sys

with open('benchmark/Benchmark.py', 'r') as f:
    content = f.read()

# Replace part 1
part1_orig = """            else:  # path is a directory containing multiple experiment files
                benchmark_files.extend(glob.glob(os.path.join(path, '**', '[!_]*.yml'), recursive=True))

    benchmark_files: list[str] = sorted(list(set(benchmark_files)))"""

part1_new = """            else:  # path is a directory containing multiple experiment files
                benchmark_files.extend(glob.glob(os.path.join(path, '**', '[!_]*.yml'), recursive=True))
                benchmark_files.extend(glob.glob(os.path.join(path, '**', '[!_]*.tpl'), recursive=True))

    benchmark_files: list[str] = sorted(list(set(benchmark_files)))"""

content = content.replace(part1_orig, part1_new)

# Replace part 2
part2_orig_start = """        # Validate schema
        if not validate_schema(path_to_file, YML_SCHEMA):
            continue

        with open(path_to_file, 'r') as yml_file:
            yml: dict[str, Any] = yaml.safe_load(yml_file)

            # Get information about experiment"""

part2_new_start = """        # Validate schema
        if not path_to_file.endswith('.tpl') and not validate_schema(path_to_file, YML_SCHEMA):
            continue

        if path_to_file.endswith('.tpl'):
            import sys
            sys.path.append('benchmark')
            import tpl_parser
            query_str = tpl_parser.parse_tpl(path_to_file)
            with open('benchmark/tpcds/data_tpcds.yml', 'r') as f:
                data_yml = yaml.safe_load(f)
            yml = {
                'suite': 'tpcds',
                'benchmark': 'tpcds',
                'name': os.path.basename(path_to_file),
                'readonly': True,
                'data': data_yml['data'],
                'systems': {
                    'mutable': {
                        'cases': { 'query': query_str },
                        'configurations': {
                            'Interpreter-DPsub': {
                                'args': '--backend Interpreter --plan-enumerator DPsub --plan',
                                'pattern': '^Execute query:.*',
                                'variables': {}
                            }
                        }
                    }
                }
            }
        else:
            with open(path_to_file, 'r') as yml_file:
                yml = yaml.safe_load(yml_file)

        # Get information about experiment"""

# Replace the start
content = content.replace(part2_orig_start, part2_new_start)

# Now unindent everything after `# Get information about experiment` up to the end of the `for path_to_file` loop
# The loop ends before `# Create .pgsql file`

lines = content.split('\n')
new_lines = []
in_loop_body = False
for line in lines:
    if line.startswith('        # Get information about experiment'):
        in_loop_body = True
    if line.startswith('    # Create .pgsql file'):
        in_loop_body = False
        
    if in_loop_body and line.startswith('            '):
        new_lines.append(line[4:])
    elif in_loop_body and line.startswith('        '):
        # For lines that are empty or have fewer spaces, don't chop blindly
        if line.strip() == '':
            new_lines.append('')
        else:
            new_lines.append(line) # Wait, lines like `        # Get information about experiment` are 8 spaces, so they stay 8 spaces
    else:
        new_lines.append(line)

with open('benchmark/Benchmark.py', 'w') as f:
    f.write('\n'.join(new_lines))

