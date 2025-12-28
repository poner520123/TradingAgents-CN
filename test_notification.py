#!/usr/bin/env python
"""
测试爬虫通知系统
"""
import asyncio
import time
from datetime import datetime
from app.routers.websocket_notifications import send_notification_via_websocket

async def test_notification():
    """测试发送通知"""
    print("开始测试通知系统...")
    
    # 模拟爬虫启动通知
    start_notification = {
        "id": f"test_{int(time.time())}",
        "title": "爬虫任务开始",
        "content": "开始爬取页面 1-10，目标覆盖最近3个工作日",
        "type": "info",
        "source": "crawler",
        "created_at": datetime.utcnow().isoformat(),
        "status": "unread"
    }
    
    await send_notification_via_websocket("admin", start_notification)
    print("已发送爬虫启动通知")
    
    # 模拟爬虫进度通知
    time.sleep(2)
    progress_notification = {
        "id": f"test_{int(time.time()) + 1}",
        "title": "爬虫进度",
        "content": "正在爬取第 1 页...",
        "type": "info",
        "source": "crawler",
        "created_at": datetime.utcnow().isoformat(),
        "status": "unread"
    }
    
    await send_notification_via_websocket("admin", progress_notification)
    print("已发送爬虫进度通知")
    
    # 模拟爬虫成功通知
    time.sleep(2)
    success_notification = {
        "id": f"test_{int(time.time()) + 2}",
        "title": "爬虫进度",
        "content": "第 1 页: 成功保存 10 条新数据",
        "type": "success",
        "source": "crawler",
        "created_at": datetime.utcnow().isoformat(),
        "status": "unread"
    }
    
    await send_notification_via_websocket("admin", success_notification)
    print("已发送爬虫成功通知")
    
    # 模拟爬虫完成通知
    time.sleep(2)
    completion_notification = {
        "id": f"test_{int(time.time()) + 3}",
        "title": "爬虫任务完成",
        "content": "爬虫任务完成，共爬取 10 页，保存 100 条新数据",
        "type": "success",
        "source": "crawler",
        "created_at": datetime.utcnow().isoformat(),
        "status": "unread"
    }
    
    await send_notification_via_websocket("admin", completion_notification)
    print("已发送爬虫完成通知")
    
    print("通知测试完成")

if __name__ == "__main__":
    asyncio.run(test_notification())
