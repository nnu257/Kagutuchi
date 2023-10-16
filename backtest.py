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

import mylib_stock


# データパスと変数の用意
DATA_PATH_PRICE = "datas/price_summary.csv"
DATA_PATH_CODE = "datas/code/20231008205049.tsv"
DATA_PATH_CLACULATED = "datas/backtest/calculated_price_summary.joblib"
DATA_PATH_TRADE_LOG = "datas/backtest/trade_log.txt"
DATA_PATH_ASSET_LOG = "datas/backtest/asset_log.txt"
DATA_PATH_ASSET_IMG= "datas/backtest/asset_log.png"

FROM = date(2021, 7, 16)
TO = date(2023, 7, 14)

FIRST_MONEY = 3000000.0


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


# pdに対して，取引のルール判断に必要な数値を計算する
for i, code in enumerate(tqdm(codes_normal, desc="Calculating indices...")):
    
    # 調整済み終値
    adj_clo_prices = [x[15] for x in prices_normal[i]]
    
    # 売買代金(調整されてないっぽい)
    adj_volume = [x[10] for x in prices_normal[i]]
    
    # 出来立てで26日ない時は，0のリストを用意，これがmacdのルールに引っかかることはないはず
    if len(adj_clo_prices) >= 26:
        
        # 売買代金の10日移動平均
        movingvolume_10 = bn.move_mean(np.array(adj_volume), window=10).tolist()
        
        # 移動平均5，25
        movingline_5 = bn.move_mean(np.array(adj_clo_prices), window=5).tolist()
        movingline_25 = bn.move_mean(np.array(adj_clo_prices), window=25).tolist()
        
        # MACD, シグナル
        macd, signal = mylib_stock.calculate_macds(adj_clo_prices)
                
        # 9, 14, 22日RSI
        rsi_9 = mylib_stock.calculate_rsi(adj_clo_prices, n=9)
        rsi_14 = mylib_stock.calculate_rsi(adj_clo_prices, n=14)
        rsi_22 = mylib_stock.calculate_rsi(adj_clo_prices, n=22)
        
        # 移動平均乖離率
        movingline_deviation_5 = mylib_stock.calculate_movingline_deviation(adj_clo_prices, movingline_5)
        movingline_deviation_25 = mylib_stock.calculate_movingline_deviation(adj_clo_prices, movingline_25)
        
        # ボリンジャーバンド +1~3, -1~3, *25日移動平均で設定
        bollinger25_p1, bollinger25_p2, bollinger25_p3, bollinger25_m1, bollinger25_m2, bollinger25_m3 = mylib_stock.calculate_bollingers(adj_clo_prices, movingline_25)
        
        # ストキャスティクス
        FastK, FastD, SlowK, SlowD = mylib_stock.calculate_stochastics(adj_clo_prices)
        
        # サイコロジカルライン
        psychological = mylib_stock.calculate_psychological(adj_clo_prices)
        
        # 比率のモメンタム
        momentum_rate_10 = mylib_stock.calculate_momentum_rate(adj_clo_prices, 10)
        momentum_rate_20 = mylib_stock.calculate_momentum_rate(adj_clo_prices, 20)
        
    else:
        # 26日分作っておけばlist index out of rangeにはならない
        movingvolume_10, movinglines_5, movinglines_25, macd, signal, rsi_9, rsi_14, rsi_22, psychological, movingline_deviation_5, movingline_deviation_25, bollinger25_p1, bollinger25_p2, bollinger25_p3, bollinger25_m1, bollinger25_m2, bollinger25_m3, FastK, FastD, SlowK, SlowD, momentum_rate_10, momentum_rate_20 = [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26
    
    # 指標をリストに追加
    for j, day_price in enumerate(prices_normal[i]):
        prices_normal[i][j].extend([movingvolume_10[j], movingline_5[j], movingline_25[j], macd[j], signal[j], rsi_9[j], rsi_14[j], rsi_22[j], psychological[j],movingline_deviation_5[j], movingline_deviation_25[j], bollinger25_p1[j], bollinger25_p2[j], bollinger25_p3[j], bollinger25_m1[j], bollinger25_m2[j], bollinger25_m3[j], FastK[j], FastD[j], SlowK[j], SlowD[j], momentum_rate_10[j], momentum_rate_20[j]])


# データ処理が結構重いが，読み込みに1分強かかっていた．
# よって，保存せずに毎回計算する．           


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
        yesterday_record = code_price[today_index-1]
        today_record = code_price[today_index]

        # 前提条件
        # 平均売買代金が5千万円以上
        # さらに，株価が1万円以下
        judge_buy = False
        if today_record[17] > 50000000:
            if today_record[6] <= 10000:
                   
                # (1)さらに，MACDがシグナルを突き抜けた(record[20] > record[21]) or MACDが0を上回った(record[20]>0)
                # (1)さらに，RSIが40以下
                if (yesterday_record[20] < yesterday_record[21] and today_record[20] > yesterday_record[21]) or (yesterday_record[20] < 0 and today_record[20] > 0):
                    if today_record[23] <= 50:
                        judge_buy = True
                        
                # (2)さらに，株価が移動平均線25日の上から漸近した = 移動平均乖離率25(record[27])の下降が2%~20%，当日が0~20%
                deviation_down = yesterday_record[27] - today_record[27]
                deviation_today = today_record[27]
                if deviation_today >= 3 and deviation_today < 20 and deviation_down > 2 and deviation_down < 7:
                    #judge_buy = True
                    pass
                        
        if judge_buy:                
            trade_buy_candidates.append([today_record[1], today_record[2], today_record[6], today_record[17], today_record[15]])
    
    trade_buy_candidates.sort(key=lambda x:x[3], reverse=True)
    
    # trade_buy_candidatesの例
    # [['2021-08-16', 14190, 2370.0, 3923232400.0, price], ['2021-08-16', 14140, 4840.0, 660690650.0, price]]
    
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
        stocks.append([code, buy_num])

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
        sell_num = stock[1]
        
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
        
        # MACDのデッドクロスorMACDが0を下回ったか確認
        # MACD = record[20], シグ = record[21]
        if (yesterday_record[20] > yesterday_record[21] and today_record[20] < yesterday_record[21]) or (yesterday_record[20] > 0 and today_record[20] < 0):
            
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
        sell_num = stock[1]
        
        # prices_normalからcodeでrecordsを特定    
        code_index = codes_normal.index(code)  
        
        # 今日のレコードから代金を取得
        for record in prices_normal[code_index]:   
            if record[1] == today:
                price = record[15]
                break
            
        # 所持金の追加
        tmp_money += price*sell_num
        
    # ログ出力
    log = [today, str(tmp_money)]
    f_ase.write(f"{', '.join(log)}\n")
        

# 1日ずつ，取引を行う．移動平均などがあるので，30日ずらす
today = FROM + timedelta(days=30)
# 手持ち代金
money = FIRST_MONEY
# 手持ち株
stocks = defaultdict(int)
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
            stocks[code] = 0
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
                    stocks[x[0]] += x[1]
            # 一つだけの時は一つ
            elif type(sto[0]) is str:
                stocks[sto[0]] += sto[1]
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