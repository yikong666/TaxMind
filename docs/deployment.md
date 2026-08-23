# TaxMind 部署、运维与验收

接口鉴权和调用方式见 [API 接口文档](api.md)，组件关系见
[系统架构文档](architecture.md)。

## 开发环境

1. 复制 `.env.example` 为 `.env`，替换所有中文占位符和 `change_me` 密码。
2. 执行 `powershell -ExecutionPolicy Bypass -File scripts/setup.ps1`。
3. 执行 `powershell -ExecutionPolicy Bypass -File scripts/start.ps1`。
4. 访问前端、注册账号并依次验证知识库上传、解析、元数据、向量化和智能问答。

## 生产注意事项

- 不向仓库提交 `.env`、模型、Docker 数据卷或原始内部资料。
- 使用反向代理终止 TLS，只开放前端与 API；MySQL、Redis、MinIO、Milvus 不暴露公网。
- 替换全部默认密码，限制 MinIO 桶为私有，并定期备份 MySQL、MinIO 与 etcd 数据。
- 固定镜像版本，先执行 `alembic upgrade head` 再切换应用实例。
- 配置日志采集、磁盘容量、容器健康检查和 API 响应时间告警。

## 配置与发布顺序

1. 从 `.env.example` 创建由部署平台托管的生产配置，设置 `APP_ENV=production`。
2. 为 MySQL、Redis、MinIO 和 JWT 分别生成高强度且不复用的密钥。
3. 将 `CORS_ORIGINS` 限制为正式前端域名，按需关闭 `DOCS_ENABLED`。
4. 启动并确认 MySQL、Redis、MinIO、etcd 和 Milvus 健康。
5. 执行 `uv run alembic upgrade head`，再发布后端实例。
6. 构建前端静态资源并通过反向代理发布，最后执行就绪和业务冒烟检查。

数据库迁移必须先在备份数据或预发布环境演练。多实例发布时只运行一次迁移任务，不允许每个
应用实例并发执行 Alembic。

## 网络与数据边界

- 外部只开放 HTTPS 前端和 `/api`；后端可由反向代理通过内部网络访问。
- MySQL、Redis、MinIO API/Console、etcd 和 Milvus 仅允许应用或运维网络访问。
- MinIO Bucket 禁止匿名访问，内部资料不得进入公开知识库或官方数据目录。
- 容器挂载目录需要专用磁盘和最小权限，禁止将 `docker/volumes` 提交到 Git。

## 备份与恢复

需要作为同一恢复点管理的内容包括：

- MySQL：用户、知识库、文档元数据、Chunk、会话、FAQ 和工单。
- MinIO：原始上传文档。
- etcd 与 Milvus：向量索引状态。Milvus 数据可从 MySQL Chunk 和模型重建，但重建耗时。
- `.env` 对应的密钥：由密钥管理系统备份，不与业务备份放在同一位置。

至少每日执行数据库和对象存储增量/全量备份，并定期在隔离环境做恢复演练。恢复时先还原
MySQL 和 MinIO，再检查文档/对象一致性；Milvus 无法恢复时按文档重新索引。

## 监控与日志

- 采集后端文件日志和容器标准输出，按环境设置保留周期并脱敏。
- 监控 `/api/v1/health`、HTTP 5xx/429、P95 响应时间、SSE 中断率和 LLM 调用失败率。
- 监控 MySQL 连接/慢查询、Redis 内存、MinIO 容量、Milvus 延迟及宿主机磁盘水位。
- 对认证爆破、异常上传、连续解析/索引失败和人工工单积压设置告警。

## 回滚原则

- 应用回滚前确认旧版本是否兼容当前数据库 Schema。
- 不直接删除或降级生产数据；破坏性数据库回滚必须使用已演练的恢复方案。
- 模型或检索参数回滚后，对受影响文档重新索引并记录模型版本。
- 发布失败时保留日志、迁移版本和镜像标签，禁止用未版本化文件覆盖线上实例。

## 验收命令

```powershell
uv run python scripts/check_readiness.py
uv run python -m pytest tests/ -v
uv run ruff check backend rag scripts tests
Set-Location frontend; npm run build
```

验收还应覆盖注册登录、知识库所有权、上传格式校验、解析与索引、政策时效和地区过滤、FAQ、
Query Rewrite、引用、无上下文拒答、高风险门禁、反馈、人工工单以及备份恢复抽查。
