# 健康状态使用字面量，避免接口返回无法识别的状态值。
from typing import Literal

from pydantic import BaseModel


class HealthData(BaseModel):
    status: Literal["healthy"]
    version: str
