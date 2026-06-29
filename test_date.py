import re

expr = 'date([YEAR]+"-01-01",[YEAR]+"-07-01",sales)'
m = re.match(r'(?i)date\(\s*([^,]+)\s*,', expr)
if m:
    val = m.group(1).replace('+', '').replace('"', '').replace("'", "")
    print(val)
