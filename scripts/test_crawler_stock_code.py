#!/usr/bin/env python3
"""
测试爬虫数据是否正确关联股票代码
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + '/..')

from pymongo import MongoClient
from app.core.config import settings

# 配置日志
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    logger.info("🚀 开始测试爬虫数据是否正确关联股票代码")
    
    try:
        # 连接MongoDB
        client = MongoClient(settings.MONGO_URI)
        db = client[settings.MONGO_DB]
        crawler_collection = db.crawler_data
        stock_map_collection = db.stock_name_code_mapping
        
        logger.info(f"✅ 成功连接到MongoDB数据库: {settings.MONGO_DB}")
        
        # 1. 检查爬虫数据集合
        logger.info("🔍 正在检查爬虫数据集合...")
        
        # 统计爬虫数据总数
        total_crawler_data = crawler_collection.count_documents({})
        logger.info(f"📊 爬虫数据总数: {total_crawler_data}")
        
        # 统计包含stock_code字段的数据数
        data_with_stock_code = crawler_collection.count_documents({"stock_code": {"$exists": True, "$ne": None}})
        logger.info(f"📊 包含stock_code字段的数据数: {data_with_stock_code}")
        
        # 统计stock_code为None或空字符串的数据数
        data_without_stock_code = crawler_collection.count_documents({"stock_code": {"$in": [None, ""]}})
        logger.info(f"📊 stock_code为None或空的数据数: {data_without_stock_code}")
        
        # 计算stock_code覆盖率
        coverage_rate = (data_with_stock_code / total_crawler_data) * 100 if total_crawler_data > 0 else 0
        logger.info(f"📈 stock_code覆盖率: {coverage_rate:.2f}%")
        
        # 2. 检查股票名称代码映射集合
        logger.info("🔍 正在检查股票名称代码映射集合...")
        
        # 统计映射数据总数
        total_mappings = stock_map_collection.count_documents({})
        logger.info(f"📊 股票名称代码映射总数: {total_mappings}")
        
        # 3. 获取最新的10条爬虫数据，查看stock_code字段
        logger.info("🔍 正在获取最新的10条爬虫数据，查看stock_code字段...")
        latest_crawler_data = crawler_collection.find().sort("crawled_at", -1).limit(10)
        
        logger.info("📋 最新10条爬虫数据:")
        for i, data in enumerate(latest_crawler_data, 1):
            logger.info(f"   {i}. 股票名称: {data.get('stock_name')}, 股票代码: {data.get('stock_code')}, 爬取时间: {data.get('crawled_at')}")
        
        # 4. 验证新爬取的数据是否能正确关联股票代码
        logger.info("🔍 正在验证新爬取的数据是否能正确关联股票代码...")
        
        # 导入爬虫服务
        from app.services.crawler_service import CrawlerService
        crawler_service = CrawlerService()
        
        # 爬取最新的1页数据
        logger.info("🔄 正在爬取最新的1页数据...")
        crawler_service.crawl_pages(1, 1, force=True)
        
        # 获取最新的10条爬虫数据，查看stock_code字段
        logger.info("🔍 正在获取最新的10条爬虫数据（含刚刚爬取的数据）...")
        latest_crawler_data = crawler_collection.find().sort("crawled_at", -1).limit(10)
        
        logger.info("📋 最新10条爬虫数据（含刚刚爬取的数据）:")
        for i, data in enumerate(latest_crawler_data, 1):
            logger.info(f"   {i}. 股票名称: {data.get('stock_name')}, 股票代码: {data.get('stock_code')}, 爬取时间: {data.get('crawled_at')}")
        
        logger.info("🎉 测试完成!")
        
    except Exception as e:
        logger.error(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
