#!/usr/bin/env python3
"""
重新同步股票名称代码映射数据并更新历史爬虫数据
"""

import logging
from app.services.stock_map_service import stock_map_service
from app.services.crawler_service import CrawlerService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    logger.info("🚀 开始执行股票名称代码映射重新同步和历史数据更新")
    
    try:
        # 1. 重新同步股票名称代码映射数据
        logger.info("🔄 正在重新同步股票名称代码映射数据...")
        resync_result = stock_map_service.resync_mappings()
        logger.info(f"✅ 股票名称代码映射重新同步完成: {resync_result}")
        
        # 2. 更新历史爬虫数据中的股票代码
        logger.info("📊 正在更新历史爬虫数据中的股票代码...")
        crawler_service = CrawlerService()
        update_result = crawler_service.update_historical_stock_codes()
        logger.info(f"✅ 历史爬虫数据股票代码更新完成: {update_result}")
        
        logger.info("🎉 所有操作执行完成!")
        logger.info(f"📋 总结:")
        logger.info(f"   - 从CSV加载映射: {resync_result.get('loaded_from_csv', 0)} 条")
        logger.info(f"   - 补充映射: {resync_result.get('supplemented', 0)} 条")
        logger.info(f"   - 更新历史数据: {update_result.get('updated', 0)} 条")
        
    except Exception as e:
        logger.error(f"❌ 执行过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
