from tqdm import tqdm

from datetime import date, timedelta
import datetime

import numpy as np
import bottleneck as bn
import pandas as pd

import matplotlib.pyplot as plt
import japanize_matplotlib

import sys
from collections import defaultdict

import joblib

import mylib_stock


# データパス
DATA_PATH_PRICE = "datas/price_summary.csv"
DATA_PATH_CODE = "datas/code/20231008205049.tsv"
DATA_PATH_CLACULATED = "datas/backtest/calculated_price_summary.joblib"
DATA_PATH_TRADE_LOG = "datas/backtest/trade_log.txt"
DATA_PATH_ASSET_LOG = "datas/backtest/asset_log.txt"
DATA_PATH_ASSET_IMG= "datas/backtest/asset_log.png"

# 検証開始/終了の日付
FROM = date(2021, 7, 16)
TO = date(2023, 7, 14)

# 初期所持金額
FIRST_MONEY = 3000000.0

# 利確・損切の基準(%ベースで絶対値, しない場合は100000のように入力)
SECURE_PROFIT = 20
LOSS_CUT = 15

# 書き出しと途中終了のためのフラグ
WRITE = True
WRITE_SAMPLE = True
INTERRUPT = True

# 型変換のための関数
def change_type(num:str, k:int):
    if k == 0 or k== 2:
        return int(num)
    elif k != 1:
        return float(num)
    else:
        return num


# データの用意
# コード一覧，codesは全ての銘柄コード，codes_normalは17業種コードが"その他"以外のもの．つまり，投信を弾いたもの．
print("Loading datas...", end="", flush=True)
codes_info = open(DATA_PATH_CODE, "r").read().splitlines()[1:]
codes_info = [code_info.split("\t") for code_info in codes_info]
codes = [int(code_info[2]) for code_info in codes_info]
codes_normal = [int(code_info[2]) for code_info in codes_info if code_info[6] != 'その他']

# 株価データは投信以外のデータを読み込む
# pricesの構造は，3次元リスト．[[日付，銘柄コード，4本値]のリスト=ある銘柄の2年のデータ]のリスト=全銘柄の2年のデータ
prices_normal = [[x.split(",") for x in code_price.splitlines()] for i, code_price in enumerate(open(DATA_PATH_PRICE).read().split("\n\n")[:-1]) if codes_info[i][6] != "その他"]
print("Completed!")

# 投信以外で''があることが確認済．コード13800など，
# 前の行をコピーしておき，''があった場合は，前の行のモノを入れる．
for i, code_price in enumerate(prices_normal):
    for j, day_price in enumerate(code_price):
        if "" in day_price:
            if j != 0:
                prices_normal[i][j] = prices_normal[i][j][0:2] + prices_normal[i][j-1][2:9] + ['0','0'] + prices_normal[i][j-1][11:16] + ['0']
            else:
                prices_normal[i][j] = prices_normal[i][j][0:2] + prices_normal[i][j+1][2:9] + ['0','0'] + prices_normal[i][j+1][11:16] + ['0']


# それでも''が存在する場合，連続した2日以上取引がされていないことになる．
# そういった銘柄は取引には適さないので，codes_normalとprices_normalから削除する．
st = set()
for i, code_price in enumerate(prices_normal):
    for day_price in code_price:
        if "" in day_price:
            st.add(i)

codes_normal = [code_normal for i, code_normal in enumerate(codes_normal) if i not in st]  
prices_normal = [price_normal for i, price_normal in enumerate(prices_normal) if i not in st]

# データは日付の列以外，全てintかfloatにする
for i in tqdm(range(len(prices_normal)), desc="Changing type..."):
    prices_normal[i] = [[change_type(prices_normal[i][j][k], k) for k in range(17)] for j in range(len(prices_normal[i]))]

# Vicugna用に，最新30日分を保存しておく
prices_normal_not_indices_30 = [prices_normal[i][-30:] if len(prices_normal[i])>=30 else prices_normal[i] for i in range(prices_normal)]
joblib.dump(prices_normal_not_indices_30, '/Users/yuta/Desktop/nnu/program/AI/Vicugna/etc/prices_normal_not_indices_30.job')
    

# pdに対して，取引のルール判断に必要な指標などを計算して追加する
prices_normal = mylib_stock.calculate_indices(codes_normal, prices_normal)


# データ処理が結構重いが，読み込みに1分強かかっていた．
# よって，保存せずに毎回計算する．

# Vicugnaのために，書き出しが可能になるようにする(フラグ管理)
if WRITE:
    joblib.dump(prices_normal, '/Users/yuta/Desktop/nnu/program/AI/Vicugna/etc/prices_normal.job')
if WRITE_SAMPLE:
    joblib.dump(prices_normal[200:250], '/Users/yuta/Desktop/nnu/program/AI/Vicugna/etc/prices_normal_sample.job')

# デバッグ用
if INTERRUPT:
    sys.exit()


# 営業日のリスト
biz_days = [record[1] for record in prices_normal[0]]


# 購入する銘柄を決定する関数
def decide_buy_code(today:datetime.date) -> list:
    today = today.strftime("%Y-%m-%d")
    #print(f"today:{today}, decide")
    
    # 購入する銘柄の候補のリスト
    # 要素は銘柄コードと10日平均売買代金の組
    trade_buy_candidates = []
    
    # 今回はMACDがシグナルを上回った時に購入する
    for i, code_price in enumerate(prices_normal):
        
        # 今日のレコードを探す
        # code_priceの長さは一定ではない(上場がn年以上前でないと短くなる)ので，添字指定は不可．
        # 同じ理由でtodayのデータがなければスキップする
        today_index = -1
        for j, record in enumerate(code_price):
            if record[1] == today:
                today_index = j
                break
        
        # もし最後の行まできていたら，上場が近すぎてデータがないのでスキップ
        if today_index == -1:
            break      

        # 今日と昨日のレコード，i-1としているが，
        # main関数でtodayは+30して始まっているので，out indexにはならない
        dbyesterday_record = code_price[today_index-2]
        yesterday_record = code_price[today_index-1]
        today_record = code_price[today_index]

        # 前提条件
        # 平均売買代金が5千万円以上
        # さらに，株価が1万円以下
        judge_buy = False
        if yesterday_record[17] > 50000000:
            if yesterday_record[6] <= 10000:
                   
                # (1)さらに，MACDがシグナルを突き抜けた(record[20] > record[21]) or MACDが0を上回った(record[20]>0)
                # (1)さらに，RSIが50以下
                if (dbyesterday_record[20] < dbyesterday_record[21] and yesterday_record[20] > yesterday_record[21]) or (dbyesterday_record[20] < 0 and yesterday_record[20] > 0):
                    if yesterday_record[23] <= 50:
                        judge_buy = True
                        
                # (2)さらに，株価が移動平均線25日の上から漸近した = 移動平均乖離率25(record[27])の下降が2%~20%，当日が0~20%
                deviation_down = dbyesterday_record[27] - yesterday_record[27]
                deviation_yesterday = yesterday_record[27]
                if deviation_yesterday >= 3 and deviation_yesterday < 20 and deviation_down > 2 and deviation_down < 7:
                    #judge_buy = True
                    pass
                        
        if judge_buy:                
            trade_buy_candidates.append([today_record[1], today_record[2], today_record[3], today_record[17]])
    
    trade_buy_candidates.sort(key=lambda x:x[3], reverse=True)
    
    # trade_buy_candidatesの例
    # [['2021-08-16', 14190, 2370.0, 3923232400.0], ['2021-08-16', 14140, 4840.0, 660690650.0]]
    
    return trade_buy_candidates
    
    
# 決定された銘柄を売買し，ログに出力する関数
def trade_buy_day(today:datetime.date, trade_buy_candidates:list, tmp_money:float) -> [float, list]:
    
    # 変数処理
    today = today.strftime("%Y-%m-%d")
    trade_buy_candidates = trade_buy_candidates
    tmp_money = money
    stocks = []
    
    # 取引，ログに出力してmoneyを減らす．
    # 終値で買えるものとし，ストップは考えない．<変更予定>
    for candidate in trade_buy_candidates:
        
        # 変数用意
        code = candidate[1]
        price = candidate[2]
        
        # 1単位買えるか確認
        if price > tmp_money/100:
            break
        
        # 何株買うか決定
        # リスクの%は，現時点では同じ銘柄を違う日に買うことによる積算は考慮していない
        #buy_num = int(((tmp_money*0.02)/(price*0.2))/100)*100
        buy_num = 100
        
        # moneyを減らす
        # 売買代金, 手数料はなし(SBIゼロ革命利用)
        # 記録用のmoneyも保存
        before_money = tmp_money
        tmp_money -= price*buy_num
        
        # ログに出力
        log = candidate[0:3] + [buy_num, price*buy_num, before_money, tmp_money]
        log = [str(x) for x in log]
            
        f_tra.write(f"buy：{', '.join(log)}\n")
        
        # return用の株価保持リスト
        stocks.append([code, buy_num, price])

    return tmp_money, stocks


# 売却関数
def trade_sell_day(today:datetime.date, stocks:dict, tmp_money:float) -> [float, list]:
    
    # 変数処理
    today = today.strftime("%Y-%m-%d")
    stock_items = stocks.items()
    tmp_money = money
    sell_list = []
    
    # 一つ一つの株について，売るかどうか判断
    for stock in stock_items:
        code = stock[0]
        # 条件に合致したら全て売却する
        sell_num = stock[1][0]
        average_price = stock[1][1]
        
        # prces_normalからcodeでrecordsを特定    
        code_index = codes_normal.index(code)  
        
        # 今日のレコードを探す 
        today_index = -1
        for i, record in enumerate(prices_normal[code_index]):   
            if record[1] == today:
                today_index = i
                break
        
        # もし最後の行まできていたら，上場が近すぎてデータがないのでスキップ
        if today_index == -1:
            break

        # 今日と昨日のレコード
        yesterday_record = prices_normal[code_index][today_index-1]
        today_record = prices_normal[code_index][today_index]
        price = today_record[6]
        
        # 売却判断用フラグ
        judge_sell = False
        
        # MACDのデッドクロスorMACDが0を下回ったか確認
        # MACD = record[20], シグ = record[21]
        if (yesterday_record[20] > yesterday_record[21] and today_record[20] < yesterday_record[21]) or (yesterday_record[20] > 0 and today_record[20] < 0):
            judge_sell = True
        
        # 利確．昨日の終値が取得平均単価よりSECURE_PROFIT%上回ったら，その価格で利確(指値注文をしておくものとする)
        fixed_price_p = average_price * (100+SECURE_PROFIT)*0.01
        if yesterday_record[6] > fixed_price_p:
            judge_sell = True
            
            # priceを上書きする．つまり，この判断はMACDの判断よりも優先される
            price = fixed_price_p
        
        # 損切はLOSS_CUT%で計算
        fixed_price_l = average_price * (100-LOSS_CUT)*0.01
        if yesterday_record[6] < fixed_price_l:
            judge_sell = True
            price = fixed_price_l
        
        # 当該コードが売却フラグを満たしていたら売却    
        if judge_sell:
            
            # 条件に合致したら売るリストに追加
            sell_list.append(code)
            
            # 所持金の追加
            before_money = tmp_money
            tmp_money += price*sell_num
            
            # ログ出力
            log = [today, code,  price, sell_num, price*sell_num, before_money, tmp_money]
            log = [str(x) for x in log]
            f_tra.write(f"sell：{', '.join(log)}\n")
            
    return tmp_money, sell_list


# moneyと持ち株決算分を足して資産を計算
def calculate_asset(today:datetime.date, money:float, stocks:dict):
    
    # 変数処理
    today = today.strftime("%Y-%m-%d")
    stock_items = stocks.items()
    tmp_money = money
    
    # すべて売った時の所持金を計算
    for stock in stock_items:
        code = stock[0]
        sell_num = stock[1][0]
        
        # prices_normalからcodeでrecordsを特定    
        code_index = codes_normal.index(code)  
        
        # 今日のレコードから代金を取得
        for record in prices_normal[code_index]:   
            if record[1] == today:
                price = record[6]
                break
            
        # 所持金の追加
        tmp_money += price*sell_num
        
    # ログ出力
    log = [today, str(tmp_money)]
    f_ase.write(f"{', '.join(log)}\n")
        
# defualtdict初期化のための関数
def init():
    return [0, 0]


# 1日ずつ，取引を行う．移動平均などがあるので，30日ずらす
today = FROM + timedelta(days=30)
# 手持ち代金
money = FIRST_MONEY
# 手持ち株
stocks = defaultdict(init)
# ログファイル
f_tra = open(DATA_PATH_TRADE_LOG, "w")
f_ase = open(DATA_PATH_ASSET_LOG, "w")

# トレードのループ
print("Trading... (About 20seconds)： ", end="", flush=True)
while today != TO:
    
    # 文字列today
    today_str = today.strftime("%Y-%m-%d")
    
    # その日が営業日リストにあれば処理，なければ次のループ
    if today_str in biz_days:
        
        # 売却フロー
        # 売却
        mon, sell_list = trade_sell_day(today, stocks, money)
        # 所持金の更新
        money =  mon
        # 辞書のやつを減らす
        for code in sell_list:
            del stocks[code]
        
        # 購入フロー
        # 株購入の候補を決める
        trade_buy_candidates = decide_buy_code(today)
        
        # 購入
        mon, sto = trade_buy_day(today, trade_buy_candidates, money)
        
        # 所持金の更新
        money = mon
        
        # 持ち株の更新
        # そもそも株を買ったか
        if sto:
            # 複数の株を買った時はfor文
            if type(sto[0]) is list:
                for x in sto:
                    
                    # 今までの持分と合算して取得単価を計算
                    have_num = stocks[x[0]][0]
                    have_price = stocks[x[0]][1]
                    add_num = x[1]
                    add_price = x[2]
                    average_price = (have_num*have_price + add_num*add_price) / (have_num+add_num)
                    
                    # 取得単価を更新
                    stocks[x[0]][1] = average_price
                    # 持株数を更新
                    stocks[x[0]][0] += x[1]
                    
            # 一つだけの時は一つ
            elif type(sto[0]) is str:
                
                have_num = stocks[x[0]][0]
                have_price = stocks[x[0]][1]
                add_num = sto[1]
                add_price = sto[2]
                average_price = (have_num*have_price + add_num*add_price) / (have_num+add_num)
                
                stocks[sto[0]][1] = average_price
                stocks[sto[0]][0] += sto[1]
            else:
                pass
        else:
            pass
        
        # 資産の計算
        calculate_asset(today, money, stocks)
    
    # 一日ずつ進める
    today += timedelta(days=1)

# ファイルクローズ
f_tra.close()
f_ase.close()
print("Completed!")


# ログを分析してサマリーを出力
# <変更済>priceは調整してないけどいいのか？：むしろ，調整済みやとお金の増減がおかしくなりそうなので，放置しておいた．
prices = [float(line.split(", ")[1])/1000000.0 for line in open(DATA_PATH_ASSET_LOG).read().splitlines()]
ticks = [i for i in range(len(prices))]
terms = [line.split(", ")[0] for line in open(DATA_PATH_ASSET_LOG).read().splitlines()]
old_ticks = [int(len(prices)/8)*i for i in range(8+1)]
new_ticks = [terms[i] for i in old_ticks]

plt.figure(figsize=(15,5))
plt.plot(ticks, prices)
plt.title("transition of asset")
plt.xlabel("term")
plt.ylabel("yen")
plt.xticks(old_ticks, new_ticks, rotation="vertical")
plt.draw()
xlocs, xlabs = plt.yticks()
plt.text(-50, xlocs[-1], '(単位：百万円)')
plt.savefig(DATA_PATH_ASSET_IMG, bbox_inches='tight')