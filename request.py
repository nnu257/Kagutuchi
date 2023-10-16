import json
import requests
import pandas as pd
import joblib
from datetime import datetime, timedelta
from tqdm import tqdm
import os


API_URL = "https://api.jquants.com"
TOKEN_PATH = "etc/tokens.joblib"
EXE_TIME_RECORD_PATH = "etc/exe_time.txt"
DATETIME_FORMAT = '%Y%m%d%H%M%S'

MAIL_ADDRESS, PASSWORD = open("etc/mail-pass.txt", "r").read().split("\n")
USER_DATA = {"mailaddress":MAIL_ADDRESS, "password":PASSWORD}
NOW = (datetime.utcnow() + timedelta(hours=9)).strftime(DATETIME_FORMAT)


# トークン取得は前回実行から5時間以降経過しているなら実行
# 本来なら24時間で切れるが，実行時間を考慮
if not os.path.isfile(EXE_TIME_RECORD_PATH):
    get_token = True
else:
    exerted_time_before = datetime.strptime(open(EXE_TIME_RECORD_PATH).read(), DATETIME_FORMAT)
    if (datetime.strptime(NOW, DATETIME_FORMAT) - exerted_time_before).total_seconds() > 18000:
        get_token = True
    else:
        get_token = False
open(EXE_TIME_RECORD_PATH, "w").write(NOW)
        
# 強制でフラグをonにしたい時用
# get_token = True

# 各取得情報フラグ
# TOPIX4本値はLight以上(有料)のプランのみ取得可能
get_code = False
get_price = False
get_fins = False
get_TOPIX = False


if get_token:
    # refresh token取得
    try:
        res = requests.post(f"{API_URL}/v1/token/auth_user", data=json.dumps(USER_DATA))
        refresh_token = res.json()['refreshToken']
    except:
        print("RefreshTokenの取得に失敗しました。")
    else:
        # id token取得
        try:
            res = requests.post(f"{API_URL}/v1/token/auth_refresh?refreshtoken={refresh_token}")
            id_token = res.json()['idToken']
        except:
            print("idTokenの取得に失敗しました。")
        else:
            headers = {'Authorization': 'Bearer {}'.format(id_token)}
            joblib.dump(headers, TOKEN_PATH, compress=3)
            print("API使用の準備が完了しました。")
else:
    headers = joblib.load(TOKEN_PATH)
            
# 銘柄情報の取得
if get_code:
    
    code = ""
    date = ""
    
    query = ""
    if code != "":
        query += f'code={code}'
    if date != "":
        if code !="":
            query += "&"
        query += f'date={date}'
    if query != "":
        query = "?"+query
    res = requests.get(f"{API_URL}/v1/listed/info{query}", headers=headers)
    if res.status_code == 200:
        data = res.json()["info"]
        df = pd.DataFrame(data)
        #print(df)
        df.to_csv(f"datas/code/{NOW}.tsv", sep="\t")
    else:
        print(res.json())
        
# 株価の取得
# 最初からまとめるのではなく，まずは別々で取得して保存する
# その後，summary_priceなどでまとめる．
if get_price:
    
    codes = open("datas/code/20231008205049_codes.txt", "r").read().splitlines()
    
    # codes = ["30730","47390","84730", "97190"]
    
    for code in tqdm(codes, desc="scraping price..."):
        code = code
        date = ""
        from_ = ""
        to = ""
        
        query = ""
        if code != "":
            query += f'code={code}'
        if date != "":
            if code !="":
                query += "&"
            query += f'date={date}'
        if from_ != "":
            if query !="":
                query += "&"
            query += f'from={from_}'
        if to != "":
            if query !="":
                query += "&"
            query += f'to={to}'
        if query != "":
            query = "?"+query
            
        res = requests.get(f"{API_URL}/v1/prices/daily_quotes{query}", headers=headers)
        
        if res.status_code == 200:
            
            data = res.json()["daily_quotes"]
            
            # 大容量データが返却された場合の再検索
            # データ量により複数ページ取得できる場合があるため、pagination_keyが含まれる限り、再検索を実施
            while "pagination_key" in res.json():
                pagination_key = res.json()["pagination_key"]
                res = requests.get(f"{API_URL}/v1/prices/daily_quotes{query}&pagination_key={pagination_key}", headers=headers)
                data += res.json()["daily_quotes"]
            
            df = pd.DataFrame(data)
            df.to_csv(f"datas/price/{NOW}_{code}.csv")

        else:
            print(res.json())
            print(code)
            
            
# 財務情報の取得
# 最初からまとめるのではなく，まずは別々で取得して保存する
# その後，summary_finsでまとめる．
if get_fins:
    
    codes = open("datas/code/20231008205049_codes.txt", "r").read().splitlines()
    
    # codes = ["30730","47390","84730", "97190"]
    
    for code in tqdm(codes, desc="scraping fins..."):
        code = code
        date = ""
        query = ""
        if code != "":
            query += f'code={code}'
        if date != "":
            if code !="":
                query += "&"
            query += f'date={date}'
        if query != "":
            query = "?"+query

        res = requests.get(f"{API_URL}/v1/fins/statements{query}", headers=headers)

        if res.status_code == 200:
            data = res.json()["statements"]
            
            # 大容量データが返却された場合の再検索
            # データ量により複数ページ取得できる場合があるため、pagination_keyが含まれる限り、再検索を実施
            while "pagination_key" in res.json():
                pagination_key = res.json()["pagination_key"]
                res = requests.get(f"{API_URL}/v1/fins/statements{query}&pagination_key={pagination_key}", headers=headers)
                data += res.json()["statements"]
            
            df = pd.DataFrame(data)
            df.to_csv(f"datas/fins/{NOW}_{code}.csv")
        else:
            print(res.json())
            print(code)
            

# TOPIX4本値の取得
if get_TOPIX:
    date_from = ""
    date_to = ""
    query = ""
    if date_from != "":
        query += f'from={date_from}'
    if date_to != "":
        if date_from !="":
            query += "&"
        query += f'to={date_to}'
    if query != "":
        query = "?"+query
    
    res = requests.get(f"{API_URL}/v1/indices/topix{query}", headers=headers)
    
    if res.status_code == 200:
        data = res.json()["topix"]
        
        # 大容量データが返却された場合の再検索
        # データ量により複数ページ取得できる場合があるため、pagination_keyが含まれる限り、再検索を実施
        while "pagination_key" in res.json():
            pagination_key = res.json()["pagination_key"]
            res = requests.get(f"{API_URL}/v1/indices/topix{query}&pagination_key={pagination_key}", headers=headers)
            data += res.json()["topix"]
        
        df = pd.DataFrame(data)
        df.to_csv(f"datas/{NOW}_TOPIX.csv")
    else:
        print(res.json())