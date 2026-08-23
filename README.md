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
uv run python scripts/download_models.py
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
- `POST /api/v1/retrieval/search`：按知识库、地区、有效期和纳税人条件执行混合检索
- `POST /api/v1/query/understand`：使用 LLM Structured Output 提取意图并判断信息完整性与风险

文档上传支持 PDF、DOC/DOCX、PPT/PPTX、Markdown、TXT、HTML 和常见图片格式，
默认单文件上限为 50MB。PDF、DOCX、PPTX、Markdown、TXT、HTML 和图片可直接解析，
图片使用 OCR 提取文字；旧版 DOC/PPT 文件需先转换为 DOCX/PPTX。政策类文档只有在
解析完成且必填政策元数据完整后才进入可检索状态，内部资料解析完成后即可检索。

混合检索使用 BGE-M3 Dense/Sparse 两路召回和 Milvus WeightedRanker，再由
`bge-reranker-v2-m3` 对 Top-N 候选重排序并按 Parent Chunk 去重。当前政策检索仅
允许 `active` 状态且在查询日期有效的政策；地方查询可同时使用全国政策和本地区政策，
全国查询不会混入地方政策。Child Chunk 参与召回，接口返回对应 Parent Chunk 和引用元数据。

问题理解使用 `qwen3-max + 中文 Prompt`，不训练 BERT。系统会提取地区、纳税人类型、
税种、所属期、金额和业务类型；信息不足时先追问，违法违规操作请求会被保守风险规则拦截。

## 测试

```powershell
uv run python -m pytest tests/ -v
uv run ruff check backend rag tests config.py
```

完整架构、数据导入和 API 文档会随后续里程碑持续补充。
