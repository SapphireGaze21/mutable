import csv
import glob

for fpath in glob.glob("benchmark/tpcds/data/csvs/*.csv"):
    rows = []
    with open(fpath, 'r', newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            new_row = []
            for col in row:
                col = col.strip()
                if not col:
                    new_row.append('0')
                elif '.' in col or col.startswith('-') or col.isdigit():
                    try:
                        val = int(float(col))
                        new_row.append(str(abs(val)))
                    except ValueError:
                        if '-' in col and len(col) == 10 and col.count('-') == 2:
                            try:
                                new_row.append(col.replace('-', ''))
                            except ValueError:
                                new_row.append(col)
                        else:
                            new_row.append(col)
                elif '-' in col and len(col) == 10 and col.count('-') == 2:
                    try:
                        new_row.append(col.replace('-', ''))
                    except ValueError:
                        new_row.append(col)
                else:
                    new_row.append(col)
            # Append dummy string to absorb the \n during Mutable parsing
            new_row.append('dummy')
            rows.append(new_row)
            
    with open(fpath, 'w', newline='') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerows(rows)
    print("Sanitized and appended dummy to", fpath)
