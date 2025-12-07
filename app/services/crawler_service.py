import requests
from bs4 import BeautifulSoup
import urllib3
import time
import random
import logging
from datetime import datetime, timedelta
from pymongo import MongoClient, ASCENDING, DESCENDING
from app.core.config import settings
from app.core.crawler_config import (
    BASE_URL, get_random_headers, get_random_proxy, build_proxy_dict,
    get_random_delay, should_insert_random_pause, get_random_pause,
    get_mandatory_pause, DELAY_CONFIG, EXCEPTION_CONFIG,
    get_exponential_backoff_delay, RATE_LIMIT_CONFIG, get_proxy_rate_limiter,
    get_randomized_params, PARAM_RANDOMIZATION_CONFIG
)

# Configure logging
logger = logging.getLogger(__name__)

# Suppress InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class CrawlerService:
    """Handles fetching and parsing of stock prediction pages with session management."""
    
    def __init__(self):
        # Initialize sync MongoDB connection
        self.client = MongoClient(settings.MONGO_URI)
        self.db = self.client[settings.MONGO_DB]
        self.collection = self.db.crawler_data
        
        self._init_db()
        self._init_session()
        self._init_concepts()
        
        # Session lifetime configuration
        self.session_max_lifetime = timedelta(minutes=10)
        self.consecutive_errors = 0
        self.max_consecutive_errors = 3
        self.reset_cooldown = timedelta(seconds=30)
    
    def _init_db(self):
        """Initialize database indexes."""
        try:
            # Create unique index for deduping
            self.collection.create_index([
                ("user_name", ASCENDING),
                ("stock_name", ASCENDING),
                ("time", ASCENDING)
            ], unique=True)
            # Index for sorting by time
            self.collection.create_index([("time", DESCENDING)])
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")

    def _init_session(self):
        """Initialize a new requests session with proper headers."""
        self.session = requests.Session()
        session_headers = get_random_headers()
        self.session.headers.update(session_headers)
        self.session.verify = False
        self.session.timeout = 15
        self.session_creation_time = datetime.now()
        logger.info("🔄 Initialized new browser session")
    
    def _init_concepts(self):
        """Initialize concept mapping."""
        from app.core.crawler_concepts import CONCEPT_MAPPING, LAST_UPDATE_TIME, UPDATE_INTERVAL
        self.concept_mapping = CONCEPT_MAPPING.copy() # Make a copy to avoid modifying global state if imported elsewhere
        self.last_update_time = LAST_UPDATE_TIME
        self.update_interval = UPDATE_INTERVAL
        self._check_concept_update()
    
    def _check_concept_update(self):
        """Check if concept mapping needs to be updated."""
        # Simple implementation for now
        pass
    
    def is_valid_stock_name(self, stock_name):
        """Check if the given name is a valid stock name."""
        import re
        invalid_patterns = [
            r'^[a-zA-Z0-9_]+$',
            r'^[\u4e00-\u9fa5]{1,2}$',
            r'^[\u4e00-\u9fa5]*[0-9]+[\u4e00-\u9fa5]*$',
            r'^[\u4e00-\u9fa5]*[a-zA-Z]+[\u4e00-\u9fa5]*$'
        ]
        
        for pattern in invalid_patterns:
            if re.match(pattern, stock_name):
                return False
        
        if len(stock_name) < 3 or len(stock_name) > 4:
            return False
            
        return True

    def _should_reset_session(self):
        """Check if session should be reset."""
        if not hasattr(self, 'session_creation_time'):
            return True
            
        if datetime.now() - self.session_creation_time > self.session_max_lifetime:
            logger.info(f"⏰ Session expired ({self.session_max_lifetime.seconds}s), resetting")
            return True
            
        if self.consecutive_errors >= self.max_consecutive_errors:
            if hasattr(self, 'last_reset_time'):
                if datetime.now() - self.last_reset_time > self.reset_cooldown:
                    logger.warning(f"⚠️ Too many errors ({self.consecutive_errors}), resetting session")
                    return True
            else:
                logger.warning(f"⚠️ Too many errors ({self.consecutive_errors}), resetting session")
                return True
                
        return False
    
    def _reset_session(self):
        """Reset the session."""
        logger.info("🔄 Resetting session")
        if hasattr(self, 'session'):
            try:
                self.session.close()
            except:
                pass
        self._init_session()
        self.consecutive_errors = 0
        self.last_reset_time = datetime.now()
    
    def clear_cookies(self):
        self.session.cookies.clear()
        logger.info("🍪 Cookies cleared")

    def fetch_page(self, page_num):
        """Fetch a specific page."""
        if self._should_reset_session():
            self._reset_session()
            
        headers = get_random_headers()
        url_base = BASE_URL.format(page_num)
        max_retries = EXCEPTION_CONFIG['max_retries']
        retries = 0
        
        proxy = get_random_proxy()
        proxies = build_proxy_dict(proxy) if proxy else None
        
        if proxy:
            logger.info(f"🔀 Using proxy: {proxy.split('@')[-1] if '@' in proxy else proxy}")
        
        while retries <= max_retries:
            if RATE_LIMIT_CONFIG['use_rate_limiting']:
                rate_limiter = get_proxy_rate_limiter(proxy)
                success, wait_time = rate_limiter.consume()
                if wait_time > 0:
                    logger.info(f"⏱️ Rate limit: waiting {wait_time:.2f}s")
                if not success:
                    time.sleep(1)
                    continue
            
            try:
                params = get_randomized_params()
                if params and PARAM_RANDOMIZATION_CONFIG['use_randomization']:
                    import urllib.parse
                    query_string = urllib.parse.urlencode(params)
                    url = f"{url_base}?{query_string}" if '?' not in url_base else f"{url_base}&{query_string}"
                else:
                    url = url_base
                
                response = self.session.get(url, headers=headers, proxies=proxies, timeout=15)
                response.encoding = response.apparent_encoding
                
                if response.status_code == 200:
                    self.consecutive_errors = 0
                    return response.text
                else:
                    logger.warning(f"❌ Failed to fetch page {page_num}: {response.status_code}")
                    self.consecutive_errors += 1
                    
                    if response.status_code in EXCEPTION_CONFIG['retry_status_codes'] and retries < max_retries:
                        if response.status_code in [403, 429, 502, 503]:
                            self._reset_session()
                            self.clear_cookies()
                            proxy = get_random_proxy()
                            proxies = build_proxy_dict(proxy) if proxy else None
                        
                        retry_delay = get_exponential_backoff_delay(retries, 
                            backoff_factor=EXCEPTION_CONFIG['backoff_factor'],
                            max_delay=EXCEPTION_CONFIG['max_backoff_time'])
                        time.sleep(retry_delay)
                        retries += 1
                        continue
                    return None
                    
            except Exception as e:
                logger.error(f"❌ Error fetching page {page_num}: {type(e).__name__}: {str(e)}")
                self.consecutive_errors += 1
                
                # Check for fatal/transient errors (logic simplified from original)
                is_fatal = any(isinstance(e, t) for t in EXCEPTION_CONFIG['fatal_errors'])
                if is_fatal:
                    break
                    
                is_transient = any(isinstance(e, t) for t in EXCEPTION_CONFIG['transient_errors'])
                if is_transient or isinstance(e, (requests.ConnectionError, ConnectionResetError)):
                    self._reset_session()
                    self.clear_cookies()
                    proxy = get_random_proxy()
                    proxies = build_proxy_dict(proxy) if proxy else None
                
                should_retry = not is_fatal
                if should_retry and retries < max_retries:
                    retry_delay = get_exponential_backoff_delay(retries,
                        backoff_factor=EXCEPTION_CONFIG['backoff_factor'],
                        max_delay=EXCEPTION_CONFIG['max_backoff_time'])
                    time.sleep(retry_delay)
                    retries += 1
                    continue
                return None
        return None

    def get_stock_concepts(self, stock_name):
        """Get stock concepts."""
        if not self.is_valid_stock_name(stock_name):
            return '暂未分类'
        
        if stock_name in self.concept_mapping:
            return self.concept_mapping[stock_name]
            
        # Try Baidu search fallback (simplified)
        try:
            import urllib.parse
            encoded_name = urllib.parse.quote(stock_name)
            url = f"https://gushitong.baidu.com/stock/ab-" + encoded_name
            response = requests.get(url, timeout=5, verify=False)
            response.encoding = 'utf-8'
            if response.status_code == 200:
                import re
                match = re.search(r'概念：([^<]+)', response.text)
                if match:
                    concepts = match.group(1).strip()
                    concept_list = concepts.split(',')[:5]
                    concept_str = ','.join(concept_list)
                    self.concept_mapping[stock_name] = concept_str
                    return concept_str
        except:
            pass
        return '暂未分类'

    def _get_recent_workdays(self, days=3):
        """Get date of recent workdays start."""
        today = datetime.now()
        workdays = 0
        start_date = today
        while workdays < days:
            start_date -= timedelta(days=1)
            if start_date.weekday() < 5:
                workdays += 1
        return start_date

    def parse_html(self, html):
        """Parse HTML and extract stock data."""
        if not html:
            return []
            
        soup = BeautifulSoup(html, 'html.parser')
        data_list = []
        target_table = None
        
        for table in soup.find_all('table'):
            header_row = table.find('tr')
            if header_row and "伏击人" in header_row.get_text():
                target_table = table
                break
        
        if not target_table:
            logger.warning("Target table not found in HTML")
            return []
            
        rows = target_table.find_all('tr')
        if len(rows) <= 1:
            return []
            
        start_date = self._get_recent_workdays(3)
        
        for row in rows[1:]:
            cols = row.find_all('td')
            if len(cols) < 11:
                continue
                
            try:
                user_name = cols[0].get_text(strip=True)
                stock_name = cols[3].get_text(strip=True)
                time_str = cols[5].get_text(strip=True)
                
                if not stock_name or not user_name or not time_str:
                    continue
                    
                # Date parsing logic
                try:
                    ts = time_str.strip()
                    if '-' in ts:
                        fmt = '%Y-%m-%d %H:%M' if ':' in ts else '%Y-%m-%d'
                    elif '/' in ts:
                        fmt = '%Y/%m/%d %H:%M' if ':' in ts else '%Y/%m/%d'
                    else:
                        continue
                    row_date = datetime.strptime(ts, fmt)
                except ValueError:
                    continue
                
                # Filter by date (only keep recent)
                if row_date < start_date:
                    continue
                    
                concepts = self.get_stock_concepts(stock_name)
                
                data_list.append({
                    'user_name': user_name,
                    'success_count': cols[1].get_text(strip=True),
                    'success_rate': cols[2].get_text(strip=True),
                    'stock_name': stock_name,
                    'reason': cols[4].get_text(strip=True),
                    'time': time_str,
                    'price': cols[6].get_text(strip=True),
                    'current_price': cols[7].get_text(strip=True),
                    'increase': cols[8].get_text(strip=True),
                    'limit_up': cols[9].get_text(strip=True),
                    'limit_up_date': cols[10].get_text(strip=True),
                    'concepts': concepts
                })
            except Exception as e:
                logger.warning(f"Error parsing row: {e}")
                continue
                
        return data_list

    def save_data(self, data_list):
        """Save data to MongoDB with upsert."""
        if not data_list:
            return 0
            
        count = 0
        # Import here to avoid circular import
        from app.services.stock_map_service import stock_map_service
        
        for item in data_list:
            try:
                # Add timestamp
                item['crawled_at'] = datetime.utcnow()
                
                # Add stock_code to item
                if 'stock_name' in item:
                    stock_code = stock_map_service.get_code_by_name(item['stock_name'])
                    item['stock_code'] = stock_code
                
                # Upsert based on unique keys
                result = self.collection.update_one(
                    {
                        "user_name": item['user_name'],
                        "stock_name": item['stock_name'],
                        "time": item['time']
                    },
                    {"$set": item},
                    upsert=True
                )
                
                # Perform count if upserted (matched_count == 0 means new document)
                if result.upserted_id:
                    count += 1
            except Exception as e:
                logger.error(f"Error saving data: {e}")
        return count
    
    def update_historical_stock_codes(self):
        """更新历史爬虫数据中的股票代码"""
        logger.info("开始更新历史爬虫数据中的股票代码")
        
        # Import here to avoid circular import
        from app.services.stock_map_service import stock_map_service
        
        # 获取所有缺少stock_code的文档
        cursor = self.collection.find({"stock_code": {"$exists": False}})
        total = self.collection.count_documents({"stock_code": {"$exists": False}})
        updated = 0
        
        if total == 0:
            logger.info("没有需要更新的历史数据")
            return {"total": 0, "updated": 0}
        
        logger.info(f"找到 {total} 条缺少stock_code的历史数据，开始更新")
        
        # 按批次处理，每批100条
        batch_size = 100
        batch = []
        
        for doc in cursor:
            batch.append(doc)
            
            if len(batch) == batch_size:
                # 批量获取股票代码
                names = [d['stock_name'] for d in batch]
                code_map = stock_map_service.get_codes_by_names(names)
                
                # 更新批次中的文档
                for d in batch:
                    if d['stock_name'] in code_map:
                        self.collection.update_one(
                            {"_id": d["_id"]},
                            {"$set": {"stock_code": code_map[d['stock_name']]}}
                        )
                        updated += 1
                
                batch = []
        
        # 处理剩余的文档
        if batch:
            names = [d['stock_name'] for d in batch]
            code_map = stock_map_service.get_codes_by_names(names)
            
            for d in batch:
                if d['stock_name'] in code_map:
                    self.collection.update_one(
                        {"_id": d["_id"]},
                        {"$set": {"stock_code": code_map[d['stock_name']]}}
                    )
                    updated += 1
        
        logger.info(f"历史爬虫数据股票代码更新完成，共处理 {total} 条，成功更新 {updated} 条")
        return {"total": total, "updated": updated}

    def get_data(self, page=1, page_size=20):
        """Retrieve data for API."""
        skip = (page - 1) * page_size
        total = self.collection.count_documents({})
        cursor = self.collection.find().sort("time", DESCENDING).skip(skip).limit(page_size)
        data = list(cursor)
        # Convert ObjectId to string and process data types
        for d in data:
            if '_id' in d:
                d['_id'] = str(d['_id'])
            
            # Ensure success_count is an integer
            if 'success_count' in d:
                try:
                    d['success_count'] = int(d['success_count'])
                except (ValueError, TypeError):
                    d['success_count'] = 0
        return data, total

    def crawl_pages(self, start_page, end_page, force=False):
        """Crawl pages with enhanced thread stability."""
        # Logic similar to original but with enhanced error handling
        total_saved = 0
        
        for page in range(start_page, end_page + 1):
            try:
                logger.info(f"HTML Crawling page {page}...")
                html = self.fetch_page(page)
                if html:
                    try:
                        data = self.parse_html(html)
                        if data:
                            try:
                                saved = self.save_data(data)
                                total_saved += saved
                                logger.info(f"Page {page}: Saved {saved} new records")
                                delay = get_random_delay("success")
                            except Exception as e:
                                logger.error(f"Page {page}: Error saving data - {type(e).__name__}: {str(e)}")
                                delay = get_random_delay("failure")
                        else:
                            logger.warning(f"Page {page}: No data or parsing failed")
                            delay = get_random_delay("failure")
                    except Exception as e:
                        logger.error(f"Page {page}: Error parsing HTML - {type(e).__name__}: {str(e)}")
                        delay = get_random_delay("failure")
                    
                    # Add random pause if needed
                    if should_insert_random_pause():
                        random_pause = get_random_pause()
                        logger.info(f"🔄 Inserting random pause: {random_pause:.2f}s")
                        time.sleep(random_pause)
                    
                    # Add base delay
                    logger.info(f"⏱️ Waiting {delay:.2f}s before next request")
                    time.sleep(delay)
                else:
                    logger.error(f"Page {page}: Failed to fetch")
                    delay = get_random_delay("failure")
                    time.sleep(delay)
                    
            except Exception as e:
                logger.error(f"❌ Fatal error on page {page} - {type(e).__name__}: {str(e)}")
                # Add longer delay on fatal errors
                fatal_delay = random.uniform(10, 15)
                logger.info(f"⚠️ Fatal error occurred, waiting {fatal_delay:.2f}s before continuing")
                time.sleep(fatal_delay)
                # Reset session to avoid persistent issues
                self._reset_session()
                continue
        
        logger.info(f"✅ Crawl completed: Saved {total_saved} new records from pages {start_page}-{end_page}")
        
        # 通过 WebSocket 发送通知给前端，让前端刷新数据
        try:
            from app.routers.websocket_notifications import send_notification_via_websocket
            import asyncio
            
            # 发送爬虫完成通知
            notification = {
                "id": f"crawler-{int(time.time())}",
                "title": "爬虫完成",
                "content": f"成功爬取 {total_saved} 条新数据",
                "type": "crawler",
                "link": "/analysis/crawler",
                "source": "crawler",
                "created_at": datetime.utcnow().isoformat(),
                "status": "unread"
            }
            
            # 使用异步方式发送通知
            loop = asyncio.get_event_loop()
            loop.run_until_complete(send_notification_via_websocket("admin", notification))
            
            logger.info("📤 WebSocket 通知发送成功")
        except Exception as e:
            logger.error(f"❌ 发送 WebSocket 通知失败: {type(e).__name__}: {str(e)}")
        
        return total_saved
