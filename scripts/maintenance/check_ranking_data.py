"""检查排行数据"""
from pymongo import MongoClient

# 连接MongoDB
client = MongoClient('mongodb://admin:admin123@localhost:27017/')
db = client['tradingagents']

# 检查人气排行数据
popularity_collection = db.popularity_ranking
popularity_count = popularity_collection.count_documents({})
print(f"人气排行数据数量: {popularity_count}")

if popularity_count > 0:
    # 查看最近5条数据
    recent_data = popularity_collection.find().sort("crawl_time", -1).limit(5)
    print("\n最近5条人气排行数据:")
    for item in recent_data:
        print(f"- 股票: {item.get('stock_name', '未知')} ({item.get('stock_code', '未知')})")
        print(f"  人气值: {item.get('popularity_value', '未知')}")
        print(f"  价格: {item.get('price', '未知')}")
        print(f"  爬取时间: {item.get('crawl_time', '未知')}")
        print()

# 检查资金排行数据
fund_collection = db.fund_ranking
fund_count = fund_collection.count_documents({})
print(f"资金排行数据数量: {fund_count}")

if fund_count > 0:
    # 查看最近5条数据
    recent_data = fund_collection.find().sort("crawl_time", -1).limit(5)
    print("\n最近5条资金排行数据:")
    for item in recent_data:
        print(f"- 股票: {item.get('stock_name', '未知')} ({item.get('stock_code', '未知')})")
        print(f"  资金净流入: {item.get('net_inflow', '未知')}")
        print(f"  价格: {item.get('price', '未知')}")
        print(f"  爬取时间: {item.get('crawl_time', '未知')}")
        print()

# 检查爬虫数据
crawler_collection = db.crawler_data
crawler_count = crawler_collection.count_documents({})
print(f"爬虫数据数量: {crawler_count}")

client.close()