from app.core.crawler_popularity import PopularityRankingCrawler
from app.core.crawler_fund import FundRankingCrawler

# 测试人气排行数据
print("=== 测试人气排行数据 ===")
popularity_crawler = PopularityRankingCrawler()
popularity_data = popularity_crawler.get_popularity_ranking(limit=5)

for item in popularity_data:
    print(f"股票: {item['name']}, 价格: {item['price']}, 涨跌幅: {item['change_ratio']}")

# 测试资金排行数据
print("\n=== 测试资金排行数据 ===")
fund_crawler = FundRankingCrawler()
fund_data = fund_crawler.get_fund_ranking(limit=5)

for item in fund_data:
    print(f"股票: {item['name']}, 价格: {item['price']}, 涨跌幅: {item['change_ratio']}")
