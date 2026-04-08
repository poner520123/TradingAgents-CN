#!/usr/bin/env python3
"""
修复缺失的股票代码
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
    '中工国际': '002051',
    '中国电建': '601669',
    '中国中铁': '601390',
    '中国建筑': '601668',
    '中国铁建': '601186',
    '中国交建': '601800',
    '中国中冶': '601618',
    '中国建筑': '601668',
    '中国电建': '601669',
    '中国中铁': '601390',
    '中国铁建': '601186',
    '中国交建': '601800',
    '中国中冶': '601618',
}

def fix_missing_stock_codes():
    """修复缺失的股票代码"""
    print("=== 修复缺失的股票代码 ===")
    
    try:
        # 连接MongoDB
        client = MongoClient(MONGODB_CONNECTION_STRING)
        db = client[MONGODB_DATABASE_NAME]
        collection = db['crawler_data']
        
        # 查询没有股票代码的记录
        missing_code_records = list(collection.find({'stock_code': {'$exists': False}}))
        print(f"\n找到 {len(missing_code_records)} 条没有股票代码的记录")
        
        if missing_code_records:
            print("\n没有股票代码的股票名称:")
            stock_names = set()
            for record in missing_code_records:
                stock_names.add(record.get('stock_name'))
            
            for name in sorted(stock_names):
                print(f"  - {name}")
            
            # 使用手动映射添加股票代码
            updated_count = 0
            for stock_name, stock_code in STOCK_CODE_MAPPING.items():
                result = collection.update_many(
                    {'stock_name': stock_name, 'stock_code': {'$exists': False}},
                    {'$set': {'stock_code': stock_code}}
                )
                if result.modified_count > 0:
                    print(f"✓ 已为 '{stock_name}' 添加股票代码: {stock_code} (更新了 {result.modified_count} 条记录)")
                    updated_count += result.modified_count
            
            # 查询仍然没有股票代码的记录
            still_missing = list(collection.find({'stock_code': {'$exists': False}}))
            print(f"\n仍然没有股票代码的记录: {len(still_missing)} 条")
            
            if still_missing:
                print("\n仍然缺失的股票名称:")
                remaining_names = set()
                for record in still_missing:
                    remaining_names.add(record.get('stock_name'))
                
                for name in sorted(remaining_names):
                    print(f"  - {name}")
        
        # 统计每个股票代码的记录数
        print("\n=== 股票代码统计 ===")
        pipeline = [
            {
                '$match': {'stock_code': {'$exists': True}}
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
            code_count = collection.count_documents({'stock_name': stock_name, 'stock_code': {'$exists': True}})
            print(f"  {stock_name}: 总计 {count}条, 有代码 {code_count}条")
            
    except Exception as e:
        print(f"修复失败: {e}")

if __name__ == "__main__":
    fix_missing_stock_codes()
