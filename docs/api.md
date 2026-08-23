# TaxMind API 接口文档

本文档描述 TaxMind V1 HTTP API。FastAPI OpenAPI Schema 是字段定义的最终依据；开发环境
启动后可访问 `http://127.0.0.1:8000/docs` 进行交互式调试。

## 基本约定

| 项目 | 值 |
| --- | --- |
| 默认服务地址 | `http://127.0.0.1:8000` |
| API 前缀 | `/api/v1` |
| 普通请求 | `application/json; charset=utf-8` |
| 文件上传 | `multipart/form-data` |
| 流式回答 | `text/event-stream` |
| 鉴权 | `Authorization: Bearer <access_token>` |

除健康检查、验证码、注册和登录外，其他业务接口均要求 JWT。Token 不得写入 URL、日志或仓库。

## 统一响应与错误

```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "操作成功",
  "data": {}
}
```

失败时 `success=false`，`code` 为稳定业务错误码，`message` 为中文提示，`data=null`。

| HTTP 状态码 | 含义 |
| --- | --- |
| `200/201` | 成功或资源创建成功 |
| `400` | 参数或业务规则不满足 |
| `401/403` | 未认证、凭据错误、账号停用或无权限 |
| `404` | 资源不存在；跨租户访问同样返回不存在 |
| `409` | 名称、FAQ、反馈或工单等资源冲突 |
| `422` | 请求字段未通过校验 |
| `429` | 认证请求超过限流阈值 |
| `500` | 未预期服务端异常 |
| `502/503` | LLM、模型或外部依赖暂不可用 |

## 认证与健康检查

| 方法 | 路径 | 鉴权 | 说明 |
| --- | --- | --- | --- |
| GET | `/health` | 否 | 应用探活 |
| GET | `/auth/captcha` | 否 | 获取一次性验证码 ID、SVG 和有效期 |
| POST | `/auth/register` | 否 | 注册账号 |
| POST | `/auth/login` | 否 | 登录并获取 JWT |

注册请求：

```json
{
  "username": "tax_user",
  "password": "SecurePass123!",
  "confirm_password": "SecurePass123!",
  "captcha_id": "验证码ID",
  "captcha_code": "A7K9M2"
}
```

后续请求通过请求头携带登录响应中的 `data.access_token`：

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

验证码一次性消费；登录和注册同时按客户端与账号维度限流。

## 知识库

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/knowledge-bases` | 创建知识库 |
| GET | `/knowledge-bases` | 查询当前用户知识库和统计信息 |
| GET | `/knowledge-bases/{knowledge_base_id}` | 查询知识库、文档和处理状态 |
| PATCH | `/knowledge-bases/{knowledge_base_id}` | 修改名称或描述 |
| DELETE | `/knowledge-bases/{knowledge_base_id}` | 删除知识库及其私有原文 |
| POST | `/knowledge-bases/{knowledge_base_id}/documents` | 批量上传文档 |

创建请求示例：

```json
{
  "name": "全国税收政策库",
  "description": "国家级现行税收政策",
  "kb_type": "public_policy"
}
```

上传字段名为 `files`，支持 PDF、DOC/DOCX、PPT/PPTX、Markdown、TXT、HTML、JPG、PNG
和 WebP，默认单文件不超过50MB。服务端校验扩展名与真实格式，文件保存到私有 MinIO 桶。

## 文档处理与 Chunk

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/documents/{document_id}/parse` | 解析文档并生成 Parent/Child Chunk |
| GET | `/documents/{document_id}/chunks` | 查看标题层级、父块和子块 |
| GET | `/documents/{document_id}/download` | 下载有权访问的原文件 |
| PUT | `/documents/{document_id}/policy-metadata` | 更新政策元数据 |
| POST | `/documents/{document_id}/index` | 生成 Dense/Sparse 向量并写入 Milvus |
| GET | `/documents/{document_id}/vector-status` | 查询向量状态统计 |
| PATCH | `/chunks/parents/{chunk_id}` | 修改父块标题或内容 |
| DELETE | `/chunks/parents/{chunk_id}` | 删除父块及子块 |
| PATCH | `/chunks/children/{chunk_id}` | 修改子块内容 |
| DELETE | `/chunks/children/{chunk_id}` | 删除子块 |

解析参数可省略以使用服务端配置：

```json
{
  "parent_chunk_size": 1200,
  "child_chunk_size": 300,
  "chunk_overlap": 50
}
```

政策元数据示例：

```json
{
  "policy_title": "增值税小规模纳税人减免增值税政策",
  "doc_no": "财政部 税务总局公告2023年第19号",
  "region": "全国",
  "tax_type": "增值税",
  "taxpayer_type": "小规模纳税人",
  "publish_date": "2023-08-01",
  "effective_start": "2023-08-01",
  "effective_end": "2027-12-31",
  "policy_status": "active",
  "source_url": "https://example.gov.cn/policy"
}
```

政策库必须补齐必填元数据后才能索引。编辑或删除 Chunk 会清理该文档旧向量，并将剩余子块
标记为待索引。

## 意图理解与检索

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/query/understand` | 抽取意图、地区、税种、期间、金额、风险和缺失字段 |
| POST | `/retrieval/search` | 执行多租户、地区及时效约束下的混合检索 |

检索请求：

```json
{
  "query": "重庆小规模纳税人有什么增值税优惠？",
  "knowledge_base_ids": [1],
  "region": "重庆",
  "query_date": "2026-08-23",
  "tax_type": "增值税",
  "taxpayer_type": "小规模纳税人",
  "top_k": 5
}
```

响应包含 Child Chunk、Parent Context、混合/重排分数、文号、地区、有效期和来源 URL。
政策检索只返回查询日期有效的 `active` 政策；地方查询可使用全国与本地政策，全国查询不会
混入地方政策。

## FAQ

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/faqs` | 创建 FAQ |
| GET | `/faqs` | 按关键词、分类、地区和状态筛选 |
| GET | `/faqs/{faq_id}` | 查询详情 |
| PATCH | `/faqs/{faq_id}` | 修改 FAQ 并清理缓存 |
| DELETE | `/faqs/{faq_id}` | 删除 FAQ |
| POST | `/faqs/route/match` | 执行精确缓存和 BM25 优先路由 |

FAQ 只在启用、地区匹配且处于有效期时参与路由；低于阈值时返回
`continue_to_rag=true`。

## 会话与 SSE 流式回答

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/conversations` | 创建会话 |
| GET | `/conversations` | 查询会话列表 |
| GET | `/conversations/{conversation_id}` | 查询会话和历史消息 |
| PATCH | `/conversations/{conversation_id}` | 重命名会话 |
| DELETE | `/conversations/{conversation_id}` | 删除会话 |
| POST | `/conversations/{conversation_id}/messages/stream` | 获取 SSE 流式回答 |

流式请求：

```json
{
  "query": "小规模纳税人月销售额10万元以下是否免征增值税？",
  "knowledge_base_ids": [1],
  "region": "全国",
  "query_date": "2026-08-23",
  "model": "qwen3-max",
  "temperature": 0.2,
  "top_p": 0.8,
  "max_tokens": 2000,
  "history_rounds": 5
}
```

| SSE 事件 | 说明 |
| --- | --- |
| `session` | 会话和 AI 消息 ID |
| `status` | Query Rewrite、检索或生成阶段 |
| `token` | 增量答案文本 |
| `citation` | 文号、地区、时效、来源和上下文 |
| `done` | 消息持久化完成及实际路由来源 |
| `error` | 本轮失败，客户端应停止读取并提示重试 |

浏览器应使用 `fetch` 读取响应流并携带 JWT；不建议使用无法自定义 Authorization 请求头的
原生 `EventSource`。

## 反馈与人工工单

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/messages/{message_id}/feedback` | 对 AI 回答点赞或点踩；点踩需要原因 |
| POST | `/messages/{message_id}/handoff` | 主动创建人工复核工单 |
| GET | `/tickets` | 按状态筛选工单 |
| GET | `/tickets/{ticket_id}` | 查询工单详情 |
| PATCH | `/tickets/{ticket_id}` | 流转工单并填写处理结果 |

工单按照 `pending → processing → resolved` 流转，解决时必须填写 `resolution`。无可靠上下文
和高风险回答也会自动创建复核任务。

## 调用安全建议

- 服务端对知识库、文档、FAQ、会话和工单执行用户所有权校验。
- 不要把 Token、密码、验证码或内部资料写入前端日志和监控标签。
- 收到 `429` 时使用指数退避，不要自动轮换验证码持续重试。
- 财税答案必须展示引用和适用期间；`no_context`、`HIGH` 场景应进入人工复核。
- 生产环境应关闭或限制 Swagger，并通过 TLS 反向代理访问 API。

系统部署、安全配置和上线验收见 [部署运维文档](deployment.md)。
