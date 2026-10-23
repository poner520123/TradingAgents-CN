from app.services.scrapy_crawler_service import ScrapyCrawlerService

# 获取Scrapy爬虫服务实例
service = ScrapyCrawlerService()

# 获取所有专家排行数据
cursor = service.expert_ranking_collection.find()
all_data = list(cursor)

print(f"数据库中专家排行总数据条数: {len(all_data)}")

# 检查缺失股票代码的记录
missing_codes = []
for item in all_data:
    if not item.get('code') or item.get('code') == '':
        missing_codes.append(item)

print(f'\n缺失股票代码的记录数: {len(missing_codes)}')
if missing_codes:
    print('缺失股票代码的记录:')
    for item in missing_codes[:10]:  # 只显示前10条
        print(f"  expert_name={item.get('expert_name')}, name={item.get('name')}, analysis_time={item.get('analysis_time')}")

# 检查特定股票
target_stocks = ['正泰电源', '东方新能']
print(f'\n检查特定股票:')
for stock_name in target_stocks:
    records = [item for item in all_data if stock_name in item.get('name', '')]
    print(f"  {stock_name}: 找到 {len(records)} 条记录")
    for record in records:
        print(f"    - code={record.get('code')}, expert={record.get('expert_name')}")
