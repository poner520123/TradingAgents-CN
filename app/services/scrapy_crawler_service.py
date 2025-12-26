import os
import subprocess
import json
import logging
from datetime import datetime
from pymongo import MongoClient, ASCENDING, DESCENDING
from app.core.config import settings

logger = logging.getLogger(__name__)

class ScrapyCrawlerService:
    """Handles Scrapy crawler execution and data management."""
    
    def __init__(self):
        # Initialize MongoDB connection
        self.client = MongoClient(settings.MONGO_URI)
        self.db = self.client[settings.MONGO_DB]
        
        # Create collections
        self.popularity_collection = self.db.popularity_data
        self.capital_flow_collection = self.db.capital_flow_data
        self.expert_ranking_collection = self.db.expert_ranking_data
        
        # Initialize indexes
        self._init_indexes()
        
        # Scrapy project path
        self.scrapy_project_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scrapy_project', 'crawler')
    
    def _init_indexes(self):
        """Initialize database indexes."""
        try:
            # Popularity collection indexes
            self.popularity_collection.create_index([("code", ASCENDING)], unique=True)
            self.popularity_collection.create_index([("rank", ASCENDING)])
            self.popularity_collection.create_index([("crawled_at", DESCENDING)])
            
            # Capital flow collection indexes
            self.capital_flow_collection.create_index([("code", ASCENDING)], unique=True)
            self.capital_flow_collection.create_index([("main_flow", DESCENDING)])
            self.capital_flow_collection.create_index([("crawled_at", DESCENDING)])
            
            # Expert ranking collection indexes
            self.expert_ranking_collection.create_index([
                ("expert_name", ASCENDING),
                ("code", ASCENDING),
                ("analysis_time", DESCENDING)
            ], unique=True)
            self.expert_ranking_collection.create_index([("success_rate", DESCENDING)])
            self.expert_ranking_collection.create_index([("success_count", DESCENDING)])
            self.expert_ranking_collection.create_index([("crawled_at", DESCENDING)])
            
            logger.info("✅ Created indexes for all collections")
        except Exception as e:
            logger.error(f"❌ Failed to create indexes: {e}")
    
    def run_scrapy_spider(self, spider_name):
        """Run a specific Scrapy spider and return its output."""
        logger.info(f"🚀 Running Scrapy spider: {spider_name}")
        
        # Change to scrapy project directory and run spider
        cmd = f"python -m scrapy crawl {spider_name} -o -:jsonlines"
        
        try:
            result = subprocess.run(
                cmd, 
                shell=True, 
                cwd=self.scrapy_project_path, 
                capture_output=True, 
                text=True, 
                encoding='utf-8',
                timeout=120  # 延长超时时间到120秒
            )
            
            if result.returncode != 0:
                logger.error(f"❌ Spider {spider_name} failed with return code {result.returncode}")
                logger.error(f"Error output: {result.stderr}")
                return None
            
            logger.info(f"✅ Spider {spider_name} completed successfully")
            return result.stdout
        except subprocess.TimeoutExpired:
            logger.error(f"❌ Spider {spider_name} timed out after 60 seconds")
            return None
        except Exception as e:
            logger.error(f"❌ Error running spider {spider_name}: {type(e).__name__}: {str(e)}")
            return None
    
    def parse_spider_output(self, output):
        """Parse Scrapy spider JSON output."""
        if not output:
            return []
        
        try:
            # Split output by lines and parse each JSON object
            data = []
            for line in output.strip().split('\n'):
                if line.strip():
                    item = json.loads(line)
                    data.append(item)
            return data
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse spider output: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Error parsing spider output: {type(e).__name__}: {str(e)}")
            return []
    
    def save_popularity_data(self, data):
        """Save popularity ranking data to database."""
        if not data:
            return 0
        
        count = 0
        for item in data:
            try:
                # Add crawled_at timestamp
                item['crawled_at'] = datetime.utcnow()
                
                # Upsert based on code
                result = self.popularity_collection.update_one(
                    {"code": item["code"]}, 
                    {"$set": item}, 
                    upsert=True
                )
                
                if result.upserted_id:
                    count += 1
            except Exception as e:
                logger.error(f"❌ Error saving popularity data: {e}")
        
        logger.info(f"✅ Saved {count} new popularity records")
        return count
    
    def save_capital_flow_data(self, data):
        """Save capital flow data to database."""
        if not data:
            return 0
        
        count = 0
        for item in data:
            try:
                # Add crawled_at timestamp
                item['crawled_at'] = datetime.utcnow()
                
                # Upsert based on code
                result = self.capital_flow_collection.update_one(
                    {"code": item["code"]}, 
                    {"$set": item}, 
                    upsert=True
                )
                
                if result.upserted_id:
                    count += 1
            except Exception as e:
                logger.error(f"❌ Error saving capital flow data: {e}")
        
        logger.info(f"✅ Saved {count} new capital flow records")
        return count
    
    def save_expert_ranking_data(self, data):
        """Save expert ranking data to database."""
        if not data:
            return 0
        
        count = 0
        for item in data:
            try:
                # Add crawled_at timestamp
                item['crawled_at'] = datetime.utcnow()
                
                # Upsert based on expert_name, code, and analysis_time
                result = self.expert_ranking_collection.update_one(
                    {
                        "expert_name": item["expert_name"],
                        "code": item["code"],
                        "analysis_time": item["analysis_time"]
                    }, 
                    {"$set": item}, 
                    upsert=True
                )
                
                if result.upserted_id:
                    count += 1
            except Exception as e:
                logger.error(f"❌ Error saving expert ranking data: {e}")
        
        logger.info(f"✅ Saved {count} new expert ranking records")
        return count
    
    def crawl_popularity(self):
        """Run popularity crawler and save data."""
        logger.info("🕷️  Starting popularity crawl...")
        output = self.run_scrapy_spider("popularity")
        if output:
            data = self.parse_spider_output(output)
            return self.save_popularity_data(data)
        return 0
    
    def crawl_capital_flow(self):
        """Run capital flow crawler and save data."""
        logger.info("🕷️  Starting capital flow crawl...")
        output = self.run_scrapy_spider("capital_flow")
        if output:
            data = self.parse_spider_output(output)
            return self.save_capital_flow_data(data)
        return 0
    
    def crawl_expert_ranking(self):
        """Run expert ranking crawler and save data."""
        logger.info("🕷️  Starting expert ranking crawl...")
        output = self.run_scrapy_spider("expert_ranking")
        if output:
            data = self.parse_spider_output(output)
            return self.save_expert_ranking_data(data)
        return 0
    
    def get_popularity_data(self, page=1, page_size=20):
        """Get paginated popularity data."""
        skip = (page - 1) * page_size
        total = self.popularity_collection.count_documents({})
        cursor = self.popularity_collection.find()
        cursor = cursor.sort("rank", ASCENDING).skip(skip).limit(page_size)
        
        data = list(cursor)
        # Convert ObjectId to string
        for d in data:
            if '_id' in d:
                d['_id'] = str(d['_id'])
        
        return data, total
    
    def get_capital_flow_data(self, page=1, page_size=20):
        """Get paginated capital flow data."""
        skip = (page - 1) * page_size
        total = self.capital_flow_collection.count_documents({})
        cursor = self.capital_flow_collection.find()
        cursor = cursor.sort("main_flow", DESCENDING).skip(skip).limit(page_size)
        
        data = list(cursor)
        # Convert ObjectId to string
        for d in data:
            if '_id' in d:
                d['_id'] = str(d['_id'])
        
        return data, total
    
    def get_expert_ranking_data(self, page=1, page_size=20):
        """Get paginated expert ranking data."""
        skip = (page - 1) * page_size
        total = self.expert_ranking_collection.count_documents({})
        cursor = self.expert_ranking_collection.find()
        cursor = cursor.sort("success_rate", DESCENDING).skip(skip).limit(page_size)
        
        data = list(cursor)
        # Convert ObjectId to string
        for d in data:
            if '_id' in d:
                d['_id'] = str(d['_id'])
        
        return data, total
    
    def get_cross_analysis_data(self, page=1, page_size=20):
        """Get cross analysis data."""
        # This is a simple implementation, can be expanded based on requirements
        skip = (page - 1) * page_size
        
        # Get expert ranking data sorted by success rate and success count
        cursor = self.expert_ranking_collection.find()
        cursor = cursor.sort([
            ("success_rate", DESCENDING),
            ("success_count", DESCENDING)
        ]).skip(skip).limit(page_size)
        
        data = list(cursor)
        # Convert ObjectId to string
        for d in data:
            if '_id' in d:
                d['_id'] = str(d['_id'])
        
        total = self.expert_ranking_collection.count_documents({})
        return data, total
    
    def run_all_crawlers(self):
        """Run all crawlers sequentially."""
        logger.info("🚀 Running all Scrapy crawlers...")
        
        total_saved = 0
        
        # Run popularity crawler
        total_saved += self.crawl_popularity()
        
        # Run capital flow crawler
        total_saved += self.crawl_capital_flow()
        
        # Run expert ranking crawler
        total_saved += self.crawl_expert_ranking()
        
        logger.info(f"✅ All crawlers completed. Total new records saved: {total_saved}")
        return total_saved