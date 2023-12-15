import numpy as np
import pandas as pd
import bottleneck as bn
import math
import tqdm

import sys


# 価格のデータを受け取り，テクニカル指標などを追加して返す
def calculate_indices(codes_normal:list, prices_normal:list) -> list:
    for i, code in enumerate(tqdm(codes_normal, desc="Calculating indices...")):
    
        # 調整済み終値
        adj_clo_prices = [x[15] for x in prices_normal[i]]
        
        # 調整済み始値
        adj_ope_prices = [x[12] for x in prices_normal[i]]
        
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
            macd, signal = calculate_macds(adj_clo_prices)
                    
            # 9, 14, 22日RSI
            rsi_9 = calculate_rsi(adj_clo_prices, n=9)
            rsi_14 = calculate_rsi(adj_clo_prices, n=14)
            rsi_22 = calculate_rsi(adj_clo_prices, n=22)
            
            # 移動平均乖離率
            movingline_deviation_5 = calculate_movingline_deviation(adj_clo_prices, movingline_5)
            movingline_deviation_25 = calculate_movingline_deviation(adj_clo_prices, movingline_25)
            
            # ボリンジャーバンド +1~3, -1~3, *25日移動平均で設定
            bollinger25_p1, bollinger25_p2, bollinger25_p3, bollinger25_m1, bollinger25_m2, bollinger25_m3 = calculate_bollingers(adj_clo_prices, movingline_25)
            
            # ストキャスティクス
            FastK, FastD, SlowK, SlowD = calculate_stochastics(adj_clo_prices)
            
            # サイコロジカルライン
            psychological = calculate_psychological(adj_clo_prices)
            
            # 比率のモメンタム
            momentum_rate_10 = calculate_momentum_rate(adj_clo_prices, 10)
            momentum_rate_20 = calculate_momentum_rate(adj_clo_prices, 20)
            
            # 終値の階差割合
            close_diff_rate1 = calculate_close_diff_rate(adj_clo_prices, 1)
            close_diff_rate5 = calculate_close_diff_rate(adj_clo_prices, 5)
            close_diff_rate25 = calculate_close_diff_rate(adj_clo_prices, 25)
            
            # ボラティリティ
            volatility5 = calculate_volatility(adj_clo_prices, 5)
            volatility25 = calculate_volatility(adj_clo_prices, 25)
            volatility60 = calculate_volatility(adj_clo_prices, 60)
            
            # 1日リターン{(close/open)-1.0}
            ret1 = calculate_return(adj_clo_prices, adj_ope_prices)
            
        else:
            # 26日分作っておけばlist index out of rangeにはならない
            movingvolume_10, movingline_5, movingline_25, macd, signal, rsi_9, rsi_14, rsi_22, psychological, movingline_deviation_5, movingline_deviation_25, bollinger25_p1, bollinger25_p2, bollinger25_p3, bollinger25_m1, bollinger25_m2, bollinger25_m3, FastK, FastD, SlowK, SlowD, momentum_rate_10, momentum_rate_20, close_diff_rate1, close_diff_rate5, close_diff_rate25, volatility5, volatility25, volatility60, ret1 = [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26, [0]*26
        
        # 指標をリストに追加
        for j, day_price in enumerate(prices_normal[i]):
            prices_normal[i][j].extend([movingvolume_10[j], movingline_5[j], movingline_25[j], macd[j], signal[j], rsi_9[j], rsi_14[j], rsi_22[j], psychological[j],movingline_deviation_5[j], movingline_deviation_25[j], bollinger25_p1[j], bollinger25_p2[j], bollinger25_p3[j], bollinger25_m1[j], bollinger25_m2[j], bollinger25_m3[j], FastK[j], FastD[j], SlowK[j], SlowD[j], momentum_rate_10[j], momentum_rate_20[j], close_diff_rate1[j], close_diff_rate5[j], close_diff_rate25[j], volatility5[j], volatility25[j], volatility60[j], ret1[j]])

# 与えられたリストからRSIを計算
def calculate_rsi(prices:list, n=14) -> list:
    
    # 最初のn-1日はすべてRSIが同じ
    # 株価の変化
    deltas = np.diff(prices)
    tmp = deltas[:n+1]
    
    # 上昇・下降した値の和
    up = tmp[tmp >= 0].sum()/n
    down = -tmp[tmp < 0].sum()/n
    
    # rsおよびrsiの計算
    if down == 0:
        down = 0.001
    rs = up/down
    rsi = np.zeros(len(prices))
    rsi[:n] = 100. - 100./(1.+rs)

    # n日目以降はその日からn日前までの値で計算
    for i in range(n, len(prices)):
        delta = deltas[i-1]

        if delta > 0:
            up_day = delta
            down_day = 0.
        else:
            up_day = 0.
            down_day = -delta

        up = (up*(n-1) + up_day)/n
        down = (down*(n-1) + down_day)/n

        rs = up/down
        rsi[i] = 100. - 100./(1.+rs)
        
    rsi = [round(x) if type(x) is float else x for x in list(rsi)]
        
    return rsi


# 与えられたリストからMACDとシグナルを計算
def calculate_macds(prices:list, short_n=12, long_n=26, sig_n=9) -> [list, list]:
    
    pd_prices = pd.Series(prices)

    # 短期EMA(short_n週)
    s_ema = pd_prices.ewm(span=short_n, adjust=False).mean()
    # 長期EMA(long_n週)
    l_ema = pd_prices.ewm(span=long_n, adjust=False).mean()
    # macd
    macd = (s_ema - l_ema).tolist()
    # シグナル
    signal = pd.Series(macd).ewm(span=sig_n, adjust=False).mean().tolist()
    
    return macd, signal


# 与えられたリスト(株価，移動平均線)から移動平均乖離率を計算
def calculate_movingline_deviation(prices:list, movingline_n:list) -> list:
        
    deviations = [(float(x-y)/float(y))*100 for x, y in zip(prices, movingline_n)]    
    return deviations


# 与えられたリストからボリンジャーバンド +1~3, -1~3を計算
def calculate_bollingers(prices:list, movingline_n:list, n=25):
    
    # 初期24日分は計算できないので0
    bollinger25_p1, bollinger25_p2, bollinger25_p3, bollinger25_m1, bollinger25_m2, bollinger25_m3 = [0]*(n-1), [0]*(n-1), [0]*(n-1), [0]*(n-1), [0]*(n-1), [0]*(n-1)
    
    # 25日目からpriceの長さまで計算
    for i in range(n, len(prices)+1):
        
        # 直近25日分の価格から標準偏差を計算
        tmp = prices[i-n:i]
        tmp_pow_sum = sum([x**2 for x in tmp])
        tmp_sum_pow = sum(tmp)**2
        sigma = math.sqrt((n*tmp_pow_sum-tmp_sum_pow)/(n*(n-1)))
        
        bollinger25_p1.append(movingline_n[i-1]+sigma)
        bollinger25_p2.append(movingline_n[i-1]+sigma*2)
        bollinger25_p3.append(movingline_n[i-1]+sigma*3)
        bollinger25_m1.append(movingline_n[i-1]-sigma)
        bollinger25_m2.append(movingline_n[i-1]-sigma*2)
        bollinger25_m3.append(movingline_n[i-1]-sigma*3)
    
    return bollinger25_p1, bollinger25_p2, bollinger25_p3, bollinger25_m1, bollinger25_m2, bollinger25_m3


# 与えられたリストからストキャスティクスを計算
def calculate_stochastics(prices:list, n=9) -> [list, list, list, list]:
    
    # FastK以外はFastKから計算できるので，まずFastKを計算
    # 最初のn-1日間は計算できない
    FastK = [0]*(n-1)
    
    # 9日目から計算
    for i in range(n, len(prices)+1):
        
        # 直近9日の値から最高/最低を計算
        tmp = prices[i-n:i]
        now = tmp[-1]
        up = max(tmp)
        down = min(tmp)
        
        # FastKを計算して追加
        # division zero対策もしておく
        if  up-down == 0:
            up += 0.001
            
        tmp_FastK = ((now-down)/(up-down)) * 100
        FastK.append(tmp_FastK)
        
    # FastD, SlowDなどの計算で0が伝播していく．
    # しかし，よって，トレードで30日ずらしており，伝播していく日にちは9+3+3=15<30なので大丈夫．
    # FastDの計算
    FastD = bn.move_mean(np.array(FastK), window=3).tolist()
    # SLowKはFastDに同じ
    SlowK = FastD
    # SlowDの計算
    SlowD = bn.move_mean(np.array(FastD), window=3).tolist()
    
    return FastK, FastD, SlowK, SlowD


# 与えられたリストからサイコロジカルラインを計算
def calculate_psychological(prices:list, n=12) -> list:
    
    # 最初の11日間は0
    psychological = [0]*(n-1)
    
    # 株価の差
    deltas = np.diff(prices)
    
    # 12日から，サイコロジカルラインを計算
    for i in range(n, len(prices)+1):
        
        # 11日分の差を取得
        tmp = deltas[i-n:i-1]
        
        # 値上がりした日数/nがサイコロジカル
        psychological.append(len(tmp[tmp > 0])/(n-1))
    
    return psychological

# 与えられたリストからモメンタムを比率ベースで計算
def calculate_momentum_rate(prices:list, n=int) -> list:
    
    # 最初のn-1日間は0
    momentum_rate = [0]*(n-1)
    
    # n日目からはモメンタムを計算
    # 今回は，比率ベース(100を超えるかどうか)で計算
    for i in range(n-1, len(prices)):
                
        # 当日の株価/n日前の株価がモメンタム
        momentum_rate.append(prices[i]/prices[i-n]*100)
    
    return momentum_rate

# 与えられたリストから終値の階差を比率ベースで計算
def calculate_close_diff_rate(prices:list, n=int) -> list:
    
    pd_prices = pd.Series(prices)
    close_diff_rate = pd_prices.pct_change(n).fillna(0)
    
    return close_diff_rate

# 与えられたリストからボラティリティを計算
def calculate_volatility(prices:list, n=int) -> list:
    
    pd_prices = pd.Series(prices)
    volatility = np.log(pd_prices).diff().rolling(n).std().fillna(0)
    
    return volatility

# 与えられたリストから1日リターン(close/open)-1.0を計算
def calculate_return(closes:list, opens=list) -> list:
    
    pd_close = pd.Series(closes)
    pd_open = pd.Series(opens)
    
    ret1 = (pd_close / pd_open) - 1.0
    ret1 = ret1.shift(-1).fillna(0)
    
    return ret1