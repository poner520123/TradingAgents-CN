from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class CrawlerData(BaseModel):
    user_name: str = Field(..., description="伏击人")
    success_count: Optional[str] = Field(None, description="成功次数")
    success_rate: Optional[str] = Field(None, description="成功率")
    stock_name: str = Field(..., description="股票名称")
    reason: Optional[str] = Field(None, description="伏击理由")
    time: str = Field(..., description="伏击时间(原始字符串)")
    price: Optional[str] = Field(None, description="伏击价格")
    current_price: Optional[str] = Field(None, description="当前价格")
    increase: Optional[str] = Field(None, description="涨幅")
    limit_up: Optional[str] = Field(None, description="是否涨停")
    limit_up_date: Optional[str] = Field(None, description="涨停日期")
    concepts: Optional[str] = Field(None, description="题材概念")
    crawled_at: datetime = Field(default_factory=datetime.utcnow, description="爬取时间")

class CrawlerDataListResponse(BaseModel):
    success: bool = True
    data: List[CrawlerData] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
    message: str = ""

class StartCrawlRequest(BaseModel):
    pages: int = 1
    force: bool = False
