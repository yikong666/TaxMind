"""FastAPI 应用入口。"""

# Uvicorn 通过此模块发现应用实例。
from backend.app import create_app

app = create_app()
