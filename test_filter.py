#!/usr/bin/env python3
"""
测试爬虫分析筛选功能
"""

import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000/api/crawler/list"

def test_filter_user_name():
    """测试伏击人筛选"""
    print("=== 测试伏击人筛选 ===")
    
    # 测试空筛选
    params = {"page": 1, "page_size": 10}
    response = requests.get(BASE_URL, params=params)
    data = response.json()
    total_all = data.get("total", 0)
    print(f"总记录数: {total_all}")
    
    # 测试具体的伏击人
    user_names = ["涤生三风", "老子到处说", "无量击掌"]
    for user_name in user_names:
        params = {"page": 1, "page_size": 10, "user_name": user_name}
        response = requests.get(BASE_URL, params=params)
        data = response.json()
        filtered_total = data.get("total", 0)
        print(f"伏击人 '{user_name}' 筛选结果: {filtered_total} 条")
        
        if filtered_total > 0:
            sample = data.get("data", [])[0]
            print(f"  示例数据: {sample['user_name']} - {sample['stock_name']}")

def test_filter_success_rate():
    """测试成功率筛选"""
    print("\n=== 测试成功率筛选 ===")
    
    # 测试不同的成功率阈值
    thresholds = [80, 70, 60]
    for threshold in thresholds:
        params = {"page": 1, "page_size": 10, "min_success_rate": threshold}
        response = requests.get(BASE_URL, params=params)
        data = response.json()
        filtered_total = data.get("total", 0)
        print(f"成功率 >= {threshold}% 筛选结果: {filtered_total} 条")
        
        if filtered_total > 0:
            sample = data.get("data", [])[0]
            print(f"  示例数据: {sample['success_rate']}% - {sample['stock_name']}")

def test_filter_reason():
    """测试伏击理由筛选"""
    print("\n=== 测试伏击理由筛选 ===")
    
    # 测试关键词筛选
    keywords = ["倍阳", "黄金柱", "回踩"]
    for keyword in keywords:
        params = {"page": 1, "page_size": 10, "reason": keyword}
        response = requests.get(BASE_URL, params=params)
        data = response.json()
        filtered_total = data.get("total", 0)
        print(f"伏击理由包含 '{keyword}' 筛选结果: {filtered_total} 条")
        
        if filtered_total > 0:
            sample = data.get("data", [])[0]
            print(f"  示例数据: {sample['reason'][:50]}...")

def test_filter_date_range():
    """测试日期范围筛选"""
    print("\n=== 测试日期范围筛选 ===")
    
    # 获取今天和昨天的日期
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # 测试今天的数据
    params = {"page": 1, "page_size": 10, "start_date": today, "end_date": today}
    response = requests.get(BASE_URL, params=params)
    data = response.json()
    today_total = data.get("total", 0)
    print(f"今天 ({today}) 数据: {today_total} 条")
    
    # 测试昨天的数据
    params = {"page": 1, "page_size": 10, "start_date": yesterday, "end_date": yesterday}
    response = requests.get(BASE_URL, params=params)
    data = response.json()
    yesterday_total = data.get("total", 0)
    print(f"昨天 ({yesterday}) 数据: {yesterday_total} 条")

def test_combined_filters():
    """测试组合筛选"""
    print("\n=== 测试组合筛选 ===")
    
    # 组合多个筛选条件
    params = {
        "page": 1,
        "page_size": 10,
        "user_name": "涤生三风",
        "min_success_rate": 80,
        "reason": "倍阳"
    }
    response = requests.get(BASE_URL, params=params)
    data = response.json()
    combined_total = data.get("total", 0)
    print(f"组合筛选结果: {combined_total} 条")
    
    if combined_total > 0:
        sample = data.get("data", [])[0]
        print(f"  示例数据: {sample['user_name']} - {sample['stock_name']} - {sample['success_rate']}%")

def main():
    """主测试函数"""
    print("开始测试爬虫分析筛选功能...")
    
    try:
        # 测试各个筛选条件
        test_filter_user_name()
        test_filter_success_rate()
        test_filter_reason()
        test_filter_date_range()
        test_combined_filters()
        
        print("\n=== 测试完成 ===")
        
    except Exception as e:
        print(f"测试过程中发生错误: {e}")

if __name__ == "__main__":
    main()
