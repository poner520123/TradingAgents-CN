#!/usr/bin/env python3
"""
验证股票映射导入结果的脚本
"""

from pymongo import MongoClient
from app.core.config import settings

# 连接MongoDB
client = MongoClient(settings.MONGO_URI)
db = client[settings.MONGO_DB]

# 获取映射总数
count = db.stock_name_code_mapping.count_documents({})
print(f'📊 股票映射总数: {count}')

# 获取前10条映射作为样本
print('\n🔍 前10条映射:')
sample = list(db.stock_name_code_mapping.find({}, {'_id': 0}).limit(10))
for item in sample:
    print(f'  {item["name"]} -> {item["code"]} ({item["market"]})')

# 获取后10条映射作为样本
print('\n🔍 后10条映射:')
sample = list(db.stock_name_code_mapping.find({}, {'_id': 0}).skip(count-10).limit(10))
for item in sample:
    print(f'  {item["name"]} -> {item["code"]} ({item["market"]})')

# 关闭MongoDB连接
client.close()
print('\n✅ 验证完成')