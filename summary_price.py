import os
from tqdm import tqdm


files = sorted(os.listdir("datas/price"))
files = [file for file in files if "DS" not in file]

with open("datas/price_summary.csv", "w") as f:
    for file in tqdm(files):
        for line in open(f"datas/price/{file}", "r").readlines()[1:]:
            f.write(line)
        f.write("\n")