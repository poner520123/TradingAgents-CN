#!/usr/bin/env python3
"""
简单测试API是否正常工作
"""

import requests
import time

BASE_URL = "http://localhost:8000/api/crawler/list"

def test_api_simple():
    """简单测试API"""
    print("=== 测试API连接 ===")
    
    try:
        # 测试基本连接
        start_time = time.time()
        response = requests.get(BASE_URL, params={"page": 1, "page_size": 5}, timeout=30)
        elapsed_time = time.time() - start_time
        
        print(f"请求耗时: {elapsed_time:.2f}秒")
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"成功: {data.get('success')}")
            print(f"总记录数: {data.get('total')}")
            print(f"数据条数: {len(data.get('data', []))}")
            
            if data.get('data'):
                print("\n数据示例:")
                for item in data['data'][:3]:
                    print(f"  {item.get('user_name')} - {item.get('stock_name')} - {item.get('success_rate')}")
        else:
            print(f"错误响应: {response.text}")
            
    except Exception as e:
        print(f"请求失败: {e}")

if __name__ == "__main__":
    test_api_simple()
