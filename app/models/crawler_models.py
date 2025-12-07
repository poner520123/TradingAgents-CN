from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class CrawlerData(BaseModel):
    user_name: str = Field(..., description="伏击人")
    success_count: Optional[int] = Field(None, description="成功次数")
    success_rate: Optional[str] = Field(None, description="成功率")
    stock_name: str = Field(..., description="股票名称")
    stock_code: Optional[str] = Field(None, description="股票代码")
    reason: Optional[str] = Field(None, description="伏击理由")
    time: str = Field(..., description="伏击时间(原始字符串)")
    price: Optional[str] = Field(None, description="伏击价格")
    current_price: Optional[str] = Field(None, description="当前价格")
    increase: Optional[str] = Field(None, description="涨幅")
    limit_up: Optional[str] = Field(None, description="是否涨停")
    limit_up_date: Optional[str] = Field(None, description="涨停日期")
    concepts: Optional[str] = Field(None, description="题材概念")
    crawled_at: datetime = Field(default_factory=datetime.utcnow, description="爬取时间")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "user_name": "过犹不及6666",
                    "success_count": 6239,
                    "success_rate": "70.10%",
                    "stock_name": "骏亚科技",
                    "stock_code": "603386",
                    "reason": "事件驱动",
                    "time": "2025-12-06  21:46",
                    "price": "16.65",
                    "current_price": "",
                    "increase": "",
                    "limit_up": "--",
                    "limit_up_date": "",
                    "concepts": "暂未分类",
                    "crawled_at": "2025-12-06T13:51:49.043000"
                }
            ]
        },
        "exclude_none": False
    }

class CrawlerDataListResponse(BaseModel):
    success: bool = True
    data: List[CrawlerData] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
    message: str = ""

class StartCrawlRequest(BaseModel):
    pages: int = 5
    force: bool = False
