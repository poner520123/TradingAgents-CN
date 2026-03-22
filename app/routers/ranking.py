from fastapi import APIRouter, HTTPException
from app.core.crawler_fund import fund_ranking_crawler
from app.core.crawler_popularity import popularity_ranking_crawler
from app.services.ranking_scheduler import ranking_scheduler

router = APIRouter()

@router.get("/fund")
async def get_fund_ranking(limit: int = 50):
    """获取资金排行数据"""
    try:
        data = fund_ranking_crawler.get_fund_ranking(limit)
        return {
            "success": True,
            "data": data,
            "count": len(data),
            "message": "资金排行数据获取成功"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取资金排行数据失败: {str(e)}")

@router.get("/popularity")
async def get_popularity_ranking(limit: int = 50):
    """获取人气排行数据"""
    try:
        data = popularity_ranking_crawler.get_popularity_ranking(limit)
        return {
            "success": True,
            "data": data,
            "count": len(data),
            "message": "人气排行数据获取成功"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取人气排行数据失败: {str(e)}")

@router.get("/status")
async def get_ranking_status():
    """获取排行数据状态"""
    try:
        status = ranking_scheduler.get_status()
        return {
            "success": True,
            "data": status,
            "message": "排行数据状态获取成功"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取排行数据状态失败: {str(e)}")

@router.post("/crawl/fund")
async def crawl_fund_ranking():
    """手动触发资金排行爬取"""
    try:
        result = fund_ranking_crawler.crawl_fund_ranking()
        return {
            "success": True,
            "data": {"crawled_count": result},
            "message": f"资金排行爬取成功，获取 {result} 条记录"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"资金排行爬取失败: {str(e)}")

@router.post("/crawl/popularity")
async def crawl_popularity_ranking():
    """手动触发人气排行爬取"""
    try:
        result = popularity_ranking_crawler.crawl_popularity_ranking()
        return {
            "success": True,
            "data": {"crawled_count": result},
            "message": f"人气排行爬取成功，获取 {result} 条记录"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"人气排行爬取失败: {str(e)}")
