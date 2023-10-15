from collections import defaultdict
from tqdm import tqdm
import matplotlib.pyplot as plt
import japanize_matplotlib
import pandas as pd
import math
import statistics


# 辞書から画像を作成する関数
def analyse2image(code_dict, code_kind, xlimf, xlimt, ylimf, ylimt, avg_or_med):
    labels = [x[0] for x in code_dict.items()]
    num = [x[1][1] for x in code_dict.items()]
    avg = [x[1][2] for x in code_dict.items()]

    plt.scatter(num, avg)
    plt.title(f"num of companies - price {avg_or_med} : {code_kind}code")
    plt.xlabel("num of companies")
    plt.ylabel(f"price {avg_or_med}")
    plt.grid(True)
    plt.xlim(xlimf, xlimt)
    plt.ylim(ylimf, ylimt)
    
    for i, label in enumerate(labels):
        plt.text(num[i], avg[i],label)
        
    plt.savefig(f"datas/image/price_{avg_or_med}_{code_kind}.png")
    plt.close()


# データの変数の用意
print("Loading datas...")
panda = pd.read_csv("datas/price_summary.csv", header=None, names=['Num','Date','Code','Open','High','Low','Close','UpperLimit','LowerLimit','Volume','TurnoverValue','AdjustmentFactor','AdjustmentOpen','AdjustmentHigh','AdjustmentLow','AdjustmentClose','AdjustmentVolume'])
codes_info = open("datas/code/20231008205049.tsv", "r").read().splitlines()[1:]
codes_info = [code_info.split("\t") for code_info in codes_info]
codes = [code_info[2] for code_info in codes_info]

avg_17 = defaultdict(lambda: [float(), int(), float()])
avg_33 = defaultdict(lambda: [float(), int(), float()])
med_17 = defaultdict(lambda: [list(), int(), float()])
med_33 = defaultdict(lambda: [list(), int(), float()])


# 株価データから，業種コード(17/33それぞれ)ごとに株価の平均と中央値を計算
for i, code in enumerate(tqdm(codes, desc="Analysing prices...")):
    code_pd = panda.query(f"Code == {code}")
    avg = code_pd["AdjustmentClose"].mean()
    
    if not math.isnan(avg):
        avg_17[codes_info[i][6]][0] += avg
        avg_33[codes_info[i][8]][0] += avg
        avg_17[codes_info[i][6]][1] += 1
        avg_33[codes_info[i][8]][1] += 1
        
        med_17[codes_info[i][6]][0].append(avg)
        med_33[codes_info[i][8]][0].append(avg)
        med_17[codes_info[i][6]][1] += 1
        med_33[codes_info[i][8]][1] += 1

for key in avg_17.keys():
    avg_17[key][2] = avg_17[key][0] / avg_17[key][1]
for key in avg_33.keys():
    avg_33[key][2] = avg_33[key][0] / avg_33[key][1]
    
for key in med_17.keys():
    med_17[key][2] = statistics.median(med_17[key][0])
for key in med_33.keys():
    med_33[key][2] = statistics.median(med_33[key][0])


# 画像作成(平均と中央値)
analyse2image(avg_17, 17, 0, 1300, 1250, 2750, "avg")
analyse2image(avg_33, 33, 0, 610, 1100, 2750, "avg")
analyse2image(med_17, 17, 0, 1300, 800, 2100, "med")
analyse2image(med_33, 33, 0, 650, 500, 2500, "med")


# 各業種ごとの株価のヒストグラムを並べて表示
fig = plt.figure(figsize = (30,18), facecolor='lightblue')
keys = list(med_17.keys())

for i in range(17):
    plt.subplot(3, 6, i+1)
    plt.hist(med_17[keys[i]])
    plt.xlim([0, 25000])
    plt.xlabel("price")
    plt.ylabel("num")
    plt.title(keys[i])
    
fig.savefig("datas/image/price_summary_17.png")
plt.close()