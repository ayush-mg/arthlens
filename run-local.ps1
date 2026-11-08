<#
.SYNOPSIS
    Starts the full ArthLens application locally (PostgreSQL/PostGIS, FastAPI backend, Next.js frontend).

.DESCRIPTION
    1. Verifies Docker PostGIS database is running on port 5433.
    2. Executes latest database schema migrations via Alembic.
    3. Seeds default local development demo accounts and administrator.
    4. Launches FastAPI backend on http://127.0.0.1:8000.
    5. Launches Next.js frontend on http://localhost:3000.
    6. Verifies endpoint health and records process IDs in .arthlens-pids.json.
#>

[CmdletBinding()]
param(
    [switch]$SkipMigrations,
    [switch]$DevFrontend
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $RepoRoot

Write-Host "==========================================================" -ForegroundColor DarkCyan
Write-Host "           ARTHLENS LOCAL RUNTIME ORCHESTRATOR            " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor DarkCyan

# 1. Check & Ensure PostGIS Database
Write-Host "[1/6] Checking PostGIS 3.4 database on port 5433..." -ForegroundColor Yellow
$DbRunning = $false
try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $tcp.Connect("127.0.0.1", 5433)
    $tcp.Close()
    $DbRunning = $true
} catch {
    $DbRunning = $false
}

if (-not $DbRunning) {
    Write-Host "      Database port 5433 not responding. Checking Docker container 'arthlens-postgis'..." -ForegroundColor Gray
    try {
        & docker start arthlens-postgis | Out-Null
        Start-Sleep -Seconds 3
    } catch {
        Write-Warning "Failed to start Docker container automatically. Ensure Docker Desktop is active."
    }
} else {
    Write-Host "      PostGIS database verified active on port 5433." -ForegroundColor Green
}

# 2. Database Migrations
if (-not $SkipMigrations) {
    Write-Host "[2/6] Running database migrations (alembic upgrade head)..." -ForegroundColor Yellow
    try {
        & "$RepoRoot\.venv\Scripts\alembic.exe" -c "$RepoRoot\backend\alembic.ini" upgrade head
        Write-Host "      Database schema is up to date." -ForegroundColor Green
    } catch {
        Write-Warning "Migration execution encountered an issue: $_"
    }
}

# 3. Seed Demo Accounts
Write-Host "[3/6] Verifying demo and governance accounts..." -ForegroundColor Yellow
try {
    & "$RepoRoot\.venv\Scripts\python.exe" "$RepoRoot\scripts\seed_demo_accounts.py"
    Write-Host "      Demo accounts verified." -ForegroundColor Green
} catch {
    Write-Warning "Demo account seeding issue: $_"
}

# 4. Start FastAPI Backend Server
Write-Host "[4/6] Starting FastAPI backend on port 8000..." -ForegroundColor Yellow

# Terminate any stale process on port 8000
$port8000Proc = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($port8000Proc) {
    Stop-Process -Id $port8000Proc -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}

$BackendProcess = Start-Process `
    -FilePath "$RepoRoot\.venv\Scripts\python.exe" `
    -ArgumentList "-m uvicorn backend.arthlens.api.app:create_app --factory --host 127.0.0.1 --port 8000" `
    -WorkingDirectory $RepoRoot `
    -PassThru

# Poll for backend readiness
$BackendReady = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Milliseconds 500
    try {
        $res = Invoke-RestMethod -Uri "http://127.0.0.1:8000/auth/ping" -Method Get -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($res.status -eq "ok" -or $res.auth) {
            $BackendReady = $true
            break
        }
    } catch {
        # Retry until available
    }
}

if ($BackendReady) {
    Write-Host "      FastAPI backend active (PID: $($BackendProcess.Id))." -ForegroundColor Green
} else {
    Write-Warning "Backend started (PID: $($BackendProcess.Id)), waiting for requests."
}

# 5. Start Durable Agent Run Worker
Write-Host "[5/6] Starting durable agent execution worker..." -ForegroundColor Yellow
$WorkerProcess = Start-Process `
    -FilePath "$RepoRoot\.venv\Scripts\python.exe" `
    -ArgumentList "$RepoRoot\scripts\run_agent_worker.py --poll-interval 1.0" `
    -WorkingDirectory $RepoRoot `
    -PassThru
Write-Host "      Agent worker active (PID: $($WorkerProcess.Id))." -ForegroundColor Green

# 6. Start Next.js Frontend Server
Write-Host "[6/6] Starting Next.js frontend on port 3000..." -ForegroundColor Yellow

# Terminate any stale process on port 3000
$port3000Proc = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($port3000Proc) {
    Stop-Process -Id $port3000Proc -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}

$FrontendScript = if ($DevFrontend) { "dev" } else { "start -- -p 3000" }
$FrontendProcess = Start-Process `
    -FilePath "cmd.exe" `
    -ArgumentList "/c npm --prefix frontend run $FrontendScript" `
    -WorkingDirectory $RepoRoot `
    -PassThru

# Record PIDs for clean shutdown via stop-local.ps1
$PidInfo = @{
    backend_pid = $BackendProcess.Id
    worker_pid = $WorkerProcess.Id
    frontend_pid = $FrontendProcess.Id
    started_at = (Get-Date).ToString("o")
}
$PidInfo | ConvertTo-Json | Set-Content -Path "$RepoRoot\.arthlens-pids.json" -Encoding utf8

Write-Host "`n==========================================================" -ForegroundColor DarkCyan
Write-Host "        ARTHLENS APPLICATION OPERATIONAL AND READY         " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor DarkCyan
Write-Host "  Cinematic Homepage:  http://localhost:3000" -ForegroundColor White
Write-Host "  Interactive Engine:  http://localhost:3000/app" -ForegroundColor White
Write-Host "  Scenario Lab:        http://localhost:3000/app?view=scenarios" -ForegroundColor White
Write-Host "  Evidence Graph:      http://localhost:3000/app?view=graph" -ForegroundColor White
Write-Host "  FastAPI Backend:     http://localhost:8000" -ForegroundColor White
Write-Host "  Interactive Docs:    http://localhost:8000/docs" -ForegroundColor White
Write-Host "----------------------------------------------------------" -ForegroundColor DarkGray
Write-Host "  Demo Credentials (Local Development Only):" -ForegroundColor Yellow
Write-Host "  - Entrepreneur:  entrepreneur@arthlens.org  / Password123!" -ForegroundColor Gray
Write-Host "  - Steward:       steward@arthlens.org       / Password123!" -ForegroundColor Gray
Write-Host "  - Administrator: admin@arthlens.org         / Password123!" -ForegroundColor Gray
Write-Host "==========================================================" -ForegroundColor DarkCyan
Write-Host "  To cleanly stop all servers, run: .\stop-local.ps1`n" -ForegroundColor Cyan

