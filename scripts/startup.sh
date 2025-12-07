#!/bin/bash

# 初始化脚本 - 在容器启动时执行

# 设置日志格式
echo "🚀 启动 TradingAgents-CN 后端服务..."

# 检查是否需要执行初始化
echo "🔍 检查是否需要执行初始化..."

# 检查是否是首次启动或者需要重新初始化
if [ ! -f /app/.initialized ]; then
    echo "🔄 执行初始化操作..."
    
    # 执行股票名称代码映射数据初始化和历史数据更新
    python /app/scripts/init_stock_mapping_and_crawler.py
    
    if [ $? -eq 0 ]; then
        echo "✅ 初始化操作执行成功!"
        # 创建初始化完成标记文件
        touch /app/.initialized
    else
        echo "❌ 初始化操作执行失败!"
        exit 1
    fi
else
    echo "✅ 系统已经初始化，跳过初始化操作."
fi

# 启动FastAPI服务
echo "🚀 启动FastAPI服务..."
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
