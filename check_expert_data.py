from app.services.scrapy_crawler_service import ScrapyCrawlerService

# 获取Scrapy爬虫服务实例
service = ScrapyCrawlerService()

# 获取所有专家排行数据
cursor = service.expert_ranking_collection.find()
all_data = list(cursor)

print(f"数据库中专家排行总数据条数: {len(all_data)}")

# 统计股票代码重复情况
from collections import defaultdict
code_counts = defaultdict(int)
for item in all_data:
    code = item.get('code', '')
    code_counts[code] += 1

print('\n股票代码重复情况:')
for code, count in code_counts.items():
    if count > 1:
        print(f'{code}: {count}次')

# 查看具体的重复记录
print('\n重复记录详情:')
for code, count in code_counts.items():
    if count > 1:
        print(f'\n股票代码 {code} 的记录:')
        records = [item for item in all_data if item.get('code') == code]
        for i, record in enumerate(records):
            print(f"  记录{i+1}: expert_name={record.get('expert_name')}, name={record.get('name')}, analysis_time={record.get('analysis_time')}")
