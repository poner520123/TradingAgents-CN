from fastapi import APIRouter, Query
from typing import List, Dict, Optional
from app.services.quotes_service import get_quotes_service

router = APIRouter(prefix="/quotes", tags=["quotes"])

@router.post("/batch")
async def get_batch_quotes(codes: List[str]):
    """
    批量获取股票实时行情数据
    
    Args:
        codes: 股票代码列表（6位数字）
    
    Returns:
        字典，key为股票代码，value包含最新价、涨跌幅等信息
    """
    quotes_service = get_quotes_service()
    result = await quotes_service.get_quotes(codes)
    return {"success": True, "data": result}

@router.get("/pct-changes")
async def get_pct_changes(codes: str = Query(None)):
    """
    获取股票涨跌幅数据
    
    Args:
        codes: 逗号分隔的股票代码列表（如 "600519,300750,000858"）
    
    Returns:
        字典，key为股票代码，value包含涨跌幅信息
    """
    if not codes:
        return {"success": False, "message": "请提供股票代码"}
    
    code_list = [c.strip() for c in codes.split(",") if c.strip()]
    quotes_service = get_quotes_service()
    result = await quotes_service.get_quotes(code_list)
    
    # 只返回涨跌幅信息
    pct_result = {code: {"pct_chg": data.get("pct_chg"), "close": data.get("close")} 
                  for code, data in result.items()}
    
    return {"success": True, "data": pct_result}

@router.get("/single/{code}")
async def get_single_quote(code: str):
    """
    获取单只股票的实时行情数据（从同花顺页面获取）
    
    Args:
        code: 股票代码（6位数字）
    
    Returns:
        包含股票代码、名称、最新价、涨跌幅等信息
    """
    quotes_service = get_quotes_service()
    result = await quotes_service.fetch_single_stock(code)
    
    if result:
        return {"success": True, "data": result}
    else:
        return {"success": False, "message": f"无法获取股票 {code} 的数据"}