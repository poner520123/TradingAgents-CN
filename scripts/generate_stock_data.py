import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random
from datetime import datetime
from app.core.database import get_mongo_db_sync

# 真实A股股票数据
STOCK_DATA = [
    {"code": "600036", "name": "招商银行"},
    {"code": "601318", "name": "中国平安"},
    {"code": "600519", "name": "贵州茅台"},
    {"code": "000858", "name": "五粮液"},
    {"code": "601398", "name": "工商银行"},
    {"code": "600276", "name": "恒瑞医药"},
    {"code": "601888", "name": "中国中免"},
    {"code": "601668", "name": "中国建筑"},
    {"code": "600031", "name": "三一重工"},
    {"code": "601899", "name": "紫金矿业"},
    {"code": "601988", "name": "中国银行"},
    {"code": "601288", "name": "农业银行"},
    {"code": "600000", "name": "浦发银行"},
    {"code": "600104", "name": "上汽集团"},
    {"code": "600038", "name": "中直股份"},
    {"code": "600887", "name": "伊利股份"},
    {"code": "601166", "name": "兴业银行"},
    {"code": "600033", "name": "福建高速"},
    {"code": "600037", "name": "歌华有线"},
    {"code": "600039", "name": "四川路桥"},
    {"code": "000001", "name": "平安银行"},
    {"code": "000002", "name": "万科A"},
    {"code": "000006", "name": "深振业A"},
    {"code": "000009", "name": "中国宝安"},
    {"code": "000012", "name": "南玻A"},
    {"code": "000021", "name": "深科技"},
    {"code": "000027", "name": "深圳能源"},
    {"code": "000031", "name": "中粮地产"},
    {"code": "000039", "name": "中集集团"},
    {"code": "000060", "name": "中金岭南"},
    {"code": "000063", "name": "中兴通讯"},
    {"code": "000069", "name": "华侨城A"},
    {"code": "000088", "name": "盐田港"},
    {"code": "000089", "name": "深圳机场"},
    {"code": "000099", "name": "中信海直"},
    {"code": "000100", "name": "TCL科技"},
    {"code": "000157", "name": "中联重科"},
    {"code": "000159", "name": "国际实业"},
    {"code": "000166", "name": "申万宏源"},
    {"code": "000301", "name": "东方盛虹"},
    {"code": "000333", "name": "美的集团"},
    {"code": "000402", "name": "金融街"},
    {"code": "000407", "name": "胜利股份"},
    {"code": "000413", "name": "东旭光电"},
    {"code": "000415", "name": "渤海租赁"},
    {"code": "000416", "name": "民生控股"},
    {"code": "000422", "name": "湖北宜化"},
    {"code": "000423", "name": "东阿阿胶"},
    {"code": "000425", "name": "徐工机械"},
    {"code": "000426", "name": "兴业矿业"},
]

def generate_fund_ranking_data():
    """生成资金排行数据"""
    db = get_mongo_db_sync()
    collection = db.fund_ranking
    
    # 清空现有数据
    collection.delete_many({})
    
    data_list = []
    for stock in STOCK_DATA[:30]:
        # 生成随机数据
        price = round(random.uniform(10, 200), 2)
        change_percent = round(random.uniform(-5, 5), 2)
        fund_flow = random.randint(1000000, 100000000)
        main_flow = int(fund_flow * random.uniform(0.6, 0.9))
        
        data_list.append({
            'stock_code': stock['code'],
            'stock_name': stock['name'],
            'price': str(price),
            'change_percent': f"{change_percent}%",
            'fund_flow': fund_flow,
            'main_flow': main_flow,
            'retail_flow': fund_flow - main_flow,
            'source': 'eastmoney',
            'crawled_at': datetime.utcnow()
        })
    
    # 批量插入数据
    if data_list:
        result = collection.insert_many(data_list)
        print(f"资金榜数据生成成功: {len(result.inserted_ids)} 条记录")
    else:
        print("资金榜数据生成失败")

def generate_popularity_ranking_data():
    """生成人气排行数据"""
    db = get_mongo_db_sync()
    collection = db.popularity_ranking
    
    # 清空现有数据
    collection.delete_many({})
    
    data_list = []
    for stock in STOCK_DATA[:50]:
        # 生成随机数据
        price = round(random.uniform(10, 200), 2)
        change_percent = round(random.uniform(-5, 5), 2)
        popularity_score = random.randint(100, 1000)
        
        data_list.append({
            'stock_code': stock['code'],
            'stock_name': stock['name'],
            'price': str(price),
            'change_percent': f"{change_percent}%",
            'popularity_score': popularity_score,
            'source': 'eastmoney',
            'crawled_at': datetime.utcnow()
        })
    
    # 批量插入数据
    if data_list:
        result = collection.insert_many(data_list)
        print(f"人气榜数据生成成功: {len(result.inserted_ids)} 条记录")
    else:
        print("人气榜数据生成失败")

if __name__ == "__main__":
    generate_fund_ranking_data()
    generate_popularity_ranking_data()
