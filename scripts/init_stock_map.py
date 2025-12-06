#!/usr/bin/env python3
"""
初始化股票名称和代码映射脚本
从namecode.csv文件加载股票名称和代码映射到MongoDB数据库
"""

import os
import sys
import logging

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.stock_map_service import stock_map_service

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """主函数"""
    logger.info("开始初始化股票名称和代码映射...")
    
    # 定义namecode.csv文件路径
    csv_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), 
        '..', 
        'newstock', 
        'data', 
        'namecode.csv'
    ))
    
    # 检查文件是否存在
    if not os.path.exists(csv_path):
        logger.error(f"namecode.csv文件不存在: {csv_path}")
        return 1
    
    # 清空现有映射
    logger.info("清空现有股票名称和代码映射...")
    if stock_map_service.clear_mappings():
        logger.info("成功清空现有映射")
    else:
        logger.error("清空现有映射失败")
        return 1
    
    # 加载数据到MongoDB
    loaded_count = stock_map_service.load_from_csv(csv_path)
    
    if loaded_count > 0:
        logger.info(f"成功加载 {loaded_count} 条股票名称和代码映射")
        logger.info(f"当前映射总数: {stock_map_service.get_total_count()}")
    else:
        logger.warning("未加载到新的股票名称和代码映射")
    
    # 关闭连接
    stock_map_service.close()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
