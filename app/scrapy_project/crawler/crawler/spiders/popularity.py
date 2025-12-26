import scrapy
import json
import random
import time
from ..items import PopularityItem

class PopularitySpider(scrapy.Spider):
    name = "popularity"
    allowed_domains = ["eastmoney.com"]
    
    def start_requests(self):
        # 尝试 API v1
        url = "https://emappdata.eastmoney.com/stockrank/getAllCurrentList"
        payload = {
            "appId": "appId01",
            "globalId": f"{random.randint(100000, 999999)}-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}",
            "marketType": "",
            "pageNo": 1,
            "pageSize": 100,
        }
        yield scrapy.Request(
            url,
            method="POST",
            body=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            callback=self.parse_v1,
            errback=self.errback_v1,
            dont_filter=True
        )

    def parse_v1(self, response):
        try:
            data = response.json()
            if data and "data" in data and data["data"]:
                self.logger.info("API v1 success")
                yield from self.parse_data(data["data"])
                return
        except:
            pass
        
        self.logger.info("API v1 failed or empty, trying v2")
        yield from self.start_v2()

    def errback_v1(self, failure):
        self.logger.info(f"API v1 error: {failure}, trying v2")
        yield from self.start_v2()

    def start_v2(self):
        url = "https://emappdata.eastmoney.com/stockrank/getbrand"
        payload = {
            "appId": "appId01",
            "globalId": f"{random.randint(100000, 999999)}-{random.randint(1000, 9999)}",
            "type": 1,
            "pageNo": 1,
            "pageSize": 100,
        }
        yield scrapy.Request(
            url,
            method="POST",
            body=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            callback=self.parse_v2,
            errback=self.errback_v2,
            dont_filter=True
        )

    def parse_v2(self, response):
        try:
            data = response.json()
            if data and "data" in data and data["data"]:
                items = data["data"]
                if isinstance(items, dict) and "list" in items:
                    items = items["list"]
                if items:
                    self.logger.info("API v2 success")
                    yield from self.parse_data(items)
                    return
        except:
            pass
            
        self.logger.info("API v2 failed or empty, trying v3")
        yield from self.start_v3()

    def errback_v2(self, failure):
        self.logger.info(f"API v2 error: {failure}, trying v3")
        yield from self.start_v3()

    def start_v3(self):
        url = "http://push2.eastmoney.com/api/qt/clist/get"
        params = {
            "fid": "f8", # 换手率
            "po": 1,
            "pz": 100,
            "pn": 1,
            "np": 1,
            "fltt": 2,
            "invt": 2,
            "fs": "m:0+t:6,m:0+t:80",
            "fields": "f12,f14,f2,f3,f8,f5,f6",
            "_": str(int(time.time() * 1000)),
        }
        # Scrapy Request expects url with params already encoded or minimal params
        # But we can use FormRequest.from_response or just build url string
        # Here we just append params string manually or use 'meta' if needed? 
        # Easier to just construct URL string
        from urllib.parse import urlencode
        full_url = f"{url}?{urlencode(params)}"
        
        yield scrapy.Request(
            full_url,
            callback=self.parse_v3,
            dont_filter=True
        )

    def parse_v3(self, response):
        try:
            data = response.json()
            if data and "data" in data and data["data"] and "diff" in data["data"]:
                diff_data = data["data"]["diff"]
                if isinstance(diff_data, dict):
                    diff_data = list(diff_data.values())
                
                # 使用集合去重，确保每个股票代码只返回一次
                processed_codes = set()
                
                # 尝试导入股票名称映射功能
                try:
                    # 添加Python路径以便导入
                    import sys
                    import os
                    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
                    
                    from src.database import get_stock_name_map
                    # 获取完整的股票名称映射
                    stock_name_map = get_stock_name_map()
                    self.logger.info(f"成功导入股票名称映射功能，共 {len(stock_name_map)} 条映射数据")
                except Exception as e:
                    self.logger.warning(f"无法导入股票名称映射功能: {e}")
                    stock_name_map = {}
                
                for idx, row in enumerate(diff_data):
                    item = PopularityItem()
                    item['rank'] = idx + 1
                    
                    code = str(row.get('f12', ''))
                    if isinstance(code, str):
                        code = code.strip()  # 去除空格
                    item['code'] = code
                    
                    # 去重：如果该代码已经处理过，跳过
                    if code in processed_codes or not code:
                        continue
                    processed_codes.add(code)
                    
                    # 1. 优先从API返回数据中获取名称
                    name = row.get('f14', '')
                    
                    # 2. 如果API返回的名称为空，尝试从股票名称映射表获取
                    if not name or not name.strip():
                        name = stock_name_map.get(code, '')
                    
                    # 3. 确保名称不为空
                    if not name or not name.strip():
                        self.logger.warning(f"无法获取股票 {code} 的名称")
                        name = "未知"
                    
                    item['name'] = name.strip()
                    
                    item['price'] = float(row.get('f2', 0)) if row.get('f2') != '-' else 0
                    
                    change = row.get('f3', 0)
                    item['change_ratio'] = f"{change:.2f}%" if change != '-' and change is not None else '-'
                    item['rank_change'] = '-' # V3 has no rank change info
                    
                    yield item
                self.logger.info(f"API v3 success, extracted {len(processed_codes)} items")
            else:
                 self.logger.warning("API v3 returned no data")
        except Exception as e:
            self.logger.error(f"API v3 parse error: {e}")

    def parse_data(self, items):
        # Parsing logic for V1/V2 data structure
        # First, try to build a name lookup from v3-style API
        self.name_cache = getattr(self, 'name_cache', {})
        
        # 使用集合去重，确保每个股票代码只返回一次
        processed_codes = set()
        
        # 尝试导入股票名称映射功能
        try:
            # 添加Python路径以便导入
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
            
            from src.database import get_stock_name_map
            # 获取完整的股票名称映射
            stock_name_map = get_stock_name_map()
            self.logger.info(f"成功导入股票名称映射功能，共 {len(stock_name_map)} 条映射数据")
        except Exception as e:
            self.logger.warning(f"无法导入股票名称映射功能: {e}")
            stock_name_map = {}
        
        for idx, row in enumerate(items):
            item = PopularityItem()
            
            # Extract fields with fallbacks for different API formats
            code = row.get('sCode') or row.get('sc') or str(row.get('f12', ''))
            # Normalization
            if isinstance(code, str):
                if code.startswith('SH') or code.startswith('SZ'):
                    code = code[2:]
                code = code.strip()  # 去除空格
            item['code'] = code
            
            # 去重：如果该代码已经处理过，跳过
            if code in processed_codes or not code:
                continue
            processed_codes.add(code)
            
            # 1. 优先尝试从多个字段获取名称
            name = row.get('sName') or row.get('sn') or row.get('nm') or row.get('f14') or row.get('name')
            
            # 2. 如果还是没有名称，尝试从缓存获取
            if not name or not name.strip():
                name = self.name_cache.get(code, '')
            
            # 3. 如果还是没有名称，尝试从股票名称映射表获取
            if not name or not name.strip():
                name = stock_name_map.get(code, '')
            
            # 4. 确保名称不为空
            if not name or not name.strip():
                self.logger.warning(f"无法获取股票 {code} 的名称")
                name = "未知"
        
            item['name'] = name.strip()
            
            rank = row.get('iRank') or row.get('rk') or row.get('rank')
            if rank is None:
                rank = idx + 1
            item['rank'] = int(rank)
            
            price = row.get('fNowPrice') or row.get('np') or row.get('p')
            try:
                item['price'] = float(price) if price and price != '-' else 0.0
            except:
                item['price'] = 0.0
                
            change = row.get('fChangeRatio') or row.get('cr')
            try:
                item['change_ratio'] = f"{float(change):.2f}%" if change and change != '-' else '-'
            except:
                 item['change_ratio'] = str(change) if change else '-'
            
            # Rank Change calculation
            prev_rank = row.get('iPreRank') or row.get('his_rk')
            if prev_rank:
                try:
                    diff = int(prev_rank) - int(rank)
                    if diff > 0:
                        item['rank_change'] = f"↑{diff}"
                    elif diff < 0:
                        item['rank_change'] = f"↓{abs(diff)}"
                    else:
                        item['rank_change'] = "-"
                except:
                    item['rank_change'] = "-"
            else:
                item['rank_change'] = "-"
            
            self.logger.info(f"Extracted Popularity: {item['code']} - {item['name']} (Rank: {item['rank']})")
            yield item

