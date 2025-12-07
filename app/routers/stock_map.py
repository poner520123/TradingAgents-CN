from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Optional, Any
from app.services.stock_map_service import stock_map_service
from app.models.stock_map_models import StockCodeRequest, StockCodeResponse, StockNameCodeMapResponse

router = APIRouter()

@router.get("/stock-map/codes", response_model=StockCodeResponse)
async def get_stock_code_by_name(
    name: str = Query(..., description="股票名称")
):
    """根据股票名称获取股票代码"""
    code = stock_map_service.get_code_by_name(name)
    if code:
        return StockCodeResponse(
            success=True,
            data={"code": code, "found": True},
            message="获取成功"
        )
    else:
        return StockCodeResponse(
            success=False,
            data={"code": "", "found": False},
            message="未找到对应股票代码"
        )

@router.post("/stock-map/codes/batch", response_model=Dict[str, str])
async def get_stock_codes_by_names(
    request: StockCodeRequest
):
    """根据股票名称列表批量获取股票代码"""
    return stock_map_service.get_codes_by_names(request.names)

@router.get("/stock-map/maps", response_model=dict)
async def get_stock_maps(
    skip: int = Query(0, ge=0, description="跳过条数"),
    limit: int = Query(100, ge=1, le=1000, description="返回条数")
):
    """获取股票名称和代码映射列表"""
    maps = stock_map_service.get_all_maps(skip=skip, limit=limit)
    total = stock_map_service.get_total_count()
    return {
        "success": True,
        "data": maps,
        "total": total,
        "message": "获取成功"
    }

@router.get("/stock-map/count", response_model=Dict[str, int])
async def get_stock_map_count():
    """获取股票名称和代码映射总数"""
    count = stock_map_service.get_total_count()
    return {"count": count}

@router.post("/stock-map/supplement", response_model=Dict[str, int])
async def supplement_stock_mappings():
    """遍历A股上市公司名称，补充缺失的映射"""
    result = stock_map_service.supplement_stock_mappings()
    return result

@router.post("/stock-map/resync", response_model=Dict[str, Any])
async def resync_stock_mappings():
    """清空映射并重新同步"""
    result = stock_map_service.resync_mappings()
    # 重新同步后重建缓存
    stock_map_service._rebuild_cache()
    return result

@router.get("/stock-map/name")
async def get_stock_name_by_code(
    code: str = Query(..., description="股票代码")
):
    """根据股票代码获取股票名称"""
    name = stock_map_service.get_name_by_code(code)
    from fastapi.responses import JSONResponse
    if name:
        return JSONResponse(
            content={
                "success": True,
                "data": name,
                "message": "获取成功"
            },
            media_type="application/json; charset=utf-8"
        )
    else:
        return JSONResponse(
            content={
                "success": False,
                "data": "",
                "message": "未找到对应股票名称"
            },
            media_type="application/json; charset=utf-8"
        )
