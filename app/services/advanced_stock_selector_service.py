from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import numpy as np
from pymongo import MongoClient, DESCENDING
from app.core.config import settings
from app.core.database import get_mongo_db_sync
from app.services.stock_map_service import stock_map_service
from app.services.crawler_service import crawler_service

logger = logging.getLogger(__name__)


class AdvancedStockSelectorService:
    """高级股票筛选服务 - 基于三维共振方法"""
    
    def __init__(self):
        """初始化高级股票筛选服务"""
        self.db = get_mongo_db_sync()
        self.crawler_collection = self.db.crawler_data
        self.stock_data_collection = self.db.stock_data
        self.screening_results_collection = self.db.screening_results
        self._init_db()
    
    def _init_db(self):
        """初始化数据库索引"""
        try:
            self.screening_results_collection.create_index([("screening_time", DESCENDING)])
            self.screening_results_collection.create_index([("stock_code", 1), ("screening_time", DESCENDING)])
        except Exception as e:
            logger.error(f"初始化数据库索引失败: {e}")
    
    def get_latest_stock_data(self, limit: int = 100) -> List[Dict]:
        """获取最新涨幅的前N个股票数据"""
        try:
            # 获取最近24小时的数据
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            
            # 查询并按涨幅降序排序
            cursor = self.crawler_collection.find(
                {"crawled_at": {"$gte": cutoff_time}, "increase": {"$exists": True}},
                sort=[("increase", DESCENDING)]
            ).limit(limit)
            
            stocks = list(cursor)
            
            # 排除涨停的股票（涨幅>=9.9%）
            filtered_stocks = []
            for stock in stocks:
                try:
                    increase = float(stock["increase"].replace("%", ""))
                    if increase < 9.9:  # 排除涨停
                        filtered_stocks.append(stock)
                except (ValueError, TypeError):
                    continue
            
            return filtered_stocks
            
        except Exception as e:
            logger.error(f"获取最新股票数据失败: {e}")
            return []
    
    def calculate_moving_averages(self, stock_code: str, days: int = 30) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """计算股票的5日、13日、21日均线"""
        try:
            # 获取股票历史数据
            cursor = self.stock_data_collection.find(
                {"code": stock_code},
                sort=[("date", DESCENDING)]
            ).limit(days)
            
            prices = [doc.get("close") for doc in cursor if doc.get("close")]
            
            if len(prices) < 21:
                return None, None, None
            
            # 计算均线
            ma5 = np.mean(prices[:5])
            ma13 = np.mean(prices[:13])
            ma21 = np.mean(prices[:21])
            
            return ma5, ma13, ma21
            
        except Exception as e:
            logger.error(f"计算均线失败 {stock_code}: {e}")
            return None, None, None
    
    def is_ma_bullish(self, ma5: float, ma13: float, ma21: float) -> bool:
        """判断是否均线多头排列（5>13>21）"""
        if ma5 is None or ma13 is None or ma21 is None:
            return False
        
        # 均线多头排列：5日均线 > 13日均线 > 21日均线
        return ma5 > ma13 and ma13 > ma21
    
    def calculate_left_pressure(self, stock_code: str, days: int = 60) -> float:
        """计算左侧压力位（左峰或平台）"""
        try:
            # 获取股票历史数据
            cursor = self.stock_data_collection.find(
                {"code": stock_code},
                sort=[("date", DESCENDING)]
            ).limit(days)
            
            prices = [doc.get("high") for doc in cursor if doc.get("high")]
            
            if len(prices) < 20:
                return 0
            
            # 计算最近20天的最高价作为左峰压力
            recent_highs = prices[:20]
            left_peak = max(recent_highs)
            
            # 计算最近5天的平均价格
            recent_prices = prices[:5]
            current_avg = np.mean(recent_prices)
            
            # 如果当前价格接近左峰，视为突破压力位
            pressure_ratio = current_avg / left_peak if left_peak > 0 else 0
            
            return pressure_ratio
            
        except Exception as e:
            logger.error(f"计算左侧压力失败 {stock_code}: {e}")
            return 0
    
    def is_breakout_left_pressure(self, stock_code: str, current_price: float) -> bool:
        """判断是否突破左侧压力位"""
        try:
            pressure_ratio = self.calculate_left_pressure(stock_code)
            
            # 突破条件：当前价格接近或超过左峰（0.95-1.05之间）
            return 0.95 <= pressure_ratio <= 1.05
            
        except Exception as e:
            logger.error(f"判断突破压力位失败 {stock_code}: {e}")
            return False
    
    def calculate_volume_change(self, stock_code: str, days: int = 5) -> float:
        """计算成交量变化"""
        try:
            # 获取股票历史数据
            cursor = self.stock_data_collection.find(
                {"code": stock_code},
                sort=[("date", DESCENDING)]
            ).limit(days + 5)  # 多取5天计算平均值
            
            volumes = [doc.get("volume") for doc in cursor if doc.get("volume")]
            
            if len(volumes) < days + 5:
                return 0
            
            # 最近5天成交量
            recent_volumes = volumes[:days]
            recent_avg = np.mean(recent_volumes)
            
            # 之前5天成交量
            previous_volumes = volumes[days:days + 5]
            previous_avg = np.mean(previous_volumes)
            
            # 成交量变化率
            if previous_avg > 0:
                volume_change = (recent_avg - previous_avg) / previous_avg
            else:
                volume_change = 0
            
            return volume_change
            
        except Exception as e:
            logger.error(f"计算成交量变化失败 {stock_code}: {e}")
            return 0
    
    def calculate_3d_resonance_score(self, stock: Dict) -> float:
        """计算三维共振评分
        
        三维共振方法参考：
        1. 量能共振：成交量放大
        2. 价格共振：突破压力位
        3. 均线共振：均线多头排列
        
        评分越高，次日涨停概率越大
        """
        try:
            stock_code = stock.get("stock_code")
            current_price = float(stock.get("current_price", 0))
            increase = float(stock.get("increase", "0").replace("%", ""))
            
            if not stock_code or current_price <= 0:
                return 0
            
            score = 0
            
            # 1. 量能共振 (30分)
            volume_change = self.calculate_volume_change(stock_code)
            if volume_change > 0.3:  # 成交量放大30%以上
                score += 30
            elif volume_change > 0.1:
                score += 15
            
            # 2. 价格共振 (40分)
            if self.is_breakout_left_pressure(stock_code, current_price):
                score += 40
            
            # 3. 均线共振 (30分)
            ma5, ma13, ma21 = self.calculate_moving_averages(stock_code)
            if self.is_ma_bullish(ma5, ma13, ma21):
                score += 30
            
            # 4. 涨幅加分 (额外20分)
            if 5 <= increase < 8:
                score += 10
            elif 2 <= increase < 5:
                score += 5
            
            # 5. 价格位置加分 (额外10分)
            if ma21 is not None and current_price > ma21 * 1.02:
                score += 10
            
            return score
            
        except Exception as e:
            logger.error(f"计算三维共振评分失败: {e}")
            return 0
    
    def select_stocks_for_next_day_limit_up(self, limit: int = 10) -> List[Dict]:
        """选择最可能次日涨停的股票
        
        筛选流程：
        1. 获取最新涨幅前100个股票
        2. 排除涨停股票
        3. 计算三维共振评分
        4. 按评分排序，取前N个
        """
        try:
            logger.info("开始执行高级股票筛选")
            
            # 1. 获取最新涨幅前100个股票，排除涨停
            stocks = self.get_latest_stock_data(limit=100)
            
            if not stocks:
                logger.warning("未获取到股票数据")
                return []
            
            logger.info(f"获取到 {len(stocks)} 个非涨停股票")
            
            # 2. 计算每个股票的三维共振评分
            scored_stocks = []
            for stock in stocks:
                try:
                    score = self.calculate_3d_resonance_score(stock)
                    if score > 0:
                        scored_stocks.append({
                            **stock,
                            "resonance_score": score
                        })
                except Exception as e:
                    logger.error(f"处理股票 {stock.get('stock_code')} 失败: {e}")
                    continue
            
            # 3. 按评分降序排序
            scored_stocks.sort(key=lambda x: x.get("resonance_score", 0), reverse=True)
            
            # 4. 返回前N个
            result = scored_stocks[:limit]
            
            logger.info(f"筛选完成，共选出 {len(result)} 个高概率涨停股票")
            
            return result
            
        except Exception as e:
            logger.error(f"高级股票筛选失败: {e}")
            return []
    
    def generate_3d_resonance_report(self, stock: Dict) -> str:
        """生成三维共振分析报告"""
        try:
            stock_name = stock.get("stock_name", "未知")
            stock_code = stock.get("stock_code", "未知")
            current_price = float(stock.get("current_price", 0))
            increase = float(stock.get("increase", "0").replace("%", ""))
            resonance_score = stock.get("resonance_score", 0)
            
            ma5, ma13, ma21 = self.calculate_moving_averages(stock_code)
            pressure_ratio = self.calculate_left_pressure(stock_code)
            volume_change = self.calculate_volume_change(stock_code)
            
            # 生成报告
            report = f"""# STOCK - 三维共振选股报告

## 📊 核心信息
- **股票名称**: {stock_name} ({stock_code})
- **当前价格**: {current_price}
- **当前涨幅**: {increase}%
- **共振评分**: {resonance_score}分
- **发布时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## 🎯 三维共振分析

### 1️⃣ 量能共振
- **成交量变化**: {"↑" if volume_change > 0 else "↓"} {abs(volume_change) * 100:.1f}%
- **评分**: {"✅" if volume_change > 0.3 else "⚠️" if volume_change > 0 else "❌"}

### 2️⃣ 价格共振
- **左峰压力比率**: {pressure_ratio:.2f}
- **突破状态**: {"✅ 突破压力位" if 0.95 <= pressure_ratio <= 1.05 else "❌ 未突破"}

### 3️⃣ 均线共振
- **5日均线**: {ma5:.2f if ma5 else "N/A"}
- **13日均线**: {ma13:.2f if ma13 else "N/A"}
- **21日均线**: {ma21:.2f if ma21 else "N/A"}
- **均线状态**: {"✅ 多头排列" if ma5 and ma13 and ma21 and ma5 > ma13 > ma21 else "❌ 非多头"}

## 📈 交易建议
- **关注区间**: {current_price * 0.98:.2f} - {current_price * 1.05:.2f}
- **目标区间**: {current_price * 1.05:.2f} - {current_price * 1.15:.2f}
- **防守区间**: {current_price * 0.95:.2f} - {current_price * 1.02:.2f}

---

⚠️ **风险提示**
以上内容基于三维共振算法分析，仅供参考，不构成投资建议。
股市有风险，入市需谨慎。"""
            
            return report.strip()
            
        except Exception as e:
            logger.error(f"生成三维共振报告失败: {e}")
            return ""
    
    def save_screening_result(self, stock: Dict, report: str) -> bool:
        """保存筛选结果到数据库"""
        try:
            result = {
                "stock_code": stock.get("stock_code"),
                "stock_name": stock.get("stock_name"),
                "screening_time": datetime.utcnow(),
                "resonance_score": stock.get("resonance_score", 0),
                "report": report,
                "stock_data": stock
            }
            self.screening_results_collection.insert_one(result)
            logger.info(f"三维共振筛选结果保存成功: {stock.get('stock_code')}")
            return True
        except Exception as e:
            logger.error(f"保存筛选结果失败: {e}")
            return False


# 单例实例
advanced_stock_selector_service = AdvancedStockSelectorService()
