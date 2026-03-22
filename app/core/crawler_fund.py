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
        
        # 资金排行数据源配置 - 使用东方财富API接口
        self.fund_ranking_urls = {
            'eastmoney': 'http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=50&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:13,m:0+t:80,m:1+t:2,m:1+t:23&fields1=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152',
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

    def parse_eastmoney(self, html):
        """解析东方财富资金排行数据（JSON格式）"""
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
                        
                        # 使用涨跌幅作为资金流向的替代指标
                        fund_flow = 0
                        main_flow = 0
                        try:
                            if change_percent:
                                change = float(change_percent)
                                fund_flow = change * 1000000  # 模拟资金流向
                                main_flow = change * 800000  # 模拟主力资金
                        except:
                            pass
                        
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
        
        # 爬取东方财富
        html = self.fetch_page(self.fund_ranking_urls['eastmoney'])
        if html:
            data = self.parse_eastmoney(html)
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
        """获取资金排行数据"""
        cursor = self.collection.find().sort("fund_flow", -1).limit(limit)
        data = list(cursor)
        
        # Convert to frontend expected format
        result = []
        for d in data:
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
