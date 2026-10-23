from pymongo import MongoClient
from app.core.config import settings

# 连接数据库
client = MongoClient(settings.MONGO_URI)
db = client[settings.MONGO_DB]

# 查找正泰电源记录
print('查找正泰电源记录:')
zt_records = list(db.expert_ranking_data.find({'name': '正泰电源'}))
print(f'正泰电源记录数: {len(zt_records)}')
for r in zt_records:
    print(f'  {r.get("expert_name")}: {r.get("code")}')

# 查找东方新能记录
print('\n查找东方新能记录:')
df_records = list(db.expert_ranking_data.find({'name': '东方新能'}))
print(f'东方新能记录数: {len(df_records)}')
for r in df_records:
    print(f'  {r.get("expert_name")}: {r.get("code")}')

# 检查资金榜和人气榜数据
print('\n检查资金榜数据:')
fund_data = list(db.fund_ranking.find().limit(5))
print(f'资金榜记录数: {len(fund_data)}')
for d in fund_data:
    print(f'  {d.get("stock_name")} ({d.get("stock_code")})')

print('\n检查人气榜数据:')
pop_data = list(db.popularity_ranking.find().limit(5))
print(f'人气榜记录数: {len(pop_data)}')
for d in pop_data:
    print(f'  {d.get("stock_name")} ({d.get("stock_code")})')
