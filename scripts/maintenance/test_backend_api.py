#!/usr/bin/env python3
"""
直接测试后端API筛选功能
"""

import requests

BASE_URL = "http://localhost:8000/api/crawler/list"

def test_backend_api():
    """测试后端API筛选功能"""
    print("=== 测试后端API筛选功能 ===")
    
    # 测试1: 空筛选
    print("\n1. 测试空筛选")
    params = {"page": 1, "page_size": 10}
    response = requests.get(BASE_URL, params=params)
    data = response.json()
    print(f"状态码: {response.status_code}")
    print(f"总记录数: {data.get('total', 0)}")
    print(f"数据条数: {len(data.get('data', []))}")
    
    # 测试2: 伏击人筛选
    print("\n2. 测试伏击人筛选 - 涤生三风")
    params = {"page": 1, "page_size": 10, "user_name": "涤生三风"}
    response = requests.get(BASE_URL, params=params)
    data = response.json()
    print(f"状态码: {response.status_code}")
    print(f"总记录数: {data.get('total', 0)}")
    print(f"数据条数: {len(data.get('data', []))}")
    
    # 测试3: 成功率筛选
    print("\n3. 测试成功率筛选 - >= 80%")
    params = {"page": 1, "page_size": 10, "min_success_rate": 80}
    response = requests.get(BASE_URL, params=params)
    data = response.json()
    print(f"状态码: {response.status_code}")
    print(f"总记录数: {data.get('total', 0)}")
    print(f"数据条数: {len(data.get('data', []))}")
    
    # 测试4: 日期范围筛选
    print("\n4. 测试日期范围筛选 - 2026-04-07")
    params = {"page": 1, "page_size": 10, "start_date": "2026-04-07", "end_date": "2026-04-07"}
    response = requests.get(BASE_URL, params=params)
    data = response.json()
    print(f"状态码: {response.status_code}")
    print(f"总记录数: {data.get('total', 0)}")
    print(f"数据条数: {len(data.get('data', []))}")
    
    # 测试5: 组合筛选
    print("\n5. 测试组合筛选 - 涤生三风 + >= 80%")
    params = {"page": 1, "page_size": 10, "user_name": "涤生三风", "min_success_rate": 80}
    response = requests.get(BASE_URL, params=params)
    data = response.json()
    print(f"状态码: {response.status_code}")
    print(f"总记录数: {data.get('total', 0)}")
    print(f"数据条数: {len(data.get('data', []))}")

if __name__ == "__main__":
    test_backend_api()
