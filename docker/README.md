# TaxMind 基础设施

根目录的 `docker-compose.yml` 会启动 MySQL、Redis、Milvus、etcd 和 MinIO。
`minio-init` 会在 MinIO 健康后自动创建私有的 `taxmind-documents` 桶。

首次启动前请复制 `.env.example` 为 `.env`，并替换所有示例密码。

```powershell
docker compose up -d
docker compose ps
```

MinIO API 默认端口为 `9000`，管理控制台为 `http://localhost:9001`。
