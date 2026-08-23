# 数据目录

- `raw/`：从官方来源下载的原始文件，不提交到 Git。
- `processed/`：清洗后的可复现数据。
- `manifests/`：数据来源、下载时间、校验值和许可说明。
- `evaluation/`：脱敏后的专项评测集。
- `models/`：运行时下载的 BGE-M3 等模型文件，不提交到 Git。

项目只采集国家税务总局、试点地区税务局等官方公开资料，下载脚本和来源清单会随代码提交。

首批来源清单位于 `manifests/official_tax_sources.json`。执行以下命令可重复下载并清洗
5 份官方政策资料，同时生成带 SHA-256 和抓取时间的下载记录：

```powershell
uv run python scripts/download_official_data.py
```

设置 `TAXMIND_ACCESS_TOKEN` 和 `TAXMIND_KNOWLEDGE_BASE_ID` 后，可通过正式 API 批量
解析、维护元数据并向量化现行有效政策：

```powershell
uv run python scripts/import_official_data.py
```

`evaluation/taxmind_mvp_50.jsonl` 包含 50 条首版专项评测问题，可通过
`scripts/build_evaluation_seed.py` 确定性重建。

模型可通过 `uv run python scripts/download_models.py` 下载，来源与许可证记录在
`manifests/` 中。
