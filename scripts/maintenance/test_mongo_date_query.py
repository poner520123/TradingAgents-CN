#!/usr/bin/env python3
"""
测试MongoDB日期查询
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 获取MongoDB连接信息
MONGODB_CONNECTION_STRING = os.getenv('MONGODB_CONNECTION_STRING', 'mongodb://admin:admin123@localhost:27017/tradingagents?authSource=admin')
MONGODB_DATABASE_NAME = os.getenv('MONGODB_DATABASE_NAME', 'tradingagents')

def test_mongo_date_query():
    """测试MongoDB日期查询"""
    print("=== 测试MongoDB日期查询 ===")
    
    try:
        # 连接MongoDB
        client = MongoClient(MONGODB_CONNECTION_STRING)
        db = client[MONGODB_DATABASE_NAME]
        collection = db['crawler_data']
        
        # 测试1: 使用substr查询
        print("\n1. 使用substr查询2026-04-08的数据:")
        query1 = {
            '$expr': {
                '$eq': [
                    {'$substr': ['$time', 0, 10]},
                    '2026-04-08'
                ]
            }
        }
        
        count1 = collection.count_documents(query1)
        print(f"使用substr查询结果: {count1}条")
        
        # 获取一些数据示例
        if count1 > 0:
            sample_data = list(collection.find(query1, {'time': 1, 'stock_name': 1}).limit(5))
            print("数据示例:")
            for item in sample_data:
                print(f"  {item['time']} - {item['stock_name']}")
        
        # 测试2: 直接字符串查询
        print("\n2. 直接字符串查询包含2026-04-08的数据:")
        query2 = {'time': {'$regex': '^2026-04-08'}}
        count2 = collection.count_documents(query2)
        print(f"使用regex查询结果: {count2}条")
        
        # 测试3: 获取所有time字段的唯一日期
        print("\n3. 所有唯一日期:")
        pipeline = [
            {
                '$project': {
                    'date': {'$substr': ['$time', 0, 10]}
                }
            },
            {
                '$group': {
                    '_id': '$date',
                    'count': {'$sum': 1}
                }
            },
            {
                '$sort': {'_id': -1}
            },
            {
                '$limit': 10
            }
        ]
        
        result = list(collection.aggregate(pipeline))
        print("日期统计:")
        for item in result:
            print(f"  {item['_id']}: {item['count']}条")
            
    except Exception as e:
        print(f"查询失败: {e}")

if __name__ == "__main__":
    test_mongo_date_query()
