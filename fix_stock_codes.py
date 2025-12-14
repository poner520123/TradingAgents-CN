#!/usr/bin/env python3
"""
修复股票代码映射问题的脚本

功能：
1. 检查数据库中股票代码映射情况
2. 从数据源获取完整的股票列表
3. 补充缺失的股票代码映射
4. 确保所有股票都有对应的code
"""

import os
import sys
import logging
from datetime import datetime
from pymongo import MongoClient

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.services.stock_map_service import stock_map_service

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("fix_stock_codes")

def check_stock_mapping_status():
    """检查股票代码映射状态"""
    logger.info("🔍 检查股票代码映射状态")
    
    # 1. 检查stock_map_service中的映射数量
    total_mappings = stock_map_service.get_total_count()
    logger.info(f"📊 现有映射数量: {total_mappings}")
    
    # 2. 检查数据库中的stock_basic_info集合
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB]
    
    # 3. 检查stock_basic_info中的股票数量
    stock_count = db.stock_basic_info.count_documents({})
    logger.info(f"📈 stock_basic_info中的股票数量: {stock_count}")
    
    # 4. 检查缺少code的股票
    missing_code_count = db.stock_basic_info.count_documents(
        {"$or": [{"code": {"$exists": False}}, {"code": None}, {"code": ""}]}
    )
    logger.info(f"❌ 缺少code的股票数量: {missing_code_count}")
    
    # 5. 检查缺少name的股票
    missing_name_count = db.stock_basic_info.count_documents(
        {"$or": [{"name": {"$exists": False}}, {"name": None}, {"name": ""}]}
    )
    logger.info(f"❌ 缺少name的股票数量: {missing_name_count}")
    
    client.close()
    
    return {
        "total_mappings": total_mappings,
        "stock_count": stock_count,
        "missing_code_count": missing_code_count,
        "missing_name_count": missing_name_count
    }

def fix_missing_codes():
    """修复缺少code的股票"""
    logger.info("🔧 开始修复缺少code的股票")
    
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB]
    
    # 获取缺少code的股票
    missing_code_stocks = db.stock_basic_info.find(
        {"$or": [{"code": {"$exists": False}}, {"code": None}, {"code": ""}]}
    )
    
    fixed_count = 0
    skipped_count = 0
    
    for stock in missing_code_stocks:
        name = stock.get("name")
        if not name:
            logger.warning(f"❌ 跳过缺少name的股票: {stock}")
            skipped_count += 1
            continue
        
        # 尝试从stock_map_service获取code
        code = stock_map_service.get_code_by_name(name)
        if code:
            # 更新数据库
            db.stock_basic_info.update_one(
                {"_id": stock["_id"]},
                {"$set": {"code": code}}
            )
            logger.info(f"✅ 修复股票: {name} -> {code}")
            fixed_count += 1
        else:
            logger.warning(f"❌ 无法获取股票代码: {name}")
            skipped_count += 1
    
    client.close()
    
    logger.info(f"✅ 修复完成: 修复了 {fixed_count} 个股票代码，跳过了 {skipped_count} 个股票")
    return {"fixed_count": fixed_count, "skipped_count": skipped_count}

def sync_stock_mappings_from_basic_info():
    """从stock_basic_info同步股票映射到stock_name_code_mapping集合"""
    logger.info("🔄 从stock_basic_info同步股票映射")
    
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB]
    
    # 获取所有有code和name的股票
    stocks = db.stock_basic_info.find({
        "code": {"$exists": True, "$ne": None, "$ne": ""},
        "name": {"$exists": True, "$ne": None, "$ne": ""}
    })
    
    synced_count = 0
    
    for stock in stocks:
        name = stock["name"]
        code = stock["code"]
        market = stock.get("market", "A股")
        
        # 更新或插入映射
        success = stock_map_service.upsert_map(name, code, market)
        if success:
            synced_count += 1
            if synced_count % 1000 == 0:
                logger.info(f"📊 已同步 {synced_count} 个股票映射")
    
    client.close()
    
    logger.info(f"✅ 同步完成: 共同步了 {synced_count} 个股票映射")
    return {"synced_count": synced_count}

def add_fallback_mapping():
    """添加一些常见的股票映射作为备选"""
    logger.info("📝 添加备选股票映射")
    
    # 添加一些常见的股票映射
    fallback_mappings = {
        "平安银行": "000001",
        "万科A": "000002",
        "比亚迪": "002594",
        "贵州茅台": "600519",
        "五粮液": "000858",
        "招商银行": "600036",
        "宁德时代": "300750",
        "腾讯控股": "00700.HK",
        "阿里巴巴": "BABA",
        "苹果": "AAPL",
        "微软": "MSFT",
        "特斯拉": "TSLA"
    }
    
    added_count = 0
    
    for name, code in fallback_mappings.items():
        # 确定市场类型
        if code.endswith(".HK"):
            market = "港股"
        elif code.isdigit() and len(code) == 6:
            market = "A股"
        else:
            market = "美股"
        
        success = stock_map_service.upsert_map(name, code, market)
        if success:
            added_count += 1
    
    logger.info(f"✅ 备选映射添加完成: 共添加了 {added_count} 个股票映射")
    return {"added_count": added_count}

def main():
    """主函数"""
    logger.info("🚀 开始修复股票代码映射问题")
    
    # 1. 检查当前状态
    status = check_stock_mapping_status()
    
    if status["missing_code_count"] == 0 and status["missing_name_count"] == 0:
        logger.info("🎉 所有股票都有完整的code和name，无需修复")
        return
    
    # 2. 从stock_basic_info同步映射
    sync_result = sync_stock_mappings_from_basic_info()
    
    # 3. 修复缺少code的股票
    fix_result = fix_missing_codes()
    
    # 4. 添加备选映射
    fallback_result = add_fallback_mapping()
    
    # 5. 再次检查状态
    final_status = check_stock_mapping_status()
    
    logger.info("📋 修复结果总结")
    logger.info(f"   初始缺少code的股票: {status['missing_code_count']}")
    logger.info(f"   初始缺少name的股票: {status['missing_name_count']}")
    logger.info(f"   从stock_basic_info同步映射: {sync_result['synced_count']}")
    logger.info(f"   修复的股票代码: {fix_result['fixed_count']}")
    logger.info(f"   跳过的股票: {fix_result['skipped_count']}")
    logger.info(f"   添加的备选映射: {fallback_result['added_count']}")
    logger.info(f"   最终缺少code的股票: {final_status['missing_code_count']}")
    logger.info(f"   最终缺少name的股票: {final_status['missing_name_count']}")
    
    logger.info("🏁 修复股票代码映射问题完成")

if __name__ == "__main__":
    main()
