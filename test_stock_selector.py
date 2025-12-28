#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票筛选服务测试脚本

测试内容：
1. 初始化测试
2. 获取爬虫数据测试
3. 股票筛选逻辑测试
4. 报告生成测试
5. 通知发送模拟测试
"""

import sys
import os
import logging
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.stock_selector_service import StockSelectorService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_initialization():
    """测试服务初始化"""
    logger.info("=== 测试服务初始化 ===")
    try:
        service = StockSelectorService()
        logger.info("✓ 服务初始化成功")
        return True
    except Exception as e:
        logger.error(f"✗ 服务初始化失败: {e}")
        return False

def test_get_latest_crawler_data():
    """测试获取爬虫数据"""
    logger.info("=== 测试获取爬虫数据 ===")
    try:
        service = StockSelectorService()
        data = service.get_latest_crawler_data(hours=24)
        logger.info(f"✓ 获取到 {len(data)} 条爬虫数据")
        if data:
            logger.info(f"  示例数据: {data[0].get('stock_name')} ({data[0].get('stock_code')})")
        return True
    except Exception as e:
        logger.error(f"✗ 获取爬虫数据失败: {e}")
        return False

def test_filter_stocks():
    """测试股票筛选逻辑"""
    logger.info("=== 测试股票筛选逻辑 ===")
    try:
        service = StockSelectorService()
        
        # 创建模拟测试数据
        mock_data = [
            {
                "stock_name": "测试股票1",
                "stock_code": "000001",
                "current_price": "10.00",
                "increase": "3.5%",
                "concepts": "人工智能,芯片",
                "crawled_at": datetime.utcnow()
            },
            {
                "stock_name": "测试股票2",
                "stock_code": "000002",
                "current_price": "20.00",
                "increase": "1.5%",
                "concepts": "房地产",
                "crawled_at": datetime.utcnow()
            },
            {
                "stock_name": "测试股票3",
                "stock_code": "000003",
                "current_price": "30.00",
                "increase": "6.8%",
                "concepts": "新能源,光伏",
                "crawled_at": datetime.utcnow()
            }
        ]
        
        filtered = service.filter_stocks(mock_data)
        logger.info(f"✓ 筛选完成，从 {len(mock_data)} 条数据中筛选出 {len(filtered)} 条结果")
        
        for stock in filtered:
            logger.info(f"  筛选结果: {stock['stock_name']} ({stock['stock_code']}) - 涨幅: {stock['increase']}")
        
        return True
    except Exception as e:
        logger.error(f"✗ 股票筛选失败: {e}")
        return False

def test_generate_report():
    """测试报告生成"""
    logger.info("=== 测试报告生成 ===")
    try:
        service = StockSelectorService()
        
        # 测试数据
        test_data = {
            "stock_name": "测试股票",
            "stock_code": "000001",
            "current_price": "10.00",
            "increase": "3.5%",
            "concepts": "人工智能,芯片"
        }
        
        report = service.generate_report(test_data)
        logger.info("✓ 报告生成成功")
        logger.info("  报告内容:")
        logger.info(report)
        return True
    except Exception as e:
        logger.error(f"✗ 报告生成失败: {e}")
        return False

def test_save_screening_result():
    """测试保存筛选结果"""
    logger.info("=== 测试保存筛选结果 ===")
    try:
        service = StockSelectorService()
        
        # 测试数据
        test_data = {
            "stock_name": "测试股票",
            "stock_code": "000001",
            "current_price": "10.00",
            "increase": "3.5%",
            "concepts": "人工智能,芯片"
        }
        
        report = service.generate_report(test_data)
        success = service.save_screening_result(test_data, report)
        
        if success:
            logger.info("✓ 筛选结果保存成功")
            return True
        else:
            logger.error("✗ 筛选结果保存失败")
            return False
    except Exception as e:
        logger.error(f"✗ 保存筛选结果失败: {e}")
        return False

def test_run_screening():
    """测试完整筛选流程"""
    logger.info("=== 测试完整筛选流程 ===")
    try:
        service = StockSelectorService()
        success = service.run_screening()
        if success:
            logger.info("✓ 完整筛选流程执行成功")
            return True
        else:
            logger.error("✗ 完整筛选流程执行失败")
            return False
    except Exception as e:
        logger.error(f"✗ 完整筛选流程失败: {e}")
        return False

def main():
    """运行所有测试"""
    logger.info("开始运行股票筛选服务测试")
    
    tests = [
        test_initialization,
        test_get_latest_crawler_data,
        test_filter_stocks,
        test_generate_report,
        test_save_screening_result,
        test_run_screening
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
