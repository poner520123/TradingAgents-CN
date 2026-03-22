"""
Routers package: expose API routers
"""

# Import all router modules for easier access
from app.routers import (
    auth_db, analysis, screening, queue, sse, health, favorites, config, 
    reports, database, operation_logs, tags, tushare_init, akshare_init, 
    baostock_init, historical_data, multi_period_sync, financial_data, 
    news_data, social_media, internal_messages, usage_statistics, 
    model_capabilities, cache, logs, crawler, sync, multi_source_sync,
    stocks, stock_data, stock_sync, multi_market_stocks, notifications,
    websocket_notifications, scheduler, system_config, ranking, advanced_screening
)

# Alias for backward compatibility
auth = auth_db