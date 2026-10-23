#!/usr/bin/env python3
"""
检查数据库中数据的字段结构
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 获取MongoDB连接信息
MONGODB_CONNECTION_STRING = os.getenv('MONGODB_CONNECTION_STRING', 'mongodb://admin:admin123@localhost:27017/tradingagents?authSource=admin')
MONGODB_DATABASE_NAME = os.getenv('MONGODB_DATABASE_NAME', 'tradingagents')

def check_fields():
    """检查数据库中数据的字段结构"""
    print("=== 检查数据库字段结构 ===")
    
    try:
        # 连接MongoDB
        client = MongoClient(MONGODB_CONNECTION_STRING)
        db = client[MONGODB_DATABASE_NAME]
        collection = db['crawler_data']
        
        # 获取前5条记录的字段
        sample_data = list(collection.find().limit(5))
        
        if sample_data:
            print(f"\n数据字段分析（基于前5条记录）:")
            for i, item in enumerate(sample_data, 1):
                print(f"\n--- 记录 {i} 的字段 ---")
                for key, value in item.items():
                    print(f"  {key}: {value}")
            
            # 获取所有可能的字段名
            all_fields = set()
            for item in collection.find().limit(100):
                all_fields.update(item.keys())
            
            print(f"\n所有字段名: {sorted(all_fields)}")
            
            # 检查time字段的值
            print("\n=== 检查time字段 ===")
            time_values = collection.distinct('time')[:10]  # 取前10个不同的值
            print(f"time字段的值示例: {time_values}")
            
            # 检查是否有time字段为None的记录
            none_time_count = collection.count_documents({'time': None})
            print(f"time字段为None的记录数: {none_time_count}")
            
            # 检查是否有date字段
            date_values = collection.distinct('date')[:10]
            print(f"\ndate字段的值示例: {date_values}")
            
        else:
            print("数据库中没有数据")
            
    except Exception as e:
        print(f"数据库连接失败: {e}")

if __name__ == "__main__":
    check_fields()
