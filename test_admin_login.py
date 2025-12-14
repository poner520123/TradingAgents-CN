import requests
import json
from pymongo import MongoClient
from app.core.config import settings
from app.services.user_service import UserService

print("🔍 检查admin用户登录问题")

# 1. 检查MongoDB连接
print("\n1. 检查MongoDB连接...")
try:
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB]
    client.admin.command('ping')
    print("   ✅ MongoDB连接成功")
except Exception as e:
    print(f"   ❌ MongoDB连接失败: {e}")
    exit(1)

# 2. 检查admin用户是否存在
print("\n2. 检查admin用户是否存在...")
try:
    users_collection = db.users
    admin_user = users_collection.find_one({"username": "admin"})
    if admin_user:
        print(f"   ✅ admin用户存在")
        print(f"   用户名: {admin_user.get('username')}")
        print(f"   邮箱: {admin_user.get('email')}")
        print(f"   激活状态: {admin_user.get('is_active')}")
        print(f"   管理员状态: {admin_user.get('is_admin')}")
        print(f"   创建时间: {admin_user.get('created_at')}")
        print(f"   最后登录: {admin_user.get('last_login')}")
    else:
        print("   ❌ admin用户不存在")
except Exception as e:
    print(f"   ❌ 检查用户失败: {e}")
    exit(1)

# 3. 测试密码验证逻辑
print("\n3. 测试密码验证逻辑...")
try:
    user_service = UserService()
    test_password = "admin123"
    
    # 生成测试哈希
    test_hash = user_service.hash_password(test_password)
    print(f"   测试密码: {test_password}")
    print(f"   测试哈希: {test_hash[:20]}...")
    
    # 验证密码
    is_valid = user_service.verify_password(test_password, test_hash)
    print(f"   密码验证: {'✅ 成功' if is_valid else '❌ 失败'}")
    
    # 检查存储的密码哈希
    if admin_user:
        stored_hash = admin_user.get("hashed_password")
        is_stored_valid = user_service.verify_password(test_password, stored_hash)
        print(f"   存储密码验证: {'✅ 成功' if is_stored_valid else '❌ 失败'}")
        print(f"   存储哈希: {stored_hash[:20]}...")
        print(f"   哈希匹配: {test_hash == stored_hash}")
except Exception as e:
    print(f"   ❌ 测试密码逻辑失败: {e}")
    exit(1)

# 4. 尝试修复admin用户（如果需要）
print("\n4. 修复admin用户...")
try:
    # 重新创建或更新admin用户
    admin = await user_service.create_admin_user()
    if admin:
        print(f"   ✅ 管理员用户已创建/更新")
        print(f"   用户名: {admin.username}")
        print(f"   密码: admin123")
    else:
        print("   ❌ 创建管理员用户失败")
except Exception as e:
    print(f"   ❌ 修复admin用户失败: {e}")
    exit(1)

# 5. 测试登录API
print("\n5. 测试登录API...")
try:
    login_url = "http://localhost:8000/api/auth/login"
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    login_response = requests.post(login_url, json=login_data)
    print(f"   状态码: {login_response.status_code}")
    print(f"   响应: {json.dumps(login_response.json(), ensure_ascii=False, indent=2)}")
    
    if login_response.status_code == 200:
        print("   🎉 登录成功！")
    else:
        print("   ❌ 登录失败！")
except Exception as e:
    print(f"   ❌ 测试登录API失败: {e}")
    exit(1)

# 6. 测试/api/analysis/tasks端点
print("\n6. 测试/api/analysis/tasks端点...")
try:
    # 先获取token
    login_response = requests.post(login_url, json=login_data)
    token = login_response.json()["data"]["access_token"]
    
    tasks_url = "http://localhost:8000/api/analysis/tasks"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    tasks_response = requests.get(tasks_url, headers=headers)
    print(f"   状态码: {tasks_response.status_code}")
    print(f"   响应: {json.dumps(tasks_response.json(), ensure_ascii=False, indent=2)}")
    
    if tasks_response.status_code == 200:
        print("   🎉 /api/analysis/tasks 端点正常！")
    else:
        print("   ❌ /api/analysis/tasks 端点异常！")
except Exception as e:
    print(f"   ❌ 测试/api/analysis/tasks端点失败: {e}")
    exit(1)

print("\n✅ 所有测试完成！")
