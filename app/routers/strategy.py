#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Advanced strategy router (龙头复盘神器 · 高端策略).

Data logic is identical to ``docs/龙头复盘神器/高端策略.py``:

* three feeds: 题材轮动策略(tcld) / 飞云主板策略(zb) / 飞云创业板策略(cyb)
* monthly NDJSON source: ``https://gp.domekj.top/peizhi/{prefix}_YYYYMM.txt``
* columns: 日期 | 代码 | 名称 | 当日收盘价 | 次日最高价 | 次日收盘价
* monthly totals: cumulative 次日最高价 / 次日收盘价 change

The endpoint only proxies + parses the upstream files, so the browser never
has to deal with CORS or encoding issues.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import requests
from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)

router = APIRouter()

DATA_BASE_URL = "https://gp.domekj.top/peizhi/{prefix}{month}.txt"
REQUEST_TIMEOUT = 15
CACHE_TTL_SECONDS = 300

# strategy key -> upstream file prefix + display title
STRATEGY_DEFINITIONS: Dict[str, Dict[str, str]] = {
    "tcld": {"prefix": "tcld_", "title": "题材轮动策略"},
    "zb": {"prefix": "zb_", "title": "飞云主板策略"},
    "cyb": {"prefix": "cyb_", "title": "飞云创业板策略"},
}

# small process level cache: (strategy, month) -> payload
_cache: Dict[str, Dict[str, Any]] = {}


def parse_percent(value: Optional[str]) -> Optional[float]:
    """'6.76[-0.88%]' -> -0.88 ; returns None when unavailable."""
    if not value or "[" not in value:
        return None
    try:
        return float(value[value.index("[") + 1:].rstrip("%]"))
    except ValueError:
        return None


def fetch_month_rows(prefix: str, month: int) -> Optional[List[Dict[str, Any]]]:
    """Fetch one monthly file. Returns None when upstream reports 404."""
    url = DATA_BASE_URL.format(prefix=prefix, month=month)
    response = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=REQUEST_TIMEOUT,
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()

    rows: List[Dict[str, Any]] = []
    for line in response.content.decode("utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows


def build_rows(raw_rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], float, float]:
    """Normalize upstream records and accumulate the monthly totals."""
    rows: List[Dict[str, Any]] = []
    total_highest = 0.0
    total_closing = 0.0

    for item in raw_rows:
        price_raw = item.get("price", "")
        highest_raw = item.get("highest_price", "")
        closing_raw = item.get("closing_price", "")

        highest_pct = parse_percent(highest_raw)
        closing_pct = parse_percent(closing_raw)
        if highest_pct is not None:
            total_highest += highest_pct
        if closing_pct is not None:
            total_closing += closing_pct

        rows.append({
            "selected_date": item.get("selected_date", ""),
            "code": item.get("code", ""),
            "name": item.get("name", ""),
            "price": "" if price_raw == "0" else price_raw,
            "highest_price": "" if highest_raw == "0" else highest_raw,
            "closing_price": "" if closing_raw == "0" else closing_raw,
            "highest_pct": highest_pct,
            "closing_pct": closing_pct,
        })

    return rows, round(total_highest, 2), round(total_closing, 2)


def empty_payload(strategy: str, month: int, title: str, message: str, has_data: bool) -> Dict[str, Any]:
    return {
        "success": True,
        "strategy": strategy,
        "strategy_title": title,
        "month": month,
        "has_data": has_data,
        "message": message,
        "rows": [],
        "stats": None,
    }


@router.get("/strategy/monthly", tags=["strategy"])
async def get_strategy_monthly(
    strategy: str = Query(..., description="策略标识: tcld / zb / cyb"),
    month: int = Query(..., description="月份, 例如 202609"),
):
    """Return one strategy's monthly signals plus the monthly totals."""
    definition = STRATEGY_DEFINITIONS.get(strategy)
    if definition is None:
        return {
            "success": False,
            "strategy": strategy,
            "month": month,
            "has_data": False,
            "message": f"未知策略: {strategy}",
            "rows": [],
            "stats": None,
        }

    title = definition["title"]
    cache_key = f"{strategy}:{month}"
    now = time.time()

    cached = _cache.get(cache_key)
    if cached and now - cached["cached_at"] < CACHE_TTL_SECONDS:
        payload = dict(cached["payload"])
        payload["cached"] = True
        return payload

    try:
        raw_rows = fetch_month_rows(definition["prefix"], month)
    except Exception as exc:
        logger.warning("策略数据获取失败 %s %s: %s", strategy, month, exc)
        return {
            "success": False,
            "strategy": strategy,
            "strategy_title": title,
            "month": month,
            "has_data": False,
            "message": f"数据获取失败: {exc}",
            "rows": [],
            "stats": None,
        }

    if not raw_rows:
        payload = empty_payload(strategy, month, title, "该月份无数据", False)
    else:
        rows, total_highest, total_closing = build_rows(raw_rows)
        payload = {
            "success": True,
            "strategy": strategy,
            "strategy_title": title,
            "month": month,
            "has_data": True,
            "message": "",
            "rows": rows,
            "stats": {
                "highest_total": total_highest,
                "closing_total": total_closing,
                "count": len(rows),
            },
        }

    _cache[cache_key] = {"cached_at": now, "payload": payload}
    return payload
