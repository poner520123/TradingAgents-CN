import scrapy

class PopularityItem(scrapy.Item):
    rank = scrapy.Field()
    code = scrapy.Field()
    name = scrapy.Field()
    price = scrapy.Field()
    change_ratio = scrapy.Field()
    rank_change = scrapy.Field()

class CapitalFlowItem(scrapy.Item):
    code = scrapy.Field()
    name = scrapy.Field()
    price = scrapy.Field()
    change_ratio = scrapy.Field()
    main_flow = scrapy.Field()
    main_flow_text = scrapy.Field()

class ExpertRankingItem(scrapy.Item):
    expert_name = scrapy.Field()
    name = scrapy.Field()
    code = scrapy.Field()
    analysis_reason = scrapy.Field()
    analysis_time = scrapy.Field()
    analysis_price = scrapy.Field()
    success_count = scrapy.Field()
    success_rate = scrapy.Field()
    source_url = scrapy.Field()
