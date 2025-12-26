import random
import time
from scrapy import signals
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.utils.response import response_status_message
import os
import sys

# Import config for User Agents
# (Assuming path is already set in settings.py, or we add it here just in case)
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.config import USER_AGENTS

class RandomUserAgentMiddleware:
    """随机 User-Agent 中间件"""
    def __init__(self, user_agents):
        self.user_agents = user_agents

    @classmethod
    def from_crawler(cls, crawler):
        return cls(USER_AGENTS)

    def process_request(self, request, spider):
        request.headers.setdefault('User-Agent', random.choice(self.user_agents))

class CustomRetryMiddleware(RetryMiddleware):
    """自定义重试中间件: 针对特定错误进行指数退避"""
    
    def process_response(self, request, response, spider):
        if request.meta.get('dont_retry', False):
            return response
            
        if response.status in [429, 503]:
            # 指数退避: 2^n * 1.5s
            retry_times = request.meta.get('retry_times', 0) + 1
            delay = (2 ** retry_times) * 1.5
            spider.logger.warning(f"Got {response.status}, retrying in {delay}s...")
            time.sleep(delay)
            
            reason = response_status_message(response.status)
            return self._retry(request, reason, spider) or response
            
        return super().process_response(request, response, spider)

class AstockSpiderSpiderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        return None

    def process_spider_output(self, response, result, spider):
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        pass

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)

class AstockSpiderDownloaderMiddleware:
    @classmethod
    def from_crawler(cls, crawler):
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        return None

    def process_response(self, request, response, spider):
        return response

    def process_exception(self, request, exception, spider):
        pass

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)
