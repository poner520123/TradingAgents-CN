#!/usr/bin/env python3
"""
测试管理员登录功能
"""

import aiohttp
import asyncio

async def main():
    """测试登录功能"""
    url = "http://localhost:8000/api/auth/login"
    payload = {
        "username": "admin",
        "password": "admin123"
    }
    
    print("=" * 80)
    print("🔐 测试管理员登录功能")
    print("=" * 80)
    print(f"📝 登录URL: {url}")
    print(f"👤 用户名: {payload['username']}")
    print(f"🔑 密码: {'*' * len(payload['password'])}")
    print()
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers={"Content-Type": "application/json"}) as response:
                status = response.status
                response_text = await response.text()
                
                print(f"📊 响应状态码: {status}")
                print(f"📋 响应内容: {response_text}")
                print()
                
                if status == 200:
                    print("✅ 登录测试成功！")
                    print("🎉 管理员账号可以正常登录")
                    return True
                else:
                    print("❌ 登录测试失败！")
                    print(f"💡 错误信息: {response_text}")
                    return False
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    print()
    print("=" * 80)
    exit(0 if success else 1)
