# TaxMind 税智通

TaxMind 是面向代理记账机构、财税服务人员和小微企业服务场景的企业级 RAG 智能财税
知识问答系统。系统围绕政策知识库运营、时效性检索、可追溯问答、风险门禁和人工复核构建，
回答仅使用当前用户有权访问且在查询日期有效的政策依据。

## 核心能力

- LLM + 中文 Prompt 完成意图识别、信息完整性判断和风险分级，不训练 BERT 分类模型。
- BGE-M3 Dense/Sparse 混合召回、RRF 多 Query 融合和 BGE Reranker 重排序。
- Parent-Child Chunk、政策地区/时效过滤、来源文号与原文引用。
- FAQ 优先路由、Query Rewrite、SSE 流式回答和无依据拒答。
- 多租户知识库、私有 MinIO 文档、JWT 鉴权、认证限流和上传内容安全校验。
- 用户反馈、人工工单、官方政策导入和端到端专项评测。

## 系统架构

前端采用 Vue 3、TypeScript、Vite 和 Element Plus；后端采用 FastAPI、SQLAlchemy 与
Alembic。MySQL 保存业务数据，Redis 提供缓存、验证码和限流，MinIO 保存私有原文，
Milvus 保存可重建的检索向量，通义千问负责结构化理解、Query 改写和答案生成。

详细组件边界和数据流见 [系统架构文档](docs/architecture.md)。

## 文档导航

| 文档 | 位置 | 用途 |
| --- | --- | --- |
| 项目说明 | [`README.md`](README.md) | 项目定位、快速开始、研发和文档入口 |
| 系统架构 | [`docs/architecture.md`](docs/architecture.md) | 组件职责、RAG 链路和数据边界 |
| API 接口 | [`docs/api.md`](docs/api.md) | 鉴权、接口清单、请求响应、SSE 与错误处理 |
| 部署运维 | [`docs/deployment.md`](docs/deployment.md) | 环境初始化、生产安全、备份、监控和验收 |
| 项目任务 | [`TaxMind_项目任务描述.md`](TaxMind_项目任务描述.md) | 项目需求、功能范围和交付目标 |
| 开发规范 | [`Codex.md`](Codex.md) | 开发流程、测试、日志和验收规范 |
| 在线 OpenAPI | `http://127.0.0.1:8000/docs` | 启动后查看实时 Swagger 文档 |

## 目录结构

```text
TaxMind/
├── backend/        FastAPI 接口、业务服务、模型、仓储和数据库迁移
├── frontend/       Vue 3 管理端与智能问答界面
├── rag/            意图理解、改写、Embedding、检索、重排和评测
├── scripts/        初始化、启动、模型/数据下载、导入、评测和就绪检查
├── data/           可版本化清单与评测数据；原始数据和模型不提交
├── docs/           架构、API 和部署运维文档
├── tests/          pytest 单元测试与业务集成测试
└── docker-compose.yml
```

## 环境要求

- Windows 10/11 或兼容的 Linux 开发环境
- Python 3.12 或 3.13
- [uv](https://docs.astral.sh/uv/)
- Node.js 22+
- Docker Desktop / Docker Engine + Compose
- 可用的 DashScope API Key

## 快速开始

1. 创建配置文件：

   ```powershell
   Copy-Item .env.example .env
   ```

2. 修改 `.env`，至少配置 MySQL、Redis、MinIO、JWT 强随机密钥和
   `DASHSCOPE_API_KEY`。不要提交 `.env`。

3. 执行一键初始化与启动：

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
   powershell -ExecutionPolicy Bypass -File scripts/start.ps1
   ```

首次初始化会安装依赖、启动基础服务、执行数据库迁移、下载模型和官方公开数据，并运行
就绪检查。更细的手动部署步骤和生产要求见 [部署运维文档](docs/deployment.md)。

## 本地开发

单独启动后端：

```powershell
uv sync
uv run alembic upgrade head
uv run uvicorn backend.main:app --reload --port 8000
```

单独启动前端：

```powershell
Set-Location frontend
npm install
npm run dev
```

默认访问地址：

- 前端：`http://127.0.0.1:5173`
- 后端：`http://127.0.0.1:8000`
- Swagger：`http://127.0.0.1:8000/docs`
- MinIO 控制台：`http://127.0.0.1:9001`

所有业务接口使用 `/api/v1` 前缀。完整接口说明已从 README 分离至
[API 接口文档](docs/api.md)。

## 数据、模型与评测

```powershell
uv run python scripts/download_models.py
uv run python scripts/download_official_data.py
uv run python scripts/import_official_data.py
uv run python scripts/evaluate_rag.py
```

导入和评测前需要设置 `TAXMIND_ACCESS_TOKEN` 与 `TAXMIND_KNOWLEDGE_BASE_ID`。
专项评测集位于 [`data/evaluation/taxmind_mvp_50.jsonl`](data/evaluation/taxmind_mvp_50.jsonl)，
包含25个独立场景的50种问题表达；报告默认写入 `data/evaluation/latest_report.json`。

## 测试与代码质量

```powershell
uv run python -m pytest tests/ -v
uv run ruff check backend rag scripts tests
Set-Location frontend
npm run build
```

新功能必须同步增加 pytest 测试；日志同时写入控制台与 `LOG_FILE` 指定文件。详细研发约束见
[`Codex.md`](Codex.md)。

## 安全与运维

- Docker Compose 不提供可直接运行的数据库、Redis 和 MinIO 弱口令兜底。
- 基础服务默认仅绑定宿主机回环地址；生产环境仅通过 TLS 反向代理开放前端和 API。
- 知识库、文档、向量过滤、FAQ、会话和工单均执行用户级数据隔离。
- 上传文件执行扩展名、真实格式和 Office 容器安全校验；MinIO 桶保持私有。
- 生产环境需要建立 MySQL、MinIO、etcd/Milvus 备份、日志采集和健康检查告警。

完整上线、备份恢复和验收步骤见 [部署运维文档](docs/deployment.md)。

## 项目状态与边界

当前仓库完成 TaxMind MVP 的前后端、RAG 主链路、知识运营、风险控制、人工复核、部署脚本
和离线评测能力。财税回答用于信息辅助，不替代税务机关口径或持证专业人员的个案意见；
高风险、依据不足或政策冲突场景应进入人工复核。

## License

本项目使用 [MIT License](LICENSE)。
