import requests
import json
import pandas as pd
from sqlalchemy import create_engine
engine = create_engine('mysql+pymysql://root:admin@127.0.0.1:3306/lazada_ad?charset=utf8')
con = engine.connect()

request_url='http://bi.yibainetwork.com:8000/yibai/Lazada_report/query/campaign?jwt=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJzel9zYWxlc19hZF9kYXRhX2FuYWx5c2lzIiwiZXhwIjoxNjI0MzI1MTY5fQ.7m0nkQ33xejN7gMk0suwZzMRo6P3pi28iBw6iLay1VQ'
response = requests.post(url=request_url,
                         data=json.dumps({"statis_time": "2021-06-17","size":"10000000"})
                         )
data=json.loads(response.content)
df = pd.DataFrame(data=data['data_list'])

# df['account_name'].value_counts().shape
# df.drop_duplicates('account_name').count()
# tmp = df[
#             ['Spend', 'Impression', 'Clicks', 'Store Orders', 'Store Units Sold', 'Store Revenue']].sum().to_frame()
# ad=df[['account_name','store_revenue','spend', 'clicks', 'store_units_sold', 'impression','store_orders']]
# df.to_excel('D://广告数据.xlsx',index=False)
# df.to_sql(name='test', con=con, if_exists='append', index=False)

# request_url='http://bi.yibainetwork.com:8000/yibai/Lazada_report/query/store?jwt=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJzel9zYWxlc19hZF9kYXRhX2FuYWx5c2lzIiwiZXhwIjoxNjIzOTAwMDEwfQ.TcW0PxplGqtDP_sdhd60_z5IkQ7uy5ZiL76Y9kQuqng'
# response = requests.post(url=request_url,
#                          data=json.dumps({"statis_time": "2021-06-17","size":"1000000"})
#                          )
# data=json.loads(response.content)
# df = pd.DataFrame(data=data['data_list'])
df.to_sql(name='test', con=con, if_exists='append', index=False)