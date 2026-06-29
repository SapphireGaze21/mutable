import glob

for fpath in glob.glob("benchmark/tpcds/data/csvs/*.csv"):
    with open(fpath, 'r') as f:
        content = f.read()
    # Replace empty fields with 0
    content = content.replace(",,", ",0,")
    content = content.replace(",\n", ",0\n")
    # Run again for overlapping commas
    content = content.replace(",,", ",0,")
    content = content.replace(",\n", ",0\n")
    with open(fpath, 'w') as f:
        f.write(content)
    print(f"Fixed NULLs in {fpath}")
