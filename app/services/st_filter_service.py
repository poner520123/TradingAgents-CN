import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
from pymongo import MongoClient
from app.core.config import settings

logger = logging.getLogger(__name__)

class STFilterService:
    """ST股票过滤服务 - 负责识别和过滤ST股票"""
    
    def __init__(self):
        # MongoDB连接
        from app.core.database import get_mongo_db_sync
        self.db = get_mongo_db_sync()
        self.st_collection = self.db["st_stocks"]
        self.filter_log_collection = self.db["st_filter_logs"]
        
        # ST股票名称模式（A股市场）
        self.st_patterns = [
            re.compile(r'^ST.*'),
            re.compile(r'^\*ST.*'),
            re.compile(r'.*ST$'),
            re.compile(r'.*ST[-_].*'),
        ]
        
        # 初始化ST股票列表
        self.st_stock_names: Set[str] = set()
        self.st_stock_codes: Set[str] = set()
        self.last_update_time: Optional[datetime] = None
        self.update_interval = timedelta(hours=24)  # 每天更新一次
        
        # 加载ST股票列表
        self.load_st_stocks()
    
    def load_st_stocks(self):
        """从数据库加载ST股票列表"""
        logger.info("=" * 60)
        logger.info("📥 开始加载ST股票列表")
        logger.info("=" * 60)
        
        try:
            # 清空现有列表
            self.st_stock_names.clear()
            self.st_stock_codes.clear()
            
            # 从数据库获取ST股票记录
            st_records = self.st_collection.find()
            
            for record in st_records:
                stock_name = record.get("stock_name")
                stock_code = record.get("stock_code")
                
                if stock_name:
                    self.st_stock_names.add(stock_name)
                if stock_code:
                    self.st_stock_codes.add(stock_code)
            
            # 更新最后更新时间
            self.last_update_time = datetime.now()
            
            logger.info(f"✅ ST股票列表加载完成")
            logger.info(f"   - ST股票名称数量: {len(self.st_stock_names)}")
            logger.info(f"   - ST股票代码数量: {len(self.st_stock_codes)}")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"❌ 加载ST股票列表失败: {e}")
    
    def is_st_stock_by_name(self, stock_name: str) -> bool:
        """通过股票名称判断是否为ST股票"""
        if not stock_name:
            return False
        
        # 1. 检查名称是否在ST股票列表中
        if stock_name in self.st_stock_names:
            return True
        
        # 2. 检查名称是否匹配ST模式
        for pattern in self.st_patterns:
            if pattern.match(stock_name):
                return True
        
        return False
    
    def is_st_stock_by_code(self, stock_code: str) -> bool:
        """通过股票代码判断是否为ST股票"""
        if not stock_code:
            return False
        
        # 检查代码是否在ST股票代码列表中
        return stock_code in self.st_stock_codes
    
    def is_st_stock(self, stock_name: Optional[str] = None, stock_code: Optional[str] = None) -> bool:
        """判断股票是否为ST股票（支持名称或代码）"""
        # 优先通过名称判断
        if stock_name and self.is_st_stock_by_name(stock_name):
            return True
        
        # 通过代码判断
        if stock_code and self.is_st_stock_by_code(stock_code):
            return True
        
        return False
    
    def filter_st_stocks(self, data_list: List[Dict]) -> Dict[str, any]:
        """过滤数据列表中的ST股票"""
        filtered = []
        removed = []
        
        for item in data_list:
            stock_name = item.get("stock_name")
            stock_code = item.get("stock_code")
            
            if self.is_st_stock(stock_name, stock_code):
                # 记录被过滤的ST股票
                removed.append({
                    "stock_name": stock_name,
                    "stock_code": stock_code,
                    "reason": "ST股票过滤",
                    "filter_time": datetime.now(),
                    "original_data": item
                })
            else:
                filtered.append(item)
        
        # 记录过滤日志
        if removed:
            self.log_filter(removed)
        
        return {
            "filtered": filtered,
            "removed": removed,
            "total_count": len(data_list),
            "filtered_count": len(filtered),
            "removed_count": len(removed)
        }
    
    def log_filter(self, removed_items: List[Dict]):
        """记录ST股票过滤日志"""
        try:
            log_entry = {
                "filter_time": datetime.now(),
                "removed_count": len(removed_items),
                "details": removed_items
            }
            
            self.filter_log_collection.insert_one(log_entry)
            logger.info(f"📝 记录ST股票过滤日志: 共过滤 {len(removed_items)} 条ST股票数据")
            
        except Exception as e:
            logger.error(f"❌ 记录ST股票过滤日志失败: {e}")
    
    def update_st_stock_list(self, st_stocks: List[Dict]) -> Dict[str, int]:
        """更新ST股票列表"""
        logger.info(f"🔄 开始更新ST股票列表，待处理 {len(st_stocks)} 条记录")
        
        added = 0
        updated = 0
        
        try:
            for stock in st_stocks:
                stock_name = stock.get("stock_name")
                stock_code = stock.get("stock_code")
                
                if not stock_name and not stock_code:
                    continue
                
                # 构建查询条件
                query = {}
                update_data = {
                    "updated_at": datetime.now()
                }
                
                if stock_name:
                    query["stock_name"] = stock_name
                    update_data["stock_name"] = stock_name
                if stock_code:
                    query["stock_code"] = stock_code
                    update_data["stock_code"] = stock_code
                
                # 检查是否已存在
                existing = self.st_collection.find_one(query)
                
                if existing:
                    # 更新现有记录
                    self.st_collection.update_one(query, {"$set": update_data})
                    updated += 1
                else:
                    # 插入新记录
                    update_data["created_at"] = datetime.now()
                    self.st_collection.insert_one(update_data)
                    added += 1
            
            # 重新加载内存缓存
            self.load_st_stocks()
            
            logger.info(f"✅ ST股票列表更新完成: 新增 {added} 条，更新 {updated} 条")
            return {"added": added, "updated": updated, "success": True}
            
        except Exception as e:
            logger.error(f"❌ 更新ST股票列表失败: {e}")
            return {"added": 0, "updated": 0, "success": False, "error": str(e)}
    
    def should_update(self) -> bool:
        """检查是否需要更新ST股票列表"""
        if not self.last_update_time:
            return True
        
        return datetime.now() - self.last_update_time > self.update_interval
    
    def get_filter_logs(self, limit: int = 100, page: int = 1) -> Dict[str, any]:
        """获取ST股票过滤日志"""
        skip = (page - 1) * limit
        
        cursor = self.filter_log_collection.find().sort("filter_time", -1).skip(skip).limit(limit)
        logs = list(cursor)
        
        # 转换ObjectId为字符串
        for log in logs:
            if "_id" in log:
                log["_id"] = str(log["_id"])
        
        total = self.filter_log_collection.count_documents({})
        
        return {
            "logs": logs,
            "total": total,
            "page": page,
            "limit": limit
        }
    
    def get_st_stock_list(self) -> List[Dict]:
        """获取当前ST股票列表"""
        cursor = self.st_collection.find()
        stocks = list(cursor)
        
        # 转换ObjectId为字符串
        for stock in stocks:
            if "_id" in stock:
                stock["_id"] = str(stock["_id"])
        
        return stocks
    
    def get_stock_status(self, stock_name: Optional[str] = None, stock_code: Optional[str] = None) -> Dict[str, any]:
        """获取股票的ST状态信息"""
        is_st = self.is_st_stock(stock_name, stock_code)
        
        return {
            "stock_name": stock_name,
            "stock_code": stock_code,
            "is_st": is_st,
            "filter_reason": "ST股票" if is_st else "正常股票",
            "last_update_time": self.last_update_time
        }
    
    def sync_st_stocks_from_api(self) -> Dict[str, any]:
        """从API同步ST股票列表"""
        logger.info("🔄 开始从API同步ST股票列表")
        
        try:
            # 模拟从API获取ST股票列表（实际应用中应调用真实API）
            # 这里使用模拟数据作为示例
            st_stocks = self._fetch_st_stocks_from_api()
            
            if st_stocks:
                result = self.update_st_stock_list(st_stocks)
                return {"success": True, "message": f"成功同步 {len(st_stocks)} 条ST股票数据", "result": result}
            else:
                return {"success": False, "message": "未能从API获取ST股票数据"}
                
        except Exception as e:
            logger.error(f"❌ 从API同步ST股票列表失败: {e}")
            return {"success": False, "message": f"同步失败: {e}"}
    
    def _fetch_st_stocks_from_api(self) -> List[Dict]:
        """模拟从API获取ST股票列表"""
        # 实际应用中应调用交易所官方API或可靠数据源
        # 这里使用模拟数据作为示例
        mock_st_stocks = [
            {"stock_name": "ST长生", "stock_code": "002680"},
            {"stock_name": "*ST康美", "stock_code": "600518"},
            {"stock_name": "ST海航", "stock_code": "600221"},
            {"stock_name": "*ST基础", "stock_code": "600515"},
            {"stock_name": "ST易购", "stock_code": "002024"},
            {"stock_name": "*ST美谷", "stock_code": "000615"},
            {"stock_name": "ST华英", "stock_code": "002321"},
            {"stock_name": "*ST中昌", "stock_code": "600242"},
            {"stock_name": "ST天马", "stock_code": "002122"},
            {"stock_name": "*ST科林", "stock_code": "002499"},
        ]
        
        logger.info(f"📥 从API获取到 {len(mock_st_stocks)} 条ST股票数据")
        return mock_st_stocks

# 创建单例实例
st_filter_service = STFilterService()