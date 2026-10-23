"""
Routers package: expose API routers.

设计说明
--------
本模块采用 **PEP 562 惰性导入**（模块级 ``__getattr__``）。

背景：早期版本在这里 ``from app.routers import (45 个模块)`` 一次性导入全部路由。
由于 ``app.routers.analysis`` 会连带导入
``app.services.analysis_service`` → ``simple_analysis_service`` →
``tradingagents.graph.trading_graph`` → ``tradingagents.dataflows``，
而这些模块在**导入阶段**会探测 MongoDB / Redis 可用性，
导致「导入任意一个路由」都要等待数十秒的连接超时（实测本机无 MongoDB 时
``import app.main`` 耗时 133 秒）。

改为惰性导入后：
* ``from app.routers import analysis`` 等用法**完全不变**（对外接口零变化）；
* 只有真正被访问的路由才会被导入；
* 导入 ``app.routers`` 本身几乎零成本。

别名 ``auth`` 指向 ``auth_db``，保持向后兼容。
"""

from __future__ import annotations

import importlib
from typing import Any, List

# 可通过 `from app.routers import <name>` 访问的路由模块
_ROUTER_MODULES: List[str] = [
    "auth_db",
    "analysis",
    "screening",
    "queue",
    "sse",
    "health",
    "favorites",
    "config",
    "reports",
    "database",
    "operation_logs",
    "tags",
    "tushare_init",
    "akshare_init",
    "baostock_init",
    "historical_data",
    "multi_period_sync",
    "financial_data",
    "news_data",
    "social_media",
    "internal_messages",
    "usage_statistics",
    "model_capabilities",
    "cache",
    "logs",
    "crawler",
    "sync",
    "multi_source_sync",
    "stocks",
    "stock_data",
    "stock_sync",
    "stock_map",
    "multi_market_stocks",
    "notifications",
    "websocket_notifications",
    "scheduler",
    "system_config",
    "ranking",
    "advanced_screening",
    "st_filter",
    "quotes",
    "strategy",
    "astock",
    "paper",
]

# 兼容别名：auth -> auth_db
_ROUTER_ALIASES = {
    "auth": "auth_db",
}

__all__ = [*_ROUTER_MODULES, *_ROUTER_ALIASES.keys()]


def __getattr__(name: str) -> Any:
    """
    PEP 562 模块级惰性加载。

    首次访问某个路由属性时才真正导入对应模块，随后缓存到 ``globals()``，
    后续访问为普通的属性查找。
    """
    target = _ROUTER_ALIASES.get(name, name)
    if target not in _ROUTER_MODULES:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = importlib.import_module(f"{__name__}.{target}")
    globals()[target] = module
    if target != name:
        globals()[name] = module
    return module


def __dir__() -> List[str]:
    return sorted(set(globals()) | set(__all__))
