"""检查爬虫数据状态的脚本"""
import sys
sys.path.insert(0, '.')

from datetime import datetime, timedelta
from app.core.database import get_mongo_db_sync

db = get_mongo_db_sync()

print(f"爬虫数据总数: {db.crawler_data.count_documents({})}")

# 获取今天的日期
today = datetime.now().date()
yesterday = today - timedelta(days=1)

# 查找今天和昨天的数据
today_str = today.strftime('%Y-%m-%d')
yesterday_str = yesterday.strftime('%Y-%m-%d')

print(f"\n查找日期: 今天={today_str}, 昨天={yesterday_str}")

# 查找最新数据的时间
latest = db.crawler_data.find_one(sort=[("crawled_at", -1)])
if latest:
    print(f"\n最新数据的crawled_at: {latest.get('crawled_at')}")
    print(f"最新数据的time字段: {latest.get('time')}")
else:
    print("\n没有找到任何爬虫数据")

# 按日期分组统计数据
pipeline = [
    {
        "$project": {
            "date": {
                "$substr": ["$time", 0, 10]
            }
        }
    },
    {
        "$group": {
            "_id": "$date",
            "count": {"$sum": 1}
        }
    },
    {
        "$sort": {"_id": -1}
    },
    {
        "$limit": 10
    }
]

print("\n按日期统计 (最新10天):")
results = list(db.crawler_data.aggregate(pipeline))
for r in results:
    print(f"  {r['_id']}: {r['count']} 条")

# 检查4月30日的数据
april_30 = "2026-04-30"
today_str_check = datetime.now().strftime('%Y-%m-%d')

print(f"\n查找日期 {april_30} 的数据:")
april_30_data = list(db.crawler_data.find({"time": {"$regex": f"^{april_30}"}}).limit(5))
print(f"4月30日数据数量: {len(april_30_data)}")

print(f"\n查找日期 {today_str_check} 的数据:")
today_data = list(db.crawler_data.find({"time": {"$regex": f"^{today_str_check}"}}).limit(5))
print(f"今天数据数量: {len(today_data)}")

# 显示最新5条数据
print("\n最新5条数据:")
latest_5 = list(db.crawler_data.find().sort("crawled_at", -1).limit(5))
for d in latest_5:
    print(f"  time={d.get('time')}, stock_name={d.get('stock_name')}, crawled_at={d.get('crawled_at')}")
