WHEN = "20231008205049"

with open(f"datas/code/{WHEN}.tsv", "r") as f:
    lines = f.read().splitlines()[1:]
    
codes = [line.split("\t")[2] for line in lines]

with open(f"datas/code/{WHEN}_codes.txt", "w") as f:
    f.write("\n".join(codes))