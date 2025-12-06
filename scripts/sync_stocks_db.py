#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同步newstock/data/stocks.db中的股票数据到MongoDB中
"""

import sqlite3
from pymongo import MongoClient
from datetime import datetime
import logging
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# SQLite数据库配置
SQLITE_DB_PATH = os.path.join(os.path.dirname(__file__), '../newstock/data/stocks.db')

# MongoDB配置
MONGO_URI = 'mongodb://admin:admin123@localhost:27017'
MONGO_DB_NAME = 'tradingagents'
MONGO_COLLECTION_NAME = 'crawler_data'
MONGO_AUTH_SOURCE = 'admin'


def sync_stocks_to_mongodb():
    """将SQLite数据库中的股票数据同步到MongoDB"""
    logger.info("开始同步股票数据...")
    
    # 连接到SQLite数据库
    try:
        sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
        sqlite_conn.row_factory = sqlite3.Row
        sqlite_cursor = sqlite_conn.cursor()
        logger.info(f"成功连接到SQLite数据库: {SQLITE_DB_PATH}")
    except Exception as e:
        logger.error(f"连接SQLite数据库失败: {e}")
        return
    
    # 连接到MongoDB
    try:
        mongo_client = MongoClient(
            MONGO_URI,
            authSource=MONGO_AUTH_SOURCE
        )
        mongo_db = mongo_client[MONGO_DB_NAME]
        mongo_collection = mongo_db[MONGO_COLLECTION_NAME]
        logger.info(f"成功连接到MongoDB: {MONGO_URI}/{MONGO_DB_NAME}/{MONGO_COLLECTION_NAME}")
    except Exception as e:
        logger.error(f"连接MongoDB失败: {e}")
        sqlite_conn.close()
        return
    
    try:
        # 查询SQLite数据
        sqlite_cursor.execute("SELECT * FROM stock_predictions")
        rows = sqlite_cursor.fetchall()
        logger.info(f"从SQLite中获取到 {len(rows)} 条记录")
        
        # 同步到MongoDB
        synced_count = 0
        skipped_count = 0
        
        for row in rows:
            # 构建文档
            doc = {
                "user_name": row["user_name"],
                "success_count": row["success_count"],
                "success_rate": row["success_rate"],
                "stock_name": row["stock_name"],
                "reason": row["reason"],
                "time": row["time"],
                "price": row["price"],
                "current_price": row["current_price"],
                "increase": row["increase"],
                "limit_up": row["limit_up"],
                "limit_up_date": row["limit_up_date"],
                "concepts": row["concepts"],
                "crawled_at": row["crawled_at"] if row["crawled_at"] else datetime.utcnow()
            }
            
            # 使用upsert避免重复
            result = mongo_collection.update_one(
                {"user_name": doc["user_name"], "stock_name": doc["stock_name"], "time": doc["time"]},
                {"$set": doc},
                upsert=True
            )
            
            if result.upserted_id or result.modified_count > 0:
                synced_count += 1
            else:
                skipped_count += 1
        
        logger.info(f"同步完成: {synced_count} 条记录已同步，{skipped_count} 条记录已存在")
        
    except Exception as e:
        logger.error(f"同步数据失败: {e}")
    finally:
        # 关闭连接
        sqlite_conn.close()
        mongo_client.close()
        logger.info("数据库连接已关闭")


if __name__ == "__main__":
    sync_stocks_to_mongodb()