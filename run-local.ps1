<#
.SYNOPSIS
    Starts the full ArthLens application locally (PostgreSQL/PostGIS, FastAPI backend, Next.js frontend, Durable Worker).

.DESCRIPTION
    1. Loads environment configuration (.env) and resolves PostgreSQL port and credentials.
    2. Verifies Docker PostGIS database is running on the configured port; initializes container if stopped.
    3. Actively verifies database engine readiness before attempting migrations.
    4. Executes latest database schema migrations via Alembic; halts startup immediately on failure.
    5. Seeds default local development demo accounts and administrator; halts startup immediately on failure.
    6. Launches FastAPI backend on http://127.0.0.1:8000 and verifies health endpoint responsiveness.
    7. Launches durable agent worker daemon and verifies it is actively executing.
    8. Launches Next.js frontend on http://localhost:3000 and verifies port responsiveness.
    9. Records process IDs in .arthlens-pids.json for clean termination via stop-local.ps1.
#>

[CmdletBinding()]
param(
    [switch]$SkipMigrations,
    [switch]$DevFrontend,
    [switch]$Wait
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $RepoRoot

Write-Host "==========================================================" -ForegroundColor DarkCyan
Write-Host "           ARTHLENS LOCAL RUNTIME ORCHESTRATOR            " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor DarkCyan

# 0. Load .env file into current process environment if present
$EnvFile = "$RepoRoot\.env"
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $parts = $line.Split("=", 2)
            $k = $parts[0].Trim()
            $v = $parts[1].Trim().Trim("'""'")
            if (-not [System.Environment]::GetEnvironmentVariable($k)) {
                [System.Environment]::SetEnvironmentVariable($k, $v, "Process")
            }
        }
    }
}

$PostgresPort = if ($env:POSTGRES_PORT) { [int]$env:POSTGRES_PORT } else { 5432 }
$PostgresUser = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "arthlens_dev" }
$PostgresPassword = if ($env:POSTGRES_PASSWORD) { $env:POSTGRES_PASSWORD } else { "arthlens_dev_password" }
$PostgresDb = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "arthlens" }
$env:POSTGRES_PORT = "$PostgresPort"

# 1. Check & Ensure PostGIS Database
Write-Host "[1/6] Checking PostGIS 3.4 database on port $PostgresPort..." -ForegroundColor Yellow
$DbRunning = $false
try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $tcp.Connect("127.0.0.1", $PostgresPort)
    $tcp.Close()
    $DbRunning = $true
} catch {
    $DbRunning = $false
}

if (-not $DbRunning) {
    Write-Host "      Port $PostgresPort not responding. Initializing Docker Compose PostGIS container 'arthlens-postgres'..." -ForegroundColor Gray
    try {
        & docker compose up -d db
    } catch {
        Write-Host "      'docker compose up -d db' failed; attempting 'docker start arthlens-postgres'..." -ForegroundColor Gray
        try {
            & docker start arthlens-postgres | Out-Null
        } catch {
            throw "Failed to start Docker container 'arthlens-postgres'. Ensure Docker Desktop is active."
        }
    }
}

# Ensure database engine is ready to accept queries
Write-Host "      Verifying PostgreSQL readiness on port $PostgresPort..." -ForegroundColor Gray
$DbReady = $false
$MaxAttempts = 30
for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
    try {
        $testOutput = & "$RepoRoot\.venv\Scripts\python.exe" -c @"
import os, psycopg
try:
    conn = psycopg.connect('postgresql://${PostgresUser}:${PostgresPassword}@127.0.0.1:${PostgresPort}/${PostgresDb}', connect_timeout=1)
    conn.execute('SELECT 1')
    conn.close()
    print('DB_READY')
except Exception:
    pass
"@ 2>&1
        if ($testOutput -match "DB_READY") {
            $DbReady = $true
            break
        }
    } catch {}
    Start-Sleep -Seconds 1
}

if (-not $DbReady) {
    throw "Database readiness check failed: PostgreSQL on port $PostgresPort did not become ready within $MaxAttempts seconds."
}
Write-Host "      PostGIS database verified active and ready on port $PostgresPort." -ForegroundColor Green

# 2. Database Migrations (Fatal on failure)
if (-not $SkipMigrations) {
    Write-Host "[2/6] Running database migrations (alembic upgrade head)..." -ForegroundColor Yellow
    & "$RepoRoot\.venv\Scripts\alembic.exe" -c "$RepoRoot\backend\alembic.ini" upgrade head
    if ($LASTEXITCODE -ne 0) {
        throw "Database migration failed with exit code $LASTEXITCODE. Local startup halted."
    }
    Write-Host "      Database schema is up to date." -ForegroundColor Green
}

# 3. Seed Demo Accounts (Fatal on failure)
Write-Host "[3/6] Verifying demo and governance accounts..." -ForegroundColor Yellow
& "$RepoRoot\.venv\Scripts\python.exe" "$RepoRoot\scripts\seed_demo_accounts.py"
if ($LASTEXITCODE -ne 0) {
    throw "Demo account seeding failed with exit code $LASTEXITCODE. Local startup halted."
}
Write-Host "      Demo accounts verified." -ForegroundColor Green

# 4. Start FastAPI Backend Server
Write-Host "[4/6] Starting FastAPI backend on port 8000..." -ForegroundColor Yellow

# Terminate any stale process on port 8000
$port8000Proc = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($port8000Proc) {
    foreach ($p in $port8000Proc) {
        try { & taskkill /PID $p /T /F 2>&1 | Out-Null } catch { Stop-Process -Id $p -Force -ErrorAction SilentlyContinue }
    }
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
    if ($BackendProcess.HasExited) {
        throw "FastAPI backend process terminated prematurely with exit code $($BackendProcess.ExitCode)."
    }
    Start-Sleep -Milliseconds 500
    try {
        $res = Invoke-RestMethod -Uri "http://127.0.0.1:8000/auth/ping" -Method Get -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
        if ($res.status -eq "pong" -or $res.status -eq "ok" -or $res.auth) {
            $BackendReady = $true
            break
        }
    } catch {
        # Retry until available
    }
}

if (-not $BackendReady) {
    throw "FastAPI backend failed to become ready on http://127.0.0.1:8000 within timeout."
}
Write-Host "      FastAPI backend active and verified healthy (PID: $($BackendProcess.Id))." -ForegroundColor Green

# 5. Start Durable Agent Run Worker
Write-Host "[5/6] Starting durable agent execution worker..." -ForegroundColor Yellow

# Terminate any stale worker processes
try {
    $staleWorkers = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*run_agent_worker.py*" }
    if ($staleWorkers) {
        foreach ($w in $staleWorkers) {
            try { & taskkill /PID $w.ProcessId /T /F 2>&1 | Out-Null } catch { Stop-Process -Id $w.ProcessId -Force -ErrorAction SilentlyContinue }
        }
        Start-Sleep -Milliseconds 500
    }
} catch {}

$WorkerProcess = Start-Process `
    -FilePath "$RepoRoot\.venv\Scripts\python.exe" `
    -ArgumentList "$RepoRoot\scripts\run_agent_worker.py --poll-interval 1.0" `
    -WorkingDirectory $RepoRoot `
    -PassThru

Start-Sleep -Seconds 1
if ($WorkerProcess.HasExited) {
    throw "Durable agent worker terminated prematurely with exit code $($WorkerProcess.ExitCode)."
}
Write-Host "      Agent worker active and running (PID: $($WorkerProcess.Id))." -ForegroundColor Green

# 6. Start Next.js Frontend Server
Write-Host "[6/6] Starting Next.js frontend on port 3000..." -ForegroundColor Yellow

# Terminate any stale process on port 3000
$port3000Proc = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($port3000Proc) {
    foreach ($p in $port3000Proc) {
        try { & taskkill /PID $p /T /F 2>&1 | Out-Null } catch { Stop-Process -Id $p -Force -ErrorAction SilentlyContinue }
    }
    Start-Sleep -Seconds 1
}

# Ensure production bundle exists if running in production mode
if (-not $DevFrontend -and -not (Test-Path "$RepoRoot\frontend\.next")) {
    Write-Host "      Production bundle not found. Building Next.js frontend..." -ForegroundColor Gray
    cmd.exe /c "npm --prefix frontend run build"
    if ($LASTEXITCODE -ne 0) {
        throw "Frontend production build failed with exit code $LASTEXITCODE."
    }
}

$FrontendScript = if ($DevFrontend) { "dev" } else { "start -- -p 3000" }
$FrontendProcess = Start-Process `
    -FilePath "cmd.exe" `
    -ArgumentList "/c npm --prefix frontend run $FrontendScript" `
    -WorkingDirectory $RepoRoot `
    -PassThru

# Poll for frontend responsiveness on port 3000
$FrontendReady = $false
for ($i = 0; $i -lt 40; $i++) {
    if ($FrontendProcess.HasExited) {
        throw "Next.js frontend process terminated prematurely with exit code $($FrontendProcess.ExitCode)."
    }
    Start-Sleep -Milliseconds 500
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $tcp.Connect("127.0.0.1", 3000)
        $tcp.Close()
        $FrontendReady = $true
        break
    } catch {
        # Retry until available
    }
}

if (-not $FrontendReady) {
    throw "Next.js frontend failed to become ready on http://localhost:3000 within timeout."
}
Write-Host "      Next.js frontend active and verified responsive on port 3000 (PID: $($FrontendProcess.Id))." -ForegroundColor Green

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

if ($Wait) {
    Write-Host "[MONITOR] ArthLens services running. Press Ctrl+C to terminate..." -ForegroundColor Cyan
    try {
        while (-not $BackendProcess.HasExited -and -not $WorkerProcess.HasExited -and -not $FrontendProcess.HasExited) {
            Start-Sleep -Milliseconds 1000
        }
        if ($BackendProcess.HasExited) {
            Write-Warning "Backend process (PID $($BackendProcess.Id)) exited with code $($BackendProcess.ExitCode)."
        }
        if ($WorkerProcess.HasExited) {
            Write-Warning "Worker process (PID $($WorkerProcess.Id)) exited with code $($WorkerProcess.ExitCode)."
        }
        if ($FrontendProcess.HasExited) {
            Write-Warning "Frontend process (PID $($FrontendProcess.Id)) exited with code $($FrontendProcess.ExitCode)."
        }
    } finally {
        Write-Host "`nShutting down ArthLens processes..." -ForegroundColor Yellow
        & "$RepoRoot\stop-local.ps1"
    }
}
