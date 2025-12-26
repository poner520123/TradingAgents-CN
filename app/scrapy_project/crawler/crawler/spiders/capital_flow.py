import scrapy
import time
from urllib.parse import urlencode
from ..items import CapitalFlowItem

class CapitalFlowSpider(scrapy.Spider):
    name = "capital_flow"
    allowed_domains = ["eastmoney.com"]

    def start_requests(self):
        url = "http://push2.eastmoney.com/api/qt/clist/get"
        params = {
            "fid": "f62",
            "po": 1,
            "pz": 100,
            "pn": 1,
            "np": 1,
            "fltt": 2,
            "invt": 2,
            "fs": "m:0+t:6,m:0+t:80",
            "fields": "f12,f14,f2,f3,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87",
            "_": str(int(time.time() * 1000)),
        }
        full_url = f"{url}?{urlencode(params)}"
        
        yield scrapy.Request(full_url, callback=self.parse)

    def parse(self, response):
        try:
            data = response.json()
            if data and "data" in data and data["data"] and "diff" in data["data"]:
                diff_data = data["data"]["diff"]
                if isinstance(diff_data, dict):
                    diff_data = list(diff_data.values())

                for row in diff_data:
                    item = CapitalFlowItem()
                    item['code'] = str(row.get('f12', ''))
                    item['name'] = row.get('f14', '')
                    
                    try:
                        price = row.get('f2')
                        item['price'] = float(price) if price != '-' else 0.0
                    except:
                        item['price'] = 0.0
                        
                    change = row.get('f3')
                    item['change_ratio'] = f"{change:.2f}%" if change != '-' and change is not None else '-'
                    
                    flow = row.get('f62')
                    try:
                        flow_val = float(flow) if flow != '-' and flow is not None else 0.0
                        item['main_flow'] = flow_val
                        item['main_flow_text'] = self.format_money(flow_val)
                    except:
                        item['main_flow'] = 0.0
                        item['main_flow_text'] = "0"

                    self.logger.info(f"Extracted Flow: {item['code']} - {item['name']} (Flow: {item['main_flow_text']})")
                    yield item
        except Exception as e:
            self.logger.error(f"Parse error: {e}")

    def format_money(self, val):
        if val == "-" or val is None:
            return "0"
        try:
            v = float(val)
            if abs(v) >= 100000000:
                return f"{v/100000000:.2f}亿"
            elif abs(v) >= 10000:
                return f"{v/10000:.2f}万"
            return f"{v:.2f}"
        except:
            return str(val)
