param(
    [int]$BackendPort = 8001,
    [int]$FrontendPort = 3000
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "telite-backend"
$frontend = Join-Path $root "telite-frontend"

Write-Host "Starting Telite LMS backend on http://127.0.0.1:$BackendPort"
Start-Process `
    -FilePath "python" `
    -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$BackendPort", "--reload") `
    -WorkingDirectory $backend `
    -WindowStyle Hidden

Write-Host "Starting Telite LMS frontend on http://localhost:$FrontendPort"
Start-Process `
    -FilePath "npm" `
    -ArgumentList @("run", "dev", "--", "--port", "$FrontendPort") `
    -WorkingDirectory $frontend

Write-Host "Both services are starting. Open http://localhost:$FrontendPort/signup"
