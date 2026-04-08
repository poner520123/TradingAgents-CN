
"""重置管理员密码脚本"""
import bcrypt
from pymongo import MongoClient

# 连接MongoDB
client = MongoClient('mongodb://admin:admin123@localhost:27017/')
db = client['tradingagents']

# 生成密码哈希
password = "admin123"
hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

# 更新管理员密码
result = db.users.update_one(
    {"username": "admin"},
    {"$set": {"hashed_password": hashed_password}}
)

if result.modified_count > 0:
    print("管理员密码重置成功！")
    print("用户名: admin")
    print("密码: admin123")
else:
    print("管理员用户不存在或无需更新")

client.close()
