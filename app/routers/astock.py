from fastapi import APIRouter, Depends, HTTPException
from app.services.scrapy_crawler_service import ScrapyCrawlerService
from app.models.astock_models import (
    PopularityListResponse,
    CapitalFlowListResponse,
    ExpertRankingListResponse,
    CrossAnalysisListResponse
)
from typing import Optional

router = APIRouter(
    prefix="/astock",
    tags=["astock"],
    responses={404: {"description": "Not found"}},
)

def get_scrapy_crawler_service():
    """获取ScrapyCrawlerService实例"""
    return ScrapyCrawlerService()

@router.get("/popularity", response_model=PopularityListResponse, tags=["astock"])
async def get_popularity_data(
    page: int = 1,
    page_size: int = 20,
    service: ScrapyCrawlerService = Depends(get_scrapy_crawler_service)
):
    """
    获取人气排行榜数据
    
    - **page**: 当前页码，默认为1
    - **page_size**: 每页数据条数，默认为20
    """
    try:
        data, total = service.get_popularity_data(page, page_size)
        return PopularityListResponse(
            success=True,
            data=data,
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        return PopularityListResponse(
            success=False,
            message=f"获取人气排行榜数据失败: {str(e)}",
            data=[],
            total=0,
            page=page,
            page_size=page_size
        )

@router.get("/capital-flow", response_model=CapitalFlowListResponse, tags=["astock"])
async def get_capital_flow_data(
    page: int = 1,
    page_size: int = 20,
    service: ScrapyCrawlerService = Depends(get_scrapy_crawler_service)
):
    """
    获取资金流向数据
    
    - **page**: 当前页码，默认为1
    - **page_size**: 每页数据条数，默认为20
    """
    try:
        data, total = service.get_capital_flow_data(page, page_size)
        return CapitalFlowListResponse(
            success=True,
            data=data,
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        return CapitalFlowListResponse(
            success=False,
            message=f"获取资金流向数据失败: {str(e)}",
            data=[],
            total=0,
            page=page,
            page_size=page_size
        )

@router.get("/expert-ranking", response_model=ExpertRankingListResponse, tags=["astock"])
async def get_expert_ranking_data(
    page: int = 1,
    page_size: int = 20,
    service: ScrapyCrawlerService = Depends(get_scrapy_crawler_service)
):
    """
    获取专家排行数据
    
    - **page**: 当前页码，默认为1
    - **page_size**: 每页数据条数，默认为20
    """
    try:
        data, total = service.get_expert_ranking_data(page, page_size)
        return ExpertRankingListResponse(
            success=True,
            data=data,
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        return ExpertRankingListResponse(
            success=False,
            message=f"获取专家排行数据失败: {str(e)}",
            data=[],
            total=0,
            page=page,
            page_size=page_size
        )

@router.get("/cross-analysis", response_model=CrossAnalysisListResponse, tags=["astock"])
async def get_cross_analysis_data(
    page: int = 1,
    page_size: int = 20,
    service: ScrapyCrawlerService = Depends(get_scrapy_crawler_service)
):
    """
    获取交叉分析数据
    
    - **page**: 当前页码，默认为1
    - **page_size**: 每页数据条数，默认为20
    """
    try:
        data, total = service.get_cross_analysis_data(page, page_size)
        return CrossAnalysisListResponse(
            success=True,
            data=data,
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        return CrossAnalysisListResponse(
            success=False,
            message=f"获取交叉分析数据失败: {str(e)}",
            data=[],
            total=0,
            page=page,
            page_size=page_size
        )

@router.get("/hot-experts", response_model=CrossAnalysisListResponse, tags=["astock"])
async def get_hot_experts_data(
    limit: int = 20,
    service: ScrapyCrawlerService = Depends(get_scrapy_crawler_service)
):
    """
    获取仪表板达人热点数据
    
    提取交叉分析列表中，人气和资金两列都有数值（不能为空，必须大于0），
    并且按照分析时间最新的数值之和从小到大排列，提取指定数量的记录。
    
    - **limit**: 返回数据条数，默认为15
    """
    try:
        data = service.get_hot_experts_data(limit)
        return CrossAnalysisListResponse(
            success=True,
            data=data,
            total=len(data),
            page=1,
            page_size=limit
        )
    except Exception as e:
        return CrossAnalysisListResponse(
            success=False,
            message=f"获取达人热点数据失败: {str(e)}",
            data=[],
            total=0,
            page=1,
            page_size=limit
        )

@router.post("/run-crawlers", tags=["astock"])
async def run_all_crawlers(
    service: ScrapyCrawlerService = Depends(get_scrapy_crawler_service)
):
    """
    手动触发所有爬虫任务
    """
    try:
        total_saved = service.run_all_crawlers()
        return {
            "success": True,
            "message": f"所有爬虫任务执行完成，共保存 {total_saved} 条新数据"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"执行爬虫任务失败: {str(e)}"
        }