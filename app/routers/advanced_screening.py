from __future__ import annotations

from typing import List, Dict
from fastapi import APIRouter, HTTPException, Query
from app.services.advanced_stock_selector_service import advanced_stock_selector_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/advanced-screening", tags=["advanced-screening"])


@router.get("/3d-resonance", response_model=Dict)
async def get_3d_resonance_stocks(
    limit: int = Query(default=10, ge=1, le=50, description="返回股票数量")
):
    """
    获取三维共振选股结果
    
    使用三维共振方法筛选最可能次日涨停的股票：
    1. 量能共振：成交量放大
    2. 价格共振：突破左侧压力位（左峰或平台）
    3. 均线共振：均线多头排列（5>13>21）
    
    返回按共振评分排序的股票列表
    """
    try:
        logger.info(f"开始执行三维共振选股，限制数量: {limit}")
        
        # 执行高级筛选
        stocks = advanced_stock_selector_service.select_stocks_for_next_day_limit_up(limit=limit)
        
        if not stocks:
            return {
                "success": False,
                "message": "未找到符合条件的股票",
                "data": []
            }
        
        # 生成报告
        results = []
        for stock in stocks:
            report = advanced_stock_selector_service.generate_3d_resonance_report(stock)
            result = {
                "stock_code": stock.get("stock_code"),
                "stock_name": stock.get("stock_name"),
                "current_price": stock.get("current_price"),
                "increase": stock.get("increase"),
                "resonance_score": stock.get("resonance_score"),
                "report": report,
                "crawled_at": stock.get("crawled_at")
            }
            results.append(result)
        
        # 保存筛选结果
        for stock in stocks:
            report = advanced_stock_selector_service.generate_3d_resonance_report(stock)
            advanced_stock_selector_service.save_screening_result(stock, report)
        
        return {
            "success": True,
            "message": f"三维共振选股完成，共选出 {len(results)} 个股票",
            "data": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"三维共振选股失败: {e}")
        raise HTTPException(status_code=500, detail=f"三维共振选股失败: {str(e)}")


@router.get("/ma-bullish", response_model=Dict)
async def get_ma_bullish_stocks(
    limit: int = Query(default=20, ge=1, le=50, description="返回股票数量")
):
    """
    获取均线多头排列的股票
    
    筛选条件：
    1. 5日均线 > 13日均线 > 21日均线
    2. 最新涨幅为正
    3. 排除涨停股票
    """
    try:
        logger.info(f"开始筛选均线多头股票，限制数量: {limit}")
        
        # 获取最新股票数据
        stocks = advanced_stock_selector_service.get_latest_stock_data(limit=100)
        
        if not stocks:
            return {
                "success": False,
                "message": "未获取到股票数据",
                "data": []
            }
        
        # 筛选均线多头股票
        ma_bullish_stocks = []
        for stock in stocks:
            try:
                stock_code = stock.get("stock_code")
                if not stock_code:
                    continue
                
                ma5, ma13, ma21 = advanced_stock_selector_service.calculate_moving_averages(stock_code)
                if advanced_stock_selector_service.is_ma_bullish(ma5, ma13, ma21):
                    ma_bullish_stocks.append({
                        **stock,
                        "ma5": ma5,
                        "ma13": ma13,
                        "ma21": ma21
                    })
            except Exception as e:
                logger.error(f"处理股票 {stock.get('stock_code')} 失败: {e}")
                continue
        
        # 按涨幅降序排序
        ma_bullish_stocks.sort(
            key=lambda x: float(x.get("increase", "0").replace("%", "")),
            reverse=True
        )
        
        # 返回前N个
        result = ma_bullish_stocks[:limit]
        
        return {
            "success": True,
            "message": f"均线多头股票筛选完成，共选出 {len(result)} 个股票",
            "data": result,
            "count": len(result)
        }
        
    except Exception as e:
        logger.error(f"均线多头股票筛选失败: {e}")
        raise HTTPException(status_code=500, detail=f"均线多头股票筛选失败: {str(e)}")


@router.get("/breakout-stocks", response_model=Dict)
async def get_breakout_stocks(
    limit: int = Query(default=15, ge=1, le=50, description="返回股票数量")
):
    """
    获取突破左侧压力位的股票
    
    筛选条件：
    1. 突破左侧压力位（左峰或平台）
    2. 最新涨幅为正
    3. 排除涨停股票
    """
    try:
        logger.info(f"开始筛选突破压力位股票，限制数量: {limit}")
        
        # 获取最新股票数据
        stocks = advanced_stock_selector_service.get_latest_stock_data(limit=100)
        
        if not stocks:
            return {
                "success": False,
                "message": "未获取到股票数据",
                "data": []
            }
        
        # 筛选突破压力位股票
        breakout_stocks = []
        for stock in stocks:
            try:
                stock_code = stock.get("stock_code")
                current_price = float(stock.get("current_price", 0))
                if not stock_code or current_price <= 0:
                    continue
                
                if advanced_stock_selector_service.is_breakout_left_pressure(stock_code, current_price):
                    pressure_ratio = advanced_stock_selector_service.calculate_left_pressure(stock_code)
                    breakout_stocks.append({
                        **stock,
                        "pressure_ratio": pressure_ratio
                    })
            except Exception as e:
                logger.error(f"处理股票 {stock.get('stock_code')} 失败: {e}")
                continue
        
        # 按突破强度排序（压力比率接近1的优先）
        breakout_stocks.sort(
            key=lambda x: abs(x.get("pressure_ratio", 0) - 1),
            reverse=False
        )
        
        # 返回前N个
        result = breakout_stocks[:limit]
        
        return {
            "success": True,
            "message": f"突破压力位股票筛选完成，共选出 {len(result)} 个股票",
            "data": result,
            "count": len(result)
        }
        
    except Exception as e:
        logger.error(f"突破压力位股票筛选失败: {e}")
        raise HTTPException(status_code=500, detail=f"突破压力位股票筛选失败: {str(e)}")
