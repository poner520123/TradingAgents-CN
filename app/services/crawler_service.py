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
    BASE_URL, EXPERT_URL, CRAWL_TEMPLATES, get_random_headers, get_random_proxy, build_proxy_dict,
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
        # 数据库初始化推迟到首次使用（避免模块导入阶段的网络 I/O）
        self._db_initialized = False
        self.db = get_mongo_db_sync()
        self.collection = self.db.crawler_data
        
        self._init_session()
        self._init_concepts()
        
        # Session lifetime configuration
        self.session_max_lifetime = timedelta(minutes=10)
        self.consecutive_errors = 0
        self.max_consecutive_errors = 3
        self.reset_cooldown = timedelta(seconds=30)
        
        # 添加任务执行锁，确保同一时间只有一个爬虫任务在执行
        self.is_running = False
    
    def _init_db(self):
        """Initialize database indexes."""
        # 惰性初始化守卫：只在首次访问数据库时执行一次
        if getattr(self, "_db_initialized", False):
            return
        self._db_initialized = True
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

    def fetch_page(self, page_num, url_template=None):
        """Fetch a specific page.

        Args:
            page_num: 页面号
            url_template: URL 模板（可选，默认用 BASE_URL；用于同时爬伏击人+专家两个模板）
        """
        if self._should_reset_session():
            self._reset_session()
            
        headers = get_random_headers()
        template = url_template or BASE_URL
        url_base = template.format(page_num)
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
            if header_row and ("伏击人" in header_row.get_text()
                               or "发现人" in header_row.get_text()):
                target_table = table
                break
        
        if not target_table:
            logger.warning("Target table not found in HTML")
            return []
            
        rows = target_table.find_all('tr')
        if len(rows) <= 1:
            return []
            
        start_date = self._get_recent_workdays(3)
        
        # 导入ST过滤服务（延迟导入避免循环依赖）
        from app.services.st_filter_service import st_filter_service
        
        # 统计变量
        total_parsed = 0
        st_filtered_during_parse = 0
        
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
                    
                # 【前置过滤】在解析阶段就过滤ST股票（第一步过滤）
                if st_filter_service.is_st_stock_by_name(stock_name):
                    st_filtered_during_parse += 1
                    logger.debug(f"🔴 [前置过滤] ST股票被排除: {stock_name}")
                    continue
                    
                total_parsed += 1
                    
                # Date parsing logic
                try:
                    ts = time_str.strip()
                    # Replace multiple spaces with single space to handle inconsistent formatting
                    ts = ' '.join(ts.split())
                    if '-' in ts:
                        fmt = '%Y-%m-%d %H:%M' if ':' in ts else '%Y-%m-%d'
                    elif '/' in ts:
                        fmt = '%Y/%m/%d %H:%M' if ':' in ts else '%Y/%m/%d'
                    else:
                        continue
                    row_date = datetime.strptime(ts, fmt)
                except ValueError:
                    logger.warning(f"Failed to parse date: {repr(time_str)}")
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
        
        if st_filtered_during_parse > 0:
            logger.info(f"🔍 解析阶段共过滤 {st_filtered_during_parse} 只ST股票")
                
        return data_list

    def save_data(self, data_list):
        """Save data to MongoDB with upsert.

        过滤链：
          1. ST 股票（parse_html 前置过滤 + save_data 二次校验）
          2. 板块过滤（仅主板 600/601/603/605/000/001/002/003 + 创业板 300/301）
             排除 科创板 688、北交所 4/8/92 开头、基金 ETF 转债 5xxxxx/1xxxxx
        """
        self._init_db()
        if not data_list:
            return 0

        # 导入ST过滤服务（延迟导入避免循环依赖）
        from app.services.st_filter_service import st_filter_service

        # 【二次校验】检查是否存在遗漏的ST股票（第二步过滤）
        validation_result = st_filter_service.filter_st_stocks(data_list)
        filtered_data = validation_result['filtered']
        removed_count = validation_result['removed_count']

        if removed_count > 0:
            logger.info(f"🔍 [二次校验] 发现并过滤 {removed_count} 只遗漏的ST股票")

        count = 0
        excluded_board = 0
        # Import here to avoid circular import
        from app.services.stock_map_service import stock_map_service

        for item in filtered_data:
            try:
                # Add timestamp
                item['crawled_at'] = datetime.utcnow()

                # Add stock_code to item
                if 'stock_name' in item:
                    stock_code = stock_map_service.get_code_by_name(item['stock_name'])
                    item['stock_code'] = stock_code

                    # 【板块过滤】仅保留主板和创业板，排除科创板/北交所/基金ETF转债
                    if stock_code and not self._is_main_board_or_chinext(stock_code):
                        excluded_board += 1
                        logger.debug(
                            f"🟡 [板块过滤] 非主板/创业板排除: {item['stock_name']} ({stock_code})"
                        )
                        continue

                    # 【最终过滤】在存储前再次检查ST状态（第三步过滤）
                    if st_filter_service.is_st_stock_by_code(stock_code):
                        logger.warning(f"🔴 [最终过滤] 通过股票代码检测到ST股票: {item['stock_name']} ({stock_code})")
                        st_filter_service.log_filter([{
                            "stock_name": item['stock_name'],
                            "stock_code": stock_code,
                            "reason": "最终过滤-代码检测",
                            "filter_time": datetime.now(),
                            "original_data": item
                        }])
                        continue
                
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
        if excluded_board > 0:
            logger.info(f"🟡 [板块过滤] 共排除 {excluded_board} 只非主板/创业板股票")
        return count

    @staticmethod
    def _is_main_board_or_chinext(stock_code: str) -> bool:
        """判断股票代码是否属于主板或创业板（是返回 True）。

        保留：600/601/603/605 沪市主板、000/001/002/003 深市主板、300/301 创业板。
        排除：688 科创板、4xxxx/8xxxx/92xxx 北交所、5xxxxx 基金 ETF、1xxxxx 转债等。
        stock_code 为空或非 6 位数字 → 视为不属于（保守排除）。
        """
        code = str(stock_code or "").strip()
        if len(code) != 6 or not code.isdigit():
            return False
        first = code[0]
        # 沪市主板：600/601/603/605
        if code.startswith(("600", "601", "603", "605")):
            return True
        # 深市主板：000/001/002/003
        if code.startswith(("000", "001", "002", "003")):
            return True
        # 创业板：300/301
        if code.startswith(("300", "301")):
            return True
        # 其他：688 科创板、4xx 北交、8xx 北交、92x 北交、5xx 基金 ETF、1xx 转债等一律排除
        return False
    
    def update_historical_stock_codes(self):
        """更新历史爬虫数据中的股票代码"""
        self._init_db()
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

    def get_top_users_by_success_rate(self, limit=30):
        """Get top users by success rate."""
        self._init_db()
        from datetime import datetime, timedelta
        
        # Calculate 1 month ago
        one_month_ago = datetime.now() - timedelta(days=30)
        one_month_ago_str = one_month_ago.strftime('%Y-%m-%d')
        
        pipeline = [
            # Filter by time (last month)
            {
                '$match': {
                    '$expr': {
                        '$gte': [
                            {'$substr': ['$time', 0, 10]},
                            one_month_ago_str
                        ]
                    }
                }
            },
            # Extract numeric success rate
            {
                '$project': {
                    'user_name': 1,
                    'success_rate': 1,
                    'success_rate_num': {
                        '$toDouble': {'$replaceOne': {'input': '$success_rate', 'find': '%', 'replacement': ''}}
                    }
                }
            },
            # Group by user and get max success rate and count
            {
                '$group': {
                    '_id': '$user_name',
                    'max_success_rate': {'$max': '$success_rate_num'},
                    'success_rate_str': {'$first': '$success_rate'},
                    'record_count': {'$sum': 1}
                }
            },
            # Filter users with at least 10 records
            {'$match': {'record_count': {'$gte': 10}}},
            # Sort by success rate descending
            {'$sort': {'max_success_rate': DESCENDING}},
            # Limit to top N users
            {'$limit': limit},
            # Project to desired format
            {
                '$project': {
                    '_id': 0,
                    'user_name': '$_id',
                    'success_rate': '$success_rate_str',
                    'success_rate_num': '$max_success_rate',
                    'record_count': 1
                }
            }
        ]
        
        cursor = self.collection.aggregate(pipeline)
        users = list(cursor)
        
        # Convert success_rate_num to float for frontend
        for user in users:
            if 'success_rate_num' in user:
                user['success_rate_num'] = float(user['success_rate_num'])
        
        return users

    def get_data(self, page=1, page_size=20, user_name=None, stock_name=None, stock_code=None, min_success_rate=None, reason=None, start_date=None, end_date=None):
        """Retrieve data for API with filtering."""
        self._init_db()
        # Build query filter
        query = {}
        
        # Filter by user_name
        if user_name:
            query['user_name'] = {'$regex': user_name, '$options': 'i'}
        
        # Filter by stock_name
        if stock_name:
            query['stock_name'] = {'$regex': stock_name, '$options': 'i'}
        
        # Filter by stock_code
        if stock_code:
            query['stock_code'] = {'$regex': stock_code, '$options': 'i'}
        
        # Filter by reason
        if reason:
            query['reason'] = {'$regex': reason, '$options': 'i'}
        
        # Filter by date range
        if start_date or end_date:
            # 使用正则表达式匹配日期部分
            # 数据库中的time格式为"YYYY-MM-DD  HH:MM"（注意两个空格）
            if min_success_rate is not None:
                # 如果使用聚合管道，需要在聚合中处理日期筛选
                pass
            else:
                # 使用正则表达式匹配日期部分
                if start_date and end_date:
                    # 日期范围查询 - 使用正则表达式匹配日期部分
                    query['$and'] = [
                        {'time': {'$regex': f'^{start_date}'}},
                        {'time': {'$regex': f'^{end_date}'}}
                    ]
                elif start_date:
                    # 只查询开始日期的数据
                    query['time'] = {'$regex': f'^{start_date}'}
                elif end_date:
                    # 只查询结束日期的数据
                    query['time'] = {'$regex': f'^{end_date}'}
        
        # Calculate pagination
        skip = (page - 1) * page_size
        
        # Check if we need to use aggregation for success_rate filtering
        if min_success_rate is not None:
            # Use aggregation to convert string to number for comparison
            # Since success_rate is stored as string (e.g., "85%"), we need to extract numeric value
            pipeline = []
            
            # Add match stage for other filters first
            if query:
                pipeline.append({'$match': query})
            
            # Add date range filter if needed
            if start_date or end_date:
                date_conditions = []
                
                if start_date:
                    date_conditions.append({
                        '$expr': {
                            '$gte': [
                                {'$substr': ['$time', 0, 10]},
                                start_date
                            ]
                        }
                    })
                
                if end_date:
                    date_conditions.append({
                        '$expr': {
                            '$lte': [
                                {'$substr': ['$time', 0, 10]},
                                end_date
                            ]
                        }
                    })
                
                if date_conditions:
                    pipeline.append({'$match': {'$and': date_conditions}})
            
            # Add match stage for success_rate using aggregation
            pipeline.extend([
                {
                    '$project': {
                        'stock_code': 1,
                        'stock_name': 1,
                        'user_name': 1,
                        'success_rate': 1,
                        'concepts': 1,
                        'reason': 1,
                        'time': 1,
                        'price': 1,
                        'success_count': 1,
                        # Extract numeric value from success_rate string
                        'success_rate_num': {
                            '$toDouble': {'$replaceOne': {'input': '$success_rate', 'find': '%', 'replacement': ''}}
                        }
                    }
                },
                {
                    '$match': {
                        'success_rate_num': {'$gte': min_success_rate}
                    }
                },
                {
                    '$sort': {'time': DESCENDING}
                },
                {
                    '$skip': skip
                },
                {
                    '$limit': page_size
                }
            ])
            
            # Execute aggregation pipeline
            cursor = self.collection.aggregate(pipeline)
            data = list(cursor)
            
            # Get total count with filters including success_rate
            count_pipeline = []
            if query:
                count_pipeline.append({'$match': query})
            
            # Add date range filter to count pipeline if needed
            if start_date or end_date:
                date_conditions = []
                
                if start_date:
                    date_conditions.append({
                        '$expr': {
                            '$gte': [
                                {'$substr': ['$time', 0, 10]},
                                start_date
                            ]
                        }
                    })
                
                if end_date:
                    date_conditions.append({
                        '$expr': {
                            '$lte': [
                                {'$substr': ['$time', 0, 10]},
                                end_date
                            ]
                        }
                    })
                
                if date_conditions:
                    count_pipeline.append({'$match': {'$and': date_conditions}})
            
            count_pipeline.extend([
                {
                    '$project': {
                        'success_rate_num': {
                            '$toDouble': {'$replaceOne': {'input': '$success_rate', 'find': '%', 'replacement': ''}}
                        }
                    }
                },
                {
                    '$match': {
                        'success_rate_num': {'$gte': min_success_rate}
                    }
                },
                {
                    '$count': 'total'
                }
            ])
            
            count_result = list(self.collection.aggregate(count_pipeline))
            total = count_result[0]['total'] if count_result else 0
            
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
                
                # Keep success_rate as string to match model definition
                if 'success_rate' in d:
                    try:
                        # Ensure it's a string
                        d['success_rate'] = str(d['success_rate'])
                    except (ValueError, TypeError):
                        d['success_rate'] = "0.0%"
                
                # Remove the temporary field
                d.pop('success_rate_num', None)
            
            return data, total
        else:
            # Use regular find for faster performance when no success_rate filter
            # Get total count with filters
            total = self.collection.count_documents(query)
            
            # Fetch data with filters and pagination
            cursor = self.collection.find(query).sort("time", DESCENDING).skip(skip).limit(page_size)
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
                
                # Keep success_rate as string to match model definition
                if 'success_rate' in d:
                    try:
                        # Ensure it's a string
                        d['success_rate'] = str(d['success_rate'])
                    except (ValueError, TypeError):
                        d['success_rate'] = "0.0%"
            
            return data, total

    def get_stock_summary(self, stock_name=None, stock_code=None):
        """Get summary statistics for a specific stock."""
        self._init_db()
        query = {}
        
        if stock_name:
            query['stock_name'] = {'$regex': stock_name, '$options': 'i'}
        if stock_code:
            query['stock_code'] = {'$regex': stock_code, '$options': 'i'}
        
        # Aggregation pipeline for summary
        pipeline = [
            {'$match': query},
            {
                '$group': {
                    '_id': None,
                    'total_records': {'$sum': 1},
                    'avg_success_rate': {
                        '$avg': {
                            '$toDouble': {'$replaceOne': {'input': '$success_rate', 'find': '%', 'replacement': ''}}
                        }
                    },
                    'min_time': {'$min': '$time'},
                    'max_time': {'$max': '$time'},
                    'unique_users': {'$addToSet': '$user_name'}
                }
            }
        ]
        
        cursor = self.collection.aggregate(pipeline)
        result = list(cursor)
        
        if result:
            summary = result[0]
            return {
                'stock_name': stock_name,
                'stock_code': stock_code,
                'total_records': summary.get('total_records', 0),
                'avg_success_rate': round(summary.get('avg_success_rate', 0), 2),
                'unique_users_count': len(summary.get('unique_users', [])),
                'date_range': {
                    'start': summary.get('min_time'),
                    'end': summary.get('max_time')
                }
            }
        else:
            return {
                'stock_name': stock_name,
                'stock_code': stock_code,
                'total_records': 0,
                'avg_success_rate': 0,
                'unique_users_count': 0,
                'date_range': {
                    'start': None,
                    'end': None
                }
            }
    
    def get_unique_stocks(self, keyword=None, limit=50):
        """Get unique stock list from crawler data."""
        self._init_db()
        pipeline = []
        
        if keyword:
            pipeline.append({
                '$match': {
                    '$or': [
                        {'stock_name': {'$regex': keyword, '$options': 'i'}},
                        {'stock_code': {'$regex': keyword, '$options': 'i'}}
                    ]
                }
            })
        
        pipeline.extend([
            {
                '$group': {
                    '_id': {
                        'stock_name': '$stock_name',
                        'stock_code': '$stock_code'
                    },
                    'count': {'$sum': 1},
                    'latest_time': {'$max': '$time'}
                }
            },
            {'$sort': {'count': DESCENDING}},
            {'$limit': limit},
            {
                '$project': {
                    '_id': 0,
                    'stock_name': '$_id.stock_name',
                    'stock_code': '$_id.stock_code',
                    'record_count': '$count',
                    'latest_time': '$latest_time'
                }
            }
        ])
        
        cursor = self.collection.aggregate(pipeline)
        stocks = list(cursor)
        
        return stocks

    def crawl_pages(self, start_page, end_page, force=False):
        """Crawl pages from BOTH templates (伏击人 + 专家), matching stockmonitor口径.

        每轮依次爬 fjzt-1.html(伏击人) 和 fjzt-2.html(专家)，各取 [start_page, end_page] 范围。
        与 stockmonitor 的 WebTailer 双模板轮询保持一致，确保两边数据时间间隔对齐。

        去重：save_data 按 (user_name, stock_name, time) upsert，两模板重复记录自动幂等。
        """
        if self.is_running and not force:
            logger.info("爬虫任务已经在执行中，跳过本次执行")
            return 0

        self.is_running = True

        try:
            self.__class__.total_pages_crawled = 0
            self.__class__.total_saved = 0

            # 依次爬两个模板（与 stockmonitor 一致）
            for label, url_template in CRAWL_TEMPLATES:
                logger.info(f"🔍 [{label}] 开始爬取页面 {start_page}-{end_page}")

                for page in range(start_page, end_page + 1):
                    self.__class__.total_pages_crawled += 1
                    html = self.fetch_page(page, url_template=url_template)
                    if not html:
                        logger.warning(f"[{label}] Page {page}: Failed to fetch")
                        delay = get_random_delay("failure")
                    else:
                        data = self.parse_html(html)
                        if not data:
                            logger.warning(f"[{label}] Page {page}: No data or parsing failed")
                            delay = get_random_delay("failure")
                        else:
                            try:
                                saved = self.save_data(data)
                                self.__class__.total_saved += saved
                                logger.debug(f"[{label}] Page {page}: 保存 {saved} 条 (总 {len(data)} 条)")
                                delay = get_random_delay("success")
                            except Exception as e:
                                logger.error(f"[{label}] Page {page}: Error saving: {e}")
                                delay = get_random_delay("failure")

                    if should_insert_random_pause():
                        time.sleep(get_random_pause())
                    time.sleep(delay)

                # 模板之间稍长一点的礼貌延迟
                time.sleep(random.uniform(1.0, 2.0))

            logger.info(
                f"✅ Crawl completed: Saved {self.__class__.total_saved} new records "
                f"from {self.__class__.total_pages_crawled} pages "
                f"(双模板: 伏击人+专家)"
            )
            return self.__class__.total_saved

        finally:
            self.is_running = False
            logger.info("爬虫任务执行完成，释放执行锁")


# 单例实例
crawler_service = CrawlerService()
