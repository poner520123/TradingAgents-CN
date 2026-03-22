from app.services.scrapy_crawler_service import ScrapyCrawlerService

# 创建服务实例
service = ScrapyCrawlerService()

# 调用修复后的方法
data, total = service.get_expert_ranking_data(page=1, page_size=20)

print(f"服务方法返回数据条数: {len(data)}")
print(f"总数据条数: {total}")

# 统计股票代码重复情况
from collections import defaultdict
code_counts = defaultdict(int)
for item in data:
    code = item.get('code', '')
    code_counts[code] += 1

print('\n股票代码重复情况:')
has_duplicates = False
for code, count in code_counts.items():
    if count > 1:
        print(f'{code}: {count}次')
        has_duplicates = True

if not has_duplicates:
    print('没有重复的股票代码')

# 打印具体数据
print('\n返回的数据:')
for i, item in enumerate(data):
    print(f"{i+1}: code={item.get('code')}, name={item.get('name')}, expert={item.get('expert_name')}")
