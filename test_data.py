from app.core.crawler_fund import fund_ranking_crawler
from app.core.crawler_popularity import popularity_ranking_crawler

# 测试资金榜数据
print("资金榜前10条数据:")
fund_data = fund_ranking_crawler.get_fund_ranking(10)
for item in fund_data:
    print(item)

# 测试人气榜数据
print("\n人气榜前10条数据:")
popularity_data = popularity_ranking_crawler.get_popularity_ranking(10)
for item in popularity_data:
    print(item)
