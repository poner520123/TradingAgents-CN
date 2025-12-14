#!/usr/bin/env python3
"""
补充股票名称代码映射脚本
1. 从 docs/fjzt_a.csv 文件加载股票名称和代码映射
2. 遍历A股股票，补充缺失的映射
3. 确保数据库中的所有股票都有对应的代码
"""

import os
import sys
import logging
import csv
from typing import Dict, List, Optional

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.stock_map_service import stock_map_service
from app.core.config import settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_fjzt_a_mappings() -> List[Dict[str, str]]:
    """
    从 docs/fjzt_a.csv 文件加载股票映射
    """
    mappings = []
    csv_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__),
        'docs',
        'fjzt_a.csv'
    ))
    
    if not os.path.exists(csv_path):
        logger.error(f"fjzt_a.csv 文件不存在: {csv_path}")
        return mappings
    
    logger.info(f"开始从 {csv_path} 加载股票映射")
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) == 2:
                    # 处理带引号的字段
                    name = row[0].replace('"', '').strip()
                    code = row[1].replace('"', '').strip()
                    
                    if name and code:
                        mappings.append({
                            'name': name,
                            'code': code,
                            'market': 'CN'
                        })
        
        logger.info(f"成功从 fjzt_a.csv 加载 {len(mappings)} 条映射")
    except Exception as e:
        logger.error(f"从 fjzt_a.csv 加载映射失败: {e}")
    
    return mappings


def import_mappings_to_db(mappings: List[Dict[str, str]]) -> int:
    """
    将映射导入到数据库
    """
    imported = 0
    
    for mapping in mappings:
        name = mapping['name']
        code = mapping['code']
        market = mapping['market']
        
        # 检查是否已存在
        existing = stock_map_service.collection.find_one({'name': name})
        if not existing:
            # 插入新映射
            success = stock_map_service.upsert_map(name, code, market)
            if success:
                imported += 1
                logger.info(f"导入映射: {name} -> {code}")
        else:
            # 检查是否需要更新
            if existing['code'] != code:
                success = stock_map_service.upsert_map(name, code, market)
                if success:
                    imported += 1
                    logger.info(f"更新映射: {name} -> {code} (旧: {existing['code']})")
    
    logger.info(f"总共导入 {imported} 条映射")
    return imported


def supplement_stock_codes():
    """
    补充股票代码：为没有代码的股票记录添加代码
    """
    # 使用 stock_map_service 中的数据库连接
    db = stock_map_service.db
    
    # 统计信息
    updated_count = 0
    skipped_count = 0
    error_count = 0
    
    # 1. 处理 analysis_reports 集合中的股票
    logger.info("处理 analysis_reports 集合中的股票...")
    reports = db.analysis_reports.find({'code': {'$exists': False}})
    
    for report in reports:
        stock_name = report.get('stock_name')
        if stock_name:
            # 尝试获取代码
            code = stock_map_service.get_code_by_name(stock_name)
            if code:
                # 更新报告
                db.analysis_reports.update_one(
                    {'_id': report['_id']},
                    {'$set': {'code': code}}
                )
                updated_count += 1
                logger.info(f"更新 analysis_report: {stock_name} -> {code}")
            else:
                skipped_count += 1
                logger.warning(f"无法获取代码: {stock_name}")
        else:
            error_count += 1
    
    logger.info(f"analysis_reports 集合处理完成: 更新 {updated_count} 条, 跳过 {skipped_count} 条, 错误 {error_count} 条")
    
    # 2. 处理其他可能包含股票名称但没有代码的集合
    collections_to_check = [
        'stock_basic_info',
        'stock_financial_data',
        'market_quotes',
        'stock_recommendations'
    ]
    
    for collection_name in collections_to_check:
        if collection_name in db.list_collection_names():
            logger.info(f"处理 {collection_name} 集合中的股票...")
            collection = db[collection_name]
            
            # 查找没有 code 或 code 为空的记录
            cursor = collection.find({'$or': [
                {'code': {'$exists': False}},
                {'code': ''},
                {'code': None}
            ]})
            
            coll_updated = 0
            coll_skipped = 0
            coll_error = 0
            
            for doc in cursor:
                # 根据不同集合获取股票名称字段
                stock_name = None
                if 'name' in doc:
                    stock_name = doc['name']
                elif 'stock_name' in doc:
                    stock_name = doc['stock_name']
                elif 'stock' in doc:
                    stock_name = doc['stock']
                
                if stock_name:
                    # 尝试获取代码
                    code = stock_map_service.get_code_by_name(stock_name)
                    if code:
                        # 更新记录
                        collection.update_one(
                            {'_id': doc['_id']},
                            {'$set': {'code': code}}
                        )
                        coll_updated += 1
                        logger.info(f"更新 {collection_name}: {stock_name} -> {code}")
                    else:
                        coll_skipped += 1
                else:
                    coll_error += 1
            
            logger.info(f"{collection_name} 集合处理完成: 更新 {coll_updated} 条, 跳过 {coll_skipped} 条, 错误 {coll_error} 条")
            
            updated_count += coll_updated
            skipped_count += coll_skipped
            error_count += coll_error
    
    logger.info(f"所有集合处理完成: 总计更新 {updated_count} 条, 跳过 {skipped_count} 条, 错误 {error_count} 条")
    return {
        'updated': updated_count,
        'skipped': skipped_count,
        'error': error_count
    }


def main():
    """
    主函数
    """
    logger.info("开始补充股票名称代码映射...")
    
    try:
        # 1. 加载 fjzt_a.csv 映射
        fjzt_mappings = load_fjzt_a_mappings()
        
        if fjzt_mappings:
            # 2. 导入映射到数据库
            import_mappings_to_db(fjzt_mappings)
        
        # 3. 补充缺失的股票代码
        supplement_result = supplement_stock_codes()
        
        # 4. 显示最终统计
        total_mappings = stock_map_service.get_total_count()
        logger.info(f"补充完成！")
        logger.info(f"数据库中共有 {total_mappings} 条股票名称代码映射")
        logger.info(f"更新了 {supplement_result['updated']} 条股票记录")
        logger.info(f"跳过了 {supplement_result['skipped']} 条股票记录")
        logger.info(f"处理错误 {supplement_result['error']} 条")
        
    except Exception as e:
        logger.error(f"补充股票名称代码映射失败: {e}", exc_info=True)
        return 1
    finally:
        # 关闭连接
        stock_map_service.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
