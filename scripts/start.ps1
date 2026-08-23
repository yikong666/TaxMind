# 在两个隐藏进程中启动后端与前端，日志仍由各自日志系统记录。
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
uv run python scripts/check_readiness.py
Start-Process -FilePath "uv" -ArgumentList "run","uvicorn","backend.main:app","--host","127.0.0.1","--port","8000" -WorkingDirectory $ProjectRoot -WindowStyle Hidden
Start-Process -FilePath "npm" -ArgumentList "run","dev" -WorkingDirectory "$ProjectRoot\frontend" -WindowStyle Hidden
Write-Host "TaxMind 已启动：http://127.0.0.1:5173（API：http://127.0.0.1:8000/docs）"
