#!/usr/bin/env python3
"""
修复股票代码为None的记录
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 获取MongoDB连接信息
MONGODB_CONNECTION_STRING = os.getenv('MONGODB_CONNECTION_STRING', 'mongodb://admin:admin123@localhost:27017/tradingagents?authSource=admin')
MONGODB_DATABASE_NAME = os.getenv('MONGODB_DATABASE_NAME', 'tradingagents')

# 手动添加的股票代码映射
STOCK_CODE_MAPPING = {
    '东方新能': '000958',  # 东方新能源
    '电投水电': '600905',  # 电投能源
    '电投能源': '600905',
    '中稀有色': '000831',  # 中色股份
    '国科天成': '301571',
    '瑞康医药': '002589',
    '康强电子': '002119',
    '九安医疗': '002432',
    '航天电器': '002025',
    '杭电股份': '603618',
    '民爆光电': '301362',
    '福晶科技': '002222',
    '泛微网络': '603039',
    '瑞斯康达': '603803',
    '金牛化工': '600722',
    '奥士康': '002913',
    '直真科技': '003007',
    '电连技术': '300679',
    '创业慧康': '300451',
    '天汽模': '002510',
    '远程股份': '002692',
    '金安国纪': '002636',
    '顺威股份': '002676',
    '云赛智联': '600602',
    '法尔胜': '000890',
    '翠微股份': '603123',
    '松芝股份': '002454',
    '中色股份': '000831',
    '航天动力': '600343',
    '杰恩设计': '300668',
    '中联重科': '000157',
    '长城科技': '603897',
    '鹭燕医药': '002788',
    '珈伟新能': '300317',
    '棒杰股份': '002634',
    '中工国际': '002051',
    '锴威特': '688691',
    '国科环宇': '688535',
    '中钢国际': '000928',
}

def fix_none_stock_codes():
    """修复股票代码为None的记录"""
    print("=== 修复股票代码为None的记录 ===")
    
    try:
        # 连接MongoDB
        client = MongoClient(MONGODB_CONNECTION_STRING)
        db = client[MONGODB_DATABASE_NAME]
        collection = db['crawler_data']
        
        # 查询股票代码为None的记录
        none_code_records = list(collection.find({'stock_code': None}))
        print(f"\n找到 {len(none_code_records)} 条股票代码为None的记录")
        
        if none_code_records:
            print("\n股票代码为None的股票名称:")
            stock_names = set()
            for record in none_code_records:
                stock_names.add(record.get('stock_name'))
            
            for name in sorted(stock_names):
                print(f"  - {name}")
            
            # 使用手动映射修复股票代码
            updated_count = 0
            for stock_name, stock_code in STOCK_CODE_MAPPING.items():
                result = collection.update_many(
                    {'stock_name': stock_name, 'stock_code': None},
                    {'$set': {'stock_code': stock_code}}
                )
                if result.modified_count > 0:
                    print(f"✓ 已修复 '{stock_name}' 的股票代码: {stock_code} (更新了 {result.modified_count} 条记录)")
                    updated_count += result.modified_count
            
            # 查询仍然股票代码为None的记录
            still_none = list(collection.find({'stock_code': None}))
            print(f"\n仍然股票代码为None的记录: {len(still_none)} 条")
            
            if still_none:
                print("\n仍然缺失的股票名称:")
                remaining_names = set()
                for record in still_none:
                    remaining_names.add(record.get('stock_name'))
                
                for name in sorted(remaining_names):
                    print(f"  - {name}")
        
        # 统计每个股票代码的记录数
        print("\n=== 股票代码统计 ===")
        pipeline = [
            {
                '$match': {'stock_code': {'$ne': None}}
            },
            {
                '$group': {
                    '_id': {'stock_code': '$stock_code', 'stock_name': '$stock_name'},
                    'count': {'$sum': 1}
                }
            },
            {
                '$sort': {'count': -1}
            },
            {
                '$limit': 20
            }
        ]
        
        result = list(collection.aggregate(pipeline))
        print("前20个股票代码统计:")
        for item in result:
            print(f"  {item['_id']['stock_code']} - {item['_id']['stock_name']}: {item['count']}条")
            
        # 检查特定股票
        print("\n=== 检查特定股票 ===")
        check_stocks = ['东方新能', '电投水电', '中稀有色']
        for stock_name in check_stocks:
            count = collection.count_documents({'stock_name': stock_name})
            none_count = collection.count_documents({'stock_name': stock_name, 'stock_code': None})
            valid_count = collection.count_documents({'stock_name': stock_name, 'stock_code': {'$ne': None}})
            print(f"  {stock_name}: 总计 {count}条, None代码 {none_count}条, 有效代码 {valid_count}条")
            
    except Exception as e:
        print(f"修复失败: {e}")

if __name__ == "__main__":
    fix_none_stock_codes()
