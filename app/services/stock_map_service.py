import csv
import logging
from typing import Dict, List, Optional
from datetime import datetime
from pymongo import MongoClient
from app.core.config import settings
from app.models.stock_map_models import StockNameCodeMap
import requests
import json

logger = logging.getLogger(__name__)

class StockMapService:
    """股票名称到代码的映射服务"""
    
    def __init__(self):
        self.mongodb_available = False
        self.client = None
        self.db = None
        self.collection = None
        
        # 尝试初始化MongoDB连接
        try:
            self.client = MongoClient(settings.MONGO_URI)
            self.db = self.client[settings.MONGO_DB]
            self.collection = self.db["stock_name_code_mapping"]
            # 创建唯一索引（仅对name字段，code字段可能存在重复）
            self.collection.create_index([("name", 1)], unique=True)
            self.collection.create_index([("code", 1)])  # 非唯一索引，用于加速查询
            self.mongodb_available = True
            logger.info("✅ MongoDB连接成功，股票映射服务初始化完成")
        except Exception as e:
            logger.warning(f"⚠️ MongoDB连接失败: {e}，将使用内存缓存模式")
            self.mongodb_available = False
        
        # 初始化内存缓存
        self.name_to_code: Dict[str, str] = {}  # 名称到代码的映射
        self.code_to_name: Dict[str, str] = {}  # 代码到名称的映射
        
        # 从数据库加载所有映射到缓存
        self._rebuild_cache()
    
    def _rebuild_cache(self):
        """从数据库重建内存缓存"""
        logger.info("开始从数据库重建内存缓存")
        
        # 清空现有缓存
        self.name_to_code.clear()
        self.code_to_name.clear()
        
        count = 0
        
        # 只有在MongoDB可用时才从数据库加载
        if self.mongodb_available and self.collection is not None:
            try:
                # 从数据库获取所有映射
                maps = self.collection.find()
                
                for map_item in maps:
                    name = map_item.get("name")
                    code = map_item.get("code")
                    
                    if name and code:
                        self.name_to_code[name] = code
                        self.code_to_name[code] = name
                        count += 1
                
                logger.info(f"内存缓存重建完成，共加载 {count} 条映射")
            except Exception as e:
                logger.warning(f"⚠️ 从数据库加载映射失败: {e}")
        else:
            logger.info("MongoDB不可用，使用空缓存")
        
    def load_from_csv(self, csv_path: str) -> int:
        """从CSV文件加载股票名称到代码的映射"""
        logger.info(f"开始从CSV文件加载股票名称到代码的映射: {csv_path}")
        count = 0
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) == 2:
                        name = row[0].replace('"', '').strip()
                        code = row[1].replace('"', '').strip()
                        
                        if name and code:
                            # 确定市场类型
                            market = self._get_market_by_code(code)
                            
                            # 使用upsert_map方法，确保数据更新或插入
                            success = self.upsert_map(name, code, market)
                            if success:
                                count += 1
        except Exception as e:
            logger.error(f"从CSV文件加载股票名称到代码的映射失败: {e}")
            return 0
        
        # 重新构建内存缓存
        self._rebuild_cache()
        logger.info(f"从CSV文件加载股票名称到代码的映射完成，共处理 {count} 条记录")
        return count
    
    def _get_market_by_code(self, code: str) -> str:
        """根据股票代码确定市场类型"""
        if code.startswith(('60', '688')):
            return "A股"
        elif code.startswith('30'):
            return "A股"
        elif code.startswith(('00', '000', '002')):
            return "A股"
        elif code.startswith(('83', '43')):
            return "北交所"
        elif len(code) == 4 or len(code) == 5:
            return "港股"
        else:
            return "未知"
    
    def get_code_by_name(self, name: str) -> Optional[str]:
        """根据股票名称获取股票代码"""
        logger.info(f"根据股票名称获取股票代码: {name}")
        # 先从缓存查询
        if name in self.name_to_code:
            logger.info(f"从缓存获取股票代码: {name} -> {self.name_to_code[name]}")
            return self.name_to_code[name]
        
        # 如果缓存中没有，且MongoDB可用，从数据库查询
        if self.mongodb_available and self.collection is not None:
            try:
                map_data = self.collection.find_one({"name": name})
                if map_data:
                    code = map_data["code"]
                    # 更新缓存
                    self.name_to_code[name] = code
                    self.code_to_name[code] = name
                    return code
            except Exception as e:
                logger.warning(f"⚠️ 从数据库查询失败: {e}")
        
        # 如果数据库中没有或MongoDB不可用，通过API查询
        logger.info(f"数据库中未找到股票代码或MongoDB不可用，通过API查询: {name}")
        code = self._get_stock_code_from_api(name)
        if code:
            # 将查询结果保存到数据库（如果MongoDB可用）
            if self.mongodb_available:
                market = self._get_market_by_code(code)
                self.upsert_map(name, code, market)
                logger.info(f"通过API查询到股票代码: {name} -> {code}，已保存到数据库")
            else:
                # 只更新内存缓存
                self.name_to_code[name] = code
                self.code_to_name[code] = name
                logger.info(f"通过API查询到股票代码: {name} -> {code}，已保存到内存缓存")
            return code
        
        return None
    
    def get_codes_by_names(self, names: List[str]) -> Dict[str, str]:
        """根据股票名称列表批量获取股票代码"""
        logger.info(f"根据股票名称列表批量获取股票代码: {names}")
        result = {}
        
        # 1. 优先使用内存缓存
        cached_names = []
        missing_names = []
        
        for name in names:
            if name in self.name_to_code:
                result[name] = self.name_to_code[name]
                cached_names.append(name)
            else:
                missing_names.append(name)
        
        if cached_names:
            logger.info(f"从内存缓存获取到 {len(cached_names)} 个股票代码")
        
        if not missing_names:
            return result
        
        # 2. 批量查询数据库（如果MongoDB可用）
        db_found = []
        if self.mongodb_available and self.collection is not None:
            try:
                maps = self.collection.find({"name": {"$in": missing_names}})
                for map_data in maps:
                    result[map_data["name"]] = map_data["code"]
                    # 更新内存缓存
                    self.name_to_code[map_data["name"]] = map_data["code"]
                    self.code_to_name[map_data["code"]] = map_data["name"]
                    db_found.append(map_data["name"])
                
                if db_found:
                    logger.info(f"从数据库获取到 {len(db_found)} 个股票代码")
            except Exception as e:
                logger.warning(f"⚠️ 批量查询数据库失败: {e}")
                db_found = []
        else:
            logger.info("MongoDB不可用，跳过数据库查询")
        
        # 3. 找出数据库中也没有的股票名称
        api_names = [name for name in missing_names if name not in db_found]
        if not api_names:
            return result
        
        # 4. 只对少量缺失的股票进行API查询，避免大量耗时请求
        max_api_queries = 10  # 限制最大API查询数量
        api_query_names = api_names[:max_api_queries]
        logger.info(f"数据库中缺少 {len(api_names)} 个股票代码，将对前 {len(api_query_names)} 个进行API查询")
        
        for name in api_query_names:
            try:
                code = self._get_stock_code_from_api(name)
                if code:
                    # 将查询结果保存到数据库和缓存
                    market = self._get_market_by_code(code)
                    self.upsert_map(name, code, market)
                    result[name] = code
                    logger.info(f"通过API查询到股票代码: {name} -> {code}，已保存到数据库")
            except Exception as e:
                logger.error(f"查询股票代码失败: {name}，错误: {e}")
                # 继续处理其他股票名称，不中断整个流程
        
        # 记录未找到的股票名称
        not_found_names = [name for name in api_names if name not in result]
        if not_found_names:
            logger.info(f"未找到 {len(not_found_names)} 个股票代码: {not_found_names}")
        
        return result
    
    def upsert_map(self, name: str, code: str, market: Optional[str] = None) -> bool:
        """更新或插入股票名称到代码的映射"""
        logger.info(f"更新或插入股票名称到代码的映射: {name} -> {code}")
        
        try:
            # 确定市场类型
            if not market:
                market = self._get_market_by_code(code)
            
            # 如果MongoDB可用，写入数据库
            if self.mongodb_available and self.collection is not None:
                try:
                    # 更新或插入
                    self.collection.update_one(
                        {"name": name},
                        {
                            "$set": {
                                "code": code,
                                "market": market,
                                "updated_at": datetime.utcnow()
                            },
                            "$setOnInsert": {
                                "created_at": datetime.utcnow()
                            }
                        },
                        upsert=True
                    )
                    logger.info(f"映射已保存到数据库: {name} -> {code}")
                except Exception as e:
                    logger.warning(f"⚠️ 写入数据库失败: {e}")
            
            # 无论数据库操作是否成功，都更新内存缓存
            self.name_to_code[name] = code
            self.code_to_name[code] = name
            logger.info(f"更新缓存: {name} -> {code}")
            return True
        except Exception as e:
            logger.error(f"更新或插入股票名称到代码的映射失败: {e}")
            return False
    
    def get_all_maps(self, skip: int = 0, limit: int = 100) -> List[Dict]:
        """获取所有股票名称到代码的映射"""
        logger.info(f"获取所有股票名称到代码的映射，跳过 {skip}，限制 {limit}")
        
        result = []
        
        # 如果MongoDB可用，从数据库获取
        if self.mongodb_available and self.collection is not None:
            try:
                maps = self.collection.find().skip(skip).limit(limit)
                for map_item in maps:
                    # 转换ObjectId为字符串，确保可序列化
                    if "_id" in map_item:
                        map_item["_id"] = str(map_item["_id"])
                    result.append(map_item)
            except Exception as e:
                logger.warning(f"⚠️ 从数据库获取映射失败: {e}")
                result = []
        else:
            # 如果MongoDB不可用，从内存缓存获取
            logger.info("MongoDB不可用，从内存缓存获取映射")
            count = 0
            for name, code in self.name_to_code.items():
                if count >= skip and len(result) < limit:
                    result.append({
                        "name": name,
                        "code": code,
                        "market": self._get_market_by_code(code)
                    })
                count += 1
        
        return result
    
    def get_name_by_code(self, code: str) -> Optional[str]:
        """根据股票代码获取股票名称"""
        logger.info(f"根据股票代码获取股票名称: {code}")
        # 先从缓存查询
        if code in self.code_to_name:
            logger.info(f"从缓存获取股票名称: {code} -> {self.code_to_name[code]}")
            return self.code_to_name[code]
        
        # 如果缓存中没有，且MongoDB可用，从数据库查询
        if self.mongodb_available and self.collection is not None:
            try:
                map_data = self.collection.find_one({"code": code})
                if map_data:
                    name = map_data["name"]
                    # 更新缓存
                    self.code_to_name[code] = name
                    self.name_to_code[name] = code
                    return name
            except Exception as e:
                logger.warning(f"⚠️ 从数据库查询失败: {e}")
        
        return None
    
    def get_total_count(self) -> int:
        """获取股票名称到代码的映射总数"""
        # 如果MongoDB可用，从数据库获取
        if self.mongodb_available and self.collection is not None:
            try:
                return self.collection.count_documents({})
            except Exception as e:
                logger.warning(f"⚠️ 从数据库获取计数失败: {e}")
        
        # 如果MongoDB不可用，返回内存缓存中的数量
        return len(self.name_to_code)
    
    def get_a_stock_names(self) -> List[str]:
        """获取A股上市公司名称列表"""
        logger.info("获取A股上市公司名称列表")
        names = []
        
        # 从namecode.csv文件中获取所有名称
        try:
            csv_path = "newstock/data/namecode.csv"
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) == 2:
                        name = row[0].replace('"', '').strip()
                        if name:
                            names.append(name)
            logger.info(f"从CSV文件获取到 {len(names)} 个A股上市公司名称")
        except Exception as e:
            logger.error(f"从CSV文件获取A股上市公司名称列表失败: {e}")
        
        return names
    
    def _get_stock_code_from_api(self, name: str) -> Optional[str]:
        """通过API查询股票代码"""
        logger.info(f"通过API查询股票代码: {name}")
        
        # 1. 首先尝试使用手动映射（优先使用，避免频繁API调用）
        manual_mappings = {
            # 用户提供的股票映射
            "骏亚科技": "603386",
            "安记食品": "603696",
            "国机重装": "601399",
            "渤海化学": "600800",
            "三木集团": "000632",
            "赤天化": "600227",
            "瑞康医药": "002589",
            "雪祺电气": "001387",
            "华资实业": "600191",
            "中天火箭": "003009",
            "中国一重": "601106",
            "中能电气": "002891",
            "合富中国": "603122",
            "广百股份": "002180",
            "格林达": "605311",
            "海欣食品": "002702",
            "睿能科技": "603933",
            "建设机械": "600984",
            "顺灏股份": "002565",
            "大众公用": "600635",
            "惠天热电": "000692",
            "双枪科技": "001211",
            "名雕股份": "002830",
            "贵州轮胎": "000589",
            "中源家居": "603709",
            "宝胜股份": "600479",
            "王府井": "600859",
            "重庆建工": "600939",
            "合兴包装": "002228",
            "北新路桥": "002307",
            "威士顿": "301315",
            "赛微电子": "300456",
            "东百集团": "600693",
            "永鼎股份": "600105",
            "闽发铝业": "002578",
            "昇兴股份": "002752",
            "园林股份": "605303",
            "国风新材": "000859",
            "太阳电缆": "002300",
            "中安科": "600654",
            "实达集团": "600734",
            "中国天楹": "000035",
            "嘉美包装": "002969",
            "茂硕电源": "002660",
            "西王食品": "000639",
            "南矿集团": "001360",
            "致尚科技": "301315",
            "航天发展": "000547",
            "航天科技": "000901",
            "航天机电": "600151",
            "国机通用": "600444",
            "华菱线缆": "001208",
            "中国卫星": "600118",
            "垒知集团": "002398",
            "金字火腿": "002515",
            "鸿博股份": "002229",
            "美格智能": "002881",
            "道明光学": "002632",
            "美芝股份": "002856",
            "实益达": "002137",
            "英特集团": "000411",
            "达华智能": "002512",
            "福建高速": "600033",
            "德赛电池": "000049",
            "德尔未来": "002631",
            "上海瀚讯": "300762",
            "二六三": "002467",
            "铜陵有色": "000630",
            "沃尔核材": "002130",
            "安硕信息": "300380",
            "赢时胜": "300377",
            "新安股份": "600596",
            "三维通信": "002115",
            "首开股份": "600376",
            "精艺股份": "002295",
            "乾照光电": "300102",
            "雪人集团": "002639",
            "金安国纪": "002636",
            "广济药业": "000952",
            "晨光新材": "605399",
            "国晟科技": "603778",
            "通宇通讯": "002792",
            "舒华体育": "605299",
            "特发信息": "000070",
        }
        
        if name in manual_mappings:
            logger.info(f"使用手动映射: {name} -> {manual_mappings[name]}")
            return manual_mappings[name]
        
        # 2. 百度搜索可能很慢，暂时禁用，优先使用本地缓存和手动映射
        # 如果确实需要，可以考虑使用更快的API或服务
        logger.warning(f"手动映射中未找到股票代码: {name}，百度搜索已禁用")
        return None
    
    def supplement_stock_mappings(self) -> Dict[str, int]:
        """遍历A股上市公司名称，补充缺失的映射"""
        logger.info("开始补充股票名称代码映射")
        
        # 获取A股上市公司名称列表
        a_stock_names = self.get_a_stock_names()
        if not a_stock_names:
            logger.warning("未获取到A股上市公司名称列表")
            return {"total": 0, "missing": 0, "supplemented": 0}
        
        # 统计信息
        total = len(a_stock_names)
        missing = 0
        supplemented = 0
        
        # 遍历A股上市公司名称
        for name in a_stock_names:
            # 检查是否已存在映射（先检查内存缓存，再检查数据库）
            if name in self.name_to_code:
                continue
            
            # 如果MongoDB可用，检查数据库
            existing = None
            if self.mongodb_available and self.collection is not None:
                try:
                    existing = self.collection.find_one({"name": name})
                except Exception as e:
                    logger.warning(f"⚠️ 检查数据库失败: {e}")
            
            if not existing:
                missing += 1
                
                # 通过API查询股票代码
                code = self._get_stock_code_from_api(name)
                if code:
                    # 确定市场类型
                    market = self._get_market_by_code(code)
                    
                    # 如果MongoDB可用，插入数据库
                    if self.mongodb_available and self.collection is not None:
                        try:
                            map_data = {
                                "name": name,
                                "code": code,
                                "market": market,
                                "updated_at": datetime.utcnow(),
                                "created_at": datetime.utcnow()
                            }
                            self.collection.insert_one(map_data)
                            logger.info(f"补充映射到数据库: {name} -> {code}")
                        except Exception as e:
                            logger.warning(f"⚠️ 插入数据库失败: {e}")
                    
                    # 更新内存缓存
                    self.name_to_code[name] = code
                    self.code_to_name[code] = name
                    supplemented += 1
                    logger.info(f"补充映射: {name} -> {code}")
        
        logger.info(f"股票名称代码映射补充完成，共处理 {total} 个名称，缺失 {missing} 个，补充 {supplemented} 个")
        return {
            "total": total,
            "missing": missing,
            "supplemented": supplemented
        }
    
    def clear_mappings(self) -> bool:
        """清空所有股票名称和代码映射"""
        logger.info("开始清空所有股票名称和代码映射")
        
        try:
            # 如果MongoDB可用，清空数据库
            if self.mongodb_available and self.collection is not None:
                try:
                    result = self.collection.delete_many({})
                    logger.info(f"成功清空数据库中的股票名称和代码映射，共删除 {result.deleted_count} 条记录")
                except Exception as e:
                    logger.warning(f"⚠️ 清空数据库失败: {e}")
            
            # 清空内存缓存
            self.name_to_code.clear()
            self.code_to_name.clear()
            logger.info("成功清空内存缓存中的股票名称和代码映射")
            
            return True
        except Exception as e:
            logger.error(f"清空股票名称和代码映射失败: {e}")
            return False
    
    def resync_mappings(self) -> Dict[str, int]:
        """清空映射并重新同步"""
        logger.info("开始重新同步股票名称和代码映射")
        
        # 清空现有映射
        if not self.clear_mappings():
            logger.error("清空映射失败，无法继续重新同步")
            return {"success": False, "message": "清空映射失败"}
        
        # 从CSV文件重新加载映射
        csv_path = "newstock/data/namecode.csv"
        loaded_count = self.load_from_csv(csv_path)
        
        # 补充缺失的映射
        supplement_result = self.supplement_stock_mappings()
        
        logger.info(f"股票名称和代码映射重新同步完成，从CSV加载 {loaded_count} 条，补充 {supplement_result['supplemented']} 条")
        
        return {
            "success": True,
            "loaded_from_csv": loaded_count,
            "supplemented": supplement_result['supplemented'],
            "total": loaded_count + supplement_result['supplemented']
        }
    
    def close(self):
        """关闭MongoDB连接"""
        self.client.close()

# 创建单例实例
stock_map_service = StockMapService()
