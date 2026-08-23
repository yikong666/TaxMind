# TaxMind
这是一个面向代理记账机构、财税服务人员和小微企业服务场景的企业级 RAG 智能财税知识问答系统。

## 当前进度

项目正在按里程碑迭代。当前已建立 FastAPI 后端基线、Vue 3 前端基线，以及
MySQL、Redis、Milvus、etcd、MinIO 的本地 Docker 编排。

## 环境要求

- Python 3.12 或 3.13
- uv
- Node.js 22+
- Docker Desktop

## 本地启动

复制配置模板并设置密码和 API Key：

```powershell
Copy-Item .env.example .env
uv sync
docker compose up -d
uv run alembic upgrade head
```

启动后端：

```powershell
uv run uvicorn backend.main:app --reload --port 8000
```

启动前端：

```powershell
Set-Location frontend
npm install
npm run dev
```

后端接口文档位于 `http://127.0.0.1:8000/docs`，前端位于
`http://127.0.0.1:5173`，MinIO 管理控制台位于 `http://127.0.0.1:9001`。

当前账号模块提供以下接口：

- `GET /api/v1/auth/captcha`：获取一次性图形验证码
- `POST /api/v1/auth/register`：注册账号
- `POST /api/v1/auth/login`：登录并获取 JWT

## 测试

```powershell
uv run python -m pytest tests/ -v
uv run ruff check backend rag tests config.py
```

完整架构、数据导入和 API 文档会随后续里程碑持续补充。
