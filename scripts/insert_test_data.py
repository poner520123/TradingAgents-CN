#!/usr/bin/env python3
"""
插入测试数据到达人热点集合
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from datetime import datetime
from app.core.database import get_mongo_db_sync

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """主函数"""
    logger.info("🚀 开始插入测试数据到达人热点集合...")
    
    # 使用同步数据库连接
    db = get_mongo_db_sync()
    
    # 获取达人热点集合
    expert_ranking_collection = db['expert_ranking_data']
    
    # 检查是否已存在数据
    existing_data = expert_ranking_collection.find({'code': {'$in': ['605299', '601016']}})
    existing_count = len(list(existing_data))
    logger.info(f"当前达人热点中舒华体育和节能风电数据数量: {existing_count}")
    
    # 如果没有数据，插入测试数据
    if existing_count == 0:
        logger.info("插入测试数据...")
        
        test_data = [
            {
                "expert_name": "涨停达人",
                "name": "舒华体育",
                "code": "605299",
                "analysis_reason": "今日涨停，强势突破",
                "analysis_time": "2026-03-25  14:30",
                "analysis_price": "25.88",
                "success_count": 156,
                "success_rate": 78.5,
                "source_url": "https://www.178448.com/fjzt-1.html?page=1",
                "crawled_at": datetime.utcnow()
            },
            {
                "expert_name": "风电专家",
                "name": "节能风电",
                "code": "601016",
                "analysis_reason": "风电板块龙头，今日涨停",
                "analysis_time": "2026-03-25  14:25",
                "analysis_price": "5.22",
                "success_count": 234,
                "success_rate": 82.3,
                "source_url": "https://www.178448.com/fjzt-1.html?page=1",
                "crawled_at": datetime.utcnow()
            }
        ]
        
        result = expert_ranking_collection.insert_many(test_data)
        logger.info(f"成功插入 {len(result.inserted_ids)} 条测试数据")
        
        # 验证插入结果
        new_count = expert_ranking_collection.count_documents({'code': {'$in': ['605299', '601016']}})
        logger.info(f"插入后达人热点中舒华体育和节能风电数据数量: {new_count}")
    
    logger.info("✅ 测试数据插入完成！")

if __name__ == "__main__":
    main()
