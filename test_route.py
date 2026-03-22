from app.routers.astock import get_expert_ranking_data
from app.services.scrapy_crawler_service import ScrapyCrawlerService

# 创建服务实例
service = ScrapyCrawlerService()

# 直接调用路由处理函数
result = get_expert_ranking_data(page=1, page_size=20, service=service)

print(f"路由返回数据条数: {len(result.data)}")

# 统计股票代码重复情况
from collections import defaultdict
code_counts = defaultdict(int)
for item in result.data:
    code = item.get('code', '')
    code_counts[code] += 1

print('\n股票代码重复情况:')
for code, count in code_counts.items():
    if count > 1:
        print(f'{code}: {count}次')
