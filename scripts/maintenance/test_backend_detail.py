#!/usr/bin/env python3
"""
详细测试后端API筛选功能
"""

from pymongo import MongoClient
from app.core.config import settings
from app.services.crawler_service import CrawlerService

def test_backend_detail():
    """详细测试后端筛选功能"""
    print("=== 详细测试后端筛选功能 ===")
    
    # 创建服务实例
    service = CrawlerService()
    
    # 测试1: 空筛选
    print("\n1. 测试空筛选")
    data, total = service.get_data(page=1, page_size=10)
    print(f"总记录数: {total}")
    print(f"数据条数: {len(data)}")
    
    # 测试2: 伏击人筛选
    print("\n2. 测试伏击人筛选 - 涤生三风")
    data, total = service.get_data(page=1, page_size=10, user_name="涤生三风")
    print(f"总记录数: {total}")
    print(f"数据条数: {len(data)}")
    
    # 测试3: 成功率筛选
    print("\n3. 测试成功率筛选 - >= 80%")
    data, total = service.get_data(page=1, page_size=10, min_success_rate=80)
    print(f"总记录数: {total}")
    print(f"数据条数: {len(data)}")
    
    # 测试4: 日期范围筛选
    print("\n4. 测试日期范围筛选 - 2026-04-07")
    data, total = service.get_data(page=1, page_size=10, start_date="2026-04-07", end_date="2026-04-07")
    print(f"总记录数: {total}")
    print(f"数据条数: {len(data)}")
    
    # 测试5: 组合筛选
    print("\n5. 测试组合筛选 - 涤生三风 + >= 80%")
    data, total = service.get_data(page=1, page_size=10, user_name="涤生三风", min_success_rate=80)
    print(f"总记录数: {total}")
    print(f"数据条数: {len(data)}")
    
    # 测试6: 直接数据库查询
    print("\n6. 直接数据库查询测试")
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB]
    collection = db.crawler_data
    
    # 测试正则表达式匹配
    count = collection.count_documents({"user_name": {"$regex": "涤生三风", "$options": "i"}})
    print(f"直接查询 '涤生三风' 结果: {count} 条")
    
    # 测试成功率查询
    pipeline = [
        {"$project": {
            "success_rate_num": {
                "$toDouble": {"$replaceOne": {"input": "$success_rate", "find": "%", "replacement": ""}}
            }
        }},
        {"$match": {"success_rate_num": {"$gte": 80}}},
        {"$count": "total"}
    ]
    result = list(collection.aggregate(pipeline))
    count = result[0]["total"] if result else 0
    print(f"直接查询成功率 >= 80% 结果: {count} 条")
    
    # 测试日期查询
    count = collection.count_documents({"time": {"$regex": "2026-04-07"}})
    print(f"直接查询日期 2026-04-07 结果: {count} 条")

if __name__ == "__main__":
    test_backend_detail()
