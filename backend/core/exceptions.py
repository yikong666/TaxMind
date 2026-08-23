"""统一异常类型与中文错误响应。"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.core.logging import get_logger

logger = get_logger(__name__)


class BusinessError(Exception):
    def __init__(self, message: str, code: str = "BUSINESS_ERROR", status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BusinessError)
    async def handle_business_error(_: Request, exc: BusinessError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "code": exc.code, "message": exc.message, "data": None},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("未处理异常：%s %s", request.method, request.url.path, exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "code": "INTERNAL_SERVER_ERROR",
                "message": "系统繁忙，请稍后重试",
                "data": None,
            },
        )
