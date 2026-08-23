# TaxMind 系统架构

TaxMind 由 Vue 3 管理端、FastAPI 业务服务、MySQL、Redis、MinIO、Milvus 和通义千问组成。

```text
浏览器 → FastAPI/JWT → Query Understanding + Risk Guardrail
                    → Redis / MySQL FAQ
                    → Query Rewrite → BGE-M3 Hybrid Search → Reranker
                    → Parent Context → qwen3-max SSE → Citation / Feedback / Ticket

离线文档 → MinIO → Parser → Parent/Child Chunk → Policy Metadata → Milvus
```

MySQL 保存业务事实，MinIO 保存原始文档，Milvus 只保存可重建的检索向量。政策检索强制执行
用户知识库权限、地区、有效期和 `active` 状态过滤；修改 Chunk 后会清除旧向量并要求重新索引。
