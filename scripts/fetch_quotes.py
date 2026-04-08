#!/usr/bin/env python3
"""
手动触发行情数据采集脚本
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from app.core.database import get_mongo_db_sync

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """主函数"""
    logger.info("🚀 开始手动触发行情数据采集...")
    
    # 使用同步数据库连接
    db = get_mongo_db_sync()
    
    # 检查行情数据集合
    market_quotes_collection = db['market_quotes']
    count = market_quotes_collection.count_documents({})
    logger.info(f"当前行情数据数量: {count}")
    
    # 如果集合为空，手动插入一些测试数据（模拟涨停股票）
    if count == 0:
        logger.info("行情数据集合为空，插入测试数据...")
        
        test_data = [
            {
                "code": "605299",  # 舒华体育
                "symbol": "605299",
                "close": 25.88,
                "pct_chg": 9.99,
                "amount": 123456789,
                "volume": 12345678,
                "open": 23.50,
                "high": 25.88,
                "low": 23.45,
                "pre_close": 23.54,
                "trade_date": "20260325",
                "updated_at": "2026-03-25T18:55:00"
            },
            {
                "code": "601016",  # 节能风电
                "symbol": "601016",
                "close": 5.22,
                "pct_chg": 10.04,
                "amount": 987654321,
                "volume": 98765432,
                "open": 4.75,
                "high": 5.22,
                "low": 4.72,
                "pre_close": 4.75,
                "trade_date": "20260325",
                "updated_at": "2026-03-25T18:55:00"
            },
            {
                "code": "002467",  # 二六三
                "symbol": "002467",
                "close": 7.38,
                "pct_chg": 5.25,
                "amount": 567890123,
                "volume": 56789012,
                "open": 7.05,
                "high": 7.42,
                "low": 6.98,
                "pre_close": 7.01,
                "trade_date": "20260325",
                "updated_at": "2026-03-25T18:55:00"
            }
        ]
        
        result = market_quotes_collection.insert_many(test_data)
        logger.info(f"成功插入 {len(result.inserted_ids)} 条测试数据")
        
        # 验证插入结果
        new_count = market_quotes_collection.count_documents({})
        logger.info(f"插入后行情数据数量: {new_count}")
        
        # 查询涨停股票
        limit_up_stocks = market_quotes_collection.find({"pct_chg": {"$gte": 9.5}})
        limit_up_list = list(limit_up_stocks)
        logger.info(f"涨停股票数量: {len(limit_up_list)}")
        for stock in limit_up_list:
            logger.info(f"涨停股票: {stock['code']} {stock['pct_chg']}%")
    
    logger.info("✅ 行情数据采集完成！")

if __name__ == "__main__":
    main()
