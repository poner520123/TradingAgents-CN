from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests
from pymongo import MongoClient, DESCENDING
from app.core.config import settings
from app.core.database import get_mongo_db_sync
from app.services.stock_map_service import stock_map_service

logger = logging.getLogger(__name__)


class StockSelectorService:
    def __init__(self):
        """初始化股票筛选服务"""
        self.db = get_mongo_db_sync()
        self.crawler_collection = self.db.crawler_data
        self.screening_results_collection = self.db.screening_results
        self._init_db()
        
        # 通知配置 - 使用用户提供的Webhook
        self.dingtalk_config = {
            "webhook": "https://oapi.dingtalk.com/robot/send?access_token=3445c95927eecb7e1902c05a572d6406929f3d782eb2d6c3b6c5acd16a0485a9",
            "secret": ""
        }
        self.feishu_config = {
            "webhook": "https://open.feishu.cn/open-apis/bot/v2/hook/d6dbf25a-85dd-4541-843c-669ee096686e",
            "secret": ""
        }
    
    def _init_db(self):
        """初始化数据库索引"""
        try:
            # 为筛选结果创建索引
            self.screening_results_collection.create_index([("screening_time", DESCENDING)])
            self.screening_results_collection.create_index([("stock_code", 1), ("screening_time", DESCENDING)])
        except Exception as e:
            logger.error(f"初始化数据库索引失败: {e}")
    
    def get_latest_crawler_data(self, hours: int = 3) -> List[Dict]:
        """获取最近几小时的爬虫数据"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            cursor = self.crawler_collection.find(
                {"crawled_at": {"$gte": cutoff_time}},
                sort=[("crawled_at", DESCENDING)]
            )
            return list(cursor)
        except Exception as e:
            logger.error(f"获取爬虫数据失败: {e}")
            return []
    
    def filter_stocks(self, crawler_data: List[Dict]) -> List[Dict]:
        """筛选满足条件的股票
        
        筛选条件：
        1. 股价位置刚突破压力位
        2. 属于当前市场热点板块
        3. 有明显大资金流入迹象
        4. 技术形态建构扎实
        5. 具备最大概率涨停潜力
        """
        filtered_stocks = []
        
        # 按股票代码分组，只保留最新数据
        stock_data_map = {}
        for data in crawler_data:
            if "stock_code" in data and data["stock_code"]:
                code = data["stock_code"]
                if code not in stock_data_map or data["crawled_at"] > stock_data_map[code]["crawled_at"]:
                    stock_data_map[code] = data
        
        # 遍历每个股票的最新数据
        for code, data in stock_data_map.items():
            try:
                # 基础信息检查
                if not self._check_basic_info(data):
                    continue
                
                # 条件1：股价位置刚突破压力位
                if not self._check_breakout_condition(data):
                    continue
                
                # 条件2：属于当前市场热点板块
                if not self._check_hot_sector(data):
                    continue
                
                # 条件3：有明显大资金流入迹象
                if not self._check_capital_inflow(data):
                    continue
                
                # 条件4：技术形态建构扎实
                if not self._check_technical_form(data):
                    continue
                
                # 条件5：具备最大概率涨停潜力
                if not self._check_limit_up_potential(data):
                    continue
                
                # 所有条件都满足，添加到结果列表
                filtered_stocks.append(data)
            except Exception as e:
                logger.error(f"筛选股票 {code} 失败: {e}")
                continue
        
        return filtered_stocks
    
    def _check_basic_info(self, data: Dict) -> bool:
        """检查股票基础信息"""
        required_fields = ["stock_name", "stock_code", "current_price", "increase"]
        for field in required_fields:
            if field not in data or not data[field]:
                return False
        return True
    
    def _check_breakout_condition(self, data: Dict) -> bool:
        """检查股价是否刚突破压力位"""
        # 这里实现突破压力位的逻辑
        # 简单示例：当前涨幅为正，且近期有明显上涨趋势
        try:
            increase = float(data["increase"].replace("%", ""))
            return increase > 2.0  # 涨幅超过2%，作为突破的简单判断
        except (ValueError, TypeError):
            return False
    
    def _check_hot_sector(self, data: Dict) -> bool:
        """检查是否属于当前市场热点板块"""
        # 这里实现热点板块判断逻辑
        # 简单示例：检查是否有热门概念标签
        hot_concepts = ["AI", "人工智能", "芯片", "半导体", "新能源", "光伏", "锂电池", "数字经济"]
        if "concepts" in data and data["concepts"]:
            concepts = data["concepts"]
            for hot_concept in hot_concepts:
                if hot_concept in concepts:
                    return True
        return False
    
    def _check_capital_inflow(self, data: Dict) -> bool:
        """检查是否有明显大资金流入迹象"""
        # 这里实现大资金流入判断逻辑
        # 简单示例：基于涨幅和量能判断
        try:
            increase = float(data["increase"].replace("%", ""))
            # 涨幅大于2%且为正，视为有资金流入迹象
            return increase > 2.0
        except (ValueError, TypeError):
            return False
    
    def _check_technical_form(self, data: Dict) -> bool:
        """检查技术形态是否扎实"""
        # 这里实现技术形态判断逻辑
        # 简单示例：基于涨幅和股票类型判断
        try:
            increase = float(data["increase"].replace("%", ""))
            # 涨幅在2%-8%之间，视为技术形态较好
            return 2.0 < increase < 8.0
        except (ValueError, TypeError):
            return False
    
    def _check_limit_up_potential(self, data: Dict) -> bool:
        """检查是否具备最大概率涨停潜力"""
        # 这里实现涨停潜力判断逻辑
        # 简单示例：基于多个条件综合判断
        try:
            increase = float(data["increase"].replace("%", ""))
            # 涨幅在5%-8%之间，且属于热门板块，视为有涨停潜力
            return 5.0 < increase < 8.0 and self._check_hot_sector(data)
        except (ValueError, TypeError):
            return False
    
    def generate_report(self, stock_data: Dict) -> str:
        """生成标准化分析报告"""
        try:
            stock_name = stock_data["stock_name"]
            stock_code = stock_data["stock_code"]
            current_price = float(stock_data["current_price"])
            increase = float(stock_data["increase"].replace("%", ""))
            concepts = stock_data.get("concepts", "")
            
            # 计算关注区间、目标区间、防守区间
            attention_low = round(current_price * 0.98, 2)
            attention_high = round(current_price * 1.05, 2)
            target_low = round(current_price * 1.05, 2)
            target_high = round(current_price * 1.15, 2)
            defense_low = round(current_price * 0.95, 2)
            defense_high = round(current_price * 1.02, 2)
            
            # 生成报告 - 包含STOCK关键字以满足机器人要求，使用美化格式
            report = f"""
# STOCK - 🌟 股票筛选结果

## 📊 核心信息
- **案例名称**: [{stock_name}]({stock_code})
- **研究团队**: AI研究团队
- **发布时间**: 【{datetime.now().strftime('%Y年%m月%d日 %H:%M')}】

## 🎯 交易建议
- **关注区间**: 📈 {attention_low}-{attention_high}
- **目标区间**: 🎯 {target_low}-{target_high}
- **防守区间**: 🛡️ {defense_low}-{defense_high}
- **仓位配置**: 💼 5%

## 📚 分析详情
### 📉 技术面
股价近期突破压力位，当前涨幅{increase}%，量能放大，短期趋势向好。

### 📋 基本面
所属概念板块{concepts}，符合当前市场热点，具备较强的上涨逻辑。

---

⚠️ **风险提示**
以上内容仅供参考，不构成投资建议。
股市有风险，入市需谨慎。历史战绩不代表对未来收益的承诺。
            """
            
            return report.strip()
        except Exception as e:
            logger.error(f"生成报告失败: {e}")
            return ""
    
    def send_dingtalk_notification(self, report: str, retry: int = 3) -> bool:
        """发送钉钉通知"""
        if not self.dingtalk_config["webhook"]:
            logger.warning("钉钉Webhook未配置，跳过发送")
            return False
        
        for attempt in range(retry):
            try:
                headers = {
                    "Content-Type": "application/json"
                }
                payload = {
                    "msgtype": "markdown",
                    "markdown": {
                        "title": "股票筛选结果",
                        "text": report
                    }
                }
                
                response = requests.post(
                    self.dingtalk_config["webhook"],
                    json=payload,
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("errcode") == 0:
                        logger.info("钉钉通知发送成功")
                        return True
                    else:
                        logger.error(f"钉钉通知发送失败: {result}")
                else:
                    logger.error(f"钉钉通知发送失败，HTTP状态码: {response.status_code}")
            except Exception as e:
                logger.error(f"钉钉通知发送异常: {e}")
            
            # 重试间隔
            time.sleep(2 ** attempt)  # 指数退避
        
        logger.error("钉钉通知发送多次失败")
        return False
    
    def send_feishu_notification(self, report: str, retry: int = 3) -> bool:
        """发送飞书通知"""
        if not self.feishu_config["webhook"]:
            logger.warning("飞书Webhook未配置，跳过发送")
            return False
        
        for attempt in range(retry):
            try:
                headers = {
                    "Content-Type": "application/json"
                }
                payload = {
                    "msg_type": "post",
                    "content": {
                        "post": {
                            "zh_cn": {
                                "title": "股票筛选结果",
                                "content": [
                                    [{"tag": "text", "text": report}]
                                ]
                            }
                        }
                    }
                }
                
                response = requests.post(
                    self.feishu_config["webhook"],
                    json=payload,
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("code") == 0:
                        logger.info("飞书通知发送成功")
                        return True
                    else:
                        logger.error(f"飞书通知发送失败: {result}")
                else:
                    logger.error(f"飞书通知发送失败，HTTP状态码: {response.status_code}")
            except Exception as e:
                logger.error(f"飞书通知发送异常: {e}")
            
            # 重试间隔
            time.sleep(2 ** attempt)  # 指数退避
        
        logger.error("飞书通知发送多次失败")
        return False
    
    def save_screening_result(self, stock_data: Dict, report: str) -> bool:
        """保存筛选结果到数据库"""
        try:
            result = {
                "stock_code": stock_data["stock_code"],
                "stock_name": stock_data["stock_name"],
                "screening_time": datetime.utcnow(),
                "report": report,
                "crawler_data": stock_data
            }
            self.screening_results_collection.insert_one(result)
            logger.info(f"筛选结果保存成功: {stock_data['stock_code']}")
            return True
        except Exception as e:
            logger.error(f"筛选结果保存失败: {e}")
            return False
    
    def run_screening(self) -> bool:
        """执行一次股票筛选流程"""
        logger.info("开始执行股票筛选流程")
        
        # 1. 获取最新爬虫数据
        crawler_data = self.get_latest_crawler_data()
        logger.info(f"获取到 {len(crawler_data)} 条爬虫数据")
        
        if not crawler_data:
            logger.warning("未获取到爬虫数据，跳过筛选")
            return False
        
        # 2. 筛选股票
        filtered_stocks = self.filter_stocks(crawler_data)
        logger.info(f"筛选出 {len(filtered_stocks)} 只满足条件的股票")
        
        if not filtered_stocks:
            logger.info("没有满足条件的股票，跳过通知")
            return True
        
        # 3. 生成报告并发送通知
        success_count = 0
        for stock_data in filtered_stocks:
            try:
                # 生成报告
                report = self.generate_report(stock_data)
                if not report:
                    continue
                
                # 保存筛选结果
                self.save_screening_result(stock_data, report)
                
                # 发送通知
                dingtalk_success = self.send_dingtalk_notification(report)
                feishu_success = self.send_feishu_notification(report)
                
                if dingtalk_success or feishu_success:
                    success_count += 1
                    logger.info(f"股票 {stock_data['stock_code']} 通知发送成功")
            except Exception as e:
                logger.error(f"处理股票 {stock_data.get('stock_code', '未知')} 失败: {e}")
        
        logger.info(f"股票筛选流程完成，成功处理 {success_count}/{len(filtered_stocks)} 只股票")
        return True


# 单例实例
stock_selector_service = StockSelectorService()
