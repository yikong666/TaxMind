# TaxMind 税智通 · 项目任务描述

这是一个面向代理记账机构、财税服务人员和小微企业服务场景的企业级 RAG 智能财税知识问答系统。

系统需要根据用户输入的问题，结合用户选择的知识库、地区、政策有效期、纳税人类型等条件，检索相关税务政策、办税指南、FAQ 等内容，再由大模型生成带有政策依据、文号、适用期间和来源引用的回答。

系统中页面文字、提示词、错误提示、日志说明等内容统一使用中文。

本项目按照全栈 AI 应用项目进行开发，需要包括以下部分：

- 前端页面
- 后端管理系统
- RAG 问答系统
- 离线知识库
- 风险控制与人工兜底
- 测试与评估

---

## 一、前端页面

前端使用 Vue 开发框架，代码要求结构清晰、组件划分合理、命名规范。

整体 UI 风格要求简约、专业、年轻化，适合财税 SaaS / 企业知识助手类产品，避免过度花哨。页面需要兼顾桌面端使用体验。

### 1. 登录页

支持用户通过账号名称和密码完成登录。

字段包括：

- 用户名
- 密码
- 图形验证码

需要具备基本的登录状态管理和异常提示。

---

### 2. 注册页

支持用户注册账号。

字段包括：

- 用户名
- 密码
- 确认密码
- 图形验证码

要求：

- 两次密码必须一致；
- 用户名不能重复；
- 注册成功后可跳转登录页面；
- MVP 阶段暂不支持用户自行修改密码。

---

### 3. 智能问答页面

这是系统核心页面。

#### 3.1 知识库选择

用户发起问题前，可以选择一个或多个知识库，例如：

- 全国通用税收政策库
- 重庆地方税务政策库
- 小微企业优惠政策库
- 发票与申报操作指南库
- 企业内部财税知识库

系统需要根据用户选择的知识库限定检索范围。

#### 3.2 地区选择

支持用户选择地区，例如：

- 全国
- 重庆
- 其他后续扩展地区

地区信息需要参与检索过滤，避免地方政策口径混用。

#### 3.3 对话 Session

支持：

- 新建会话
- 自定义会话名称
- 删除会话
- 查看历史会话
- 保存历史聊天记录

#### 3.4 模型参数

支持用户选择大模型和部分推理参数，包括：

- 模型名称
- temperature
- top_p
- max_tokens
- 历史对话轮数

默认历史对话轮数为 5。

#### 3.5 流式回答

大模型回答必须支持流式输出。

推荐使用：

- SSE

也可根据项目现有结构使用 WebSocket。

#### 3.6 回答结构

政策类问题的回答应尽量按照以下结构展示：

1. 结论
2. 适用条件
3. 政策依据
4. 政策文号
5. 适用地区
6. 适用期间
7. 操作步骤
8. 注意事项

回答中必须展示知识来源。

#### 3.7 政策引用卡片

每个答案需要支持展示引用来源，包括：

- 政策标题
- 文号
- 地区
- 生效日期
- 失效日期
- 原始文档
- 原始文档块内容

用户可以点击查看详细政策来源。

#### 3.8 用户反馈

每条回答支持：

- 点赞
- 点踩
- 转人工

点踩时支持填写简单反馈原因。

---

### 4. 知识库管理页面

通过“知识库”导航进入知识库管理。

支持：

- 创建知识库
- 删除知识库
- 修改知识库名称和描述
- 查看知识库详情
- 一个知识库上传多个文档
- 查看文档解析状态
- 查看文档数量和 Chunk 数量

知识库需要支持以下类型：

- 公共政策知识库
- 地方政策知识库
- 企业内部知识库

---

### 5. 知识库解析页面

支持上传离线文档。

支持格式至少包括：

- PDF
- DOC
- DOCX
- PPT
- PPTX
- Markdown
- TXT
- HTML
- 图片

文档上传后支持配置：

- Chunk 大小
- Chunk overlap
- Parent Chunk 大小
- Child Chunk 大小
- Dense Retrieval
- Hybrid Retrieval

税务政策文档优先使用“标题层级 + Parent-Child Chunk”方式切分。

---

### 6. 政策元数据编辑

文档解析后需要支持编辑和确认政策元数据。

至少包括：

- 政策标题
- 文号 doc_no
- 地区 region
- 税种 tax_type
- 纳税人类型 taxpayer_type
- 发布时间 publish_date
- 生效时间 effective_start
- 失效时间 effective_end
- 政策状态 policy_status
- 官方来源 source_url

policy_status 至少支持：

- active
- expired
- replaced

税务政策必须完成必要元数据后才能正式进入可检索状态。

---

### 7. 知识库预览页面

支持查看已经解析完成的知识库内容。

需要支持：

- 文档列表
- Parent Chunk 查看
- Child Chunk 查看
- Chunk 元数据
- Chunk 编辑
- Chunk 删除
- 查看向量化状态

对于政策文档，需要明确展示文号、地区、有效期等信息。

---

### 8. FAQ 管理页面

系统需要维护一套高频税务 FAQ。

FAQ 支持：

- 新增
- 编辑
- 删除
- 分类
- 设置地区
- 设置文号
- 设置适用期间
- 启用 / 停用

高频问题优先通过 FAQ 检索直接返回，未命中时再进入 RAG 链路。

---

### 9. 人工工单页面

低置信度、高风险问题以及用户主动转人工的问题，需要生成工单。

工单至少展示：

- 用户问题
- AI 回答
- 检索到的文档
- 风险等级
- 用户反馈
- 创建时间
- 当前状态
- 人工处理结果

工单状态至少包括：

- pending
- processing
- resolved

---

## 二、后端管理系统

后端使用 FastAPI 开发。

代码要求：

- 模块清晰
- 配置统一管理
- 业务逻辑和接口层分离
- 关键模块具备单元测试
- 保留必要日志

---

### 1. MySQL

MySQL 用于保存：

- 用户
- 会话
- 消息
- FAQ
- 文档信息
- 政策元数据
- 用户反馈
- 人工工单
- 系统配置

需要检查当前 Docker 环境中是否已经存在 MySQL。

如果已经存在，则直接复用。

如果不存在，则创建 docker-compose 配置安装 MySQL。

---

### 2. Redis

Redis 用于：

- Session 缓存
- 高频 FAQ 缓存
- 热点问题缓存
- 临时会话状态

如果当前环境已经存在 Redis，则直接复用。

---

### 3. Milvus

离线文档经过：

```text
解析
→ 分块
→ 元数据处理
→ 向量化
→ Milvus
```

后保存到 Milvus。

向量化模型使用：

- BGE-M3

需要同时支持：

- Dense Vector
- Sparse Vector
- Hybrid Search

---

### 4. Reranker

召回的候选文档需要使用：

- bge-reranker-v2-m3

进行重排序。

流程：

```text
Top-N Recall
→ Reranker
→ Top-K Context
```

最终将 Top-K 文档提供给 LLM。

---

## 三、RAG 在线问答系统

推荐主链路：

```text
用户 Query
    ↓
Query Understanding
    ↓
Risk Guardrail
    ↓
Redis Cache
    ↓
MySQL FAQ + BM25
    ↓
命中 → FAQ 返回
    ↓ 未命中
Strategy Selector
    ↓
Metadata Filtering
    ↓
BGE-M3 Hybrid Search
    ↓
Milvus
    ↓
Reranker
    ↓
Parent Context
    ↓
LLM
    ↓
结构化答案 + Citation
```

---

### 1. Query Understanding

不能只进行简单意图分类。

需要尽可能解析：

- intent
- region
- taxpayer_type
- tax_type
- period
- amount
- risk_level

例如：

```json
{
  "intent": "tax_policy",
  "region": "重庆",
  "taxpayer_type": "small_scale",
  "tax_type": "VAT",
  "period": "current_quarter",
  "amount": 200000,
  "risk_level": "LOW"
}
```

可采用：

- BERT 分类器
- LLM Structured Output
- 规则

组合实现。

---

### 2. 信息完整性判断

税务问题在信息不足时不能直接生成确定性结论。

例如用户问：

> 我这个季度开了 20 万发票，要不要交税？

系统需要判断是否缺少：

- 地区
- 纳税人类型
- 税种
- 所属期
- 业务类型

必要时进行追问。

---

### 3. FAQ 路由

高频标准问题先走：

```text
Redis
→ MySQL
→ BM25
```

如果 BM25 分数达到阈值，则直接返回标准答案。

未达到阈值，进入 RAG。

---

### 4. 检索策略

支持以下检索策略：

#### Direct Retrieval

普通明确问题直接检索。

#### MultiQuery

适合：

- 政策对比
- 复合问题
- 多条件问题

#### HyDE

用于口语表达和政策术语差异较大的问题。

#### Query Simplification

对冗长问题提取核心检索表达。

---

### 5. Metadata Filtering

这是 TaxMind 必须实现的核心能力。

向量召回时至少考虑：

```text
region
effective_start
effective_end
policy_status
```

例如：

```text
region in ["全国", "重庆"]
AND effective_start <= query_date
AND effective_end >= query_date
AND policy_status == "active"
```

必要时增加：

```text
tax_type
taxpayer_type
```

要求：

> 已失效政策不能进入当前有效政策回答的上下文。

---

### 6. 风险分级

问题风险等级分为：

- LOW
- MEDIUM
- HIGH
- PROHIBITED

处理策略：

| 风险等级 | 处理方式 |
|---|---|
| LOW | 正常回答 |
| MEDIUM | 回答 + 风险提示 / 补充信息 |
| HIGH | 提供政策依据并建议人工确认 |
| PROHIBITED | 不提供规避监管、违法操作等指导 |

---

### 7. 大模型

默认使用：

- qwen3-max

通过配置文件填写 API Key。

需要支持后续扩展其他模型。

大模型回答必须：

- 流式输出
- 支持历史对话
- 默认读取最近 5 轮历史
- 支持从前端配置历史轮数
- 尽量只根据检索上下文回答政策问题
- 不确定时明确说明
- 不允许伪造政策文号
- 必须输出引用来源

---

## 四、离线知识库

### 1. 数据来源

MVP 只使用：

- 国家税务总局公开政策
- 试点省市税务局公开政策
- 官方办税指南
- 官方 FAQ
- 官方操作手册
- 企业自行提供且有权使用的内部资料

---

### 2. 文档处理流程

```text
PDF / HTML / DOCX / PPT / Markdown / Image
        ↓
Document Loader
        ↓
文本清洗
        ↓
结构识别
        ↓
Parent Chunk
        ↓
Child Chunk
        ↓
Metadata
        ↓
BGE-M3
        ↓
Milvus
```

---

### 3. Parent-Child Chunk

Child Chunk：

- 用于向量检索
- 提高检索精准度

Parent Chunk：

- 用于生成阶段
- 保留完整政策语义

需要建立 Child → Parent 映射。

---

## 五、人工反馈闭环

用户的：

- 点踩
- 低置信度问题
- 高风险问题
- 转人工问题

需要进入人工审核队列。

人工审核后支持：

```text
审核答案
→ 更新 FAQ
→ 更新知识库
→ 加入评测集
```

形成知识持续迭代闭环。

---

## 六、测试用例

必须遵守基本开发规范。

重要功能必须有测试。

每次修改关键业务逻辑后，都需要执行相关测试。

---

### 1. 用户模块

测试：

- 注册
- 重复用户名
- 密码不一致
- 验证码
- 登录
- 错误密码
- Session

---

### 2. 文档上传

测试：

- PDF
- Markdown
- DOCX
- 图片

检查：

- 上传成功
- 文档解析成功
- Chunk 创建成功
- 元数据保存成功
- Milvus 插入成功

---

### 3. FAQ

测试：

- FAQ 添加
- FAQ 修改
- FAQ 删除
- BM25 命中
- 低于阈值后进入 RAG

---

### 4. Hybrid Retrieval

测试：

- Dense Recall
- Sparse Recall
- Hybrid Recall
- Top-K
- Reranker

---

### 5. 时效过滤

必须单独构建测试。

要求：

> 已过期政策不能被当前日期检索进入 Context。

至少包括：

- active 政策
- expired 政策
- replaced 政策
- 新旧政策同时存在

此功能属于 TaxMind 的 P0 测试。

---

### 6. 地区过滤

测试：

- 全国政策
- 地方政策
- 全国 + 地方
- 不同地区之间不能错误混用

---

### 7. RAG 问答

测试：

- 普通政策问题
- 开票操作
- 申报问题
- 优惠政策
- 个税
- 多轮对话
- 信息不足追问
- 流式输出

---

### 8. Risk Guardrail

分别测试：

- LOW
- MEDIUM
- HIGH
- PROHIBITED

高风险问题不得直接输出未经确认的确定性个案结论。

---

### 9. Citation

检查：

- 是否返回来源
- 文号是否存在
- 文号是否对应当前文档
- 地区是否正确
- 有效期是否正确
- Source URL 是否正确

---

## 七、效果评估

除了单元测试，需要构建 TaxMind 专项评测集。

建议 MVP 构建：

- 50–100 条真实涉税高频问题

每条测试数据包含：

```text
question
expected_answer
expected_doc_no
expected_region
expected_policy_period
risk_level
```

---

### 评估指标

#### Retrieval

- Recall@K
- Precision@K
- MRR
- Hit Rate

#### RAGAS

- Faithfulness
- Answer Relevancy
- Context Precision
- Context Recall

#### 财税专项

- 文号准确率
- 政策有效期准确率
- 地区匹配准确率
- 失效政策过滤率
- 高风险问题召回率
- 操作步骤一致率

---

## 八、MVP 验收目标

| 指标 | 目标 |
|---|---:|
| 高频问题自动解答率 | ≥ 80% |
| 政策引用覆盖率 | 100% |
| 文号 / 有效期准确率 | ≥ 95% |
| 操作步骤一致率 | ≥ 90% |
| 失效政策过滤正确率 | 100% |
| 财税专家抽检一致率 | ≥ 90% |
| RAGAS Faithfulness | ≥ 0.80 |
| Answer Relevancy | ≥ 0.80 |
| Context Recall | ≥ 0.70 |
| 高风险问题召回率 | ≥ 95% |
| 流式首 Token | < 1.5 秒 |
| 平均响应时间 | < 3 秒 |

---

## 九、配置要求

重要配置统一通过配置文件或环境变量管理。

至少包括：

```text
MYSQL_HOST
MYSQL_PORT
MYSQL_USER
MYSQL_PASSWORD
MYSQL_DATABASE

REDIS_HOST
REDIS_PORT

MILVUS_HOST
MILVUS_PORT

DASHSCOPE_API_KEY
LLM_MODEL

EMBEDDING_MODEL
RERANKER_MODEL

DEFAULT_TOP_K
DEFAULT_HISTORY_ROUNDS
FAQ_BM25_THRESHOLD
```

任何 API Key、密码等敏感信息禁止硬编码。

---

## 十、Docker 与部署

开发前检查本地：

```text
docker ps
docker images
```

如果已经存在：

- MySQL
- Redis
- Milvus
- MinIO

则尽可能复用。

不存在时创建 docker-compose。

最终要求：

```text
docker-compose up -d
```

可以启动项目所需基础依赖。

---

## 十一、项目开发要求

开始编码前必须先完成以下工作：

1. 阅读现有项目目录；
2. 阅读已有代码；
3. 检查 Docker 容器；
4. 检查已有配置；
5. 分析哪些模块可以复用；
6. 输出项目实现计划；
7. 确认后再开始大规模修改。

禁止：

- 未阅读原项目直接重构；
- 重复创建已经存在的组件；
- 将 API Key 写入代码；
- 删除已有可用功能；
- 为追求复杂度引入不必要中间件。

优先原则：

> 在复用现有 RAG 项目架构的基础上，以最小改动完成 TaxMind 领域化改造。

---

## 十二、代码质量要求

要求：

- 使用合理目录结构；
- Controller / Service / Repository 分层；
- RAG 模块独立；
- 配置统一；
- 完善异常处理；
- 重要流程记录日志；
- 核心函数添加类型标注；
- 关键代码添加中文注释；
- 避免超大函数；
- 避免重复代码。

---

## 十三、前端设计要求

整体风格：

> 专业、简约、年轻化、企业级。

建议：

- 浅色背景
- 卡片式布局
- 适量动画
- 清晰信息层级
- 政策来源重点突出
- 状态颜色明确
- 对话区域保持较大可读空间

TaxMind 不需要做成娱乐型聊天产品，视觉设计应体现：

> **可信、专业、清晰。**

---

## 十四、MVP 边界

本阶段不实现：

- 自动报税
- 自动操作电子税务局
- 获取企业真实申报数据
- 获取发票明细
- 自动税务筹划
- 稽查应对决策
- GraphRAG
- Multi-Agent
- 大模型微调
- 全国所有地方政策

本阶段核心目标：

> **完整跑通“知识入库 → FAQ / RAG 检索 → 时效与地域过滤 → Reranker → LLM → Citation → 风险控制 → 反馈闭环”企业级 RAG 链路。**

---

## 十五、最终交付要求

项目完成后至少包含：

```text
frontend/
backend/
rag/
tests/
data/
docker/
docs/
.env.example
docker-compose.yml
README.md
```

README 需要说明：

- 项目介绍
- 技术架构
- 环境要求
- 安装步骤
- 配置说明
- Docker 启动方式
- 数据导入方式
- 项目启动方式
- 测试执行方式
- API 说明

最终项目必须可以按照 README 从零启动运行。
