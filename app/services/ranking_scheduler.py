import asyncio
import logging
from datetime import datetime, timedelta
import threading
from app.core.crawler_fund import fund_ranking_crawler
from app.core.crawler_popularity import popularity_ranking_crawler

# Configure logging
logger = logging.getLogger(__name__)

class RankingScheduler:
    """排行数据定时调度器"""
    
    def __init__(self):
        self.fund_crawler = fund_ranking_crawler
        self.popularity_crawler = popularity_ranking_crawler
        self.running = False
        self.task = None
        self.lock = threading.Lock()
        # 爬取间隔（秒）
        self.crawl_interval = 600  # 10分钟
    
    def start(self):
        """启动定时调度器"""
        with self.lock:
            if self.running:
                logger.warning("🔄 Ranking scheduler is already running")
                return
            
        logger.info("🚀 Starting ranking scheduler")
        self.running = True
        
        # 立即执行一次爬取
        self._run_crawlers()
        
        # 启动定时任务
        self.task = asyncio.create_task(self._schedule_task())
    
    def stop(self):
        """停止定时调度器"""
        with self.lock:
            if not self.running:
                logger.warning("🔄 Ranking scheduler is not running")
                return
        
        logger.info("🛑 Stopping ranking scheduler")
        self.running = False
        
        if self.task:
            self.task.cancel()
            self.task = None
    
    async def _schedule_task(self):
        """定时任务"""
        while self.running:
            try:
                # 等待指定间隔
                await asyncio.sleep(self.crawl_interval)
                
                if self.running:
                    self._run_crawlers()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in ranking scheduler: {e}")
                # 继续运行
                continue
    
    def _run_crawlers(self):
        """运行爬虫任务"""
        logger.info("🔄 Running ranking crawlers")
        
        try:
            # 运行资金排行爬虫
            fund_result = self.fund_crawler.crawl_fund_ranking()
            logger.info(f"✅ Fund ranking crawl completed: {fund_result} records")
            
            # 运行人气排行爬虫
            popularity_result = self.popularity_crawler.crawl_popularity_ranking()
            logger.info(f"✅ Popularity ranking crawl completed: {popularity_result} records")
            
            # 检查爬虫状态
            self._check_crawler_status()
        except Exception as e:
            logger.error(f"❌ Error running crawlers: {e}")
    
    def _check_crawler_status(self):
        """检查爬虫状态"""
        logger.info("🔍 Checking crawler status")
        
        # 检查资金排行爬虫状态
        fund_status = self.fund_crawler.check_crawl_status()
        logger.info(f"📊 Fund crawler status: {fund_status['status']} - {fund_status['message']}")
        
        # 检查人气排行爬虫状态
        popularity_status = self.popularity_crawler.check_crawl_status()
        logger.info(f"📊 Popularity crawler status: {popularity_status['status']} - {popularity_status['message']}")
        
        # 如果状态异常，触发修复
        if fund_status['status'] != 'healthy':
            logger.warning(f"⚠️ Fund crawler needs attention: {fund_status['message']}")
            # 尝试修复
            self._fix_crawler(self.fund_crawler)
        
        if popularity_status['status'] != 'healthy':
            logger.warning(f"⚠️ Popularity crawler needs attention: {popularity_status['message']}")
            # 尝试修复
            self._fix_crawler(self.popularity_crawler)
    
    def _fix_crawler(self, crawler):
        """修复爬虫"""
        logger.info(f"🔧 Attempting to fix crawler")
        
        try:
            # 重置会话
            if hasattr(crawler, '_reset_session'):
                crawler._reset_session()
            
            # 重新爬取
            if hasattr(crawler, 'crawl_fund_ranking'):
                result = crawler.crawl_fund_ranking()
                logger.info(f"✅ Fund crawler fixed, crawled {result} records")
            elif hasattr(crawler, 'crawl_popularity_ranking'):
                result = crawler.crawl_popularity_ranking()
                logger.info(f"✅ Popularity crawler fixed, crawled {result} records")
        except Exception as e:
            logger.error(f"❌ Failed to fix crawler: {e}")
    
    def get_status(self):
        """获取调度器状态"""
        fund_status = self.fund_crawler.check_crawl_status()
        popularity_status = self.popularity_crawler.check_crawl_status()
        
        return {
            "scheduler_running": self.running,
            "crawl_interval": self.crawl_interval,
            "fund_crawler": fund_status,
            "popularity_crawler": popularity_status
        }

# 全局排行调度器实例
ranking_scheduler = RankingScheduler()
