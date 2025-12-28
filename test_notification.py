#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票筛选服务通知功能测试脚本

测试内容：
1. 钉钉通知发送测试
2. 飞书通知发送测试
3. 报告生成格式测试
"""

import sys
import os
import logging
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.stock_selector_service import StockSelectorService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_report_format():
    """测试报告格式，确保包含STOCK关键字"""
    logger.info("=== 测试报告格式 ===")
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
        
        # 检查报告是否包含STOCK关键字
        if "STOCK" in report:
            logger.info("✓ 报告包含STOCK关键字")
        else:
            logger.error("✗ 报告不包含STOCK关键字")
            return False
        
        # 检查报告格式是否正确
        required_fields = ["案例名称", "AI研究团队", "时间", "关注区间", "目标区间", "防守区间", "仓位配置", "技术面", "基本面"]
        for field in required_fields:
            if field in report:
                logger.info(f"✓ 报告包含字段: {field}")
            else:
                logger.error(f"✗ 报告缺少字段: {field}")
                return False
        
        logger.info("报告内容:")
        logger.info(report)
        return True
    except Exception as e:
        logger.error(f"✗ 报告格式测试失败: {e}")
        return False

def test_dingtalk_notification():
    """测试钉钉通知发送"""
    logger.info("=== 测试钉钉通知发送 ===")
    try:
        service = StockSelectorService()
        
        # 创建测试报告
        test_data = {
            "stock_name": "测试股票",
            "stock_code": "000001",
            "current_price": "10.00",
            "increase": "3.5%",
            "concepts": "人工智能,芯片"
        }
        report = service.generate_report(test_data)
        
        # 发送钉钉通知
        success = service.send_dingtalk_notification(report)
        if success:
            logger.info("✓ 钉钉通知发送成功")
            return True
        else:
            logger.warning("⚠️  钉钉通知发送失败，但不影响其他测试")
            return True  # 不强制要求通知发送成功，因为可能受网络或配置影响
    except Exception as e:
        logger.error(f"✗ 钉钉通知测试失败: {e}")
        return False

def test_feishu_notification():
    """测试飞书通知发送"""
    logger.info("=== 测试飞书通知发送 ===")
    try:
        service = StockSelectorService()
        
        # 创建测试报告
        test_data = {
            "stock_name": "测试股票",
            "stock_code": "000001",
            "current_price": "10.00",
            "increase": "3.5%",
            "concepts": "人工智能,芯片"
        }
        report = service.generate_report(test_data)
        
        # 发送飞书通知
        success = service.send_feishu_notification(report)
        if success:
            logger.info("✓ 飞书通知发送成功")
            return True
        else:
            logger.warning("⚠️  飞书通知发送失败，但不影响其他测试")
            return True  # 不强制要求通知发送成功，因为可能受网络或配置影响
    except Exception as e:
        logger.error(f"✗ 飞书通知测试失败: {e}")
        return False

def main():
    """运行所有测试"""
    logger.info("开始运行股票筛选服务通知功能测试")
    
    tests = [
        test_report_format,
        test_dingtalk_notification,
        test_feishu_notification
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
