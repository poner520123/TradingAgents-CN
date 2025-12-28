#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试交叉分析接口的查询逻辑
"""

import sys
import os
import logging
import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.scrapy_crawler_service import ScrapyCrawlerService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_cross_analysis_query():
    """测试交叉分析查询逻辑"""
    logger.info("开始测试交叉分析查询逻辑...")
    
    try:
        # 创建爬虫服务实例
        crawler_service = ScrapyCrawlerService()
        
        # 1. 测试交叉分析数据查询
        logger.info("1. 测试交叉分析数据查询...")
        data, total = crawler_service.get_cross_analysis_data(page=1, page_size=20)
        logger.info(f"查询到 {total} 条交叉分析数据，返回 {len(data)} 条")
        
        # 2. 验证数据结构和时效性
        logger.info("\n2. 验证数据结构和时效性...")
        if data:
            # 检查数据结构
            first_item = data[0]
            required_fields = ['expert_name', 'name', 'code', 'analysis_time', 'crawled_at']
            for field in required_fields:
                if field in first_item:
                    logger.info(f"✓ 包含字段: {field}")
                else:
                    logger.error(f"✗ 缺少字段: {field}")
            
            # 检查时效性
            if 'crawled_at' in first_item:
                crawled_at = first_item['crawled_at']
                if isinstance(crawled_at, datetime.datetime):
                    # 计算数据距今的时间
                    time_diff = datetime.datetime.utcnow() - crawled_at
                    logger.info(f"数据爬取时间: {crawled_at}")
                    logger.info(f"数据距今: {time_diff.days} 天 {time_diff.seconds // 3600} 小时")
                    
                    if time_diff.days < 7:
                        logger.info("✓ 数据是最近7天内的")
                    else:
                        logger.warning(f"⚠ 数据距今超过7天: {time_diff.days} 天")
            
            # 检查排序
            logger.info("\n3. 验证数据排序...")
            if len(data) > 1:
                # 检查是否按crawled_at降序排序
                sorted_by_crawled = all(data[i]['crawled_at'] >= data[i+1]['crawled_at'] for i in range(len(data)-1))
                logger.info(f"✓ 按crawled_at降序排序: {sorted_by_crawled}")
                
                # 检查是否按analysis_time降序排序
                sorted_by_analysis = all(data[i]['analysis_time'] >= data[i+1]['analysis_time'] for i in range(len(data)-1))
                logger.info(f"✓ 按analysis_time降序排序: {sorted_by_analysis}")
        else:
            logger.warning("没有查询到交叉分析数据，可能是数据库中没有数据")
        
        # 3. 测试其他数据查询方法
        logger.info("\n4. 测试其他数据查询方法...")
        
        # 测试人气排行数据
        popularity_data, popularity_total = crawler_service.get_popularity_data(page=1, page_size=5)
        logger.info(f"人气排行数据: {popularity_total} 条，返回 {len(popularity_data)} 条")
        if popularity_data:
            logger.info(f"  第一条人气数据: {popularity_data[0]['name']} (排名: {popularity_data[0]['rank']})")
        
        # 测试资金流向数据
        capital_flow_data, capital_flow_total = crawler_service.get_capital_flow_data(page=1, page_size=5)
        logger.info(f"资金流向数据: {capital_flow_total} 条，返回 {len(capital_flow_data)} 条")
        if capital_flow_data:
            logger.info(f"  第一条资金流向数据: {capital_flow_data[0]['name']} (主买额: {capital_flow_data[0]['main_flow']})")
        
        # 测试专家排名数据
        expert_ranking_data, expert_ranking_total = crawler_service.get_expert_ranking_data(page=1, page_size=5)
        logger.info(f"专家排名数据: {expert_ranking_total} 条，返回 {len(expert_ranking_data)} 条")
        if expert_ranking_data:
            logger.info(f"  第一条专家数据: {expert_ranking_data[0]['expert_name']} - {expert_ranking_data[0]['name']}")
        
        logger.info("\n测试完成！")
        return True
        
    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    test_cross_analysis_query()
