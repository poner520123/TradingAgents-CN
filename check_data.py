#!/usr/bin/env python3
"""
检查数据库中的爬虫数据
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 获取MongoDB连接信息
MONGODB_CONNECTION_STRING = os.getenv('MONGODB_CONNECTION_STRING', 'mongodb://admin:admin123@localhost:27017/tradingagents?authSource=admin')
MONGODB_DATABASE_NAME = os.getenv('MONGODB_DATABASE_NAME', 'tradingagents')

def check_database():
    """检查数据库中的爬虫数据"""
    print("=== 检查数据库连接 ===")
    
    try:
        # 连接MongoDB
        client = MongoClient(MONGODB_CONNECTION_STRING)
        db = client[MONGODB_DATABASE_NAME]
        collection = db['crawler_data']
        
        # 获取总记录数
        total_count = collection.count_documents({})
        print(f"数据库中总记录数: {total_count}")
        
        if total_count > 0:
            # 获取前5条记录作为示例
            sample_data = list(collection.find().limit(5))
            print("\n示例数据:")
            for i, item in enumerate(sample_data, 1):
                print(f"\n--- 记录 {i} ---")
                print(f"ID: {item.get('_id')}")
                print(f"伏击人: {item.get('user_name')}")
                print(f"成功率: {item.get('success_rate')}")
                print(f"伏击理由: {item.get('reason')}")
                print(f"日期: {item.get('date')}")
        else:
            print("数据库中没有数据")
            
    except Exception as e:
        print(f"数据库连接失败: {e}")

if __name__ == "__main__":
    check_database()
