from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# ========== 人气排行榜数据模型 ==========

class PopularityItem(BaseModel):
    """人气排行榜项数据模型"""
    rank: int = Field(..., description="排名")
    code: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    price: float = Field(..., description="当前价格")
    change_ratio: str = Field(..., description="涨跌幅")
    rank_change: Optional[int] = Field(None, description="排名变化")
    crawled_at: Optional[datetime] = Field(None, description="爬取时间")
    
    class Config:
        from_attributes = True

class PopularityListResponse(BaseModel):
    """人气排行榜列表响应模型"""
    success: bool = Field(default=True, description="请求是否成功")
    message: Optional[str] = Field(None, description="响应消息")
    data: List[PopularityItem] = Field(default_factory=list, description="人气排行榜数据列表")
    total: int = Field(..., description="总数据条数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数据条数")

# ========== 资金流向数据模型 ==========

class CapitalFlowItem(BaseModel):
    """资金流向项数据模型"""
    code: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    price: float = Field(..., description="当前价格")
    change_ratio: str = Field(..., description="涨跌幅")
    main_flow: float = Field(..., description="主力资金流入")
    main_flow_text: str = Field(..., description="主力资金流入文本")
    crawled_at: Optional[datetime] = Field(None, description="爬取时间")
    
    class Config:
        from_attributes = True

class CapitalFlowListResponse(BaseModel):
    """资金流向列表响应模型"""
    success: bool = Field(default=True, description="请求是否成功")
    message: Optional[str] = Field(None, description="响应消息")
    data: List[CapitalFlowItem] = Field(default_factory=list, description="资金流向数据列表")
    total: int = Field(..., description="总数据条数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数据条数")

# ========== 专家排行数据模型 ==========

class ExpertRankingItem(BaseModel):
    """专家排行项数据模型"""
    expert_name: str = Field(..., description="达人名称")
    name: str = Field(..., description="股票名称")
    code: str = Field(..., description="股票代码")
    analysis_reason: str = Field(..., description="分析理由")
    analysis_time: str = Field(..., description="分析时间")
    analysis_price: str = Field(..., description="分析价格")
    success_count: int = Field(..., description="分析数")
    success_rate: float = Field(..., description="成功率")
    source_url: str = Field(..., description="来源URL")
    crawled_at: Optional[datetime] = Field(None, description="爬取时间")
    
    class Config:
        from_attributes = True

class ExpertRankingListResponse(BaseModel):
    """专家排行列表响应模型"""
    success: bool = Field(default=True, description="请求是否成功")
    message: Optional[str] = Field(None, description="响应消息")
    data: List[ExpertRankingItem] = Field(default_factory=list, description="专家排行数据列表")
    total: int = Field(..., description="总数据条数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数据条数")

# ========== 交叉分析数据模型 ==========

class CrossAnalysisItem(BaseModel):
    """交叉分析项数据模型"""
    expert_name: str = Field(..., description="达人名称")
    name: str = Field(..., description="股票名称")
    code: str = Field(..., description="股票代码")
    analysis_reason: str = Field(..., description="分析理由")
    analysis_time: str = Field(..., description="分析时间")
    analysis_price: str = Field(..., description="分析价格")
    success_count: int = Field(..., description="分析数")
    success_rate: float = Field(..., description="成功率")
    source_url: str = Field(..., description="来源URL")
    popularity_rank: Optional[int] = Field(None, description="人气排名")
    capital_flow_rank: Optional[int] = Field(None, description="资金流向排名")
    limit_up: Optional[bool] = Field(None, description="是否涨停")
    crawled_at: Optional[datetime] = Field(None, description="爬取时间")
    ambusher_count: Optional[int] = Field(None, description="伏击人数量")
    
    class Config:
        from_attributes = True

class CrossAnalysisListResponse(BaseModel):
    """交叉分析列表响应模型"""
    success: bool = Field(default=True, description="请求是否成功")
    message: Optional[str] = Field(None, description="响应消息")
    data: List[CrossAnalysisItem] = Field(default_factory=list, description="交叉分析数据列表")
    total: int = Field(..., description="总数据条数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数据条数")