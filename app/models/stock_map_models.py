from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class StockNameCodeMap(BaseModel):
    """股票名称到代码的映射模型"""
    name: str
    code: str
    market: Optional[str] = None
    updated_at: datetime = datetime.utcnow()
    created_at: datetime = datetime.utcnow()

class StockNameCodeMapResponse(BaseModel):
    """股票名称到代码的映射响应模型"""
    success: bool
    data: Optional[List[StockNameCodeMap]] = None
    total: int = 0
    message: str = ""

class StockCodeRequest(BaseModel):
    """获取股票代码的请求模型"""
    names: List[str]

class StockCodeResponse(BaseModel):
    """获取股票代码的响应模型"""
    success: bool
    data: Optional[dict] = None
    message: str = ""
