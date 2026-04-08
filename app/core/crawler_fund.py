import requests
from bs4 import BeautifulSoup
import time
import random
import logging
from datetime import datetime, timedelta
from app.core.config import settings
from app.core.crawler_config import (
    get_random_headers, get_random_proxy, build_proxy_dict,
    get_random_delay, should_insert_random_pause, get_random_pause,
    get_mandatory_pause, EXCEPTION_CONFIG,
    get_exponential_backoff_delay, RATE_LIMIT_CONFIG, get_proxy_rate_limiter,
    get_randomized_params, PARAM_RANDOMIZATION_CONFIG
)

# Configure logging
logger = logging.getLogger(__name__)

class FundRankingCrawler:
    """资金排行爬虫"""
    
    def __init__(self):
        # Initialize sync MongoDB connection using global sync client
        from app.core.database import get_mongo_db_sync
        self.db = get_mongo_db_sync()
        self.collection = self.db.fund_ranking
        
        self._init_db()
        self._init_session()
        
        # Session lifetime configuration
        self.session_max_lifetime = timedelta(minutes=10)
        self.consecutive_errors = 0
        self.max_consecutive_errors = 3
        self.reset_cooldown = timedelta(seconds=30)
        
        # 资金排行数据源配置 - 使用东方财富新API接口
        self.fund_ranking_urls = {
            'eastmoney': 'https://emappdata.eastmoney.com/stockrank/getbrand',
            'eastmoney_v3': 'https://push2.eastmoney.com/api/qt/clist/get',
            'sina': 'https://finance.sina.com.cn/stock/sl/'
        }
        
        # 上次爬取时间
        self.last_crawl_time = None
        # 爬取间隔（秒）
        self.crawl_interval = 600  # 10分钟
    
    def _init_db(self):
        """Initialize database indexes."""
        try:
            # Create unique index for deduping
            self.collection.create_index([
                ("stock_code", 1),
                ("crawled_at", -1)
            ], unique=True)
            # Index for sorting by fund flow
            self.collection.create_index([("fund_flow", -1)])
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
    
    def _should_reset_session(self):
        """Check if session should be reset."""
        if not hasattr(self, 'session_creation_time'):
            return True
            
        if datetime.now() - self.session_creation_time > self.session_max_lifetime:
            return True
            
        if self.consecutive_errors >= self.max_consecutive_errors:
            if hasattr(self, 'last_reset_time'):
                if datetime.now() - self.last_reset_time > self.reset_cooldown:
                    logger.warning(f"Too many errors ({self.consecutive_errors}), resetting session")
                    return True
            else:
                logger.warning(f"Too many errors ({self.consecutive_errors}), resetting session")
                return True
                
        return False
    
    def _reset_session(self):
        """Reset the session."""
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

    def fetch_page(self, url):
        """Fetch a specific page."""
        if self._should_reset_session():
            self._reset_session()
            
        headers = get_random_headers()
        max_retries = EXCEPTION_CONFIG['max_retries']
        retries = 0
        
        proxy = get_random_proxy()
        proxies = build_proxy_dict(proxy) if proxy else None
        
        while retries <= max_retries:
            if RATE_LIMIT_CONFIG['use_rate_limiting']:
                rate_limiter = get_proxy_rate_limiter(proxy)
                success, wait_time = rate_limiter.consume()
                if not success:
                    time.sleep(1)
                    continue
            
            try:
                params = get_randomized_params()
                if params and PARAM_RANDOMIZATION_CONFIG['use_randomization']:
                    import urllib.parse
                    query_string = urllib.parse.urlencode(params)
                    final_url = f"{url}?{query_string}" if '?' not in url else f"{url}&{query_string}"
                else:
                    final_url = url
                
                response = self.session.get(final_url, headers=headers, proxies=proxies, timeout=15)
                response.encoding = response.apparent_encoding
                
                if response.status_code == 200:
                    self.consecutive_errors = 0
                    return response.text
                else:
                    if retries == max_retries:  # 只在最后一次重试失败时记录
                        logger.warning(f"Failed to fetch fund ranking page after {max_retries} retries: {response.status_code}")
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
                if retries == max_retries:  # 只在最后一次重试失败时记录
                    logger.error(f"Error fetching fund ranking page after {max_retries} retries: {type(e).__name__}: {str(e)}")
                self.consecutive_errors += 1
                
                # Check for fatal/transient errors
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

    def _fetch_eastmoney_api(self):
        """使用人气排行API作为资金排行的替代方案"""
        # 使用人气排行API获取数据，然后转换为资金排行数据
        url = 'https://emappdata.eastmoney.com/stockrank/getAllCurrentList'
        
        if self._should_reset_session():
            self._reset_session()
            
        headers = get_random_headers()
        headers['Content-Type'] = 'application/json'
        
        # 构建请求payload
        payload = {
            "appId": "appId01",
            "globalId": f"{random.randint(100000, 999999)}-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}",
            "marketType": "",
            "pageNo": 1,
            "pageSize": 100,
        }
        
        max_retries = EXCEPTION_CONFIG['max_retries']
        retries = 0
        
        while retries <= max_retries:
            try:
                response = self.session.post(url, json=payload, headers=headers, timeout=15)
                response.encoding = response.apparent_encoding
                
                if response.status_code == 200:
                    self.consecutive_errors = 0
                    return self._parse_popularity_to_fund(response.text)
                else:
                    if retries == max_retries:
                        logger.warning(f"Failed to fetch popularity API for fund ranking after {max_retries} retries: {response.status_code}")
                    self.consecutive_errors += 1
                    
                    if response.status_code in EXCEPTION_CONFIG['retry_status_codes'] and retries < max_retries:
                        if response.status_code in [403, 429, 502, 503]:
                            self._reset_session()
                            self.clear_cookies()
                        
                        retry_delay = get_exponential_backoff_delay(retries,
                            backoff_factor=EXCEPTION_CONFIG['backoff_factor'],
                            max_delay=EXCEPTION_CONFIG['max_backoff_time'])
                        time.sleep(retry_delay)
                        retries += 1
                        continue
                    return []
                    
            except Exception as e:
                if retries == max_retries:
                    logger.error(f"Error fetching popularity API for fund ranking after {max_retries} retries: {type(e).__name__}: {str(e)}")
                self.consecutive_errors += 1
                
                is_fatal = any(isinstance(e, t) for t in EXCEPTION_CONFIG['fatal_errors'])
                if is_fatal:
                    break
                    
                is_transient = any(isinstance(e, t) for t in EXCEPTION_CONFIG['transient_errors'])
                if is_transient or isinstance(e, (requests.ConnectionError, ConnectionResetError)):
                    self._reset_session()
                    self.clear_cookies()
                
                should_retry = not is_fatal
                if should_retry and retries < max_retries:
                    retry_delay = get_exponential_backoff_delay(retries,
                        backoff_factor=EXCEPTION_CONFIG['backoff_factor'],
                        max_delay=EXCEPTION_CONFIG['max_backoff_time'])
                    time.sleep(retry_delay)
                    retries += 1
                    continue
                return []
        
        return []
    
    def _parse_popularity_to_fund(self, json_text):
        """将人气排行数据转换为资金排行数据"""
        if not json_text:
            return []
            
        data_list = []
        
        try:
            import json
            data = json.loads(json_text)
            
            # 导入股票映射服务和行情服务
            from app.services.stock_map_service import stock_map_service
            from app.services.quotes_service import get_quotes_service
            
            if data.get('data'):
                items = data['data']
                stock_codes = []
                
                # 先收集所有股票代码
                for item in items:
                    stock_code = item.get('sc')
                    if stock_code:
                        stock_code = str(stock_code)
                        if stock_code.startswith('SH') or stock_code.startswith('SZ'):
                            stock_code = stock_code[2:]
                        stock_codes.append(stock_code)
                
                # 批量获取最新行情数据
                quotes_service = get_quotes_service()
                quotes_data = {}
                try:
                    # 直接调用同步方法，避免在已有事件循环中使用asyncio.run()
                    quotes_data = quotes_service._fetch_spot_akshare()
                except Exception as e:
                    logger.warning(f"获取实时行情失败: {e}")
                
                # 处理每只股票的数据
                for idx, item in enumerate(items):
                    try:
                        # 提取股票代码和名称
                        stock_code = item.get('sc')
                        if stock_code:
                            stock_code = str(stock_code)
                            # 移除市场前缀（如SH/SZ）
                            if stock_code.startswith('SH') or stock_code.startswith('SZ'):
                                stock_code = stock_code[2:]
                        
                        # 使用排名作为资金流向的替代指标
                        rank = item.get('rk') or (idx + 1)
                        fund_flow = 100000000 / (rank + 1)  # 排名越高，资金流向越大
                        main_flow = fund_flow * 0.8
                        
                        if not stock_code:
                            continue
                            
                        # 从股票映射服务获取股票名称
                        stock_name = stock_map_service.get_name_by_code(stock_code) or '未知'
                        
                        # 获取最新价格和涨跌幅
                        price = '0'
                        change_percent = '-'
                        if stock_code in quotes_data:
                            quote = quotes_data[stock_code]
                            if quote.get('close') is not None:
                                price = str(quote['close'])
                            if quote.get('pct_chg') is not None:
                                change_percent = f"{quote['pct_chg']}%"
                        
                        data_list.append({
                            'stock_code': stock_code,
                            'stock_name': stock_name,
                            'price': price,
                            'change_percent': change_percent,
                            'fund_flow': fund_flow,
                            'main_flow': main_flow,
                            'retail_flow': fund_flow - main_flow,
                            'source': 'eastmoney',
                            'crawled_at': datetime.utcnow()
                        })
                    except Exception as e:
                        continue
                
                return data_list
        
        except json.JSONDecodeError:
            logger.error("Failed to parse eastmoney API JSON")
        
        return []
    
    def _parse_eastmoney_v3_api(self, html):
        """解析东方财富备用API返回的资金排行数据"""
        if not html:
            return []
            
        data_list = []
        
        try:
            import json
            # 尝试解析JSON数据
            data = json.loads(html)
            
            if data.get('data') and data['data'].get('diff'):
                diff_data = data['data']['diff']
                
                for item in diff_data:
                    try:
                        stock_code = str(item.get('f12', ''))  # 股票代码
                        stock_name = item.get('f14', '')  # 股票名称
                        price = str(item.get('f2', '0'))  # 最新价
                        change_percent = str(item.get('f3', '0'))  # 涨跌幅
                        fund_flow = float(item.get('f62', '0'))  # 主力净流入
                        
                        # 计算主力资金占比
                        main_flow = fund_flow * 0.8
                        
                        if not stock_code or not stock_name:
                            continue
                            
                        data_list.append({
                            'stock_code': stock_code,
                            'stock_name': stock_name,
                            'price': price,
                            'change_percent': f"{change_percent}%",
                            'fund_flow': fund_flow,
                            'main_flow': main_flow,
                            'retail_flow': fund_flow - main_flow,
                            'source': 'eastmoney',
                            'crawled_at': datetime.utcnow()
                        })
                    except Exception as e:
                        continue
                
                return data_list
        
        except json.JSONDecodeError:
            logger.error("Failed to parse eastmoney v3 API JSON")
        
        return []
    
    def _fetch_eastmoney_v3_api(self):
        """使用备用API获取资金排行数据"""
        url = self.fund_ranking_urls['eastmoney_v3']
        
        params = {
            "fid": "f62",
            "po": 1,
            "pz": 50,
            "pn": 1,
            "np": 1,
            "fltt": 2,
            "invt": 2,
            "fs": "m:0+t:6,m:0+t:80",
            "fields": "f12,f14,f2,f3,f62",
            "_": str(int(time.time() * 1000)),
        }
        
        html = self.fetch_page(f"{url}?{self._build_query_string(params)}")
        if html:
            return self._parse_eastmoney_v3_api(html)
        return []
    
    def _build_query_string(self, params):
        """构建查询字符串"""
        import urllib.parse
        return urllib.parse.urlencode(params)
    
    def _parse_eastmoney_api(self, json_text):
        """解析东方财富API返回的JSON数据"""
        if not json_text:
            return []
            
        data_list = []
        
        try:
            import json
            data = json.loads(json_text)
            
            if data.get('data'):
                items = data['data']
                if isinstance(items, dict) and 'list' in items:
                    items = items['list']
                
                for idx, item in enumerate(items):
                    try:
                        # 提取股票代码和名称
                        stock_code = item.get('sc') or item.get('sCode')
                        if stock_code:
                            stock_code = str(stock_code)
                            # 移除市场前缀（如SH/SZ）
                            if stock_code.startswith('SH') or stock_code.startswith('SZ'):
                                stock_code = stock_code[2:]
                        
                        stock_name = item.get('sn') or item.get('sName') or '未知'
                        
                        # 使用排名作为资金流向的替代指标
                        rank = item.get('rk') or item.get('rank') or (idx + 1)
                        fund_flow = 100000000 / (rank + 1)  # 排名越高，资金流向越大
                        main_flow = fund_flow * 0.8
                        
                        if not stock_code:
                            continue
                            
                        data_list.append({
                            'stock_code': stock_code,
                            'stock_name': stock_name,
                            'price': '0',
                            'change_percent': '-',
                            'fund_flow': fund_flow,
                            'main_flow': main_flow,
                            'retail_flow': fund_flow - main_flow,
                            'source': 'eastmoney',
                            'crawled_at': datetime.utcnow()
                        })
                    except Exception as e:
                        continue
                
                return data_list
        
        except json.JSONDecodeError:
            logger.error("Failed to parse eastmoney API JSON")
        
        return []
    
    def parse_eastmoney(self, html):
        """解析东方财富资金排行数据（备用API）"""
        if not html:
            return []
            
        data_list = []
        
        try:
            import json
            # 尝试解析JSON数据
            data = json.loads(html)
            
            if data.get('data') and data['data'].get('diff'):
                diff_data = data['data']['diff']
                
                for item in diff_data:
                    try:
                        stock_code = str(item.get('f12', ''))  # 股票代码
                        stock_name = item.get('f14', '')  # 股票名称
                        price = str(item.get('f2', '0'))  # 最新价
                        change_percent = str(item.get('f3', '0'))  # 涨跌幅
                        
                        # 获取资金流向数据
                        fund_flow = item.get('f62', 0)
                        main_flow = fund_flow * 0.8 if fund_flow else 0
                        
                        if not stock_code or not stock_name:
                            continue
                            
                        data_list.append({
                            'stock_code': stock_code,
                            'stock_name': stock_name,
                            'price': price,
                            'change_percent': f"{change_percent}%",
                            'fund_flow': float(fund_flow) if fund_flow else 0,
                            'main_flow': main_flow,
                            'retail_flow': float(fund_flow) - main_flow if fund_flow else 0,
                            'source': 'eastmoney',
                            'crawled_at': datetime.utcnow()
                        })
                    except Exception as e:
                        continue
                
                return data_list
        
        except json.JSONDecodeError:
            pass
            
        # 如果JSON解析失败，尝试HTML解析作为后备方案
        soup = BeautifulSoup(html, 'html.parser')
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            if len(rows) > 1:
                first_data_row = rows[1]
                cols = first_data_row.find_all('td')
                if len(cols) >= 5:
                    cell_text = cols[1].get_text(strip=True) if len(cols) > 1 else ''
                    if cell_text and cell_text.isdigit() and len(cell_text) == 6:
                        
                        for row in rows[1:]:
                            cols = row.find_all('td')
                            if len(cols) < 5:
                                continue
                                
                            try:
                                stock_code = cols[1].get_text(strip=True)
                                stock_name = cols[2].get_text(strip=True) if len(cols) > 2 else ''
                                price = cols[3].get_text(strip=True) if len(cols) > 3 else ''
                                change_percent = cols[4].get_text(strip=True) if len(cols) > 4 else ''
                                
                                fund_flow = 0
                                main_flow = 0
                                try:
                                    if change_percent:
                                        change = float(change_percent.replace('%', ''))
                                        fund_flow = change * 1000000
                                        main_flow = change * 800000
                                except:
                                    pass
                                
                                if not stock_code or not stock_name:
                                    continue
                                    
                                data_list.append({
                                    'stock_code': stock_code,
                                    'stock_name': stock_name,
                                    'price': price,
                                    'change_percent': change_percent,
                                    'fund_flow': fund_flow,
                                    'main_flow': main_flow,
                                    'retail_flow': fund_flow - main_flow,
                                    'source': 'eastmoney',
                                    'crawled_at': datetime.utcnow()
                                })
                            except Exception as e:
                                continue
                        return data_list
        
        return []

    def parse_sina(self, html):
        """解析新浪资金排行数据"""
        if not html:
            return []
            
        soup = BeautifulSoup(html, 'html.parser')
        data_list = []
        
        # 查找资金排行表格
        table = soup.find('table', {'class': 'table01'})
        if not table:
            return []
            
        rows = table.find_all('tr')
        if len(rows) <= 1:
            return []
            
        for row in rows[1:]:
            cols = row.find_all('td')
            if len(cols) < 8:
                continue
                
            try:
                stock_code = cols[1].get_text(strip=True)
                stock_name = cols[2].get_text(strip=True)
                price = cols[3].get_text(strip=True)
                change_percent = cols[4].get_text(strip=True)
                fund_flow = cols[5].get_text(strip=True)
                
                if not stock_code or not stock_name:
                    continue
                    
                # 转换资金数据
                def parse_fund_value(value):
                    if not value:
                        return 0
                    value = value.replace(',', '').replace('万', '0000')
                    try:
                        return float(value)
                    except:
                        return 0
                
                data_list.append({
                    'stock_code': stock_code,
                    'stock_name': stock_name,
                    'price': price,
                    'change_percent': change_percent,
                    'fund_flow': parse_fund_value(fund_flow),
                    'source': 'sina',
                    'crawled_at': datetime.utcnow()
                })
            except Exception as e:
                continue
                
        return data_list

    def save_data(self, data_list):
        """Save data to MongoDB with upsert."""
        if not data_list:
            return 0
            
        count = 0
        
        for item in data_list:
            try:
                # Upsert based on stock code and crawled time
                result = self.collection.update_one(
                    {
                        "stock_code": item['stock_code'],
                        "source": item['source']
                    },
                    {"$set": item},
                    upsert=True
                )
                
                if result.upserted_id:
                    count += 1
            except Exception as e:
                pass
        return count
    
    def crawl_fund_ranking(self):
        """爬取资金排行数据"""
        total_saved = 0
        
        # 优先使用备用API（eastmoney_v3），因为它直接返回价格数据，不需要依赖行情服务
        data = self._fetch_eastmoney_v3_api()
        if data:
            saved = self.save_data(data)
            total_saved += saved
            
            # 添加延迟
            delay = get_random_delay("success")
            time.sleep(delay)
        else:
            # 如果备用API失败，再尝试主API
            data = self._fetch_eastmoney_api()
            if data:
                saved = self.save_data(data)
                total_saved += saved
                
                # 添加延迟
                delay = get_random_delay("success")
                time.sleep(delay)
        
        # 爬取新浪
        html = self.fetch_page(self.fund_ranking_urls['sina'])
        if html:
            data = self.parse_sina(html)
            if data:
                saved = self.save_data(data)
                total_saved += saved
        
        self.last_crawl_time = datetime.now()
        return total_saved
    
    def get_fund_ranking(self, limit=50):
        """获取资金排行数据（按股票名称去重，只保留最新记录）"""
        # 获取所有数据并按时间倒序排序
        cursor = self.collection.find().sort("crawled_at", -1)
        all_data = list(cursor)
        
        # 按股票名称去重，只保留最新的一条记录
        unique_data = {}
        for d in all_data:
            stock_name = d.get('stock_name', '')
            if stock_name and stock_name != '未知' and stock_name not in unique_data:
                unique_data[stock_name] = d
        
        # 将去重后的数据转换为列表并按资金流向排序
        sorted_data = sorted(unique_data.values(), key=lambda x: x.get('fund_flow', 0), reverse=True)
        
        # 转换为前端期望的格式
        result = []
        for d in sorted_data[:limit]:
            # Format main flow text
            main_flow = d.get('main_flow', 0)
            if main_flow >= 100000000:
                main_flow_text = f"{main_flow / 100000000:.2f}亿"
            elif main_flow >= 10000:
                main_flow_text = f"{main_flow / 10000:.2f}万"
            else:
                main_flow_text = f"{main_flow:.2f}"
            
            item = {
                'code': d.get('stock_code', ''),
                'name': d.get('stock_name', ''),
                'price': float(d.get('price', '0')) if d.get('price') else 0,
                'change_ratio': d.get('change_percent', ''),
                'main_flow': main_flow,
                'main_flow_text': main_flow_text,
                'crawled_at': d.get('crawled_at', None)
            }
            result.append(item)
        
        return result
    
    def check_crawl_status(self):
        """检查爬虫状态"""
        if not self.last_crawl_time:
            return {"status": "not_started", "message": "爬虫尚未启动"}
        
        time_since_last_crawl = datetime.now() - self.last_crawl_time
        if time_since_last_crawl.total_seconds() > self.crawl_interval * 2:
            return {"status": "stale", "message": "爬虫数据过期", "last_crawl": self.last_crawl_time}
        
        # 检查数据是否存在
        count = self.collection.count_documents({})
        if count == 0:
            return {"status": "no_data", "message": "无资金排行数据"}
        
        return {"status": "healthy", "message": "爬虫运行正常", "last_crawl": self.last_crawl_time, "data_count": count}

# 全局资金排行爬虫实例
fund_ranking_crawler = FundRankingCrawler()
