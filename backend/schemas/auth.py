"""账号认证请求和响应。"""
from pydantic import BaseModel, Field, field_validator


class CaptchaData(BaseModel):
    captcha_id: str
    image_svg: str
    expires_in: int


class CaptchaRequest(BaseModel):
    captcha_id: str = Field(min_length=1, max_length=64)
    captcha_code: str = Field(min_length=4, max_length=8)


class RegisterRequest(CaptchaRequest):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_\-\u4e00-\u9fff]+$")
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip()


class LoginRequest(CaptchaRequest):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class UserData(BaseModel):
    id: int
    username: str
    is_active: bool


class TokenData(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserData
