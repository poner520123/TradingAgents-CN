import requests
import json

# 测试 /api/analysis/tasks 端点
print("📋 测试 /api/analysis/tasks 接口")

# 1. 登录获取token
try:
    login_url = "http://localhost:8000/api/auth/login"
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    login_response = requests.post(login_url, json=login_data)
    login_response.raise_for_status()
    login_result = login_response.json()
    token = login_result["data"]["access_token"]
    print("✅ 登录成功，获取到token")
except Exception as e:
    print(f"❌ 登录失败: {e}")
    exit(1)

# 2. 测试 /api/analysis/tasks 端点
try:
    tasks_url = "http://localhost:8000/api/analysis/tasks"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    tasks_response = requests.get(tasks_url, headers=headers)
    tasks_response.raise_for_status()
    tasks_result = tasks_response.json()
    print(f"✅ GET /api/analysis/tasks 成功")
    print(f"   状态码: {tasks_response.status_code}")
    print(f"   响应: {json.dumps(tasks_result, ensure_ascii=False, indent=2)}")
    
    if tasks_result.get("success"):
        print("🎉 端点恢复正常！")
    else:
        print("❌ 端点返回失败状态")
except Exception as e:
    print(f"❌ GET /api/analysis/tasks 失败: {e}")
    if hasattr(e, 'response'):
        print(f"   状态码: {e.response.status_code}")
        try:
            print(f"   响应: {json.dumps(e.response.json(), ensure_ascii=False, indent=2)}")
        except:
            print(f"   响应: {e.response.text}")
    exit(1)
