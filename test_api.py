#!/usr/bin/env python3
"""
测试API是否正常工作
"""

import requests

BASE_URL = "http://localhost:8000/api/crawler/list"

def test_api():
    """测试API"""
    print("=== 测试API连接 ===")
    
    try:
        # 测试基本连接
        response = requests.get(BASE_URL, params={"page": 1, "page_size": 10}, timeout=30)
        print(f"状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"响应数据: {data}")
        else:
            print(f"错误响应: {response.text}")
            
    except Exception as e:
        print(f"请求失败: {e}")

if __name__ == "__main__":
    test_api()
