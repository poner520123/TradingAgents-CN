from app.services.scrapy_crawler_service import ScrapyCrawlerService

# 获取Scrapy爬虫服务实例
service = ScrapyCrawlerService()

# 调用修复后的方法
data, total = service.get_expert_ranking_data(page=1, page_size=20)

print(f"修复后数据条数: {len(data)}")
print(f"总数据条数: {total}")

# 统计股票代码重复情况
from collections import defaultdict
code_counts = defaultdict(int)
for item in data:
    code = item.get('code', '')
    code_counts[code] += 1

print('\n股票代码重复情况:')
for code, count in code_counts.items():
    if count > 1:
        print(f'{code}: {count}次')

# 查看具体数据
print('\n返回的数据:')
for i, item in enumerate(data):
    print(f"{i+1}: code={item.get('code')}, name={item.get('name')}, expert={item.get('expert_name')}, success_rate={item.get('success_rate')}")
