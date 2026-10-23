"""
错误处理中间件
"""

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import traceback
from typing import Callable, Dict

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """全局错误处理中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            return await self.handle_error(request, exc)
    
    async def handle_error(self, request: Request, exc: Exception) -> JSONResponse:
        """处理异常并返回标准化错误响应"""
        
        # 获取请求ID
        request_id = getattr(request.state, "request_id", "unknown")
        
        # 记录错误日志
        logger.error(
            f"请求异常 - ID: {request_id}, "
            f"路径: {request.url.path}, "
            f"方法: {request.method}, "
            f"异常: {str(exc)}",
            exc_info=True
        )
        
        # 根据异常类型返回不同的错误响应
        if isinstance(exc, ValueError):
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": str(exc),
                        "request_id": request_id
                    }
                }
            )
        
        elif isinstance(exc, PermissionError):
            return JSONResponse(
                status_code=403,
                content={
                    "error": {
                        "code": "PERMISSION_DENIED",
                        "message": "权限不足",
                        "request_id": request_id
                    }
                }
            )
        
        elif isinstance(exc, FileNotFoundError):
            return JSONResponse(
                status_code=404,
                content={
                    "error": {
                        "code": "RESOURCE_NOT_FOUND",
                        "message": "请求的资源不存在",
                        "request_id": request_id
                    }
                }
            )
        
        else:
            # 未知异常
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "服务器内部错误，请稍后重试",
                        "request_id": request_id
                    }
                }
            )


# ---------------------------------------------------------------------------
# Global 500 handler
# ---------------------------------------------------------------------------
# Provided separately for a specific reason: `ServerErrorMiddleware` sits
# **outside all user middleware**, so `RequestIDMiddleware` cannot add the
# `X-Trace-ID` header to 500 responses (it re-raises before writing headers).
# The 500 handler is the only place that can touch the 500 response, so it is
# exposed as a reusable standalone function:
#
# * `app/main.py` registers it via `add_exception_handler(Exception, ...)`;
# * test cases can assemble it directly to verify that failed requests can
#   still be correlated with logs via the Trace-ID.
def build_trace_headers(request: Request) -> Dict[str, str]:
    """
    Pull the Trace-ID out of request state and build the response headers.

    The Trace-ID is written into `request.state` by `RequestIDMiddleware`;
    if the exception happens outside that middleware (e.g. CORS), it degrades
    to an empty header set.
    """
    trace_id = (
        getattr(request.state, "trace_id", None)
        or getattr(request.state, "request_id", None)
    )
    if not trace_id:
        return {}

    return {
        "X-Trace-ID": str(trace_id),
        "X-Request-ID": str(trace_id),
    }


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Unified handler for uncaught exceptions.

    The response body keeps the `{"error": {...}}` shape; only the Trace-ID
    response headers are added, so 5xx responses can be correlated with logs
    as well.
    """
    request_id = getattr(request.state, "request_id", None)
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Internal server error occurred",
                "request_id": request_id,
            }
        },
        headers=build_trace_headers(request),
    )
