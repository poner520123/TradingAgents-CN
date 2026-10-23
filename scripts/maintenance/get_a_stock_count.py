#!/usr/bin/env python3
"""
获取A股股票数量的简单脚本
"""

import requests
import json

def get_a_stock_count():
    """
    获取A股股票数量
    """
    try:
        # 使用东方财富API获取A股股票列表
        url = "http://push2.eastmoney.com/api/qt/clist/get"
        params = {
            "pn": "1",
            "pz": "1",
            "po": "1",
            "np": "1",
            "fltt": "2",
            "invt": "2",
            "fields": "f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152",
            "fid": "f3",
            "fs": "m:0 t:6,m:0 t:13,m:0 t:80,m:1 t:2,m:1 t:23,m:1 t:3",
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "cb": "jQuery351007256145167534836_1734176313389"
        }
        
        response = requests.get(url, params=params)
        response_text = response.text
        
        # 解析JSONP响应
        json_str = response_text.split('(')[1].rstrip(')')
        data = json.loads(json_str)
        
        # 获取总股票数量
        total_count = data.get('data', {}).get('total', 0)
        
        print(f"A股股票数量: {total_count}")
        return total_count
    except Exception as e:
        print(f"获取A股股票数量失败: {e}")
        return 0

if __name__ == "__main__":
    get_a_stock_count()
