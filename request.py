import json
import requests
import pandas as pd
import joblib
import datetime
from tqdm import tqdm


API_URL = "https://api.jquants.com"
TOKEN_PATH = "etc/tokens.joblib"

MAIL_ADDRESS, PASSWORD = open("etc/mail-pass.txt", "r").read().split("\n")
USER_DATA = {"mailaddress":MAIL_ADDRESS, "password":PASSWORD}
NOW = (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).strftime('%Y%m%d%H%M%S')

get_token = False
get_code = False
get_price = False

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
    codes = codes[::]
    
    for code in tqdm(codes, desc="scraping price"):
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
                res = requests.get(f"https://api.jquants.com/v1/method?query=param&pagination_key={pagination_key}", headers=headers)
                data += res.json()["daily_quotes"]
            
            df = pd.DataFrame(data)
            df.to_csv(f"datas/price/{NOW}_{code}.csv")

        else:
            print(res.json())
            print(code)