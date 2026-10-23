#!/usr/bin/env python3
"""
检查数据库中time字段的格式
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 获取MongoDB连接信息
MONGODB_CONNECTION_STRING = os.getenv('MONGODB_CONNECTION_STRING', 'mongodb://admin:admin123@localhost:27017/tradingagents?authSource=admin')
MONGODB_DATABASE_NAME = os.getenv('MONGODB_DATABASE_NAME', 'tradingagents')

def check_time_format():
    """检查数据库中time字段的格式"""
    print("=== 检查数据库中time字段的格式 ===")
    
    try:
        # 连接MongoDB
        client = MongoClient(MONGODB_CONNECTION_STRING)
        db = client[MONGODB_DATABASE_NAME]
        collection = db['crawler_data']
        
        # 获取前5条记录的time字段
        sample_data = list(collection.find({}, {'time': 1}).limit(5))
        
        if sample_data:
            print(f"\n时间字段格式示例:")
            for i, item in enumerate(sample_data, 1):
                time_value = item.get('time')
                print(f"  记录 {i}: {time_value} (类型: {type(time_value).__name__})")
            
            # 检查time字段的格式
            print("\n=== 时间格式分析 ===")
            time_formats = {}
            
            # 获取100条记录进行分析
            for item in collection.find({}, {'time': 1}).limit(100):
                time_value = item.get('time')
                if time_value:
                    # 检查是否包含空格（日期和时间的分隔）
                    if ' ' in time_value:
                        date_part, time_part = time_value.split(' ', 1)
                        format_key = f"日期: {date_part}, 时间: {time_part[:2]}:xx"
                    else:
                        format_key = f"无空格: {time_value}"
                    
                    time_formats[format_key] = time_formats.get(format_key, 0) + 1
            
            print("时间格式分布:")
            for format_key, count in time_formats.items():
                print(f"  {format_key}: {count}条")
                
            # 获取最新的10条记录
            print("\n最新的10条记录:")
            latest_data = list(collection.find({}, {'time': 1, 'stock_name': 1}).sort('time', -1).limit(10))
            for item in latest_data:
                print(f"  {item.get('time')} - {item.get('stock_name')}")
            
        else:
            print("数据库中没有数据")
            
    except Exception as e:
        print(f"数据库连接失败: {e}")

if __name__ == "__main__":
    check_time_format()
