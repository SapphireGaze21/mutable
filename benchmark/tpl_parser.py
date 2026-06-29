import re
import os

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
            m = re.match(r'(?i)random\(\s*([0-9]+)\s*,', expr)
            if m:
                substitutions[var] = m.group(1)
        elif expr.lower().startswith('text('):
            m = re.match(r'(?i)text\(\s*\{\s*["\']([^"\']+)["\']', expr)
            if m:
                substitutions[var] = m.group(1)
        elif expr.lower().startswith('list('):
            m = re.match(r'(?i)list\(\s*\{\s*["\']([^"\']+)["\']', expr)
            if m:
                substitutions[var] = m.group(1)
        elif expr.lower().startswith('date('):
            m = re.match(r'(?i)date\(\s*([^,]+)\s*,', expr)
            if m:
                date_expr = m.group(1).strip()
                date_expr = date_expr.replace('+', '').replace('"', '').replace("'", "")
                substitutions[var] = date_expr
        else:
            m = re.match(r'["\']([^"\']*)["\']', expr)
            if m:
                substitutions[var] = m.group(1)
            else:
                substitutions[var] = expr

    # Now strip out all lines starting with define or SQL comments
    lines = content.split('\n')
    query_lines = []
    for line in lines:
        if re.match(r'(?i)^\s*define\s+', line):
            continue
        if re.match(r'^\s*--', line):
            continue  # Strip SQL comments (they break single-line queries)
        query_lines.append(line)
        
    query = '\n'.join(query_lines)

    # We need to loop multiple times because some definitions depend on others (like [YEAR])
    for _ in range(3):
        for var, val in substitutions.items():
            query = query.replace(f'[{var}]', val)
            
    # Clean up standard TPC-DS limit tokens if they weren't substituted
    query = query.replace('[_LIMITA]', '')
    query = query.replace('[_LIMITB]', '')
    query = query.replace('[_LIMITC]', '')
    
    # Clean up any other unresolved template variables
    query = re.sub(r'\[_[a-zA-Z0-9_]+\]', '', query)

    # Convert single quotes to double quotes (mutable uses double quotes for string literals)
    query = query.replace("'", '"')

    # Uppercase SQL keywords (mutable requires uppercase keywords)
    SQL_KEYWORDS = [
        'SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'NOT', 'IN', 'AS', 'ON', 'BY',
        'ORDER', 'GROUP', 'HAVING', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER',
        'FULL', 'CROSS', 'UNION', 'ALL', 'DISTINCT', 'BETWEEN', 'LIKE', 'IS',
        'NULL', 'TRUE', 'FALSE', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'EXISTS',
        'ASC', 'DESC', 'LIMIT', 'OFFSET', 'INSERT', 'INTO', 'VALUES', 'UPDATE',
        'DELETE', 'SET', 'CREATE', 'TABLE', 'DROP', 'ALTER', 'INDEX', 'VIEW',
        'DATABASE', 'USE', 'INT', 'CHAR', 'VARCHAR', 'DECIMAL', 'DATE', 'FLOAT',
        'DOUBLE', 'BOOLEAN', 'BIGINT', 'SMALLINT', 'TINYINT', 'WITH', 'RECURSIVE',
        'ROLLUP', 'CUBE', 'GROUPING', 'SETS', 'OVER', 'PARTITION', 'ROWS', 'RANGE',
        'UNBOUNDED', 'PRECEDING', 'FOLLOWING', 'CURRENT', 'ROW', 'RANK', 'SUM',
        'COUNT', 'AVG', 'MIN', 'MAX', 'CAST', 'SUBSTRING', 'SUBSTR', 'TRIM',
        'COALESCE', 'NULLIF', 'EXTRACT', 'YEAR', 'MONTH', 'DAY', 'HOUR', 'MINUTE',
        'SECOND', 'INTERVAL', 'PRIMARY', 'KEY', 'FOREIGN', 'REFERENCES', 'CHECK',
        'CONSTRAINT', 'DEFAULT', 'UNIQUE', 'IF', 'REPLACE', 'TEMP', 'TEMPORARY',
        'EXCEPT', 'INTERSECT', 'ANY', 'SOME', 'NATURAL', 'USING', 'WINDOW',
    ]

    def uppercase_keywords(sql_text):
        """Uppercase SQL keywords while preserving string literals."""
        result = []
        i = 0
        in_double_quote = False
        token_start = None

        while i < len(sql_text):
            ch = sql_text[i]

            if ch == '"' and not in_double_quote:
                in_double_quote = True
                result.append(ch)
                i += 1
                continue
            elif ch == '"' and in_double_quote:
                in_double_quote = False
                result.append(ch)
                i += 1
                continue

            if in_double_quote:
                result.append(ch)
                i += 1
                continue

            # Outside a string: accumulate word characters
            if ch.isalpha() or ch == '_':
                if token_start is None:
                    token_start = len(result)
                result.append(ch)
                i += 1
            else:
                if token_start is not None:
                    word = ''.join(result[token_start:])
                    if word.upper() in SQL_KEYWORDS:
                        result[token_start:] = list(word.upper())
                    token_start = None
                result.append(ch)
                i += 1

        # Handle trailing word
        if token_start is not None:
            word = ''.join(result[token_start:])
            if word.upper() in SQL_KEYWORDS:
                result[token_start:] = list(word.upper())

        return ''.join(result)

    query = uppercase_keywords(query)

    return query
