from app.services.scrapy_crawler_service import ScrapyCrawlerService

# 获取Scrapy爬虫服务实例
service = ScrapyCrawlerService()

# 获取所有专家排行数据
cursor = service.expert_ranking_collection.find()
all_data = list(cursor)

# 搜索类似名称的股票
search_terms = ['正泰', '东方', '电源', '新能']

print("搜索包含关键词的股票:")
for term in search_terms:
    matches = [item for item in all_data if term in item.get('name', '')]
    if matches:
        print(f"\n包含 '{term}' 的股票:")
        for item in matches[:5]:  # 只显示前5条
            print(f"  name={item.get('name')}, code={item.get('code')}, expert={item.get('expert_name')}")

# 检查数据库中所有股票名称
print(f"\n数据库中所有股票名称 ({len(set(item.get('name') for item in all_data))}个唯一名称):")
unique_names = sorted(set(item.get('name') for item in all_data))
for name in unique_names[:20]:  # 只显示前20个
    print(f"  {name}")
