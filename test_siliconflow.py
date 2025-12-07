#!/usr/bin/env python3
"""
测试Silicon Flow API的Python脚本
"""

import requests
import os

# 从环境变量获取API密钥
siliconflow_api_key = os.environ.get('SILICONFLOW_API_KEY')

# 如果环境变量没有设置，使用测试密钥
if not siliconflow_api_key:
    print("⚠️ 未找到SILICONFLOW_API_KEY环境变量，使用测试密钥")
    siliconflow_api_key = "test_key"

# API配置
base_url = "https://api.siliconflow.cn/v1"
test_model = "deepseek-ai/deepseek-chat"

test_prompt = "Hello, please respond with 'OK' if you can read this."

# 构建请求
try:
    response = requests.post(
        f"{base_url}/chat/completions",
        json={
            "model": test_model,
            "messages": [{"role": "user", "content": test_prompt}],
            "max_tokens": 20,
            "temperature": 0.1
        },
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {siliconflow_api_key}"
        },
        timeout=15
    )
    
    print(f"📡 响应状态: {response.status_code}")
    print(f"📦 响应内容: {response.text}")
    
    if response.status_code == 200:
        result = response.json()
        print("✅ API请求成功！")
        print(f"🔍 模型: {result.get('model')}")
        print(f"📝 响应: {result.get('choices', [])[0].get('message', {}).get('content')}")
    
except Exception as e:
    print(f"❌ 请求失败: {str(e)}")
