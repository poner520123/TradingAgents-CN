import os
import datetime
import sys
# Import DB_PATH from settings (which imports from src.config)
from scrapy.utils.project import get_project_settings
from .items import PopularityItem, CapitalFlowItem, ExpertRankingItem

class SQLitePipeline:
    def __init__(self):
        # 添加Python路径以便导入
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        
        # 导入数据库配置
        from src.config import DB_TYPE
        self.db_type = DB_TYPE
        
        # 直接使用应用程序的数据库连接逻辑
        from src.database import get_db_connection
        self.get_db_connection = get_db_connection
        
    def open_spider(self, spider):
        self.conn = self.get_db_connection()
        self.cursor = self.conn.cursor()
        self.crawl_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def close_spider(self, spider):
        self.conn.commit()
        self.conn.close()

    def process_item(self, item, spider):
        if isinstance(item, PopularityItem):
            if self.db_type == 'mariadb':
                # MariaDB使用%s作为占位符
                self.cursor.execute("""
                    INSERT INTO popularity_ranking (crawl_time, rank, code, name, price, change_ratio, rank_change)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    self.crawl_time,
                    item.get("rank"),
                    item.get("code"),
                    item.get("name"),
                    item.get("price"),
                    item.get("change_ratio"),
                    item.get("rank_change")
                ))
            else:
                # SQLite使用?作为占位符
                self.cursor.execute("""
                    INSERT INTO popularity_ranking (crawl_time, rank, code, name, price, change_ratio, rank_change)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.crawl_time,
                    item.get("rank"),
                    item.get("code"),
                    item.get("name"),
                    item.get("price"),
                    item.get("change_ratio"),
                    item.get("rank_change")
                ))
        elif isinstance(item, CapitalFlowItem):
            if self.db_type == 'mariadb':
                # MariaDB使用%s作为占位符
                self.cursor.execute("""
                    INSERT INTO capital_flow (crawl_time, code, name, price, change_ratio, main_flow, main_flow_text)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    self.crawl_time,
                    item.get("code"),
                    item.get("name"),
                    item.get("price"),
                    item.get("change_ratio"),
                    item.get("main_flow"),
                    item.get("main_flow_text")
                ))
            else:
                # SQLite使用?作为占位符
                self.cursor.execute("""
                    INSERT INTO capital_flow (crawl_time, code, name, price, change_ratio, main_flow, main_flow_text)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.crawl_time,
                    item.get("code"),
                    item.get("name"),
                    item.get("price"),
                    item.get("change_ratio"),
                    item.get("main_flow"),
                    item.get("main_flow_text")
                ))
        elif isinstance(item, ExpertRankingItem):
            if self.db_type == 'mariadb':
                # MariaDB使用%s作为占位符
                self.cursor.execute("""
                    INSERT INTO expert_ranking (expert_name, name, code, analysis_reason, analysis_time, analysis_price, success_count, success_rate, source_url, crawl_time)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    item.get("expert_name"),
                    item.get("name"),
                    item.get("code"),
                    item.get("analysis_reason"),
                    item.get("analysis_time"),
                    item.get("analysis_price"),
                    item.get("success_count"),
                    item.get("success_rate"),
                    item.get("source_url"),
                    self.crawl_time
                ))
            else:
                # SQLite使用?作为占位符
                self.cursor.execute("""
                    INSERT INTO expert_ranking (expert_name, name, code, analysis_reason, analysis_time, analysis_price, success_count, success_rate, source_url, crawl_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item.get("expert_name"),
                    item.get("name"),
                    item.get("code"),
                    item.get("analysis_reason"),
                    item.get("analysis_time"),
                    item.get("analysis_price"),
                    item.get("success_count"),
                    item.get("success_rate"),
                    item.get("source_url"),
                    self.crawl_time
                ))
        return item
