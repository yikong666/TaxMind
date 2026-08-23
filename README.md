# TaxMind
这是一个面向代理记账机构、财税服务人员和小微企业服务场景的企业级 RAG 智能财税知识问答系统。

## 技术架构

Vue 3 + Element Plus 提供智能问答和知识运营页面；FastAPI 提供 JWT 多租户业务接口；
MySQL 保存业务数据，Redis 缓存 FAQ，MinIO 保存私有原文，Milvus 执行 BGE-M3
Dense/Sparse Hybrid Search，候选结果经 bge-reranker-v2-m3 重排后交给 qwen3-max。
完整链路见 `docs/architecture.md`。

## 环境要求

- Python 3.12 或 3.13
- uv
- Node.js 22+
- Docker Desktop

## 本地启动

推荐执行一键初始化。首次运行会创建 `.env` 并要求先替换安全配置：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
powershell -ExecutionPolicy Bypass -File scripts/start.ps1
```

也可手动执行：

```powershell
Copy-Item .env.example .env
uv sync
docker compose up -d
uv run alembic upgrade head
uv run python scripts/download_models.py
uv run python scripts/download_official_data.py
uv run python scripts/check_readiness.py
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
- `POST /api/v1/knowledge-bases`：创建知识库
- `GET /api/v1/knowledge-bases`：查看当前用户的知识库
- `GET/PATCH/DELETE /api/v1/knowledge-bases/{id}`：查看、修改或删除知识库
- `POST /api/v1/knowledge-bases/{id}/documents`：向私有 MinIO 桶批量上传文档
- `POST /api/v1/documents/{id}/parse`：解析文档并生成 Parent-Child Chunk
- `GET /api/v1/documents/{id}/chunks`：预览标题层级、父块和子块
- `PUT /api/v1/documents/{id}/policy-metadata`：维护政策文号、地区和有效期等元数据
- `POST /api/v1/documents/{id}/index`：使用 BGE-M3 生成 Dense/Sparse 向量并写入 Milvus
- `GET /api/v1/documents/{id}/vector-status`：汇总待索引、已索引和失败 Chunk 数量
- `PATCH/DELETE /api/v1/chunks/parents/{id}`：编辑或删除 Parent Chunk
- `PATCH/DELETE /api/v1/chunks/children/{id}`：编辑或删除 Child Chunk
- `POST /api/v1/retrieval/search`：按知识库、地区、有效期和纳税人条件执行混合检索
- `POST /api/v1/query/understand`：使用 LLM Structured Output 提取意图并判断信息完整性与风险
- `POST/GET/PATCH/DELETE /api/v1/faqs`：管理高频税务 FAQ
- `POST /api/v1/faqs/route/match`：执行 Redis 精确缓存与 MySQL BM25 优先路由
- `POST/GET /api/v1/conversations`：创建或查看当前用户的问答会话
- `GET/PATCH/DELETE /api/v1/conversations/{id}`：查看聊天记录、重命名或删除会话
- `POST /api/v1/conversations/{id}/messages/stream`：通过 SSE 获取 RAG 流式回答
- `POST /api/v1/messages/{id}/feedback`：对 AI 回答点赞或点踩并填写原因
- `POST /api/v1/messages/{id}/handoff`：将指定回答主动转交人工审核
- `GET /api/v1/tickets`、`GET/PATCH /api/v1/tickets/{id}`：查看工单并执行状态流转

文档上传支持 PDF、DOC/DOCX、PPT/PPTX、Markdown、TXT、HTML 和常见图片格式，
默认单文件上限为 50MB。PDF、DOCX、PPTX、Markdown、TXT、HTML 和图片可直接解析，
图片使用 OCR 提取文字；旧版 DOC/PPT 文件需先转换为 DOCX/PPTX。政策类文档只有在
解析完成且必填政策元数据完整后才进入可检索状态，内部资料解析完成后即可检索。
编辑或删除任意 Chunk 会先清理该文档的旧 Milvus 向量，并将剩余 Child Chunk 标记为
`pending`；再次调用文档索引接口即可整篇重新索引，避免旧内容继续进入问答上下文。

混合检索使用 BGE-M3 Dense/Sparse 两路召回和 Milvus WeightedRanker，再由
`bge-reranker-v2-m3` 对 Top-N 候选重排序并按 Parent Chunk 去重。当前政策检索仅
允许 `active` 状态且在查询日期有效的政策；地方查询可同时使用全国政策和本地区政策，
全国查询不会混入地方政策。Child Chunk 参与召回，接口返回对应 Parent Chunk 和引用元数据。

问题理解使用 `qwen3-max + 中文 Prompt`，不训练 BERT。系统会提取地区、纳税人类型、
税种、所属期、金额和业务类型；信息不足时先追问，违法违规操作请求会被保守风险规则拦截。

FAQ 路由只使用当前启用、地区匹配且处于有效期内的数据。达到 BM25 阈值时直接返回
标准答案和文号来源，低于阈值时通过 `continue_to_rag=true` 进入后续 RAG 链路。

流式问答依次执行问题理解、风险门禁、FAQ、混合检索、重排序和 Parent Context 构建，
最终由通义千问生成仅基于检索依据的结构化答复。SSE 事件包括 `session`、`status`、
`token`、`citation`、`done` 和 `error`；用户问题、回答状态、路由来源、模型参数及引用
会写入 MySQL。没有可靠上下文时系统明确提示补充信息，不允许模型凭空生成政策文号。
无可靠上下文以及 HIGH/PROHIBITED 风险回答会自动进入人工审核队列；用户也可以主动
转人工。工单严格按照 `pending → processing → resolved` 流转，解决时必须填写处理结果。

FAQ 未命中且需要知识库检索时，系统使用 LLM 在 Direct、历史会话改写、关键词扩写、
Query Simplification、MultiQuery 和 HyDE 中选择策略。原始问题始终保留，多路 Query
使用 RRF 融合后再交给 Reranker；改写不得新增金额、期间等数字事实，结构异常或模型
不可用时自动降级到 Direct Retrieval。实际策略和检索 Query 会随 AI 消息保存供评估。

## 测试

```powershell
uv run python -m pytest tests/ -v
uv run ruff check backend rag tests config.py
```

## 官方数据与评测

首批 5 份官方资料、来源 URL、SHA-256 和抓取时间位于 `data/`。设置
`TAXMIND_ACCESS_TOKEN` 与 `TAXMIND_KNOWLEDGE_BASE_ID` 后运行
`uv run python scripts/import_official_data.py` 可通过正式 API 入库。首版评测集包含 50 条问题，
覆盖检索排名、文号、地区、时效和风险等级指标。

生产部署、备份与验收说明见 `docs/deployment.md`。
