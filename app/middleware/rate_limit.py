"""
速率限制中间件
防止API滥用，实现用户级和端点级速率限制
"""

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
from typing import Callable, Dict, Optional
from app.core.redis_client import get_redis_service, RedisKeys

logger = logging.getLogger(__name__)


def _http_exception_response(exc: HTTPException) -> JSONResponse:
    """
    将中间件内抛出的 HTTPException 转换为等价的 JSON 响应。

    为什么不能直接 ``raise HTTPException``：
    Starlette 的中间件栈结构为::

        ServerErrorMiddleware → 用户中间件 → ExceptionMiddleware → 路由

    负责把 HTTPException 转换成 JSON 响应的 ``ExceptionMiddleware`` 位于**用户中间件之内**，
    因此在用户中间件中抛出的 HTTPException 不会被它捕获，最终由最外层的
    ``ServerErrorMiddleware`` 处理 —— 客户端收到的是 500 而不是预期的 429。

    这里直接返回与 FastAPI 默认处理器完全一致的响应体（``{"detail": ...}``），
    保持对外契约不变。
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """速率限制中间件"""
    
    def __init__(self, app, default_rate_limit: int = 100):
        super().__init__(app)
        self.default_rate_limit = default_rate_limit
        
        # 不同端点的速率限制配置
        self.endpoint_limits = {
            "/api/analysis/single": 10,      # 单股分析：每分钟10次
            "/api/analysis/batch": 5,        # 批量分析：每分钟5次
            "/api/screening/filter": 20,     # 股票筛选：每分钟20次
            "/api/auth/login": 5,            # 登录：每分钟5次
            "/api/auth/register": 3,         # 注册：每分钟3次
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 跳过健康检查和静态资源
        if request.url.path.startswith(("/api/health", "/docs", "/redoc", "/openapi.json")):
            return await call_next(request)
        
        # 获取用户ID（如果已认证）
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            # 对于未认证用户，使用IP地址
            user_id = f"ip:{request.client.host}" if request.client else "unknown"
        
        # 检查速率限制
        try:
            redis_service = get_redis_service()
            if not redis_service.is_available:
                # Redis不可用，跳过速率限制
                return await call_next(request)
            await self.check_rate_limit(user_id, request.url.path)
        except HTTPException as exc:
            # 中间件内抛出的 HTTPException 不会被 ExceptionMiddleware 捕获，
            # 必须直接转成响应，否则客户端会收到 500 而不是 429。
            logger.warning(
                f"速率限制触发 - 用户: {user_id}, 端点: {request.url.path}"
            )
            return _http_exception_response(exc)
        except Exception as exc:
            logger.warning(f"速率限制检查失败: {exc}，允许请求通过")
            # 如果Redis不可用，允许请求通过

        return await call_next(request)
    
    async def check_rate_limit(self, user_id: str, endpoint: str):
        """检查速率限制"""
        redis_service = get_redis_service()
        
        # 获取端点的速率限制
        rate_limit = self.endpoint_limits.get(endpoint, self.default_rate_limit)
        
        # 构建Redis键
        rate_key = RedisKeys.USER_RATE_LIMIT.format(
            user_id=user_id,
            endpoint=endpoint.replace("/", "_")
        )
        
        # 获取当前计数
        current_count = await redis_service.increment_with_ttl(rate_key, ttl=60)
        
        # 检查是否超过限制
        if current_count > rate_limit:
            logger.warning(
                f"速率限制触发 - 用户: {user_id}, "
                f"端点: {endpoint}, "
                f"当前计数: {current_count}, "
                f"限制: {rate_limit}"
            )
            
            raise HTTPException(
                status_code=429,
                detail={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": f"请求过于频繁，请稍后重试",
                        "rate_limit": rate_limit,
                        "current_count": current_count,
                        "reset_time": 60
                    }
                }
            )
        
        logger.debug(
            f"速率限制检查通过 - 用户: {user_id}, "
            f"端点: {endpoint}, "
            f"当前计数: {current_count}/{rate_limit}"
        )


class QuotaMiddleware(BaseHTTPMiddleware):
    """每日配额中间件"""
    
    def __init__(self, app, daily_quota: int = 1000):
        super().__init__(app)
        self.daily_quota = daily_quota
        
        # 需要计入配额的端点
        self.quota_endpoints = {
            "/api/analysis/single",
            "/api/analysis/batch",
            "/api/screening/filter"
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 只对需要配额的端点进行检查
        if request.url.path not in self.quota_endpoints:
            return await call_next(request)
        
        # 获取用户ID
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            # 未认证用户不受配额限制
            return await call_next(request)
        
        # 检查每日配额
        try:
            redis_service = get_redis_service()
            if not redis_service.is_available:
                # Redis不可用，跳过配额限制
                return await call_next(request)
            await self.check_daily_quota(user_id)
        except HTTPException as exc:
            # 同上：中间件内的 HTTPException 必须直接转成响应
            logger.warning(f"每日配额超限 - 用户: {user_id}")
            return _http_exception_response(exc)
        except Exception as exc:
            logger.warning(f"配额检查失败: {exc}，允许请求通过")
            # 如果Redis不可用，允许请求通过

        return await call_next(request)
    
    async def check_daily_quota(self, user_id: str):
        """检查每日配额"""
        import datetime
        
        redis_service = get_redis_service()
        
        # 获取今天的日期
        today = datetime.date.today().isoformat()
        
        # 构建Redis键
        quota_key = RedisKeys.USER_DAILY_QUOTA.format(
            user_id=user_id,
            date=today
        )
        
        # 获取今日使用量
        current_usage = await redis_service.increment_with_ttl(quota_key, ttl=86400)  # 24小时TTL
        
        # 检查是否超过配额
        if current_usage > self.daily_quota:
            logger.warning(
                f"每日配额超限 - 用户: {user_id}, "
                f"今日使用: {current_usage}, "
                f"配额: {self.daily_quota}"
            )
            
            raise HTTPException(
                status_code=429,
                detail={
                    "error": {
                        "code": "DAILY_QUOTA_EXCEEDED",
                        "message": "今日配额已用完，请明天再试",
                        "daily_quota": self.daily_quota,
                        "current_usage": current_usage,
                        "reset_date": today
                    }
                }
            )
        
        logger.debug(
            f"配额检查通过 - 用户: {user_id}, "
            f"今日使用: {current_usage}/{self.daily_quota}"
        )
