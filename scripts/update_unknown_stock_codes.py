#!/usr/bin/env python3
"""
更新MongoDB中未知的股票代码
找出所有stock_code为null或不存在的爬虫数据，通过API获取对应股票代码并更新
"""

import sys
import os
import logging
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

from app.services.crawler_service import CrawlerService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """主函数"""
    logger.info("开始更新MongoDB中未知的股票代码")
    
    try:
        # 创建CrawlerService实例
        crawler_service = CrawlerService()
        
        # 更新历史数据中的股票代码
        result = crawler_service.update_historical_stock_codes()
        
        logger.info(f"更新完成，共处理 {result['total']} 条数据，成功更新 {result['updated']} 条")
        
        return 0
    except Exception as e:
        logger.error(f"更新失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())