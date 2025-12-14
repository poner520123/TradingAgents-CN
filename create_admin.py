#!/usr/bin/env python3
"""
创建或更新管理员用户
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from app.services.user_service import user_service
import asyncio

async def main():
    """主函数"""
    print("=" * 80)
    print("👤 创建或更新管理员用户")
    print("=" * 80)
    print()
    
    try:
        # 创建或更新管理员用户
        admin_user = await user_service.create_admin_user(
            username="admin",
            password="admin123",
            email="admin@ta.cn"
        )
        
        if admin_user:
            print("✅ 管理员用户创建或更新成功！")
            print(f"   用户名: {admin_user.username}")
            print(f"   邮箱: {admin_user.email}")
            print(f"   角色: {'管理员' if admin_user.is_admin else '普通用户'}")
            print(f"   状态: {'激活' if admin_user.is_active else '禁用'}")
            print(f"   创建时间: {admin_user.created_at}")
        else:
            print("❌ 管理员用户创建或更新失败！")
            sys.exit(1)
    except Exception as e:
        print(f"❌ 操作失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # 关闭数据库连接
        user_service.close()
    
    print()
    print("=" * 80)
    print("🔐 登录信息:")
    print(f"   用户名: admin")
    print(f"   密码: admin123")
    print()
    print("📝 注意事项:")
    print("   1. 建议登录后立即修改默认密码")
    print("   2. 确保生产环境中使用强密码")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
