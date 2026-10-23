#!/usr/bin/env python3
"""
生成完整的A股股票名称代码映射文件
"""

import os
import csv
import logging
import requests
import json
from typing import Dict, List, Tuple

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_stock_basic_info() -> List[Dict[str, str]]:
    """
    获取A股股票基本信息
    使用东方财富API获取A股股票列表
    """
    stocks = []
    page = 1
    page_size = 1000
    total_count = None
    
    try:
        while True:
            logger.info(f"获取第 {page} 页股票数据...")
            
            url = "http://22.push2.eastmoney.com/api/qt/clist/get"
            params = {
                "pn": str(page),
                "pz": str(page_size),
                "po": "1",
                "np": "1",
                "fltt": "2",
                "invt": "2",
                "fid": "f3",
                "fs": "m:0 t:6,m:0 t:13,m:0 t:80,m:1 t:2,m:1 t:23,m:1 t:3",
                "fields": "f12,f14",  # f12: 股票代码, f14: 股票名称
                "ut": "bd1d9ddb04089700cf9c27f6f7426281"
            }
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            response = requests.get(url, params=params, headers=headers)
            data = response.json()
            
            # 获取数据列表
            data_list = data.get("data", {}).get("diff", [])
            
            if not data_list:
                logger.info("没有更多数据了")
                break
            
            # 保存数据
            for stock in data_list:
                stocks.append({
                    "code": stock.get("f12", ""),
                    "name": stock.get("f14", "")
                })
            
            # 获取总数量
            if total_count is None:
                total_count = data.get("data", {}).get("total", 0)
                logger.info(f"A股股票总数: {total_count}")
            
            # 检查是否完成
            if len(stocks) >= total_count:
                logger.info(f"已获取所有数据，共 {len(stocks)} 条")
                break
            
            page += 1
            
            # 限制请求频率
            import time
            time.sleep(1)
            
    except Exception as e:
        logger.error(f"获取A股股票基本信息失败: {e}", exc_info=True)
    
    logger.info(f"成功获取 {len(stocks)} 条A股股票信息")
    return stocks


def generate_stock_map_file(stocks: List[Dict[str, str]], output_path: str) -> bool:
    """
    生成股票映射CSV文件
    """
    try:
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            for stock in stocks:
                writer.writerow([f'"{stock["name"]}"', f'"{stock["code"]}"'])
        
        logger.info(f"成功生成股票映射文件: {output_path}")
        logger.info(f"文件包含 {len(stocks)} 条股票映射")
        return True
    except Exception as e:
        logger.error(f"生成股票映射文件失败: {e}", exc_info=True)
        return False


def merge_with_existing_file(new_stocks: List[Dict[str, str]], existing_path: str) -> List[Dict[str, str]]:
    """
    与现有文件合并，去重并保留最新数据
    """
    # 读取现有数据
    existing_stocks = {}
    
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
                            existing_stocks[name] = code
            logger.info(f"读取到 {len(existing_stocks)} 条现有映射")
        except Exception as e:
            logger.error(f"读取现有文件失败: {e}", exc_info=True)
    
    # 合并新数据，新数据优先
    merged_stocks = existing_stocks.copy()
    for stock in new_stocks:
        merged_stocks[stock["name"]] = stock["code"]
    
    # 转换为列表格式
    result = [{
        "name": name,
        "code": code
    } for name, code in merged_stocks.items()]
    
    logger.info(f"合并后共有 {len(result)} 条股票映射")
    return result


def main():
    """
    主函数
    """
    logger.info("开始生成完整的A股股票映射文件")
    
    # 1. 获取A股股票信息
    stocks = get_stock_basic_info()
    
    if not stocks:
        logger.error("未获取到A股股票信息")
        return 1
    
    # 2. 与现有文件合并
    existing_file = "docs/fjzt_a.csv"
    merged_stocks = merge_with_existing_file(stocks, existing_file)
    
    # 3. 生成新的映射文件
    output_file = "docs/fjzt_a.csv"
    success = generate_stock_map_file(merged_stocks, output_file)
    
    if success:
        logger.info("✅ 完整的A股股票映射文件生成完成")
        logger.info(f"📊 文件位置: {output_file}")
        logger.info(f"📈 映射数量: {len(merged_stocks)}")
    else:
        logger.error("❌ 生成完整的A股股票映射文件失败")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
