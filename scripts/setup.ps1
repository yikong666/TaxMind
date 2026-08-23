# TaxMind 首次初始化：配置、依赖、容器、迁移、模型与官方数据。
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
if (-not (Test-Path .env)) { Copy-Item .env.example .env; Write-Host "已创建 .env，请先设置密码、JWT 和 DASHSCOPE_API_KEY 后重新执行。"; exit 1 }
docker compose up -d
uv sync
Push-Location frontend
npm install
Pop-Location
uv run alembic upgrade head
uv run python scripts/download_models.py
uv run python scripts/download_official_data.py
uv run python scripts/check_readiness.py
Write-Host "TaxMind 初始化完成。"
