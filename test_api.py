import requests
import json

# 测试API端点
url = "http://localhost:8000/api/stock-map/name?code=301051"

try:
    response = requests.get(url)
    response.encoding = 'utf-8'  # 显式设置编码
    print(f"状态码: {response.status_code}")
    print(f"响应头: {response.headers}")
    print(f"响应内容: {response.text}")
    
    # 解析JSON
    data = response.json()
    print(f"解析后的数据: {json.dumps(data, ensure_ascii=False)}")
    
    if data['success']:
        print(f"股票名称: {data['data']}")
    else:
        print(f"错误信息: {data['message']}")
        
except Exception as e:
    print(f"请求失败: {e}")
