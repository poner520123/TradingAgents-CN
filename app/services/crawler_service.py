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
    
    # 类变量，用于累积计数
    total_pages_crawled = 0
    total_saved = 0
    
    def __init__(self):
        # Initialize sync MongoDB connection using global sync client
        from app.core.database import get_mongo_db_sync
        self.db = get_mongo_db_sync()
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
        """Get date of recent workdays start.
        
        改进的交易日计算方法，考虑工作日和基本的节假日处理
        """
        today = datetime.now()
        workdays = 0
        start_date = today
        
        # 基本节假日列表（可以扩展或从外部数据源获取）
        # 示例：2025年主要节假日
        holidays = {
            (2025, 1, 1),  # 元旦
            (2025, 1, 2),
            (2025, 1, 3),
            (2025, 1, 28),  # 春节
            (2025, 1, 29),
            (2025, 1, 30),
            (2025, 1, 31),
            (2025, 2, 1),
            (2025, 2, 2),
            (2025, 4, 28),  # 劳动节
            (2025, 4, 29),
            (2025, 4, 30),
            (2025, 5, 1),
            (2025, 5, 2),
            (2025, 5, 27),  # 端午节
            (2025, 5, 28),
            (2025, 5, 29),
            (2025, 9, 29),  # 中秋节
            (2025, 9, 30),
            (2025, 10, 1),  # 国庆节
            (2025, 10, 2),
            (2025, 10, 3),
            (2025, 10, 4),
            (2025, 10, 5),
            (2025, 10, 6),
            (2025, 10, 7)
        }
        
        while workdays < days:
            start_date -= timedelta(days=1)
            # 检查是否是工作日且不是节假日
            is_weekday = start_date.weekday() < 5  # 0-4表示周一到周五
            is_holiday = (start_date.year, start_date.month, start_date.day) in holidays
            if is_weekday and not is_holiday:
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
        # Logic similar to original but with enhanced error handling and smart page adjustment
        from app.routers.websocket_notifications import send_notification_via_websocket
        import asyncio
        
        # 记录已获取的日期范围
        collected_dates = set()
        # 初始爬取页面范围
        current_start_page = start_page
        current_end_page = end_page
        # 标记是否已经覆盖了最近3个工作日
        has_covered_recent_workdays = False
        # 最大爬取页面数，防止无限循环
        MAX_PAGES = 200
        
        # 使用类变量累积计数，而不是局部变量
        # 每次调用时从类变量获取当前计数，而不是重新初始化
        if hasattr(self.__class__, 'total_pages_crawled'):
            # 已经初始化过，继续累积
            pass
        else:
            # 首次初始化
            self.__class__.total_pages_crawled = 0
            self.__class__.total_saved = 0
        
        # 获取最近3个工作日的日期集合
        recent_workdays = set()
        today = datetime.now().date()
        workdays = 0
        current_date = today
        while workdays < 3:
            # 使用改进的交易日判断，考虑节假日
            is_weekday = current_date.weekday() < 5  # 0-4 表示周一到周五
            # 检查是否是节假日（使用_get_recent_workdays中的节假日列表）
            holidays = {
                (2025, 1, 1), (2025, 1, 2), (2025, 1, 3),
                (2025, 1, 28), (2025, 1, 29), (2025, 1, 30), (2025, 1, 31), (2025, 2, 1), (2025, 2, 2),
                (2025, 4, 28), (2025, 4, 29), (2025, 4, 30), (2025, 5, 1), (2025, 5, 2),
                (2025, 5, 27), (2025, 5, 28), (2025, 5, 29),
                (2025, 9, 29), (2025, 9, 30),
                (2025, 10, 1), (2025, 10, 2), (2025, 10, 3), (2025, 10, 4), (2025, 10, 5), (2025, 10, 6), (2025, 10, 7)
            }
            is_holiday = (current_date.year, current_date.month, current_date.day) in holidays
            
            if is_weekday and not is_holiday:
                recent_workdays.add(current_date)
                workdays += 1
            current_date -= timedelta(days=1)
        
        logger.info(f"🎯 需要覆盖的最近3个工作日: {sorted(recent_workdays)}")
        
        # 发送开始爬取的通知
        async def send_start_notification():
            # 使用通知服务保存通知到数据库
            from app.services.notifications_service import get_notifications_service
            from app.models.notification import NotificationCreate
            from app.services.user_service import user_service
            
            notifications_service = get_notifications_service()
            
            # 获取管理员用户的实际ID
            admin_user = user_service.get_user_by_username("admin")
            admin_user_id = str(admin_user.id) if admin_user else "admin"
            
            notification_create = NotificationCreate(
                user_id=admin_user_id,
                type="system",
                title="爬虫任务开始",
                content=f"开始爬取页面 {current_start_page}-{current_end_page}，目标覆盖最近3个工作日",
                link="/analysis/cross-analysis",
                source="crawler",
                severity="info"
            )
            
            # 保存到数据库并通过WebSocket发送
            await notifications_service.create_and_publish(notification_create)
        
        # 使用asyncio.run发送通知，这是从同步代码运行异步函数的推荐方式
        try:
            asyncio.run(send_start_notification())
        except Exception as e:
            logger.error(f"❌ 发送爬虫开始通知失败: {e}")
        
        while not has_covered_recent_workdays and self.__class__.total_pages_crawled < MAX_PAGES:
            logger.info(f"🔍 开始爬取页面 {current_start_page}-{current_end_page}，目标覆盖最近3个工作日")
            
            for page in range(current_start_page, current_end_page + 1):
                if self.__class__.total_pages_crawled >= MAX_PAGES:
                    logger.warning(f"⚠️ 已达到最大爬取页面数 {MAX_PAGES}，停止爬取")
                    break
                    
                self.__class__.total_pages_crawled += 1
                # 发送开始爬取某页的通知
                msg = f"正在爬取第 {page} 页..."
                logger.info(msg)
                
                # 发送爬取页面通知到数据库和WebSocket
                async def send_page_start_notification():
                    from app.services.notifications_service import get_notifications_service
                    from app.models.notification import NotificationCreate
                    from app.services.user_service import user_service
                    
                    notifications_service = get_notifications_service()
                    
                    # 获取管理员用户的实际ID
                    admin_user = user_service.get_user_by_username("admin")
                    admin_user_id = str(admin_user.id) if admin_user else "admin"
                    
                    notification_create = NotificationCreate(
                        user_id=admin_user_id,
                        type="system",
                        title="爬虫进度",
                        content=msg,
                        link="/analysis/cross-analysis",
                        source="crawler",
                        severity="info"
                    )
                    
                    await notifications_service.create_and_publish(notification_create)
                
                try:
                    asyncio.run(send_page_start_notification())
                except Exception as e:
                    logger.error(f"❌ 发送爬虫进度通知失败: {e}")
                
                html = self.fetch_page(page)
                if html:
                    try:
                        data = self.parse_html(html)
                        if data:
                            try:
                                # 保存数据并获取具体的股票信息
                                saved = self.save_data(data)
                                self.__class__.total_saved += saved
                                
                                # 发送包含股票名称和代码的通知
                                async def send_save_notification():
                                    from app.services.notifications_service import get_notifications_service
                                    from app.models.notification import NotificationCreate
                                    from app.services.stock_map_service import stock_map_service
                                    from app.services.user_service import user_service
                                    
                                    notifications_service = get_notifications_service()
                                    
                                    # 获取管理员用户的实际ID
                                    admin_user = user_service.get_user_by_username("admin")
                                    admin_user_id = str(admin_user.id) if admin_user else "admin"
                                    
                                    # 处理最新的20条数据
                                    recent_stocks = data[:20]  # 只处理前20条
                                    
                                    for item in recent_stocks:
                                        stock_name = item['stock_name']
                                        stock_code = stock_map_service.get_code_by_name(stock_name)
                                        
                                        # 创建包含股票名称和代码的通知
                                        notification_create = NotificationCreate(
                                            user_id=admin_user_id,
                                            type="system",
                                            title="新股票数据爬取",
                                            content=f"已爬取: {stock_name} ({stock_code}) - {item['reason']}",
                                            link="/analysis/cross-analysis",
                                            source="crawler",
                                            severity="success"
                                        )
                                        
                                        await notifications_service.create_and_publish(notification_create)
                                    
                                    # 发送总进度通知
                                    total_msg = f"第 {page} 页: 成功保存 {saved} 条新数据"
                                    total_notification = NotificationCreate(
                                        user_id=admin_user_id,
                                        type="system",
                                        title="爬虫进度",
                                        content=total_msg,
                                        link="/analysis/cross-analysis",
                                        source="crawler",
                                        severity="info"
                                    )
                                    
                                    await notifications_service.create_and_publish(total_notification)
                                
                                try:
                                    asyncio.run(send_save_notification())
                                except Exception as e:
                                    logger.error(f"❌ 发送爬虫保存通知失败: {e}")
                                
                                # 收集已获取数据的日期
                                for item in data:
                                    time_str = item['time']
                                    try:
                                        ts = time_str.strip()
                                        if '-' in ts:
                                            fmt = '%Y-%m-%d %H:%M' if ':' in ts else '%Y-%m-%d'
                                            row_date = datetime.strptime(ts, fmt)
                                            # 只记录日期部分
                                            collected_dates.add(row_date.date())
                                        elif '/' in ts:
                                            fmt = '%Y/%m/%d %H:%M' if ':' in ts else '%Y/%m/%d'
                                            row_date = datetime.strptime(ts, fmt)
                                            # 只记录日期部分
                                            collected_dates.add(row_date.date())
                                        else:
                                            continue
                                    except ValueError:
                                        continue
                                    
                                    # 每次获取新数据后，立即检查是否已经覆盖了最近3个工作日
                                    if recent_workdays.issubset(collected_dates):
                                        has_covered_recent_workdays = True
                                        logger.info("✅ 已成功覆盖最近3个工作日的数据，提前结束爬取")
                                        break
                                
                                # 设置成功延迟
                                delay = get_random_delay("success")
                            except Exception as e:
                                logger.error(f"Page {page}: Error saving data - {type(e).__name__}: {str(e)}")
                                delay = get_random_delay("failure")
                                
                                # 发送保存失败通知
                                async def send_save_error_notification():
                                    from app.services.notifications_service import get_notifications_service
                                    from app.models.notification import NotificationCreate
                                    from app.services.user_service import user_service
                                    
                                    notifications_service = get_notifications_service()
                                    
                                    # 获取管理员用户的实际ID
                                    admin_user = user_service.get_user_by_username("admin")
                                    admin_user_id = str(admin_user.id) if admin_user else "admin"
                                    
                                    notification_create = NotificationCreate(
                                        user_id=admin_user_id,
                                        type="system",
                                        title="爬虫错误",
                                        content=f"第 {page} 页: 保存数据失败 - {str(e)}",
                                        link="/analysis/cross-analysis",
                                        source="crawler",
                                        severity="error"
                                    )
                                    
                                    await notifications_service.create_and_publish(notification_create)
                                
                                try:
                                    asyncio.run(send_save_error_notification())
                                except Exception as e:
                                    logger.error(f"❌ 发送爬虫错误通知失败: {e}")
                        else:
                            logger.warning(f"Page {page}: No data or parsing failed")
                            delay = get_random_delay("failure")
                        
                        # Add random pause if needed
                        if should_insert_random_pause():
                            random_pause = get_random_pause()
                            logger.info(f"🔄 Inserting random pause: {random_pause:.2f}s")
                            time.sleep(random_pause)
                        
                        # Add base delay
                        logger.info(f"⏱️ Waiting {delay:.2f}s before next request")
                        time.sleep(delay)
                    except Exception as e:
                        logger.error(f"Page {page}: Error parsing HTML - {type(e).__name__}: {str(e)}")
                        delay = get_random_delay("failure")
                        
                        # 发送解析错误通知
                        async def send_parse_error_notification():
                            from app.services.notifications_service import get_notifications_service
                            from app.models.notification import NotificationCreate
                            from app.services.user_service import user_service
                            
                            notifications_service = get_notifications_service()
                            
                            # 获取管理员用户的实际ID
                            admin_user = user_service.get_user_by_username("admin")
                            admin_user_id = str(admin_user.id) if admin_user else "admin"
                            
                            notification_create = NotificationCreate(
                                user_id=admin_user_id,
                                type="system",
                                title="爬虫错误",
                                content=f"第 {page} 页: 解析HTML失败 - {str(e)}",
                                link="/analysis/cross-analysis",
                                source="crawler",
                                severity="error"
                            )
                            
                            await notifications_service.create_and_publish(notification_create)
                        
                        try:
                            asyncio.run(send_parse_error_notification())
                        except Exception as e:
                            logger.error(f"❌ 发送爬虫错误通知失败: {e}")
                        
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
                    
                    # 发送获取页面失败通知
                    async def send_fetch_error_notification():
                        from app.services.notifications_service import get_notifications_service
                        from app.models.notification import NotificationCreate
                        from app.services.user_service import user_service
                        
                        notifications_service = get_notifications_service()
                        
                        # 获取管理员用户的实际ID
                        admin_user = user_service.get_user_by_username("admin")
                        admin_user_id = str(admin_user.id) if admin_user else "admin"
                        
                        notification_create = NotificationCreate(
                            user_id=admin_user_id,
                            type="system",
                            title="爬虫错误",
                            content=f"第 {page} 页: 获取页面失败",
                            link="/analysis/cross-analysis",
                            source="crawler",
                            severity="error"
                        )
                        
                        await notifications_service.create_and_publish(notification_create)
                    
                    try:
                        asyncio.run(send_fetch_error_notification())
                    except Exception as e:
                        logger.error(f"❌ 发送爬虫错误通知失败: {e}")
                    
                    time.sleep(delay)
                    continue
                
                # 如果已经覆盖了最近3个工作日，跳出循环
                if recent_workdays.issubset(collected_dates):
                    has_covered_recent_workdays = True
                    logger.info("✅ 已成功覆盖最近3个工作日的数据")
                    break
                
                # 检查是否已经爬取了足够多的页面但仍未覆盖所有最近3个工作日
                if total_pages_crawled >= MAX_PAGES:
                    logger.warning(f"⚠️ 已达到最大爬取页面数 {MAX_PAGES}，但仍未覆盖所有最近3个工作日")
                    break
                    
                # 智能调整下一轮爬取的页面范围
                # 如果当前轮次没有获取到新数据，增加页面步长
                pages_in_current_round = current_end_page - current_start_page + 1
                if len(collected_dates) == 0:
                    # 没有获取到任何数据，大幅增加爬取页面数
                    current_start_page = current_end_page + 1
                    current_end_page = current_start_page + pages_in_current_round * 2
                    logger.info(f"⚠️ 未获取到任何数据，大幅增加爬取页面数。新的爬取范围: {current_start_page}-{current_end_page}")
                else:
                    # 获取到了部分数据，适当增加爬取页面数
                    current_start_page = current_end_page + 1
                    current_end_page = current_start_page + pages_in_current_round
                    logger.info(f"⚠️ 已获取到部分数据，适当增加爬取页面数。新的爬取范围: {current_start_page}-{current_end_page}")
            
            logger.info(f"📅 最终收集的日期: {sorted(collected_dates)}")
            
            if recent_workdays.issubset(collected_dates):
                logger.info("✅ 成功覆盖所有最近3个工作日的数据")
            else:
                missing_days = recent_workdays - collected_dates
                logger.warning(f"⚠️ 未能覆盖所有最近3个工作日的数据，缺少: {sorted(missing_days)}")
                
            logger.info(f"✅ Crawl completed: Saved {self.__class__.total_saved} new records from {self.__class__.total_pages_crawled} pages")
            
            # 发送爬取完成通知
            async def send_completion_notification():
                from app.services.notifications_service import get_notifications_service
                from app.models.notification import NotificationCreate
                from app.services.user_service import user_service
                
                notifications_service = get_notifications_service()
                
                # 获取管理员用户的实际ID
                admin_user = user_service.get_user_by_username("admin")
                admin_user_id = str(admin_user.id) if admin_user else "admin"
                
                status = "success" if self.__class__.total_saved > 0 else "warning"
                notification_create = NotificationCreate(
                    user_id=admin_user_id,
                    type="system",
                    title="爬虫任务完成",
                    content=f"爬虫任务完成，共爬取 {self.__class__.total_pages_crawled} 页，保存 {self.__class__.total_saved} 条新数据",
                    link="/analysis/cross-analysis",
                    source="crawler",
                    severity=status
                )
                
                await notifications_service.create_and_publish(notification_create)
            
            try:
                asyncio.run(send_completion_notification())
            except Exception as e:
                logger.error(f"❌ 发送爬虫完成通知失败: {e}")
        
        return self.__class__.total_saved
