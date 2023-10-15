import numpy as np
import pandas as pd
import bottleneck as bn
import math

import sys


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
        
        # 12日分の差を取得
        tmp = deltas[i-n:i]
        
        # 値上がりした日数/nがサイコロジカル
        psychological.append(len(tmp[tmp > 0])/n)
    
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