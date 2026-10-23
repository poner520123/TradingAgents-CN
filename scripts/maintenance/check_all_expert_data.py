from pymongo import MongoClient
from app.core.config import settings
from datetime import datetime, timedelta

# 连接MongoDB
client = MongoClient(settings.MONGO_URI)
db = client[settings.MONGO_DB]
collection = db.expert_ranking_data

print("=== 检查所有专家排行数据时间分布 ===")

# 获取所有数据
cursor = collection.find().sort('crawled_at', -1)
all_data = list(cursor)

print(f"总数据量: {len(all_data)}")

if all_data:
    # 获取最新和最早的数据时间
    latest_time = all_data[0].get('crawled_at')
    earliest_time = all_data[-1].get('crawled_at')
    
    print(f"\n最新数据时间: {latest_time}")
    print(f"最早数据时间: {earliest_time}")
    
    # 按天统计数据量
    daily_counts = {}
    for item in all_data:
        crawled_at = item.get('crawled_at')
        if crawled_at:
            date_str = crawled_at.strftime('%Y-%m-%d')
            daily_counts[date_str] = daily_counts.get(date_str, 0) + 1
    
    print("\n按日期统计数据量:")
    for date in sorted(daily_counts.keys()):
        print(f"  {date}: {daily_counts[date]} 条")
    
    # 检查4月3日的数据
    print("\n=== 检查4月3日数据 ===")
    date_20260403 = datetime(2026, 4, 3)
    start_of_day = date_20260403.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)
    
    cursor = collection.find({'crawled_at': {'$gte': start_of_day, '$lt': end_of_day}})
    data_20260403 = list(cursor)
    print(f"4月3日数据量: {len(data_20260403)}")
    
else:
    print("数据库中没有专家排行数据")
