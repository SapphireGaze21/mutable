import subprocess
import time

p = subprocess.Popen(['lldb', 'build/debug_shared/bin/shell'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
p.stdin.write('settings set -- target.run-args --plan-enumerator DPccp --plan benchmark/dataset_for_graph/test_join6.sql\n')
p.stdin.write('run\n')
p.stdin.flush()

out = []
while True:
    line = p.stdout.readline()
    if not line:
        break
    out.append(line)
    if 'stop reason = signal' in line:
        break

p.stdin.write('bt\n')
p.stdin.write('quit\n')
p.stdin.flush()

for line in p.stdout:
    out.append(line)

with open('crash_bt.txt', 'w') as f:
    f.writelines(out)
