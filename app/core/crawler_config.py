# Configuration settings
import requests
import random
import time
import socket
from typing import List, Dict, Optional
import os

# 模拟真实浏览器的请求头配置

BASE_URL = "https://www.178448.com/fjzt-1.html?page={}"

# Enhanced browser user agents collection for rotation
USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    # Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Safari on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]

# Chrome versions for Sec-Ch-Ua header
CHROME_VERSIONS = [
    '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    '"Chromium";v="123", "Google Chrome";v="123", "Not-A.Brand";v="99"',
    '"Chromium";v="122", "Google Chrome";v="122", "Not-A.Brand";v="99"',
]

# Platform options
PLATFORMS = [
    '"Windows"',
    '"macOS"',
    '"Linux"'
]

# Default headers (will be enhanced with random elements)
BASE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.178448.com/",
    "Origin": "https://www.178448.com",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
    "TE": "trailers",
    # Additional headers to mimic real browsers
    "Pragma": "no-cache",
    "DNT": "1",  # Do Not Track
    "Upgrade-Insecure-Requests": "1"
}

# Default headers for backward compatibility
def get_random_headers():
    """Generate random headers to simulate different browsers and users."""
    headers = BASE_HEADERS.copy()
    headers["User-Agent"] = random.choice(USER_AGENTS)
    headers["Sec-Ch-Ua"] = random.choice(CHROME_VERSIONS)
    headers["Sec-Ch-Ua-Platform"] = random.choice(PLATFORMS)
    return headers

# For backward compatibility
HEADERS = get_random_headers()

# 延迟配置 for anti-scraping
# These settings control the random delays between requests
# to mimic human browsing behavior more effectively
DELAY_CONFIG = {
    # Base delay ranges (in seconds)
    # Successful page fetch - shorter delay range
    "success_delay_range": (0.5, 1.5),  # 减少成功请求的延迟范围
    # Failed page fetch - longer delay range
    "failure_delay_range": (2, 4),  # 减少失败请求的延迟范围
    # Extra random pause that can be inserted occasionally
    "random_pause_range": (3, 5),  # 减少随机暂停时间
    # Probability of inserting an extra random pause (0.0-1.0)
    "random_pause_probability": 0.05,  # 减少随机暂停概率
    # Jitter factor to add small random variations to delays
    "jitter_factor": 0.1,  # 减少抖动因子
    # Maximum consecutive requests before a mandatory longer pause
    "max_consecutive_requests": 5,  # 增加连续请求次数
    # Mandatory longer pause after max_consecutive_requests (seconds)
    "mandatory_pause_range": (5, 8)  # 减少强制暂停时间
}

def get_random_delay(delay_type="success"):
    """Get a random delay based on the specified type with added jitter."""
    if delay_type == "success":
        min_delay, max_delay = DELAY_CONFIG["success_delay_range"]
    elif delay_type == "failure":
        min_delay, max_delay = DELAY_CONFIG["failure_delay_range"]
    else:
        min_delay, max_delay = DELAY_CONFIG["success_delay_range"]
    
    # Base random delay within range
    base_delay = random.uniform(min_delay, max_delay)
    
    # Add jitter (random variation)
    jitter = base_delay * DELAY_CONFIG["jitter_factor"]
    delay_with_jitter = base_delay + random.uniform(-jitter, jitter)
    
    # Ensure delay is at least 0.1 seconds
    return max(0.1, delay_with_jitter)

def should_insert_random_pause():
    """Determine if an extra random pause should be inserted."""
    return random.random() < DELAY_CONFIG["random_pause_probability"]

def get_random_pause():
    """Get a random longer pause duration."""
    return random.uniform(*DELAY_CONFIG["random_pause_range"])

def get_mandatory_pause():
    """Get a mandatory longer pause duration."""
    return random.uniform(*DELAY_CONFIG["mandatory_pause_range"])

# Proxy pool configuration
PROXY_POOL = []

# Whether to use proxies (can be toggled based on needs)
USE_PROXIES = False

def get_random_proxy():
    """Get a random proxy from the proxy pool."""
    if not USE_PROXIES or not PROXY_POOL:
        return None
    return random.choice(PROXY_POOL)

def build_proxy_dict(proxy):
    """Build proxy dictionary for requests library."""
    if not proxy:
        return None
    return {
        "http": proxy,
        "https": proxy
    }

# Function to test if a proxy is working
def test_proxy(proxy):
    """Test if a proxy is working by making a simple request."""
    try:
        proxies = build_proxy_dict(proxy)
        response = requests.get("https://www.baidu.com", proxies=proxies, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 代理测试失败 {proxy}: {e}")
        return False

# Function to filter and update working proxies
def filter_working_proxies():
    """Filter the proxy pool to only include working proxies."""
    global PROXY_POOL
    if not USE_PROXIES or not PROXY_POOL:
        return []
    
    working_proxies = []
    for proxy in PROXY_POOL:
        if test_proxy(proxy):
            working_proxies.append(proxy)
            print(f"✅ 代理工作正常: {proxy}")
    
    # Update the proxy pool with only working proxies
    if working_proxies:
        PROXY_POOL = working_proxies
        print(f"✅ 代理池更新完成，剩余 {len(working_proxies)} 个可用代理")
    else:
        print("⚠️ 没有可用的代理")
    
    return working_proxies

# 异常处理配置
EXCEPTION_CONFIG = {
    'max_retries': 3,  # 降低重试次数，改为更频繁重置会话
    'retry_exceptions': [
        requests.ConnectionError,
        requests.Timeout,
        requests.exceptions.ChunkedEncodingError,
        requests.exceptions.ContentDecodingError,
        requests.exceptions.RequestException,
        # 添加更多异常类型
        socket.timeout,
        ConnectionResetError,
        EOFError
    ],
    'retry_status_codes': [403, 429, 500, 502, 503, 504],
    # 增加指数退避配置
    'backoff_factor': 0.7,  # 增加退避因子，避免过快重试
    'max_backoff_time': 60,  # 最大退避时间（秒）
    # 增加异常分类配置
    'transient_errors': [requests.ConnectionError, requests.Timeout],  # 暂时性错误
    'fatal_errors': [requests.exceptions.InvalidURL, requests.exceptions.MissingSchema]  # 致命错误不重试
}

# 指数退避延迟函数
def get_exponential_backoff_delay(retry_count, base_delay=1.0, backoff_factor=0.5, max_delay=60):
    """根据重试次数计算指数退避延迟时间"""
    # 基础退避时间 = 基础延迟 * (2 ^ 重试次数) * (0.5 + 随机因子)
    # 添加随机抖动避免重试风暴
    exponential_delay = base_delay * (2 ** retry_count) * (0.5 + random.random())
    
    # 应用退避因子
    delay = exponential_delay * backoff_factor
    
    # 确保延迟不超过最大值
    return min(delay, max_delay)

# 速率限制配置
RATE_LIMIT_CONFIG = {
    'tokens_per_second': 1,         # 降低每秒令牌生成数，更严格控制请求频率
    'max_tokens': 5,                # 减少令牌桶最大容量
    'use_rate_limiting': True,      # 是否启用速率限制
    'burst_capacity': 2             # 减少突发请求容量
}

class TokenBucket:
    """令牌桶算法实现，用于流量控制"""
    def __init__(self, tokens_per_second, max_tokens, burst_capacity=None):
        self.tokens_per_second = tokens_per_second
        self.max_tokens = max_tokens
        self.burst_capacity = burst_capacity if burst_capacity is not None else max_tokens
        self.current_tokens = self.burst_capacity  # 初始时使用突发容量
        self.last_refill_time = time.time()
        
    def refill(self):
        """根据时间流逝补充令牌"""
        now = time.time()
        elapsed = now - self.last_refill_time
        
        if elapsed > 0:
            # 计算新增的令牌数
            new_tokens = elapsed * self.tokens_per_second
            self.current_tokens = min(self.max_tokens, self.current_tokens + new_tokens)
            self.last_refill_time = now
    
    def consume(self, tokens=1):
        """消耗令牌
        Returns:
            tuple: (是否成功获取令牌, 需要等待的时间)
        """
        # 先补充令牌
        self.refill()
        
        if self.current_tokens >= tokens:
            # 有足够的令牌，消耗令牌
            self.current_tokens -= tokens
            return True, 0
        else:
            # 没有足够的令牌，计算需要等待的时间
            needed_tokens = tokens - self.current_tokens
            wait_time = needed_tokens / self.tokens_per_second
            # 模拟等待后再消耗
            time.sleep(wait_time)
            # 重新补充并消耗令牌
            self.refill()
            if self.current_tokens >= tokens:
                self.current_tokens -= tokens
                return True, wait_time
            else:
                return False, wait_time

# 创建全局令牌桶实例
global_rate_limiter = TokenBucket(
    tokens_per_second=RATE_LIMIT_CONFIG['tokens_per_second'],
    max_tokens=RATE_LIMIT_CONFIG['max_tokens'],
    burst_capacity=RATE_LIMIT_CONFIG['burst_capacity']
)

# 代理特定的令牌桶缓存（为每个代理维护独立的速率限制）
proxy_rate_limiters = {}

def get_proxy_rate_limiter(proxy_url):
    """获取或创建代理特定的速率限制器"""
    if not proxy_url:
        return global_rate_limiter
    
    if proxy_url not in proxy_rate_limiters:
        # 为新代理创建令牌桶
        proxy_rate_limiters[proxy_url] = TokenBucket(
            tokens_per_second=RATE_LIMIT_CONFIG['tokens_per_second'],
            max_tokens=RATE_LIMIT_CONFIG['max_tokens'],
            burst_capacity=RATE_LIMIT_CONFIG['burst_capacity']
        )
    
    return proxy_rate_limiters[proxy_url]

# 请求参数随机化配置
PARAM_RANDOMIZATION_CONFIG = {
    'use_randomization': True,  # 是否启用参数随机化
    'add_cache_busters': True,  # 添加缓存破坏参数
    'add_random_parameters': True,  # 添加随机参数
    'random_parameter_probability': 0.5,  # 增加随机参数概率
    'max_random_parameters': 5,  # 增加最大随机参数数量
    'timestamp_formats': ['timestamp', 'iso', 'unix_ms', 'random']  # 时间戳格式选项
}

# 随机参数名和值的生成配置
RANDOM_PARAM_CONFIG = {
    'prefixes': ['_', '__', 'a_', 'b_', 'c_'],
    'names': ['t', 'ts', 'v', 'ver', 'rnd', 'rand', 'cb', 'cache', 'no_cache', 'nocache'],
    'value_lengths': range(4, 13)  # 值长度范围
}

# 模拟搜索和过滤参数
SIMULATED_SEARCH_PARAMS = {
    'filter': ['all', 'active', 'recent'],
    'sort': ['default', 'popularity', 'date', 'price_asc', 'price_desc'],
    'view': ['list', 'grid', 'compact'],
    'limit': [10, 20, 30, 50]
}

def generate_random_string(length):
    """生成指定长度的随机字符串"""
    import string
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def generate_timestamp(format_type='timestamp'):
    """生成不同格式的时间戳"""
    import datetime
    now = datetime.datetime.now()
    
    if format_type == 'timestamp':
        return str(int(now.timestamp()))
    elif format_type == 'unix_ms':
        return str(int(now.timestamp() * 1000))
    elif format_type == 'iso':
        return now.isoformat()
    else:  # random
        formats = ['timestamp', 'unix_ms', 'iso']
        return generate_timestamp(random.choice(formats))

def get_random_parameters(count=1):
    """生成随机参数"""
    params = {}
    
    for _ in range(count):
        # 随机选择前缀和名称
        prefix = random.choice(RANDOM_PARAM_CONFIG['prefixes'])
        name = random.choice(RANDOM_PARAM_CONFIG['names'])
        param_name = prefix + name
        
        # 随机选择值长度和值类型
        length = random.choice(RANDOM_PARAM_CONFIG['value_lengths'])
        # 80%概率使用字符串，20%概率使用时间戳
        if random.random() < 0.8:
            param_value = generate_random_string(length)
        else:
            format_type = random.choice(PARAM_RANDOMIZATION_CONFIG['timestamp_formats'])
            param_value = generate_timestamp(format_type)
        
        params[param_name] = param_value
    
    return params

def get_cache_buster():
    """生成缓存破坏参数"""
    # 常见的缓存破坏参数名
    cache_buster_names = ['_', '__', 't', 'ts', 'timestamp', 'cache_bust', 'cb', 'r']
    name = random.choice(cache_buster_names)
    value = generate_timestamp(random.choice(['timestamp', 'unix_ms']))
    return {name: value}

def get_simulated_search_params():
    """生成模拟的搜索和过滤参数"""
    params = {}
    # 30%概率添加搜索参数
    if random.random() < 0.3:
        for param_name, options in SIMULATED_SEARCH_PARAMS.items():
            # 每个参数有40%概率被添加
            if random.random() < 0.4:
                params[param_name] = random.choice(options)
    return params

def get_randomized_params(base_params=None):
    """获取随机化的请求参数"""
    if not PARAM_RANDOMIZATION_CONFIG['use_randomization']:
        return base_params or {}
    
    params = base_params.copy() if base_params else {}
    
    # 添加缓存破坏参数
    if PARAM_RANDOMIZATION_CONFIG['add_cache_busters']:
        params.update(get_cache_buster())
    
    # 添加随机参数
    if PARAM_RANDOMIZATION_CONFIG['add_random_parameters']:
        if random.random() < PARAM_RANDOMIZATION_CONFIG['random_parameter_probability']:
            count = random.randint(1, PARAM_RANDOMIZATION_CONFIG['max_random_parameters'])
            params.update(get_random_parameters(count))
    
    # 添加模拟搜索参数
    params.update(get_simulated_search_params())
    
    return params
