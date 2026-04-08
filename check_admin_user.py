"""检查admin用户信息"""
import pymongo
from pymongo import MongoClient

# 连接MongoDB
client = MongoClient('mongodb://admin:admin123@localhost:27017/')
db = client['tradingagents']

# 查询admin用户
admin_user = db.users.find_one({"username": "admin"})

if admin_user:
    print("=== Admin用户信息 ===")
    print(f"用户名: {admin_user.get('username')}")
    print(f"邮箱: {admin_user.get('email')}")
    print(f"是否活跃: {admin_user.get('is_active')}")
    print(f"是否管理员: {admin_user.get('is_admin')}")
    print(f"密码哈希前20位: {admin_user.get('hashed_password', '')[:20]}...")
    print(f"密码哈希长度: {len(admin_user.get('hashed_password', ''))}")
    print(f"创建时间: {admin_user.get('created_at')}")
    print(f"最后登录: {admin_user.get('last_login')}")
else:
    print("❌ 未找到admin用户")

# 查询所有用户
all_users = list(db.users.find({}, {"username": 1, "email": 1, "is_active": 1, "is_admin": 1}))
print(f"\n=== 所有用户 ({len(all_users)}) ===")
for user in all_users:
    print(f"用户名: {user.get('username')}, 邮箱: {user.get('email')}, 活跃: {user.get('is_active')}, 管理员: {user.get('is_admin')}")

client.close()