import os
from tqdm import tqdm


files = sorted(os.listdir("datas/fins"))
files = [file for file in files if "DS" not in file]

with open("datas/fins_summary.csv", "w") as f:
    for file in tqdm(files):
        lines = open(f"datas/fins/{file}").readlines()[1:]

        for line in lines:
            f.write(line)
        if lines:
            f.write("\n")