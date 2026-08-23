# 部署与验收

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

## 验收命令

```powershell
uv run python scripts/check_readiness.py
uv run pytest -q
uv run ruff check .
Set-Location frontend; npm run build
```
