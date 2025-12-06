#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试从MongoDB读取股票名称代码映射数据，检查是否存在乱码问题
"""

import sys
import os
from pymongo import MongoClient
from app.core.config import settings

# 设置PYTHONPATH，确保能导入app模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_mongo_stock_map():
    """测试从MongoDB读取股票名称代码映射"""
    print("开始测试MongoDB股票名称代码映射...")
    
    # 连接MongoDB
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB]
    collection = db["stock_name_code_mapping"]
    
    try:
        # 统计总数
        total_count = collection.count_documents({})
        print(f"\nMongoDB中共有 {total_count} 条股票名称代码映射记录")
        
        # 读取前10条记录
        print("\n前10条映射记录:")
        print("=" * 50)
        
        # 查询前10条记录
        maps = collection.find().limit(10)
        
        for i, map_data in enumerate(maps, 1):
            name = map_data.get("name", "")
            code = map_data.get("code", "")
            market = map_data.get("market", "")
            updated_at = map_data.get("updated_at", "")
            
            print(f"{i:2d}. 名称: {name}")
            print(f"    代码: {code}")
            print(f"    市场: {market}")
            print(f"    更新时间: {updated_at}")
            print("-" * 50)
        
        # 检查是否有乱码
        print("\n检查是否存在乱码...")
        
        # 查询更多记录进行检查
        maps = collection.find().limit(100)
        has_gibberish = False
        
        for map_data in maps:
            name = map_data.get("name", "")
            
            # 简单检查是否有乱码（包含非中文字符或特定乱码模式）
            if name and ("淇℃繝" in name or "宸村畨" in name or "鎭掗攱" in name):
                print(f"发现乱码: {name} -> {map_data.get('code')}")
                has_gibberish = True
        
        if has_gibberish:
            print("\n❌ 测试失败: 发现乱码记录")
            return False
        else:
            print("\n✅ 测试成功: 未发现乱码记录")
            return True
            
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        return False
    finally:
        # 关闭MongoDB连接
        client.close()


if __name__ == "__main__":
    success = test_mongo_stock_map()
    sys.exit(0 if success else 1)
