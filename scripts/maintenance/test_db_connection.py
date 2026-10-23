#!/usr/bin/env python3
"""
测试数据库连接
"""

from pymongo import MongoClient
from app.core.config import settings

def test_db_connection():
    """测试数据库连接"""
    print("=== 测试数据库连接 ===")
    
    try:
        # 使用settings.MONGO_URI连接数据库
        client = MongoClient(settings.MONGO_URI)
        db = client[settings.MONGO_DB]
        
        # 测试连接
        client.admin.command('ping')
        print(f"✅ MongoDB连接成功: {settings.MONGO_DB}")
        
        # 查询crawler_data集合
        collection = db.crawler_data
        count = collection.count_documents({})
        print(f"crawler_data集合记录数: {count}")
        
        # 查询一条示例数据
        sample = collection.find_one()
        if sample:
            print(f"示例数据字段: {list(sample.keys())}")
            print(f"示例数据: {sample}")
        
        client.close()
        
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")

if __name__ == "__main__":
    test_db_connection()
