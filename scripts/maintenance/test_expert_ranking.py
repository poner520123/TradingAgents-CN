from app.services.scrapy_crawler_service import ScrapyCrawlerService

# 测试专家排行数据
print("=== 测试专家排行数据 ===")
service = ScrapyCrawlerService()
data, total = service.get_expert_ranking_data(page=1, page_size=10)

print(f"Total records: {total}")
print("\n专家排行数据示例:")
for item in data:
    print(f"专家: {item['expert_name']}, 股票: {item['name']}, 成功率: {item['success_rate']}%")
