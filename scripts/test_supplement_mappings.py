#!/usr/bin/env python3
"""
测试补充股票名称代码映射脚本
遍历A股上市公司名称，补充缺失的映射
"""

import os
import sys
import logging
from datetime import datetime

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
    logger.info("开始测试补充股票名称代码映射功能...")
    
    # 获取当前映射总数
    current_count = stock_map_service.get_total_count()
    logger.info(f"当前映射总数: {current_count}")
    
    # 测试获取A股上市公司名称列表
    a_stock_names = stock_map_service.get_a_stock_names()
    logger.info(f"获取到 {len(a_stock_names)} 个A股上市公司名称")
    
    # 测试通过API查询股票代码
    test_name = "贵州茅台"
    code = stock_map_service._get_stock_code_from_api(test_name)
    logger.info(f"测试API查询 '{test_name}' 的代码: {code}")
    
    # 测试补充映射
    result = stock_map_service.supplement_stock_mappings()
    logger.info(f"补充映射结果: {result}")
    
    # 获取补充后的映射总数
    new_count = stock_map_service.get_total_count()
    logger.info(f"补充后的映射总数: {new_count}")
    logger.info(f"新增映射数量: {new_count - current_count}")
    
    # 关闭连接
    stock_map_service.close()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
