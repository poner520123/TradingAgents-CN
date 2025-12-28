#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试交叉分析接口修复效果
"""

import sys
import os
import logging
import asyncio

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.scrapy_crawler_service import ScrapyCrawlerService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_cross_analysis():
    """测试交叉分析接口"""
    logger.info("开始测试交叉分析接口...")
    
    try:
        # 创建爬虫服务实例
        crawler_service = ScrapyCrawlerService()
        
        # 1. 测试数据爬取
        logger.info("1. 测试数据爬取...")
        total_saved = crawler_service.run_all_crawlers()
        logger.info(f"爬取完成，共保存 {total_saved} 条数据")
        
        # 2. 测试交叉分析数据查询
        logger.info("\n2. 测试交叉分析数据查询...")
        data, total = crawler_service.get_cross_analysis_data(page=1, page_size=20)
        logger.info(f"查询到 {total} 条交叉分析数据，返回 {len(data)} 条")
        
        # 3. 验证数据时效性
        logger.info("\n3. 验证数据时效性...")
        if data:
            # 检查第一条数据是否有 crawled_at 字段
            first_item = data[0]
            if 'crawled_at' in first_item:
                logger.info(f"第一条数据的爬取时间: {first_item['crawled_at']}")
                logger.info(f"第一条数据的分析时间: {first_item['analysis_time']}")
                logger.info(f"第一条数据的专家名称: {first_item['expert_name']}")
                logger.info(f"第一条数据的股票名称: {first_item['name']}")
                logger.info(f"第一条数据的股票代码: {first_item['code']}")
                logger.info(f"第一条数据的人气排名: {first_item.get('popularity_rank')}")
                logger.info(f"第一条数据的资金流向排名: {first_item.get('capital_flow_rank')}")
            else:
                logger.error("数据中没有 crawled_at 字段")
        else:
            logger.error("没有查询到交叉分析数据")
        
        # 4. 测试其他数据查询方法
        logger.info("\n4. 测试其他数据查询方法...")
        
        # 测试人气排行数据
        popularity_data, popularity_total = crawler_service.get_popularity_data(page=1, page_size=10)
        logger.info(f"人气排行数据: {popularity_total} 条，返回 {len(popularity_data)} 条")
        
        # 测试资金流向数据
        capital_flow_data, capital_flow_total = crawler_service.get_capital_flow_data(page=1, page_size=10)
        logger.info(f"资金流向数据: {capital_flow_total} 条，返回 {len(capital_flow_data)} 条")
        
        # 测试专家排名数据
        expert_ranking_data, expert_ranking_total = crawler_service.get_expert_ranking_data(page=1, page_size=10)
        logger.info(f"专家排名数据: {expert_ranking_total} 条，返回 {len(expert_ranking_data)} 条")
        
        logger.info("\n测试完成！")
        return True
        
    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    asyncio.run(test_cross_analysis())
