from pymongo import MongoClient
from app.core.config import settings
from datetime import datetime, timedelta

# 连接MongoDB
client = MongoClient(settings.MONGO_URI)
db = client[settings.MONGO_DB]
collection = db.expert_ranking_data

# 检查4月3日的数据
date = datetime(2026, 4, 3)
start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
end_of_day = start_of_day + timedelta(days=1)

print("=== 检查4月3日专家排行数据 ===")

# 获取当天所有数据
cursor = collection.find({'crawled_at': {'$gte': start_of_day, '$lt': end_of_day}})
all_data = list(cursor)

print(f"4月3日总数据量: {len(all_data)}")

# 按小时统计数据量
hourly_counts = {}
for item in all_data:
    crawled_at = item.get('crawled_at')
    if crawled_at:
        hour = crawled_at.hour
        hourly_counts[hour] = hourly_counts.get(hour, 0) + 1

print("\n按小时统计数据量:")
for hour in sorted(hourly_counts.keys()):
    print(f"  {hour}:00 - {hour+1}:00: {hourly_counts[hour]} 条")

# 检查8:30-12:00之间的数据
start_time = date.replace(hour=8, minute=30)
end_time = date.replace(hour=12, minute=0)
cursor = collection.find({'crawled_at': {'$gte': start_time, '$lte': end_time}})
target_data = list(cursor)

print(f"\n8:30-12:00之间的数据量: {len(target_data)}")

if target_data:
    print("\n数据示例:")
    for item in target_data[:5]:
        print(f"  时间: {item['crawled_at']}, 专家: {item['expert_name']}, 股票: {item['name']}")
