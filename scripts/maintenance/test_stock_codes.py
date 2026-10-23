#!/usr/bin/env python3
"""
测试股票代码修复效果
"""

import requests

BASE_URL = "http://localhost:8000/api/crawler/list"

def test_stock_codes():
    """测试股票代码修复效果"""
    print("=== 测试股票代码修复效果 ===")
    
    # 测试特定股票
    test_stocks = [
        {'name': '东方新能', 'expected_code': '000958'},
        {'name': '电投水电', 'expected_code': '600905'},
        {'name': '中稀有色', 'expected_code': '000831'},
    ]
    
    for stock in test_stocks:
        print(f"\n测试股票: {stock['name']}")
        
        params = {"page": 1, "page_size": 3, "stock_name": stock['name']}
        response = requests.get(BASE_URL, params=params)
        
        if response.status_code == 200:
            data = response.json()
            total = data.get("total", 0)
            print(f"总记录数: {total}")
            
            if total > 0:
                print("数据示例:")
                for item in data.get("data", []):
                    stock_code = item.get("stock_code")
                    print(f"  股票代码: {stock_code}, 期望值: {stock['expected_code']}")
                    
                    if stock_code == stock['expected_code']:
                        print(f"  ✓ 股票代码正确")
                    else:
                        print(f"  ✗ 股票代码错误")
            else:
                print("没有找到数据")
        else:
            print(f"请求失败: {response.text}")
    
    # 测试随机股票
    print("\n=== 测试随机股票 ===")
    params = {"page": 1, "page_size": 5}
    response = requests.get(BASE_URL, params=params)
    
    if response.status_code == 200:
        data = response.json()
        print("随机股票数据:")
        for item in data.get("data", []):
            print(f"  {item['stock_name']} ({item.get('stock_code', '无代码')})")

if __name__ == "__main__":
    test_stock_codes()
