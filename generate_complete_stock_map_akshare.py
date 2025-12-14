#!/usr/bin/env python3
"""
使用AkShare生成完整的A股股票名称代码映射文件
"""

import os
import csv
import logging
import akshare as ak

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_a_stock_mappings() -> dict:
    """
    使用AkShare获取A股股票代码和名称映射
    """
    logger.info("使用AkShare获取A股股票代码和名称映射")
    
    try:
        # 使用AkShare获取A股股票代码和名称
        # 方法1: stock_info_a_code_name() - 获取A股股票代码和名称
        stock_info = ak.stock_info_a_code_name()
        logger.info(f"成功获取 {len(stock_info)} 条A股股票信息")
        
        # 转换为字典格式 {"name": "code"}
        stock_mappings = {}
        for _, row in stock_info.iterrows():
            name = row.get("name", "")
            code = row.get("code", "")
            if name and code:
                stock_mappings[name] = code
        
        logger.info(f"成功转换为 {len(stock_mappings)} 条映射")
        return stock_mappings
        
    except Exception as e:
        logger.error(f"使用AkShare获取A股股票代码和名称映射失败: {e}", exc_info=True)
        return {}


def merge_with_existing_file(new_mappings: dict, existing_path: str) -> dict:
    """
    与现有文件合并，去重并保留最新数据
    """
    # 读取现有数据
    existing_mappings = {}
    
    if os.path.exists(existing_path):
        logger.info(f"读取现有股票映射文件: {existing_path}")
        try:
            with open(existing_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) == 2:
                        name = row[0].replace('"', '').strip()
                        code = row[1].replace('"', '').strip()
                        if name and code:
                            existing_mappings[name] = code
            logger.info(f"读取到 {len(existing_mappings)} 条现有映射")
        except Exception as e:
            logger.error(f"读取现有文件失败: {e}", exc_info=True)
    
    # 合并新数据，新数据优先
    merged_mappings = existing_mappings.copy()
    merged_mappings.update(new_mappings)
    
    logger.info(f"合并后共有 {len(merged_mappings)} 条股票映射")
    return merged_mappings


def generate_stock_map_file(mappings: dict, output_path: str) -> bool:
    """
    生成股票映射CSV文件
    """
    try:
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            for name, code in mappings.items():
                writer.writerow([f'"{name}"', f'"{code}"'])
        
        logger.info(f"成功生成股票映射文件: {output_path}")
        logger.info(f"文件包含 {len(mappings)} 条股票映射")
        return True
    except Exception as e:
        logger.error(f"生成股票映射文件失败: {e}", exc_info=True)
        return False


def main():
    """
    主函数
    """
    logger.info("开始生成完整的A股股票映射文件")
    
    # 1. 使用AkShare获取A股股票映射
    ak_mappings = get_a_stock_mappings()
    
    if not ak_mappings:
        logger.error("未获取到A股股票映射")
        return 1
    
    # 2. 与现有文件合并
    existing_file = "docs/fjzt_a.csv"
    merged_mappings = merge_with_existing_file(ak_mappings, existing_file)
    
    # 3. 生成新的映射文件
    output_file = "docs/fjzt_a.csv"
    success = generate_stock_map_file(merged_mappings, output_file)
    
    if success:
        logger.info("✅ 完整的A股股票映射文件生成完成")
        logger.info(f"📊 文件位置: {output_file}")
        logger.info(f"📈 映射数量: {len(merged_mappings)}")
    else:
        logger.error("❌ 生成完整的A股股票映射文件失败")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
