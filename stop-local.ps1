<#
.SYNOPSIS
    Cleanly shuts down all ArthLens local development servers.

.DESCRIPTION
    1. Reads process IDs from .arthlens-pids.json and stops them and their entire process trees.
    2. Identifies and terminates any residual processes bound to ports 8000 and 3000.
    3. Identifies and terminates any residual background worker processes (run_agent_worker.py).
    4. Removes the PID record file and prints confirmation.
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "SilentlyContinue"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $RepoRoot

Write-Host "Shutting down ArthLens local processes..." -ForegroundColor Yellow

# Helper to kill a process and its children
function Stop-ProcessTree([int]$ProcessId) {
    if ($ProcessId -le 0) { return }
    try {
        & taskkill /PID $ProcessId /T /F 2>&1 | Out-Null
    } catch {
        Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
    }
}

# 1. Terminate recorded processes
$PidFile = "$RepoRoot\.arthlens-pids.json"
if (Test-Path $PidFile) {
    try {
        $Pids = Get-Content $PidFile -Raw | ConvertFrom-Json
        if ($Pids.backend_pid) {
            Stop-ProcessTree $Pids.backend_pid
            Write-Host "  Stopped backend process (PID: $($Pids.backend_pid))" -ForegroundColor Gray
        }

        if ($Pids.frontend_pid) {
            Stop-ProcessTree $Pids.frontend_pid
            Write-Host "  Stopped frontend process (PID: $($Pids.frontend_pid))" -ForegroundColor Gray
        }
    } catch {}
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}

# 2. Terminate any residual processes on ports 8000 and 3000
foreach ($port in @(8000, 3000)) {
    $owning = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
    if ($owning) {
        foreach ($pidToKill in $owning) {
            Stop-ProcessTree $pidToKill
            Write-Host "  Cleared residual process on port $port (PID: $pidToKill)" -ForegroundColor Gray
        }
    }
}

# 3. Terminate any residual worker processes running run_agent_worker.py
try {
    $workers = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*run_agent_worker.py*" }
    if ($workers) {
        foreach ($w in $workers) {
            Stop-ProcessTree $w.ProcessId
            Write-Host "  Cleared residual worker process (PID: $($w.ProcessId))" -ForegroundColor Gray
        }
    }
} catch {}

# 4. Stop the local PostgreSQL cluster only when run-local.ps1 recorded that
# ArthLens started it. The ignored data directory is preserved for the next run.
$LocalPostgresMarker = Join-Path $RepoRoot ".postgres_local\.arthlens-managed.json"
if (Test-Path -LiteralPath $LocalPostgresMarker) {
    try {
        $LocalPostgresInfo = Get-Content -LiteralPath $LocalPostgresMarker -Raw | ConvertFrom-Json
        $ExpectedDataDir = [System.IO.Path]::GetFullPath((Join-Path $RepoRoot ".postgres_local")).TrimEnd('\')
        $RecordedDataDir = [System.IO.Path]::GetFullPath([string]$LocalPostgresInfo.data_dir).TrimEnd('\')
        $PgCtlExe = [string]$LocalPostgresInfo.pg_ctl
        if ($RecordedDataDir -ne $ExpectedDataDir -or
            (Split-Path -Leaf $PgCtlExe) -ne "pg_ctl.exe" -or
            -not (Test-Path -LiteralPath $PgCtlExe)) {
            throw "Local PostgreSQL ownership marker is invalid; refusing to stop an unverified process."
        }

        & $PgCtlExe status -D $ExpectedDataDir 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            & $PgCtlExe -D $ExpectedDataDir -m fast -w -t 30 stop
            if ($LASTEXITCODE -ne 0) {
                throw "Local PostgreSQL did not stop cleanly."
            }
            Write-Host "  Stopped ArthLens local PostgreSQL (data preserved in .postgres_local)." -ForegroundColor Gray
        }
        Remove-Item -LiteralPath $LocalPostgresMarker -Force -ErrorAction SilentlyContinue
    } catch {
        Write-Host "  Could not stop the managed local PostgreSQL cluster: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

Write-Host "All ArthLens application services stopped successfully." -ForegroundColor Green
