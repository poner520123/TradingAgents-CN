"""
测试数据工厂。

集中构造各接口的请求/响应样例，避免在测试用例里散落魔法字符串。
所有工厂均返回**全新**的 dict/list，测试之间互不影响。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

CN_TZ = timezone(timedelta(hours=8))


# --------------------------------------------------------------------------- #
# 用户 / 认证
# --------------------------------------------------------------------------- #
def user_doc(
    username: str = "testuser",
    email: Optional[str] = None,
    is_admin: bool = False,
    is_active: bool = True,
    password_hash: str = "$2b$12$notarealhashnotarealhashnotarealhashnotarealhashnotar",
    **extra: Any,
) -> Dict[str, Any]:
    """构造 ``users`` 集合中的用户文档。"""
    doc: Dict[str, Any] = {
        "username": username,
        "email": email or f"{username}@example.com",
        "hashed_password": password_hash,
        "is_active": is_active,
        "is_verified": True,
        "is_admin": is_admin,
        "created_at": datetime.now(CN_TZ),
        "updated_at": datetime.now(CN_TZ),
        "last_login": None,
        "preferences": {},
        "daily_quota": 1000,
        "concurrent_limit": 3,
        "total_analyses": 0,
        "successful_analyses": 0,
        "failed_analyses": 0,
    }
    doc.update(extra)
    return doc


# --------------------------------------------------------------------------- #
# 行情
# --------------------------------------------------------------------------- #
def quote_payload(
    code: str = "600519",
    close: float = 1680.5,
    pct_chg: float = 1.23,
    name: str = "贵州茅台",
    **extra: Any,
) -> Dict[str, Any]:
    """构造行情接口返回的单只股票数据。"""
    payload = {
        "code": code,
        "name": name,
        "close": close,
        "pct_chg": pct_chg,
        "open": close - 5,
        "high": close + 10,
        "low": close - 12,
        "pre_close": close - 5,
        "volume": 1_234_567,
        "amount": 2_000_000_000.0,
        "trade_date": datetime.now(CN_TZ).strftime("%Y-%m-%d"),
        "source": "akshare",
    }
    payload.update(extra)
    return payload


def quotes_payload(codes: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
    """构造 ``{code: quote}`` 结构的批量行情。"""
    codes = codes or ["600519", "300750"]
    return {code: quote_payload(code=code) for code in codes}


# --------------------------------------------------------------------------- #
# 股票基础信息
# --------------------------------------------------------------------------- #
def stock_basic_doc(
    code: str = "600519",
    name: str = "贵州茅台",
    source: str = "akshare",
    **extra: Any,
) -> Dict[str, Any]:
    """构造 ``stock_basic_info`` 集合文档。"""
    doc: Dict[str, Any] = {
        "code": code,
        "name": name,
        "sse": "SH",
        "category": "stock_cn",
        "full_symbol": f"{code}.SH",
        "industry": "白酒",
        "total_mv": 2_100_000_000_000,
        "circ_mv": 2_100_000_000_000,
        "pe": 28.5,
        "pb": 8.2,
        "source": source,
        "updated_at": datetime.now(CN_TZ),
    }
    doc.update(extra)
    return doc


# --------------------------------------------------------------------------- #
# 分析任务 / 报告
# --------------------------------------------------------------------------- #
def analysis_task_doc(
    task_id: str = "task-0001",
    user_id: str = "user-1",
    symbol: str = "600519",
    status: str = "pending",
    progress: int = 0,
    **extra: Any,
) -> Dict[str, Any]:
    """构造 ``analysis_tasks`` 集合文档。"""
    doc: Dict[str, Any] = {
        "task_id": task_id,
        "user_id": user_id,
        "symbol": symbol,
        "status": status,
        "progress": progress,
        "created_at": datetime.now(CN_TZ),
        "updated_at": datetime.now(CN_TZ),
        "parameters": {"market_type": "A股", "research_depth": "标准"},
        "result": None,
    }
    doc.update(extra)
    return doc


def analysis_report_doc(
    task_id: str = "task-0001",
    stock_symbol: str = "600519",
    **extra: Any,
) -> Dict[str, Any]:
    """构造 ``analysis_reports`` 集合文档。"""
    doc: Dict[str, Any] = {
        "task_id": task_id,
        "stock_symbol": stock_symbol,
        "stock_name": "贵州茅台",
        "analysis_date": datetime.now(CN_TZ).strftime("%Y-%m-%d"),
        "sections": [
            {"key": "summary", "title": "投资摘要", "content": "## 摘要\n测试内容"},
            {"key": "market", "title": "技术分析", "content": "## 技术\n测试内容"},
        ],
        "created_at": datetime.now(CN_TZ),
    }
    doc.update(extra)
    return doc


# --------------------------------------------------------------------------- #
# 统一响应封装
# --------------------------------------------------------------------------- #
def api_ok(data: Any = None, message: str = "ok") -> Dict[str, Any]:
    """构造后端统一成功响应。"""
    return {"success": True, "data": data, "message": message}


def api_fail(message: str = "error", code: int = 500, data: Any = None) -> Dict[str, Any]:
    """构造后端统一失败响应。"""
    return {"success": False, "data": data, "message": message, "code": code}
