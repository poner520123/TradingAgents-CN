from fastapi import APIRouter, Query, HTTPException
from typing import List, Dict, Optional
from app.services.st_filter_service import st_filter_service

router = APIRouter(prefix="/st-filter", tags=["ST股票过滤"])

@router.get("/status")
async def get_st_filter_status():
    """获取ST过滤服务状态"""
    return {
        "status": "healthy",
        "st_stock_count": len(st_filter_service.st_stock_names),
        "last_update_time": st_filter_service.last_update_time,
        "should_update": st_filter_service.should_update()
    }

@router.get("/stocks")
async def get_st_stocks(
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500)
):
    """获取ST股票列表"""
    stocks = st_filter_service.get_stock_list()
    total = len(stocks)
    skip = (page - 1) * limit
    paginated_stocks = stocks[skip:skip + limit]
    
    return {
        "data": paginated_stocks,
        "total": total,
        "page": page,
        "limit": limit
    }

@router.post("/stocks")
async def add_st_stocks(stocks: List[Dict]):
    """批量添加ST股票"""
    result = st_filter_service.update_st_stock_list(stocks)
    return result

@router.delete("/stocks/{stock_name}")
async def remove_st_stock(stock_name: str):
    """移除ST股票"""
    from app.core.database import get_mongo_db_sync
    db = get_mongo_db_sync()
    result = db["st_stocks"].delete_one({"stock_name": stock_name})
    
    if result.deleted_count > 0:
        # 重新加载缓存
        st_filter_service.load_st_stocks()
        return {"success": True, "message": f"成功移除ST股票: {stock_name}"}
    else:
        raise HTTPException(status_code=404, detail=f"未找到ST股票: {stock_name}")

@router.post("/sync")
async def sync_st_stocks():
    """从API同步ST股票列表"""
    result = st_filter_service.sync_st_stocks_from_api()
    return result

@router.get("/logs")
async def get_filter_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500)
):
    """获取ST股票过滤日志"""
    return st_filter_service.get_filter_logs(limit=limit, page=page)

@router.get("/check")
async def check_st_status(
    stock_name: Optional[str] = Query(None),
    stock_code: Optional[str] = Query(None)
):
    """检查股票是否为ST股票"""
    if not stock_name and not stock_code:
        raise HTTPException(status_code=400, detail="必须提供股票名称或股票代码")
    
    return st_filter_service.get_stock_status(stock_name, stock_code)

@router.post("/filter")
async def filter_st_stocks(data: List[Dict]):
    """过滤数据中的ST股票"""
    return st_filter_service.filter_st_stocks(data)