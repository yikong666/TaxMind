# 所有接口统一使用 success、code、message、data 四段响应。
from pydantic import BaseModel


class ApiResponse[T](BaseModel):
    success: bool = True
    code: str = "OK"
    message: str = "操作成功"
    data: T | None = None
