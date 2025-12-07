#!/usr/bin/env python3
"""
初始化股票名称代码映射数据并更新历史爬虫数据的整合脚本

该脚本用于：
1. 初始化股票名称和代码映射数据
2. 更新历史爬虫数据中的股票代码
3. 确保新爬取的数据能够正确关联股票代码

使用场景：
- 系统首次部署
- 容器删除或重启
- 需要重新同步股票名称代码映射数据
"""

import os
import sys
import logging
import time
import traceback
import yaml

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.stock_map_service import stock_map_service
from app.services.crawler_service import CrawlerService
from app.core.config import settings

# 配置文件路径
CONFIG_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__), 
    '..', 
    'config', 
    'stock_mapping_config.yaml'
))

# 加载配置
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# 配置日志
logging_level = getattr(logging, config.get('logging', {}).get('level', 'INFO').upper())
logging_format = config.get('logging', {}).get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logging.basicConfig(
    level=logging_level,
    format=logging_format
)

logger = logging.getLogger(__name__)

def init_stock_mapping() -> bool:
    """
    初始化股票名称代码映射数据
    
    Returns:
        bool: 初始化是否成功
    """
    logger.info("🔄 正在初始化股票名称代码映射数据...")
    
    # 从配置文件中读取参数
    csv_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), 
        '..', 
        config.get('stock_mapping', {}).get('csv_path', 'newstock/data/namecode.csv')
    ))
    
    # 检查文件是否存在
    if not os.path.exists(csv_path):
        logger.error(f"❌ namecode.csv文件不存在: {csv_path}")
        return False
    
    # 清空现有映射
    logger.info("🧹 清空现有股票名称和代码映射...")
    if stock_map_service.clear_mappings():
        logger.info("✅ 成功清空现有映射")
    else:
        logger.error("❌ 清空现有映射失败")
        return False
    
    # 加载数据到MongoDB
    loaded_count = stock_map_service.load_from_csv(csv_path)
    
    if loaded_count > 0:
        logger.info(f"✅ 成功加载 {loaded_count} 条股票名称和代码映射")
        logger.info(f"📊 当前映射总数: {stock_map_service.get_total_count()}")
        return True
    else:
        logger.warning("⚠️ 未加载到新的股票名称和代码映射")
        return True  # 即使没有加载到新数据，也认为初始化成功

def update_historical_crawler_data() -> bool:
    """
    更新历史爬虫数据中的股票代码
    
    Returns:
        bool: 更新是否成功
    """
    logger.info("📊 正在更新历史爬虫数据中的股票代码...")
    
    try:
        crawler_service = CrawlerService()
        update_result = crawler_service.update_historical_stock_codes()
        logger.info(f"✅ 历史爬虫数据股票代码更新完成: {update_result}")
        return True
    except Exception as e:
        logger.error(f"❌ 更新历史爬虫数据失败: {e}")
        traceback.print_exc()
        return False

def wait_for_database() -> bool:
    """
    等待数据库连接可用
    
    Returns:
        bool: 数据库是否可用
    """
    logger.info("⏳ 正在等待数据库连接可用...")
    
    max_retries = 30
    retry_interval = 5
    
    for i in range(max_retries):
        try:
            # 测试MongoDB连接
            from pymongo import MongoClient
            client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
            client.server_info()  # 这将抛出异常如果连接失败
            client.close()
            logger.info("✅ 数据库连接可用")
            return True
        except Exception as e:
            logger.warning(f"⚠️ 数据库连接失败 (尝试 {i+1}/{max_retries}): {e}")
            time.sleep(retry_interval)
    
    logger.error("❌ 数据库连接超时，放弃初始化")
    return False

def main() -> int:
    """
    主函数
    
    Returns:
        int: 退出码，0表示成功，非0表示失败
    """
    logger.info("🚀 开始执行股票名称代码映射数据初始化和历史数据更新")
    
    try:
        # 1. 等待数据库连接可用
        if not wait_for_database():
            return 1
        
        # 从配置文件中读取参数
        reinitialize = config.get('stock_mapping', {}).get('reinitialize', False)
        update_historical_data = config.get('stock_mapping', {}).get('update_historical_data', True)
        
        # 2. 检查是否需要初始化股票名称代码映射数据
        current_mapping_count = stock_map_service.get_total_count()
        logger.info(f"📊 当前股票名称代码映射总数: {current_mapping_count}")
        
        if reinitialize or current_mapping_count == 0:
            if not init_stock_mapping():
                return 1
        else:
            logger.info("✅ 跳过股票名称代码映射初始化：映射表中已有数据，且配置中reinitialize=false")
        
        # 3. 更新历史爬虫数据中的股票代码（如果配置为true）
        if update_historical_data:
            if not update_historical_crawler_data():
                return 1
        else:
            logger.info("✅ 跳过历史爬虫数据更新：配置中update_historical_data=false")
        
        # 4. 关闭连接
        stock_map_service.close()
        
        logger.info("🎉 所有初始化操作执行完成!")
        return 0
    except KeyboardInterrupt:
        logger.info("⚠️ 初始化操作被用户中断")
        return 1
    except Exception as e:
        logger.error(f"❌ 执行过程中出现错误: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
