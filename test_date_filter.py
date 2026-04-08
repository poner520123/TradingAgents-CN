#!/usr/bin/env python3
"""
测试日期筛选功能
"""

import requests
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000/api/crawler/list"

def test_date_filter():
    """测试日期筛选"""
    print("=== 测试日期筛选功能 ===")
    
    # 获取今天的日期
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"今天日期: {today}")
    
    # 测试今天的数据
    params = {"page": 1, "page_size": 10, "start_date": today, "end_date": today}
    response = requests.get(BASE_URL, params=params)
    
    print(f"请求URL: {response.url}")
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        total = data.get("total", 0)
        print(f"今天数据总数: {total}")
        
        if total > 0:
            print("数据示例:")
            for item in data.get("data", [])[:3]:
                print(f"  {item['time']} - {item['stock_name']}")
        else:
            print("没有找到数据")
    else:
        print(f"请求失败: {response.text}")
    
    # 测试日期范围
    print("\n=== 测试日期范围 ===")
    start_date = "2026-04-08"
    end_date = "2026-04-08"
    
    params = {"page": 1, "page_size": 10, "start_date": start_date, "end_date": end_date}
    response = requests.get(BASE_URL, params=params)
    
    print(f"请求URL: {response.url}")
    
    if response.status_code == 200:
        data = response.json()
        total = data.get("total", 0)
        print(f"日期范围 {start_date} 到 {end_date} 的数据总数: {total}")
    else:
        print(f"请求失败: {response.text}")

if __name__ == "__main__":
    test_date_filter()
