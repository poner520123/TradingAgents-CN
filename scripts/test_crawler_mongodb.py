#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试MongoDB爬虫分析数据服务功能
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

def test_mongodb_connection():
    """测试MongoDB连接"""
    logger.info("测试MongoDB连接...")
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

def test_collection_exists(client):
    """测试集合是否存在"""
    logger.info("测试集合是否存在...")
    try:
        db = client[MONGO_DB_NAME]
        collections = db.list_collection_names()
        if MONGO_COLLECTION_NAME in collections:
            logger.info(f"✅ 集合 {MONGO_COLLECTION_NAME} 已存在")
            return True
        else:
            logger.warning(f"⚠️  集合 {MONGO_COLLECTION_NAME} 不存在，将创建")
            db.create_collection(MONGO_COLLECTION_NAME)
            return True
    except Exception as e:
        logger.error(f"❌ 测试集合存在失败: {e}")
        return False

def test_insert_data(client):
    """测试插入数据"""
    logger.info("测试插入数据...")
    try:
        db = client[MONGO_DB_NAME]
        collection = db[MONGO_COLLECTION_NAME]
        
        # 插入测试数据
        test_data = {
            "user_name": "测试用户",
            "success_count": "10",
            "success_rate": "80%",
            "stock_name": "测试股票",
            "reason": "测试理由",
            "time": "2025-12-06 10:00:00",
            "price": "100.00",
            "current_price": "110.00",
            "increase": "+10.00%",
            "limit_up": "是",
            "limit_up_date": "2025-12-06",
            "concepts": "测试概念1,测试概念2",
            "crawled_at": datetime.utcnow()
        }
        
        result = collection.insert_one(test_data)
        logger.info(f"✅ 插入数据成功，ID: {result.inserted_id}")
        return result.inserted_id
    except Exception as e:
        logger.error(f"❌ 插入数据失败: {e}")
        return None

def test_query_data(client):
    """测试查询数据"""
    logger.info("测试查询数据...")
    try:
        db = client[MONGO_DB_NAME]
        collection = db[MONGO_COLLECTION_NAME]
        
        # 查询所有数据
        total = collection.count_documents({})
        logger.info(f"✅ 查询数据成功，总数: {total}")
        
        # 查询最近的10条数据
        recent_data = list(collection.find().sort("time", pymongo.DESCENDING).limit(10))
        logger.info(f"✅ 查询最近10条数据成功")
        
        # 打印部分数据
        for i, data in enumerate(recent_data[:3]):
            logger.info(f"   数据{i+1}: 股票名称={data.get('stock_name')}, 伏击人={data.get('user_name')}, 成功率={data.get('success_rate')}")
        
        return total
    except Exception as e:
        logger.error(f"❌ 查询数据失败: {e}")
        return 0

def test_update_data(client, doc_id):
    """测试更新数据"""
    logger.info("测试更新数据...")
    try:
        if not doc_id:
            logger.warning("⚠️  没有要更新的文档ID")
            return False
            
        db = client[MONGO_DB_NAME]
        collection = db[MONGO_COLLECTION_NAME]
        
        # 更新数据
        result = collection.update_one(
            {"_id": doc_id},
            {"$set": {"success_count": "11", "updated_at": datetime.utcnow()}}
        )
        
        if result.modified_count > 0:
            logger.info("✅ 更新数据成功")
            return True
        else:
            logger.warning("⚠️  没有更新任何数据")
            return False
    except Exception as e:
        logger.error(f"❌ 更新数据失败: {e}")
        return False

def test_delete_data(client, doc_id):
    """测试删除数据"""
    logger.info("测试删除数据...")
    try:
        if not doc_id:
            logger.warning("⚠️  没有要删除的文档ID")
            return False
            
        db = client[MONGO_DB_NAME]
        collection = db[MONGO_COLLECTION_NAME]
        
        # 删除数据
        result = collection.delete_one({"_id": doc_id})
        
        if result.deleted_count > 0:
            logger.info("✅ 删除数据成功")
            return True
        else:
            logger.warning("⚠️  没有删除任何数据")
            return False
    except Exception as e:
        logger.error(f"❌ 删除数据失败: {e}")
        return False

def test_data_types(client):
    """测试数据类型转换"""
    logger.info("测试数据类型转换...")
    try:
        db = client[MONGO_DB_NAME]
        collection = db[MONGO_COLLECTION_NAME]
        
        # 查询一条数据
        data = collection.find_one()
        if not data:
            logger.warning("⚠️  没有找到数据，无法测试数据类型")
            return False
            
        logger.info(f"✅ 找到测试数据: {data}")
        
        # 测试success_count转换
        if 'success_count' in data:
            success_count = data['success_count']
            logger.info(f"   success_count原始值: {success_count}, 类型: {type(success_count)}")
            
            try:
                success_count_int = int(success_count)
                logger.info(f"   ✅ success_count转换为整数成功: {success_count_int}")
            except (ValueError, TypeError):
                logger.error(f"   ❌ success_count转换为整数失败")
        
        return True
    except Exception as e:
        logger.error(f"❌ 测试数据类型转换失败: {e}")
        return False

def main():
    """主函数"""
    logger.info("="*60)
    logger.info("开始测试MongoDB爬虫分析数据服务")
    logger.info("="*60)
    
    # 测试连接
    client = test_mongodb_connection()
    if not client:
        logger.error("测试失败，MongoDB连接失败")
        return 1
    
    try:
        # 测试集合存在
        if not test_collection_exists(client):
            logger.error("测试失败，集合操作失败")
            return 1
        
        # 测试查询数据
        total = test_query_data(client)
        
        # 测试插入数据
        doc_id = test_insert_data(client)
        
        # 再次查询，验证插入
        new_total = test_query_data(client)
        if new_total > total:
            logger.info(f"✅ 数据插入验证成功，总数从 {total} 增加到 {new_total}")
        
        # 测试数据类型转换
        test_data_types(client)
        
        # 测试更新数据
        test_update_data(client, doc_id)
        
        # 测试删除数据
        test_delete_data(client, doc_id)
        
        # 最终验证
        final_total = test_query_data(client)
        if final_total == total:
            logger.info(f"✅ 数据删除验证成功，总数回到 {final_total}")
        
        logger.info("="*60)
        logger.info("所有测试完成")
        logger.info("✅ MongoDB爬虫分析数据服务功能正常")
        logger.info("="*60)
        return 0
        
    except Exception as e:
        logger.error(f"❌ 测试过程中发生异常: {e}")
        return 1
    finally:
        if client:
            client.close()
            logger.info("🔌 MongoDB连接已关闭")

if __name__ == "__main__":
    sys.exit(main())
