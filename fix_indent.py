import sys

with open('benchmark/Benchmark.py', 'r') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    # lines 440 to 523 (0-indexed 439 to 522)
    if 439 <= i <= 522:
        if line.startswith('    '):
            new_lines.append(line[4:])
        else:
            new_lines.append(line)
    else:
        new_lines.append(line)

with open('benchmark/Benchmark.py', 'w') as f:
    f.writelines(new_lines)
