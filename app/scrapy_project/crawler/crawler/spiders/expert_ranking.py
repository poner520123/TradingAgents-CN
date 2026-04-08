import scrapy
import random
import time
import re
import datetime
from ..items import ExpertRankingItem


class ExpertRankingSpider(scrapy.Spider):
    name = "expert_ranking"
    allowed_domains = ['178448.com', 'www.178448.com']
    start_urls = ['https://www.178448.com/fjzt-2.html?page=1', 'https://www.178448.com/fjzt-1.html?page=1']
    
    def __init__(self):
        self.max_pages = 10  # 最大爬取页面数
        self.crawl_time = datetime.datetime.now()
        # 最近3周的开始时间
        self.time_pre_week_1 = (datetime.datetime.now() - datetime.timedelta(weeks=3)).strftime("%Y-%m-%d %H:%M")
        # 初始化股票名称映射
        self.stock_name_map = {}
        # 尝试加载股票名称映射
        self._load_stock_name_map()
    
    def start_requests(self):
        """重写start_requests方法，设置初始请求"""
        # 随机User-Agent列表
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        for url in self.start_urls:
            self.logger.info(f"开始爬取: {url}")
            
            # 随机选择User-Agent
            user_agent = random.choice(user_agents)
            
            headers = {
                'User-Agent': user_agent,
                'Referer': 'https://www.178448.com/',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0'
            }
            
            # 添加Cookie
            cookies = {
                'Hm_lvt_66b3990901952af5a1033e189085235e': str(int(time.time())),
                'Hm_lpvt_66b3990901952af5a1033e189085235e': str(int(time.time())),
                'sessionid': f'session_{random.randint(100000, 999999)}'
            }
            
            yield scrapy.Request(
                url=url,
                headers=headers,
                cookies=cookies,
                callback=self.parse,
                errback=self.handle_error,
                dont_filter=False,
                meta={'retry_times': 0, 'dont_redirect': False}
            )
            # 初始请求之间添加更长的延迟
            time.sleep(random.uniform(5, 8))
    
    def handle_error(self, failure):
        """处理请求错误"""
        self.logger.error(f"请求失败: {failure.request.url}, 错误: {failure.value}")
        
        # 如果重试次数小于3次，则重新请求
        retry_times = failure.request.meta.get('retry_times', 0)
        if retry_times < 3:
            self.logger.info(f"重试请求: {failure.request.url}, 第{retry_times + 1}次重试")
            # 添加随机延迟
            time.sleep(random.uniform(1, 3))
            
            new_request = failure.request.copy()
            new_request.meta['retry_times'] = retry_times + 1
            yield new_request
    
    def validate_stock_data(self, fjr, cg, cgl, stock_name, analysis_time):
        """验证股票数据的有效性"""
        try:
            # 检查必要字段是否存在
            if not all([fjr, cg, cgl, stock_name, analysis_time]):
                return False
            
            # 检查成功数和成功率是否为数字
            float(cg)
            float(cgl)
            
            # 检查时间格式
            datetime.datetime.strptime(analysis_time, "%Y-%m-%d %H:%M")
            
            return True
        except (ValueError, TypeError) as e:
            self.logger.warning(f"数据验证失败: {e}")
            return False
            
    def _load_stock_name_map(self):
        """从stock_name_map中加载股票名称映射"""
        try:
            # 添加项目根目录到Python路径
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
            
            # 导入数据库相关模块
            from src.database import get_db_connection
            
            # 连接数据库
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 查询股票名称映射
            cursor.execute("SELECT code, name FROM stock_name_map")
            rows = cursor.fetchall()
            
            # 构建映射字典
            for row in rows:
                if isinstance(row, dict):
                    # 字典格式（如MariaDB的DictCursor）
                    self.stock_name_map[row['name']] = row['code']
                else:
                    # 元组格式（如SQLite）
                    self.stock_name_map[row[1]] = row[0]
            
            conn.close()
            self.logger.info(f"✓ 加载股票名称映射成功，共 {len(self.stock_name_map)} 条数据")
        except Exception as e:
            self.logger.warning(f"加载股票名称映射失败: {e}")
            self.stock_name_map = {}
    
    def extract_stock_code(self, fjgp):
        """从股票名称中提取股票代码，如果无法提取则从stock_name_map中获取"""
        try:
            # 常见格式: "股票名称(600000)" 或 "600000 股票名称"
            import re
            
            # 格式1: 股票名称(600000)
            match = re.search(r'\((\d{6})\)', fjgp)
            if match:
                stock_code = match.group(1)
            else:
                # 格式2: 600000 股票名称
                match = re.match(r'(\d{6})\s+', fjgp)
                if match:
                    stock_code = match.group(1)
                else:
                    # 格式3: 只有股票名称，从stock_name_map中获取
                    # 先去掉可能的空格和特殊字符
                    clean_name = fjgp.strip()
                    stock_code = self.stock_name_map.get(clean_name, "")
            
            return stock_code
        except Exception as e:
            self.logger.warning(f"提取股票代码出错: {e}, fjgp: {fjgp}")
            return ""
    
    def parse(self, response):
        """处理页面响应，解析数据"""
        try:
            current_url = response.url
            
            # 更新已爬取页面计数
            if 'fjzt-1.html' in current_url:
                page_type = 'fjzt-1'
            elif 'fjzt-2.html' in current_url:
                page_type = 'fjzt-2'
            else:
                page_type = 'unknown'
            
            self.logger.info(f"🔄 开始处理页面: {current_url}")
            
            # 获取股票列表
            stockList = response.xpath('//tbody/tr')
            self.logger.info(f"找到股票数据: {len(stockList)} 条")
            
            # 处理每个股票数据
            for stock in stockList:
                try:
                    # 安全提取数据
                    fjr = stock.xpath('.//td[1]/a/text()').extract_first()  # 分析师
                    cg = stock.xpath('.//td[2]/text()').extract_first()  # 分析数
                    cgl_raw = stock.xpath('.//td[3]/text()').extract_first()  # 成功率
                    fjgp = stock.xpath('.//td[4]/text()').extract_first()  # 股票名称
                    fjly = stock.xpath('.//td[5]/text()').extract_first()  # 分析理由
                    fjsj = stock.xpath('.//td[6]/text()').extract_first()  # 分析时间
                    fjj = stock.xpath('.//td[7]/text()').extract_first()  # 分析价格
                    ztrq = stock.xpath('.//td[11]/text()').extract_first() or ''  # 涨停日期
                    
                    # 处理成功率数据
                    if cgl_raw:
                        cgl = cgl_raw.strip('%')
                    else:
                        continue
                    
                    # 验证数据有效性
                    if not self.validate_stock_data(fjr=fjr, cg=cg, cgl=cgl, stock_name=fjgp, analysis_time=fjsj):
                        self.logger.warning(f"数据验证失败，跳过: {fjgp}")
                        continue

                    # 筛选条件检查（最近3周，分析数>2，成功率>60%）
                    if fjsj >= self.time_pre_week_1 and float(cg) > 2 and float(cgl) > 60:
                        # 提取股票代码
                        stock_code = self.extract_stock_code(fjgp)
                        
                        # 创建专家排行项目
                        item = ExpertRankingItem()
                        item['expert_name'] = fjr  # 达人名称
                        item['name'] = fjgp  # 股票名称
                        item['code'] = stock_code  # 股票代码
                        item['analysis_reason'] = fjly  # 分析理由
                        item['analysis_time'] = fjsj  # 分析时间
                        item['analysis_price'] = fjj  # 分析价格
                        item['success_count'] = int(cg)  # 分析数
                        item['success_rate'] = float(cgl)  # 成功率
                        item['source_url'] = current_url  # 来源URL
                        
                        # 交给piplines处理
                        yield item
                        self.logger.info(f"✓ 提取有效专家数据: {fjgp} | 达人:{fjr} | 成功率:{cgl}% | 分析时间:{fjsj}")
                    
                except Exception as e:
                    self.logger.error(f"处理股票数据时出错: {e}")
                    continue
            
            # 翻页处理
            # 解析当前页码
            page_num = 1
            if 'page=' in current_url:
                try:
                    page_str = current_url.split('page=')[1]
                    if '&' in page_str:
                        page_str = page_str.split('&')[0]
                    page_num = int(page_str)
                except (ValueError, IndexError):
                    page_num = 1
                    self.logger.warning(f"无法解析页面参数，默认设置为第1页")
            
            # 如果未达到最大页面数，继续翻页
            if page_num < self.max_pages:
                next_page = page_num + 1
                # 确保正确构建下一页URL
                if 'page=' in current_url:
                    next_url = current_url.replace(f"page={page_num}", f"page={next_page}")
                else:
                    next_url = current_url + f"?page={next_page}"
                
                self.logger.info(f"🔄 准备翻页: {page_type} 第{page_num}页 -> 第{next_page}页")
                self.logger.info(f"下一页URL: {next_url}")
                
                # 添加随机延迟避免请求过快
                delay = random.uniform(0.5, 1.5)
                time.sleep(delay)
                
                yield scrapy.Request(
                    url=next_url, 
                    callback=self.parse, 
                    dont_filter=False,
                    errback=self.handle_error,
                    meta={'retry_times': 0}
                )
            else:
                self.logger.info(f"🏁 {page_type}页面爬取完成，已达到最大页数 {self.max_pages}")
        
        except Exception as e:
            self.logger.error(f"处理页面时出错: {e}, URL: {response.url}")
            # 继续爬取下一页
            pass