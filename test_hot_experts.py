#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试达人热点数据接口

测试内容：
1. 测试达人热点数据获取
2. 验证数据筛选条件
3. 验证排序逻辑
"""

import sys
import os
import logging
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.scrapy_crawler_service import ScrapyCrawlerService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_hot_experts_data():
    """测试达人热点数据获取"""
    logger.info("=== 测试达人热点数据获取 ===")
    try:
        service = ScrapyCrawlerService()
        
        # 测试获取15条数据
        hot_experts = service.get_hot_experts_data(limit=15)
        logger.info(f"✓ 成功获取 {len(hot_experts)} 条达人热点数据")
        
        # 验证数据数量
        if len(hot_experts) <= 15:
            logger.info(f"✓ 数据数量符合要求: {len(hot_experts)} <= 15")
        else:
            logger.error(f"✗ 数据数量超过限制: {len(hot_experts)} > 15")
            return False
        
        # 验证每条数据都有人气排名和资金流向排名，且都大于0
        for i, expert in enumerate(hot_experts, 1):
            popularity_rank = expert.get('popularity_rank')
            capital_flow_rank = expert.get('capital_flow_rank')
            combined_rank = expert.get('combined_rank')
            
            if (popularity_rank is None or popularity_rank <= 0 or 
                capital_flow_rank is None or capital_flow_rank <= 0):
                logger.error(f"✗ 第 {i} 条数据不满足条件: popularity_rank={popularity_rank}, capital_flow_rank={capital_flow_rank}")
                return False
            
            # 验证综合排名计算是否正确
            if combined_rank != popularity_rank + capital_flow_rank:
                logger.error(f"✗ 第 {i} 条数据综合排名计算错误: combined_rank={combined_rank}, expected={popularity_rank + capital_flow_rank}")
                return False
            
            logger.info(f"  第 {i} 条: {expert.get('name')} ({expert.get('code')}) - 人气排名: {popularity_rank}, 资金排名: {capital_flow_rank}, 综合排名: {combined_rank}")
        
        # 验证数据是否按照综合排名从小到大排序
        for i in range(1, len(hot_experts)):
            if hot_experts[i]['combined_rank'] < hot_experts[i-1]['combined_rank']:
                logger.error(f"✗ 数据排序错误: 第 {i} 条综合排名 {hot_experts[i]['combined_rank']} < 第 {i-1} 条 {hot_experts[i-1]['combined_rank']}")
                return False
        logger.info("✓ 数据按照综合排名从小到大排序正确")
        
        return True
    except Exception as e:
        logger.error(f"✗ 测试达人热点数据失败: {e}")
        return False

def test_hot_experts_limit():
    """测试不同限制数量"""
    logger.info("\n=== 测试不同限制数量 ===")
    try:
        service = ScrapyCrawlerService()
        
        # 测试获取5条数据
        hot_experts_5 = service.get_hot_experts_data(limit=5)
        logger.info(f"✓ 成功获取 {len(hot_experts_5)} 条达人热点数据 (limit=5)")
        
        # 测试获取10条数据
        hot_experts_10 = service.get_hot_experts_data(limit=10)
        logger.info(f"✓ 成功获取 {len(hot_experts_10)} 条达人热点数据 (limit=10)")
        
        # 测试获取20条数据
        hot_experts_20 = service.get_hot_experts_data(limit=20)
        logger.info(f"✓ 成功获取 {len(hot_experts_20)} 条达人热点数据 (limit=20)")
        
        return True
    except Exception as e:
        logger.error(f"✗ 测试不同限制数量失败: {e}")
        return False

def main():
    """运行所有测试"""
    logger.info("开始运行达人热点数据测试")
    
    tests = [
        test_hot_experts_data,
        test_hot_experts_limit
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1
    
    logger.info(f"\n测试结果: 共 {len(tests)} 个测试，{passed} 个通过，{failed} 个失败")
    
    if failed == 0:
        logger.info("🎉 所有测试通过！")
        return 0
    else:
        logger.error("❌ 部分测试失败！")
        return 1

if __name__ == "__main__":
    sys.exit(main())
