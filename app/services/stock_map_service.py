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
        # 初始化MongoDB连接
        self.client = MongoClient(settings.MONGO_URI)
        self.db = self.client[settings.MONGO_DB]
        self.collection = self.db["stock_name_code_mapping"]
        # 创建唯一索引
        self.collection.create_index([("name", 1)], unique=True)
        
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
                            # 检查是否已存在
                            existing = self.collection.find_one({"name": name})
                            if not existing:
                                # 确定市场类型
                                market = self._get_market_by_code(code)
                                
                                # 插入数据
                                map_data = {
                                    "name": name,
                                    "code": code,
                                    "market": market,
                                    "updated_at": datetime.utcnow(),
                                    "created_at": datetime.utcnow()
                                }
                                self.collection.insert_one(map_data)
                                count += 1
        except Exception as e:
            logger.error(f"从CSV文件加载股票名称到代码的映射失败: {e}")
            return 0
        
        logger.info(f"从CSV文件加载股票名称到代码的映射完成，共加载 {count} 条记录")
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
        # 先从数据库查询
        map_data = self.collection.find_one({"name": name})
        if map_data:
            return map_data["code"]
        
        # 如果数据库中没有，通过API查询
        logger.info(f"数据库中未找到股票代码，通过API查询: {name}")
        code = self._get_stock_code_from_api(name)
        if code:
            # 将查询结果保存到数据库
            market = self._get_market_by_code(code)
            self.upsert_map(name, code, market)
            logger.info(f"通过API查询到股票代码: {name} -> {code}，已保存到数据库")
            return code
        
        return None
    
    def get_codes_by_names(self, names: List[str]) -> Dict[str, str]:
        """根据股票名称列表批量获取股票代码"""
        logger.info(f"根据股票名称列表批量获取股票代码: {names}")
        result = {}
        
        # 查询数据库
        maps = self.collection.find({"name": {"$in": names}})
        for map_data in maps:
            result[map_data["name"]] = map_data["code"]
        
        # 找出数据库中没有的股票名称
        missing_names = [name for name in names if name not in result]
        if missing_names:
            logger.info(f"数据库中缺少 {len(missing_names)} 个股票代码，通过API查询")
            
            # 逐个通过API查询，确保单个失败不影响整体
            for name in missing_names:
                try:
                    code = self._get_stock_code_from_api(name)
                    if code:
                        # 将查询结果保存到数据库
                        market = self._get_market_by_code(code)
                        self.upsert_map(name, code, market)
                        result[name] = code
                        logger.info(f"通过API查询到股票代码: {name} -> {code}，已保存到数据库")
                except Exception as e:
                    logger.error(f"查询股票代码失败: {name}，错误: {e}")
                    # 继续处理其他股票名称，不中断整个流程
        
        return result
    
    def upsert_map(self, name: str, code: str, market: Optional[str] = None) -> bool:
        """更新或插入股票名称到代码的映射"""
        logger.info(f"更新或插入股票名称到代码的映射: {name} -> {code}")
        
        try:
            # 确定市场类型
            if not market:
                market = self._get_market_by_code(code)
            
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
            return True
        except Exception as e:
            logger.error(f"更新或插入股票名称到代码的映射失败: {e}")
            return False
    
    def get_all_maps(self, skip: int = 0, limit: int = 100) -> List[Dict]:
        """获取所有股票名称到代码的映射"""
        logger.info(f"获取所有股票名称到代码的映射，跳过 {skip}，限制 {limit}")
        
        maps = self.collection.find().skip(skip).limit(limit)
        return list(maps)
    
    def get_total_count(self) -> int:
        """获取股票名称到代码的映射总数"""
        return self.collection.count_documents({})
    
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
        
        # 2. 尝试使用百度搜索
        try:
            import urllib.parse
            import re
            from bs4 import BeautifulSoup
            
            # 构建百度搜索URL
            search_keyword = f"{name} 股票代码"
            encoded_keyword = urllib.parse.quote(search_keyword)
            url = f"https://www.baidu.com/s?wd={encoded_keyword}"
            
            logger.info(f"使用百度搜索: {url}")
            
            # 发送HTTP请求
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=5, verify=False)
            response.raise_for_status()
            
            # 解析HTML
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 提取搜索结果
            results = soup.find_all("div", class_="result")
            
            # 正则表达式匹配股票代码，格式为6位数字
            stock_code_pattern = re.compile(r"(\d{6})")
            
            # 遍历结果，查找股票代码
            for result in results:
                text = result.get_text()
                match = stock_code_pattern.search(text)
                if match:
                    stock_code = match.group(1)
                    logger.info(f"通过百度搜索找到股票代码: {name} -> {stock_code}")
                    return stock_code
        except Exception as e:
            logger.error(f"百度搜索失败: {e}")
        
        logger.warning(f"无法查询到股票代码: {name}")
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
            # 检查是否已存在映射
            existing = self.collection.find_one({"name": name})
            if not existing:
                missing += 1
                
                # 通过API查询股票代码
                code = self._get_stock_code_from_api(name)
                if code:
                    # 确定市场类型
                    market = self._get_market_by_code(code)
                    
                    # 插入数据
                    map_data = {
                        "name": name,
                        "code": code,
                        "market": market,
                        "updated_at": datetime.utcnow(),
                        "created_at": datetime.utcnow()
                    }
                    self.collection.insert_one(map_data)
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
            result = self.collection.delete_many({})
            logger.info(f"成功清空所有股票名称和代码映射，共删除 {result.deleted_count} 条记录")
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
