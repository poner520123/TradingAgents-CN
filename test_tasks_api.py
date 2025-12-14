#!/usr/bin/env python3
"""
测试 /api/analysis/tasks 接口
"""

import aiohttp
import asyncio

async def main():
    """测试 tasks 接口"""
    url = "http://localhost:8000/api/analysis/tasks"
    headers = {
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc2NTY5MTAzMH0.Q7WoxFDcigCvEb_lKOVlnrloXLstxcMae71ghUQIx7M"
    }
    
    print("=" * 80)
    print("📋 测试 /api/analysis/tasks 接口")
    print("=" * 80)
    print(f"📝 API URL: {url}")
    print(f"🔐 Authorization: Bearer {headers['Authorization'][:20]}...")
    print()
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                status = response.status
                response_text = await response.text()
                
                print(f"📊 响应状态码: {status}")
                print(f"📋 响应内容: {response_text}")
                print()
                
                if status == 200:
                    print("✅ 接口测试成功！")
                    print("🎉 服务器内部错误已修复")
                    return True
                else:
                    print("❌ 接口测试失败！")
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
