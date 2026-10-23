#!/usr/bin/env python3
"""
批量导入股票名称和代码映射脚本

功能：
1. 从指定CSV文件读取股票名称和代码映射
2. 将映射数据写入MongoDB的stock_name_code_mapping集合
3. 同时更新stock_basic_info集合中的缺失代码
4. 支持增量导入，避免重复数据
"""

import os
import sys
import csv
import logging
from datetime import datetime
from pymongo import MongoClient
from typing import Dict, List, Tuple

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("batch_import_stock_mappings")

class BatchStockMappingImporter:
    """批量股票映射导入器"""
    
    def __init__(self):
        # 初始化MongoDB连接
        self.client = MongoClient(settings.MONGO_URI)
        self.db = self.client[settings.MONGO_DB]
        self.stock_map_collection = self.db["stock_name_code_mapping"]
        self.stock_basic_collection = self.db["stock_basic_info"]
        
        # 创建索引
        self.stock_map_collection.create_index([("name", 1)], unique=True)
        self.stock_map_collection.create_index([("code", 1)])
    
    def _get_market_by_code(self, code: str) -> str:
        """根据股票代码确定市场类型"""
        if code.startswith(('60', '688')):
            return "A股"
        elif code.startswith('30'):
            return "A股"
        elif code.startswith(('00', '000', '002')):
            return "A股"
        elif code.startswith(('83', '43')):
            return "北交所"
        elif len(code) == 4 or len(code) == 5:
            return "港股"
        else:
            return "未知"
    
    def read_csv(self, csv_path: str) -> List[Tuple[str, str]]:
        """从CSV文件读取股票名称和代码映射"""
        logger.info(f"开始从CSV文件读取股票名称和代码映射: {csv_path}")
        mappings = []
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) == 2:
                        name = row[0].replace('"', '').strip()
                        code = row[1].replace('"', '').strip()
                        
                        if name and code:
                            mappings.append((name, code))
        except Exception as e:
            logger.error(f"从CSV文件读取股票名称和代码映射失败: {e}")
            return []
        
        logger.info(f"从CSV文件读取完成，共获取 {len(mappings)} 条映射")
        return mappings
    
    def import_to_stock_map(self, mappings: List[Tuple[str, str]]) -> Dict[str, int]:
        """将映射导入到stock_name_code_mapping集合"""
        logger.info("开始将映射导入到stock_name_code_mapping集合")
        
        stats = {
            "total": len(mappings),
            "imported": 0,
            "skipped": 0,
            "failed": 0
        }
        
        for name, code in mappings:
            try:
                # 确定市场类型
                market = self._get_market_by_code(code)
                
                # 更新或插入数据
                result = self.stock_map_collection.update_one(
                    {"name": name},
                    {
                        "$set": {
                            "code": code,
                            "market": market,
                            "updated_at": datetime.utcnow()
                        },
                        "$setOnInsert": {
                            "created_at": datetime.utcnow()
                        }
                    },
                    upsert=True
                )
                
                if result.upserted_id:
                    stats["imported"] += 1
                    logger.info(f"✅ 导入映射: {name} -> {code} (市场: {market})")
                else:
                    stats["skipped"] += 1
                    logger.info(f"ℹ️ 跳过已存在的映射: {name} -> {code}")
            except Exception as e:
                stats["failed"] += 1
                logger.error(f"❌ 导入映射失败: {name} -> {code}, 错误: {e}")
        
        logger.info(f"映射导入到stock_name_code_mapping集合完成，总记录: {stats['total']}, 导入: {stats['imported']}, 跳过: {stats['skipped']}, 失败: {stats['failed']}")
        return stats
    
    def update_stock_basic_info(self, mappings: List[Tuple[str, str]]) -> Dict[str, int]:
        """更新stock_basic_info集合中的缺失代码"""
        logger.info("开始更新stock_basic_info集合中的缺失代码")
        
        stats = {
            "total": len(mappings),
            "updated": 0,
            "not_found": 0,
            "failed": 0
        }
        
        for name, code in mappings:
            try:
                # 查找缺少code的股票
                result = self.stock_basic_collection.update_many(
                    {
                        "name": name,
                        "$or": [{"code": {"$exists": False}}, {"code": None}, {"code": ""}]
                    },
                    {"$set": {"code": code, "updated_at": datetime.utcnow()}}
                )
                
                if result.modified_count > 0:
                    stats["updated"] += 1
                    logger.info(f"✅ 更新stock_basic_info中的股票代码: {name} -> {code}")
                else:
                    stats["not_found"] += 1
                    # 检查是否存在该名称但已有code的记录
                    existing = self.stock_basic_collection.find_one({"name": name})
                    if existing and existing.get("code"):
                        logger.info(f"ℹ️ 股票已存在且有代码，无需更新: {name} -> {existing['code']}")
                    else:
                        logger.info(f"ℹ️ 未找到需要更新的股票: {name}")
            except Exception as e:
                stats["failed"] += 1
                logger.error(f"❌ 更新stock_basic_info失败: {name} -> {code}, 错误: {e}")
        
        logger.info(f"更新stock_basic_info集合完成，总记录: {stats['total']}, 更新: {stats['updated']}, 未找到: {stats['not_found']}, 失败: {stats['failed']}")
        return stats
    
    def run(self, csv_path: str):
        """执行批量导入"""
        logger.info("🚀 开始执行批量股票映射导入")
        
        # 1. 读取CSV文件
        mappings = self.read_csv(csv_path)
        if not mappings:
            logger.error("❌ 未获取到映射数据，导入失败")
            return
        
        # 2. 导入到stock_name_code_mapping集合
        stock_map_stats = self.import_to_stock_map(mappings)
        
        # 3. 更新stock_basic_info集合
        stock_basic_stats = self.update_stock_basic_info(mappings)
        
        # 4. 打印总结
        logger.info("📋 批量股票映射导入完成")
        logger.info(f"   从CSV读取: {stock_map_stats['total']} 条记录")
        logger.info(f"   导入到stock_name_code_mapping:")
        logger.info(f"     成功: {stock_map_stats['imported']}")
        logger.info(f"     跳过: {stock_map_stats['skipped']}")
        logger.info(f"     失败: {stock_map_stats['failed']}")
        logger.info(f"   更新到stock_basic_info:")
        logger.info(f"     更新: {stock_basic_stats['updated']}")
        logger.info(f"     未找到: {stock_basic_stats['not_found']}")
        logger.info(f"     失败: {stock_basic_stats['failed']}")
        
        # 5. 关闭MongoDB连接
        self.client.close()
        logger.info("🏁 批量股票映射导入全部完成")

if __name__ == "__main__":
    # CSV文件路径
    csv_path = "docs/fjzt_a.csv"
    
    # 检查文件是否存在
    if not os.path.exists(csv_path):
        logger.error(f"❌ CSV文件不存在: {csv_path}")
        sys.exit(1)
    
    # 创建导入器实例并执行导入
    importer = BatchStockMappingImporter()
    importer.run(csv_path)