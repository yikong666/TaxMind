from pydantic import BaseModel


class ApiResponse[T](BaseModel):
    success: bool = True
    code: str = "OK"
    message: str = "操作成功"
    data: T | None = None
