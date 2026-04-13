import os
import subprocess
import json
import logging
import asyncio
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
            # Popularity collection indexes - allow multiple records for same code but different crawled_at
            self.popularity_collection.create_index([("code", ASCENDING), ("crawled_at", DESCENDING)])
            self.popularity_collection.create_index([("rank", ASCENDING)])
            self.popularity_collection.create_index([("crawled_at", DESCENDING)])
            
            # Capital flow collection indexes - allow multiple records for same code but different crawled_at
            self.capital_flow_collection.create_index([("code", ASCENDING), ("crawled_at", DESCENDING)])
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
        # Import here to avoid circular import
        from app.services.stock_map_service import stock_map_service
        
        # Get current timestamp for all items
        current_time = datetime.utcnow()
        
        for item in data:
            try:
                # Add crawled_at timestamp
                item['crawled_at'] = current_time
                
                # Process rank_change field: convert '-' to None
                if 'rank_change' in item and item['rank_change'] == '-':
                    item['rank_change'] = None
                elif 'rank_change' in item and isinstance(item['rank_change'], str):
                    try:
                        item['rank_change'] = int(item['rank_change'])
                    except ValueError:
                        item['rank_change'] = None
                
                # Get correct stock name from stock_map_service
                if 'code' in item:
                    stock_name = stock_map_service.get_name_by_code(item['code'])
                    if stock_name:
                        item['name'] = stock_name
                
                # Upsert based on code, but always update with latest data
                # We want to keep all data with different crawled_at timestamps
                # to allow historical analysis
                self.popularity_collection.insert_one(item)
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
        # Import here to avoid circular import
        from app.services.stock_map_service import stock_map_service
        
        # Get current timestamp for all items
        current_time = datetime.utcnow()
        
        for item in data:
            try:
                # Add crawled_at timestamp
                item['crawled_at'] = current_time
                
                # Get correct stock name from stock_map_service
                if 'code' in item:
                    stock_name = stock_map_service.get_name_by_code(item['code'])
                    if stock_name:
                        item['name'] = stock_name
                
                # Insert new record instead of upserting
                # to keep all historical data
                self.capital_flow_collection.insert_one(item)
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
        # Import here to avoid circular import
        from app.services.stock_map_service import stock_map_service
        
        # Get current timestamp for all items
        current_time = datetime.utcnow()
        
        for item in data:
            try:
                # Add crawled_at timestamp
                item['crawled_at'] = current_time
                
                # Get correct stock code and name from stock_map_service
                if 'name' in item:
                    # If code is empty, try to get it by name
                    if not item.get('code'):
                        item['code'] = stock_map_service.get_code_by_name(item['name'])
                    
                    # If we have a code, get the correct name
                    if item.get('code'):
                        stock_name = stock_map_service.get_name_by_code(item['code'])
                        if stock_name:
                            item['name'] = stock_name
                
                # Upsert based on expert_name, code, and analysis_time
                # This ensures we don't duplicate the same analysis
                result = self.expert_ranking_collection.update_one(
                    {
                        "expert_name": item["expert_name"],
                        "code": item["code"],
                        "analysis_time": item["analysis_time"]
                    }, 
                    {"$set": item}, 
                    upsert=True
                )
                
                if result.upserted_id or result.modified_count > 0:
                    count += 1
            except Exception as e:
                logger.error(f"❌ Error saving expert ranking data: {e}")
        
        logger.info(f"✅ Saved {count} expert ranking records (new: {count})")
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
        """Get paginated popularity data with deduplication."""
        from pymongo import DESCENDING
        
        # Get the most recent record for each stock code
        pipeline = [
            {
                "$sort": {"code": 1, "crawled_at": DESCENDING}
            },
            {
                "$group": {
                    "_id": "$code",
                    "doc": {"$first": "$$ROOT"}
                }
            },
            {
                "$replaceRoot": {"newRoot": "$doc"}
            },
            {
                "$sort": {"rank": ASCENDING}
            },
            {
                "$skip": (page - 1) * page_size
            },
            {
                "$limit": page_size
            }
        ]
        
        data = list(self.popularity_collection.aggregate(pipeline))
        
        # Get total count using aggregation instead of distinct (faster)
        count_pipeline = [
            {
                "$group": {
                    "_id": "$code"
                }
            },
            {
                "$count": "total"
            }
        ]
        count_result = list(self.popularity_collection.aggregate(count_pipeline))
        total = count_result[0]['total'] if count_result else 0
        
        # Convert ObjectId to string
        for d in data:
            if '_id' in d:
                d['_id'] = str(d['_id'])
        
        return data, total
    
    def get_capital_flow_data(self, page=1, page_size=20):
        """Get paginated capital flow data with deduplication."""
        from pymongo import DESCENDING
        
        # Get the most recent record for each stock code
        pipeline = [
            {
                "$sort": {"code": 1, "crawled_at": DESCENDING}
            },
            {
                "$group": {
                    "_id": "$code",
                    "doc": {"$first": "$$ROOT"}
                }
            },
            {
                "$replaceRoot": {"newRoot": "$doc"}
            },
            {
                "$sort": {"main_flow": DESCENDING}
            },
            {
                "$skip": (page - 1) * page_size
            },
            {
                "$limit": page_size
            }
        ]
        
        data = list(self.capital_flow_collection.aggregate(pipeline))
        
        # Get total count using aggregation instead of distinct (faster)
        count_pipeline = [
            {
                "$group": {
                    "_id": "$code"
                }
            },
            {
                "$count": "total"
            }
        ]
        count_result = list(self.capital_flow_collection.aggregate(count_pipeline))
        total = count_result[0]['total'] if count_result else 0
        
        # Convert ObjectId to string
        for d in data:
            if '_id' in d:
                d['_id'] = str(d['_id'])
        
        return data, total
    
    def get_expert_ranking_data(self, page=1, page_size=20):
        """Get paginated expert ranking data with deduplication."""
        from datetime import datetime
        
        # Get all expert ranking data first for de-duplication
        cursor = self.expert_ranking_collection.find()
        all_data = list(cursor)
        
        # Convert ObjectId to string
        for d in all_data:
            if '_id' in d:
                d['_id'] = str(d['_id'])
        
        # De-duplicate based on stock code - only keep the latest record for each stock code
        # Priority: 1. Records with stock code 2. Newest record based on crawled_at/analysis_time
        unique_items = {}
        for item in all_data:
            stock_code = item.get('code', '')
            
            # Only process records with stock code (user requirement: all records must have stock code)
            if not stock_code:
                continue
                
            # Check if this stock code already exists
            if stock_code in unique_items:
                existing_item = unique_items[stock_code]
                
                # Compare crawled_at first (more reliable than analysis_time)
                existing_crawled = existing_item.get('crawled_at', datetime.min)
                current_crawled = item.get('crawled_at', datetime.min)
                
                if current_crawled > existing_crawled:
                    unique_items[stock_code] = item
                # Fall back to analysis_time if crawled_at is not available
                elif existing_crawled == current_crawled:
                    existing_time = existing_item.get('analysis_time', '')
                    current_time = item.get('analysis_time', '')
                    if current_time > existing_time:
                        unique_items[stock_code] = item
            else:
                # Add new item if stock code doesn't exist
                unique_items[stock_code] = item
        
        # Convert back to list and filter records with success_rate >= 60%
        unique_data = list(unique_items.values())
        # Filter out records with success_rate < 60%
        unique_data = [item for item in unique_data if item.get('success_rate', 0) >= 60]
        unique_data.sort(key=lambda x: x.get('success_rate', 0), reverse=True)
        total = len(unique_data)
        
        # Apply pagination
        skip = (page - 1) * page_size
        paginated_data = unique_data[skip:skip + page_size]
        
        return paginated_data, total
    
    def get_cross_analysis_data(self, page=1, page_size=20):
        """Get cross analysis data with popularity and capital flow ranks."""
        from datetime import datetime, timedelta
        
        # Get all expert ranking data first for de-duplication, filter by recent 7 days
        one_week_ago = datetime.utcnow() - timedelta(days=7)
        cursor = self.expert_ranking_collection.find({
            "crawled_at": {"$gte": one_week_ago}
        })
        
        all_data = list(cursor)
        # Convert ObjectId to string
        for d in all_data:
            if '_id' in d:
                d['_id'] = str(d['_id'])
        
        # First filter out records with None code to avoid validation errors
        all_data = [item for item in all_data if item.get('code') is not None]
        
        # De-duplicate based on expert_name and name (stock name) as unique index
        # Priority is given to records with code (stock code), and if both have code, keep the newer one
        unique_items = {}
        for item in all_data:
            # Create a unique key using expert_name and name (stock name)
            expert_name = item.get('expert_name', '')
            stock_name = item.get('name', '')
            unique_key = f"{expert_name}_{stock_name}"
            
            # Check if this key already exists
            if unique_key in unique_items:
                existing_item = unique_items[unique_key]
                existing_has_code = existing_item.get('code') is not None
                current_has_code = item.get('code') is not None
                
                # If both have code, keep the newer one based on crawled_at
                if existing_has_code and current_has_code:
                    # Try to compare crawled_at first (more reliable than analysis_time)
                    existing_crawled = existing_item.get('crawled_at', datetime.min)
                    current_crawled = item.get('crawled_at', datetime.min)
                    
                    if current_crawled > existing_crawled:
                        unique_items[unique_key] = item
                    # Fall back to analysis_time if crawled_at is not available
                    elif existing_crawled == current_crawled:
                        existing_time = existing_item.get('analysis_time', '')
                        current_time = item.get('analysis_time', '')
                        if current_time > existing_time:
                            unique_items[unique_key] = item
            else:
                # Add new item if key doesn't exist
                unique_items[unique_key] = item
        
        # Convert back to list and sort by crawled_at first, then analysis_time in descending order
        unique_data = list(unique_items.values())
        unique_data.sort(key=lambda x: (x.get('crawled_at', datetime.min), x.get('analysis_time', '')), reverse=True)
        total = len(unique_data)
        
        # Apply pagination
        skip = (page - 1) * page_size
        paginated_data = unique_data[skip:skip + page_size]
        
        # Get all popularity data with ranks, use latest data (sort by crawled_at)
        popularity_data = list(self.popularity_collection.find().sort([
            ("crawled_at", DESCENDING),
            ("rank", ASCENDING)
        ]).limit(200))
        popularity_rank_map = {item['code']: item['rank'] for item in popularity_data}
        
        # Get all capital flow data with ranks, use latest data (sort by crawled_at)
        capital_flow_data = list(self.capital_flow_collection.find().sort([
            ("crawled_at", DESCENDING),
            ("main_flow", DESCENDING)
        ]).limit(200))
        capital_flow_rank_map = {item['code']: i+1 for i, item in enumerate(capital_flow_data)}
        
        # 导入同步数据库连接
        from app.core.database import get_mongo_db_sync
        
        # Add popularity and capital flow ranks to cross analysis data
        final_data = []
        for item in paginated_data:
            code = item.get('code')
            # Ensure code is not None to avoid validation errors
            if code is None:
                continue
            
            # Add rank regardless of top 100 limit, will show actual rank or None if not found
            item['popularity_rank'] = popularity_rank_map.get(code)
            item['capital_flow_rank'] = capital_flow_rank_map.get(code)
            
            # 判断是否涨停
            try:
                # 使用同步数据库查询获取行情数据
                db = get_mongo_db_sync()
                market_quotes_collection = db['market_quotes']
                quote = market_quotes_collection.find_one({'code': code})
                
                if quote and 'pct_chg' in quote and quote['pct_chg'] is not None:
                    # 判断是否涨停（普通股票10%，科创板20%，ST股票5%）
                    # 根据用户要求：涨幅大于9.5%即为涨停
                    if quote['pct_chg'] >= 9.5:
                        item['limit_up'] = True
                    else:
                        item['limit_up'] = False
                else:
                    item['limit_up'] = False
            except Exception as e:
                logger.error(f"获取股票{code}行情数据失败: {e}")
                item['limit_up'] = False
            
            final_data.append(item)
        
        return final_data, total
    
    def get_hot_experts_data(self, limit=15):
        """Get hot experts data for dashboard.
        
        Extract cross analysis data where both popularity_rank and capital_flow_rank have values (>0),
        sort by the sum of the latest values in ascending order, and extract the top N unique records.
        
        Args:
            limit: Number of records to return
        
        Returns:
            List of hot experts data
        """
        from datetime import datetime, timedelta
        
        # Get cross analysis data with popularity and capital flow ranks
        cross_data, _ = self.get_cross_analysis_data(page=1, page_size=1000)  # Get all data first
        
        # Filter data where both popularity_rank and capital_flow_rank are not None and > 0
        # Also ensure code is not None to avoid validation errors
        filtered_data = []
        for item in cross_data:
            code = item.get('code')
            popularity_rank = item.get('popularity_rank')
            capital_flow_rank = item.get('capital_flow_rank')
            
            if (code is not None and
                popularity_rank is not None and popularity_rank > 0 and
                capital_flow_rank is not None and capital_flow_rank > 0):
                # Calculate combined rank (sum of popularity and capital flow ranks)
                item['combined_rank'] = popularity_rank + capital_flow_rank
                filtered_data.append(item)
        
        # Sort by combined_rank in ascending order (smaller sum means better rank)
        filtered_data.sort(key=lambda x: x['combined_rank'])
        
        # Deduplicate by stock code, keep the record with the lowest combined_rank for each stock
        unique_stocks = {}
        for item in filtered_data:
            stock_code = item.get('code')
            if stock_code not in unique_stocks:
                unique_stocks[stock_code] = item
        
        # Convert back to list and sort again
        unique_data = list(unique_stocks.values())
        unique_data.sort(key=lambda x: x['combined_rank'])
        
        # Return top N records
        return unique_data[:limit]
    
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