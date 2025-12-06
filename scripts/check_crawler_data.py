#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查MongoDB中爬虫数据的结构，特别是是否有stock_code字段
"""

import pymongo
from datetime import datetime
import logging
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# MongoDB配置
MONGO_URI = 'mongodb://admin:admin123@localhost:27017'
MONGO_DB_NAME = 'tradingagents'
MONGO_COLLECTION_NAME = 'crawler_data'
MONGO_AUTH_SOURCE = 'admin'

def check_mongodb_connection():
    """检查MongoDB连接"""
    logger.info("检查MongoDB连接...")
    try:
        client = pymongo.MongoClient(
            MONGO_URI,
            authSource=MONGO_AUTH_SOURCE
        )
        # 测试连接
        client.admin.command('ping')
        logger.info("✅ MongoDB连接成功")
        return client
    except Exception as e:
        logger.error(f"❌ MongoDB连接失败: {e}")
        return None

def check_collection_structure(client):
    """检查集合结构"""
    logger.info("检查集合结构...")
    try:
        db = client[MONGO_DB_NAME]
        collection = db[MONGO_COLLECTION_NAME]
        
        # 获取一条数据，查看字段结构
        sample = collection.find_one()
        if sample:
            logger.info(f"✅ 找到样本数据，字段: {list(sample.keys())}")
            logger.info(f"样本数据: {sample}")
            
            # 检查是否有stock_code字段
            if 'stock_code' in sample:
                logger.info("✅ 数据中包含stock_code字段")
                # 检查stock_code字段的类型和值
                logger.info(f"stock_code值: {sample['stock_code']}, 类型: {type(sample['stock_code'])}")
            else:
                logger.warning("⚠️  数据中不包含stock_code字段")
                
            # 检查是否有stock_name字段
            if 'stock_name' in sample:
                logger.info(f"✅ 数据中包含stock_name字段，值: {sample['stock_name']}")
            else:
                logger.warning("⚠️  数据中不包含stock_name字段")
        else:
            logger.warning("⚠️  集合中没有数据")
            
        return sample
    except Exception as e:
        logger.error(f"❌ 检查集合结构失败: {e}")
        return None

def check_data_count(client):
    """检查数据数量"""
    logger.info("检查数据数量...")
    try:
        db = client[MONGO_DB_NAME]
        collection = db[MONGO_COLLECTION_NAME]
        count = collection.count_documents({})
        logger.info(f"✅ 集合中共有 {count} 条数据")
        return count
    except Exception as e:
        logger.error(f"❌ 检查数据数量失败: {e}")
        return 0

def main():
    """主函数"""
    logger.info("="*60)
    logger.info("开始检查MongoDB爬虫数据结构")
    logger.info("="*60)
    
    # 检查连接
    client = check_mongodb_connection()
    if not client:
        logger.error("检查失败，MongoDB连接失败")
        return 1
    
    try:
        # 检查集合结构
        check_collection_structure(client)
        
        # 检查数据数量
        check_data_count(client)
        
        logger.info("="*60)
        logger.info("检查完成")
        logger.info("="*60)
        return 0
    except Exception as e:
        logger.error(f"检查过程中发生异常: {e}")
        return 1
    finally:
        if client:
            client.close()
            logger.info("🔌 MongoDB连接已关闭")

if __name__ == "__main__":
    sys.exit(main())
