#!/usr/bin/env python3
"""
调试筛选功能
"""

from pymongo import MongoClient
from app.core.config import settings

def debug_database():
    """调试数据库查询"""
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB]
    collection = db.crawler_data
    
    print("=== 数据库调试信息 ===")
    
    # 统计总记录数
    total = collection.count_documents({})
    print(f"总记录数: {total}")
    
    # 查看字段名
    sample = collection.find_one()
    if sample:
        print(f"字段列表: {list(sample.keys())}")
    
    # 查看用户名称分布
    print("\n=== 用户名称分布 ===")
    pipeline = [
        {"$group": {"_id": "$user_name", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    users = list(collection.aggregate(pipeline))
    for user in users:
        print(f"  {user['_id']}: {user['count']} 条")
    
    # 查看成功率分布
    print("\n=== 成功率分布 ===")
    pipeline = [
        {"$project": {
            "success_rate_num": {
                "$toDouble": {"$replaceOne": {"input": "$success_rate", "find": "%", "replacement": ""}}
            }
        }},
        {"$match": {"success_rate_num": {"$gte": 0}}},
        {"$group": {
            "_id": {
                "$floor": {"$divide": ["$success_rate_num", 10]}
            },
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]
    rates = list(collection.aggregate(pipeline))
    for rate in rates:
        range_start = rate["_id"] * 10
        range_end = (rate["_id"] + 1) * 10
        print(f"  {range_start}-{range_end}%: {rate['count']} 条")
    
    # 查看时间分布
    print("\n=== 时间分布 ===")
    pipeline = [
        {"$group": {"_id": {"$substr": ["$time", 0, 10]}, "count": {"$sum": 1}}},
        {"$sort": {"_id": -1}},
        {"$limit": 10}
    ]
    dates = list(collection.aggregate(pipeline))
    for date in dates:
        print(f"  {date['_id']}: {date['count']} 条")
    
    # 测试正则表达式匹配
    print("\n=== 测试正则表达式匹配 ===")
    test_users = ["涤生三风", "老子到处说", "无量击掌"]
    for user in test_users:
        count = collection.count_documents({"user_name": {"$regex": user, "$options": "i"}})
        print(f"  用户 '{user}' 匹配结果: {count} 条")

if __name__ == "__main__":
    debug_database()
