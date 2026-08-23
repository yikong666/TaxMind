"""用户数据模型。"""

# 密码字段只保存不可逆哈希，不保存或记录明文密码。
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
