<#
.SYNOPSIS
    Starts the full ArthLens application locally (PostgreSQL/PostGIS, FastAPI backend, Next.js frontend, Durable Worker).

.DESCRIPTION
    1. Loads environment configuration (.env) and resolves PostgreSQL port and credentials.
    2. Verifies Docker is available, starts its PostGIS service when possible, or initializes an ignored local Windows PostGIS cluster.
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

$env:NO_PROXY = "localhost,127.0.0.1"
$env:no_proxy = "localhost,127.0.0.1"
Write-Host "           ARTHLENS LOCAL RUNTIME ORCHESTRATOR            " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor DarkCyan

$env:NO_PROXY = "localhost,127.0.0.1"
$env:no_proxy = "localhost,127.0.0.1"

# 0. Load .env file into current process environment (auto-initialize if absent)
$EnvFile = "$RepoRoot\.env"
if (-not (Test-Path $EnvFile) -and (Test-Path "$RepoRoot\.env.example")) {
    Copy-Item "$RepoRoot\.env.example" $EnvFile
    Write-Host "      Created .env from .env.example" -ForegroundColor Yellow
}
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

# Pass the Google web client ID to FastAPI. Root .env is authoritative; when it
# is unset or blank, reuse the public client ID configured for the frontend.
$GoogleClientIdSource = "root .env or process environment"
if ([string]::IsNullOrWhiteSpace($env:GOOGLE_CLIENT_ID)) {
    $FrontendEnvFile = Join-Path $RepoRoot "frontend\.env.local"
    if (Test-Path -LiteralPath $FrontendEnvFile) {
        foreach ($line in Get-Content -LiteralPath $FrontendEnvFile) {
            $line = $line.Trim()
            if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
                $parts = $line.Split("=", 2)
                if ($parts[0].Trim() -eq "NEXT_PUBLIC_GOOGLE_CLIENT_ID") {
                    $frontendGoogleClientId = $parts[1].Trim().Trim([char[]]@("'", '"'))
                    if (-not [string]::IsNullOrWhiteSpace($frontendGoogleClientId)) {
                        $env:GOOGLE_CLIENT_ID = $frontendGoogleClientId
                        $GoogleClientIdSource = "frontend/.env.local"
                    }
                    break
                }
            }
        }
    }
}
if (-not [string]::IsNullOrWhiteSpace($env:GOOGLE_CLIENT_ID)) {
    $env:GOOGLE_CLIENT_ID = $env:GOOGLE_CLIENT_ID.Trim()
    $env:NEXT_PUBLIC_GOOGLE_CLIENT_ID = $env:GOOGLE_CLIENT_ID
    Write-Host "      Google OIDC client ID loaded from $GoogleClientIdSource." -ForegroundColor Gray
}

$PythonExe = if (Test-Path "$RepoRoot\.venv\Scripts\python.exe") {
    "$RepoRoot\.venv\Scripts\python.exe"
} else {
    $pyCmd = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($pyCmd) { $pyCmd.Source } else { "python.exe" }
}

$AlembicExe = if (Test-Path "$RepoRoot\.venv\Scripts\alembic.exe") {
    "$RepoRoot\.venv\Scripts\alembic.exe"
} else {
    $alCmd = Get-Command alembic.exe -ErrorAction SilentlyContinue
    if ($alCmd) { $alCmd.Source } else { "alembic.exe" }
}

$PostgresPort = if ($env:POSTGRES_PORT) { [int]$env:POSTGRES_PORT } else { 5433 }
$PostgresUser = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "arthlens_dev" }
$PostgresPassword = if ($env:POSTGRES_PASSWORD) { $env:POSTGRES_PASSWORD } else { "arthlens_dev_password" }
$PostgresDb = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "arthlens" }
$LocalPostgresData = Join-Path $RepoRoot ".postgres_local"
$LocalPostgresMarker = Join-Path $LocalPostgresData ".arthlens-managed.json"
$LocalPostgresStarted = $false

if ($PostgresUser -match '^(?i:replace_with|change_me|your_)' -or $PostgresUser -match '^<.*>$') {
    $PostgresUser = "arthlens_dev"
}
if ($PostgresPassword -match '^(?i:replace_with|change_me|your_)' -or $PostgresPassword -match '^<.*>$') {
    $PostgresPassword = "arthlens_dev_password"
}

# Local Windows processes must connect through loopback rather than Compose's
# service hostname. Compose services keep their own db:5432 settings.
$env:POSTGRES_HOST = "127.0.0.1"
$env:POSTGRES_USER = $PostgresUser
$env:POSTGRES_PASSWORD = $PostgresPassword
$env:POSTGRES_DB = $PostgresDb
$env:POSTGRES_PORT = "$PostgresPort"
$escapedPostgresUser = [System.Uri]::EscapeDataString($PostgresUser)
$escapedPostgresPassword = [System.Uri]::EscapeDataString($PostgresPassword)
$escapedPostgresDb = [System.Uri]::EscapeDataString($PostgresDb)
$env:DATABASE_URL = "postgresql+psycopg://${escapedPostgresUser}:${escapedPostgresPassword}@127.0.0.1:${PostgresPort}/${escapedPostgresDb}"

# 1. Check Docker first, then use a local Windows PostgreSQL/PostGIS cluster if
# the Docker Desktop engine is unavailable. Every probe is bounded so startup
# cannot hang waiting for the Docker named pipe.
Write-Host "[1/6] Checking PostGIS database on port $PostgresPort..." -ForegroundColor Yellow
$DbRunning = $false
try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $tcp.Connect("127.0.0.1", $PostgresPort)
    $tcp.Close()
    $DbRunning = $true
} catch {
    $DbRunning = $false
}

if (-not $DbRunning -or (Test-Path -LiteralPath $LocalPostgresMarker)) {
    $DockerReady = $false
    $DockerCmd = Get-Command docker.exe -ErrorAction SilentlyContinue
    $ManagedLocalPostgres = Test-Path -LiteralPath $LocalPostgresMarker
    if ($DockerCmd -and -not $ManagedLocalPostgres) {
        $DockerProbeBase = Join-Path $env:TEMP "arthlens-docker-probe-$PID"
        $DockerProbeOut = "$DockerProbeBase.out"
        $DockerProbeErr = "$DockerProbeBase.err"
        $DockerProbe = $null
        try {
            $DockerProbe = Start-Process -FilePath $DockerCmd.Source `
                -ArgumentList 'info --format "{{.ServerVersion}}"' `
                -WindowStyle Hidden -PassThru `
                -RedirectStandardOutput $DockerProbeOut `
                -RedirectStandardError $DockerProbeErr
            if ($DockerProbe.WaitForExit(6000)) {
                $DockerReady = ($DockerProbe.ExitCode -eq 0)
            } else {
                Stop-Process -Id $DockerProbe.Id -Force -ErrorAction SilentlyContinue
            }
        } catch {
            $DockerReady = $false
        } finally {
            Remove-Item -LiteralPath $DockerProbeOut, $DockerProbeErr -Force -ErrorAction SilentlyContinue
        }
    }

    if ($ManagedLocalPostgres) {
        Write-Host "      Reusing the ArthLens-managed local PostgreSQL cluster." -ForegroundColor Gray
    }
    if ($DockerReady) {
        Write-Host "      Docker engine is available; starting the Compose PostGIS service..." -ForegroundColor Gray
        & $DockerCmd.Source compose up -d db
        if ($LASTEXITCODE -ne 0) {
            Write-Host "      Docker Compose could not start PostGIS; switching to local PostgreSQL." -ForegroundColor Yellow
            $DockerReady = $false
        }
    }

    if (-not $DockerReady) {
        if ($ManagedLocalPostgres) {
            Write-Host "      Preparing the ArthLens-managed local PostgreSQL cluster on port $PostgresPort..." -ForegroundColor Gray
        } else {
            Write-Host "      Docker Desktop is unavailable; initializing local Windows PostgreSQL on port $PostgresPort..." -ForegroundColor Gray
        }

        $PostgresBin = $env:POSTGRES_BIN
        if (-not $PostgresBin -or -not (Test-Path (Join-Path $PostgresBin "pg_ctl.exe"))) {
            $PostgresBin = $null
            $PostgresInstallRoot = Join-Path $env:ProgramFiles "PostgreSQL"
            if (Test-Path $PostgresInstallRoot) {
                $PostgresVersions = Get-ChildItem -LiteralPath $PostgresInstallRoot -Directory -ErrorAction SilentlyContinue |
                    Sort-Object { try { [version]$_.Name } catch { [version]'0.0' } } -Descending
                foreach ($PostgresVersion in $PostgresVersions) {
                    $CandidateBin = Join-Path $PostgresVersion.FullName "bin"
                    if ((Test-Path (Join-Path $CandidateBin "pg_ctl.exe")) -and
                        (Test-Path (Join-Path $CandidateBin "initdb.exe")) -and
                        (Test-Path (Join-Path $PostgresVersion.FullName "share\extension\postgis.control")) -and
                        (Test-Path (Join-Path $PostgresVersion.FullName "lib\postgis-3.dll"))) {
                        $PostgresBin = $CandidateBin
                        break
                    }
                }
            }
        }
        if (-not $PostgresBin) {
            throw "Docker Desktop is unavailable and no local PostgreSQL installation with PostGIS was found. Install PostgreSQL/PostGIS or set POSTGRES_BIN to its bin directory."
        }

        $PgCtlExe = Join-Path $PostgresBin "pg_ctl.exe"
        $InitDbExe = Join-Path $PostgresBin "initdb.exe"
        $PsqlExe = Join-Path $PostgresBin "psql.exe"
        $CreateDbExe = Join-Path $PostgresBin "createdb.exe"
        if (-not (Test-Path -LiteralPath $LocalPostgresData)) {
            New-Item -ItemType Directory -Path $LocalPostgresData -Force | Out-Null
        }

        $LocalClusterInitialized = Test-Path -LiteralPath (Join-Path $LocalPostgresData "PG_VERSION")
        if (-not $LocalClusterInitialized) {
            $ExistingClusterFiles = @(Get-ChildItem -LiteralPath $LocalPostgresData -Force -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -ne ".arthlens-managed.json" })
            if ($ExistingClusterFiles.Count -gt 0) {
                throw "The local PostgreSQL data directory contains files but no PG_VERSION: $LocalPostgresData. Move or inspect it manually before initializing; the launcher will not overwrite it."
            }
            $InitPasswordFile = Join-Path $env:TEMP "arthlens-initdb-password-$PID"
            Set-Content -LiteralPath $InitPasswordFile -Value $PostgresPassword -NoNewline -Encoding Ascii
            & $InitDbExe -D $LocalPostgresData -U $PostgresUser --pwfile=$InitPasswordFile --auth-local=trust --auth-host=scram-sha-256 --encoding=UTF8
            $InitDbExitCode = $LASTEXITCODE
            Remove-Item -LiteralPath $InitPasswordFile -Force -ErrorAction SilentlyContinue
            if ($InitDbExitCode -ne 0) {
                throw "Local PostgreSQL initialization failed with exit code $InitDbExitCode."
            }
        }

        $PgStatusOutput = & $PgCtlExe status -D $LocalPostgresData 2>&1
        $LocalPostgresRunning = ($LASTEXITCODE -eq 0)
        if (-not $LocalPostgresRunning) {
            # Each launcher run gets its own log so a stale/locked startup log
            # from an earlier PostgreSQL process cannot block pg_ctl on Windows.
            $LocalPostgresLog = Join-Path $LocalPostgresData ("pg_ctl-startup-{0}-{1}.log" -f $PID, (Get-Date -Format "yyyyMMdd-HHmmss-fff"))
            & $PgCtlExe -D $LocalPostgresData -o "-h 127.0.0.1 -p $PostgresPort" -l $LocalPostgresLog -w -t 120 start
            if ($LASTEXITCODE -ne 0) {
                throw "Local PostgreSQL failed to start. See $LocalPostgresLog for details."
            }
            $LocalPostgresStarted = $true
            @{ data_dir = $LocalPostgresData; pg_ctl = $PgCtlExe } |
                ConvertTo-Json | Set-Content -LiteralPath $LocalPostgresMarker -Encoding utf8
        } elseif (Test-Path -LiteralPath $LocalPostgresMarker) {
            $LocalPostgresStarted = $true
        }

        $PreviousPgPassword = $env:PGPASSWORD
        $env:PGPASSWORD = $PostgresPassword
        try {
            $DatabaseNames = @($PostgresDb)
            if ($PostgresDb -eq "arthlens" -and -not $DatabaseNames.Contains("arthlens_test")) {
                $DatabaseNames += "arthlens_test"
            }
            foreach ($DatabaseName in $DatabaseNames) {
                $DatabaseExists = & $PsqlExe -h 127.0.0.1 -p $PostgresPort -U $PostgresUser -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$DatabaseName'"
                if ($LASTEXITCODE -ne 0) {
                    throw "Could not inspect local PostgreSQL databases on port $PostgresPort."
                }
                if (-not ($DatabaseExists -match '1')) {
                    & $CreateDbExe -h 127.0.0.1 -p $PostgresPort -U $PostgresUser -O $PostgresUser $DatabaseName
                    if ($LASTEXITCODE -ne 0) {
                        throw "Could not create local PostgreSQL database '$DatabaseName'."
                    }
                }
                & $PsqlExe -h 127.0.0.1 -p $PostgresPort -U $PostgresUser -d $DatabaseName -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS postgis;"
                if ($LASTEXITCODE -ne 0) {
                    throw "Could not enable PostGIS in local PostgreSQL database '$DatabaseName'."
                }
            }
        } finally {
            if ($null -eq $PreviousPgPassword) { Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue }
            else { $env:PGPASSWORD = $PreviousPgPassword }
        }
    }
}

# Ensure database engine is ready to accept queries
Write-Host "      Verifying PostgreSQL readiness on port $PostgresPort..." -ForegroundColor Gray
$DbReady = $false
$MaxAttempts = 30
for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
    try {
        $testOutput = & $PythonExe -c @"
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
    & $AlembicExe -c "$RepoRoot\backend\alembic.ini" upgrade head
    if ($LASTEXITCODE -ne 0) {
        throw "Database migration failed with exit code $LASTEXITCODE. Local startup halted."
    }
    Write-Host "      Database schema is up to date." -ForegroundColor Green
}

# 3. Seed Demo Accounts (Fatal on failure)
Write-Host "[3/6] Verifying demo and governance accounts..." -ForegroundColor Yellow
& $PythonExe "$RepoRoot\scripts\seed_demo_accounts.py"
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
    -FilePath $PythonExe `
    -ArgumentList "-m uvicorn backend.arthlens.api.app:create_app --factory --host 127.0.0.1 --port 8000 --reload --reload-dir backend" `
    -WorkingDirectory $RepoRoot `
    -WindowStyle Hidden `
    -PassThru

# Poll for backend readiness
$BackendReady = $false
for ($i = 0; $i -lt 30; $i++) {
    if ($BackendProcess.HasExited) {
        throw "FastAPI backend process terminated prematurely with exit code $($BackendProcess.ExitCode)."
    }
    Start-Sleep -Milliseconds 500
    $response = $null
    $reader = $null
    try {
        $request = [System.Net.HttpWebRequest]::Create("http://127.0.0.1:8000/auth/ping")
        $request.Proxy = $null
        $request.Timeout = 2000
        $response = $request.GetResponse()
        $healthStatusCode = [int]$response.StatusCode
        $reader = New-Object System.IO.StreamReader($response.GetResponseStream())
        $healthPayload = $reader.ReadToEnd()
        if ($healthStatusCode -eq 200 -and $healthPayload -match '"status"\s*:\s*"(pong|ok)"') {
            $BackendReady = $true
            break
        }
    } catch {
        # Retry until available
    } finally {
        if ($reader) { $reader.Dispose() }
        if ($response) { $response.Dispose() }
    }
}

if (-not $BackendReady) {
    throw "FastAPI backend failed to become ready on http://127.0.0.1:8000 within timeout."
}
Write-Host "      FastAPI backend active and verified healthy (PID: $($BackendProcess.Id))." -ForegroundColor Green

# 5. Start Next.js Frontend Server
Write-Host "[5/6] Starting Next.js frontend on port 3000..." -ForegroundColor Yellow

# Terminate every stale listener on port 3000 before touching Next.js build files.
$port3000Proc = @()
try {
    $port3000Proc = @(Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction Stop |
        Select-Object -ExpandProperty OwningProcess -Unique)
} catch {
    # No listener is the normal case; continue to the port readiness check below.
}
foreach ($listenerProcessId in $port3000Proc) {
    if (-not $listenerProcessId -or $listenerProcessId -eq $PID) { continue }
    try {
        Stop-Process -Id $listenerProcessId -Force -ErrorAction Stop
        Write-Host "      Stopped stale port 3000 listener (PID: $listenerProcessId)." -ForegroundColor Gray
    } catch {
        & taskkill.exe /PID $listenerProcessId /T /F 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Could not stop stale process $listenerProcessId listening on port 3000."
        }
    }
}

$Port3000Available = $false
for ($attempt = 0; $attempt -lt 20; $attempt++) {
    $tcp = $null
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $tcp.Connect("127.0.0.1", 3000)
        $tcp.Close()
    } catch {
        $Port3000Available = $true
        break
    } finally {
        if ($tcp) { $tcp.Dispose() }
    }
    Start-Sleep -Milliseconds 250
}
if (-not $Port3000Available) {
    throw "Port 3000 is still occupied after stopping its stale listener."
}

# A crashed Next.js process can leave its trace file locked even after the
# listener is gone. Remove only that generated file; if it remains locked,
# stop the matching Next.js process for this frontend and retry.
$FrontendRoot = Join-Path $RepoRoot "frontend"
$NextTracePath = Join-Path $FrontendRoot ".next\trace"
if (Test-Path -LiteralPath $NextTracePath) {
    try {
        Remove-Item -LiteralPath $NextTracePath -Force -ErrorAction Stop
    } catch {
        $frontendRootFull = [System.IO.Path]::GetFullPath($FrontendRoot).TrimEnd('\')
        $staleNextProcesses = @(Get-CimInstance Win32_Process -Filter "Name = 'node.exe'" -ErrorAction SilentlyContinue |
            Where-Object {
                $_.CommandLine -and
                $_.CommandLine.IndexOf($frontendRootFull, [System.StringComparison]::OrdinalIgnoreCase) -ge 0 -and
                $_.CommandLine -match '(?i)next(?:\.js)?\s+(?:dev|start)\b'
            })
        foreach ($staleNext in $staleNextProcesses) {
            Stop-Process -Id $staleNext.ProcessId -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Milliseconds 500
        Remove-Item -LiteralPath $NextTracePath -Force -ErrorAction Stop
    }
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
$FrontendCommand = if ($DevFrontend) { "npm.cmd run dev" } else { "npm.cmd run $FrontendScript" }
$CommandProcessor = if ($env:ComSpec) { $env:ComSpec } else { Join-Path $env:SystemRoot "System32\cmd.exe" }
$FrontendProcess = Start-Process `
    -FilePath $CommandProcessor `
    -ArgumentList "/d /s /c `"$FrontendCommand`"" `
    -WorkingDirectory $FrontendRoot `
    -WindowStyle Hidden `
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
Write-Host "[6/6] Recording managed process IDs and confirming startup..." -ForegroundColor Yellow
$PidInfo = @{
    backend_pid = $BackendProcess.Id
        frontend_pid = $FrontendProcess.Id
    started_at = (Get-Date).ToString("o")
}
$PidInfo | ConvertTo-Json | Set-Content -Path "$RepoRoot\.arthlens-pids.json" -Encoding utf8

Write-Host "`n==========================================================" -ForegroundColor DarkCyan
Write-Host "        ARTHLENS APPLICATION OPERATIONAL AND READY         " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor DarkCyan

$env:NO_PROXY = "localhost,127.0.0.1"
$env:no_proxy = "localhost,127.0.0.1"
Write-Host "  Business Dashboard:  http://localhost:3000" -ForegroundColor White
Write-Host "  Workspace Auth:      http://localhost:3000/login" -ForegroundColor White
Write-Host "  FastAPI Backend:     http://localhost:8000" -ForegroundColor White
Write-Host "  Interactive Docs:    http://localhost:8000/docs" -ForegroundColor White
Write-Host "----------------------------------------------------------" -ForegroundColor DarkGray
Write-Host "  Demo Credentials (Local Development Only):" -ForegroundColor Yellow
Write-Host "  - Entrepreneur:  entrepreneur@arthlens.org  / Password123!" -ForegroundColor Gray
Write-Host "  - Steward:       steward@arthlens.org       / Password123!" -ForegroundColor Gray
Write-Host "  - Administrator: admin@arthlens.org         / Password123!" -ForegroundColor Gray
Write-Host "==========================================================" -ForegroundColor DarkCyan

$env:NO_PROXY = "localhost,127.0.0.1"
$env:no_proxy = "localhost,127.0.0.1"
Write-Host "  To cleanly stop all servers, run: .\stop-local.ps1`n" -ForegroundColor Cyan

if ($Wait) {
    Write-Host "[MONITOR] ArthLens services running. Press Ctrl+C to terminate..." -ForegroundColor Cyan
    try {
        while (-not $BackendProcess.HasExited -and -not $FrontendProcess.HasExited) {
            Start-Sleep -Milliseconds 1000
        }
        if ($BackendProcess.HasExited) {
            Write-Warning "Backend process (PID $($BackendProcess.Id)) exited with code $($BackendProcess.ExitCode)."
        }

        if ($FrontendProcess.HasExited) {
            Write-Warning "Frontend process (PID $($FrontendProcess.Id)) exited with code $($FrontendProcess.ExitCode)."
        }
    } finally {
        Write-Host "`nShutting down ArthLens processes..." -ForegroundColor Yellow
        & "$RepoRoot\stop-local.ps1"
    }
}
