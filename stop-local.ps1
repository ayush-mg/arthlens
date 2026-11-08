<#
.SYNOPSIS
    Cleanly shuts down all ArthLens local development servers.

.DESCRIPTION
    1. Reads process IDs from .arthlens-pids.json and stops them.
    2. Identifies and terminates any residual processes bound to ports 8000 and 3000.
    3. Removes the PID record file and prints confirmation.
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "SilentlyContinue"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $RepoRoot

Write-Host "Shutting down ArthLens local processes..." -ForegroundColor Yellow

# 1. Terminate recorded processes
$PidFile = "$RepoRoot\.arthlens-pids.json"
if (Test-Path $PidFile) {
    try {
        $Pids = Get-Content $PidFile -Raw | ConvertFrom-Json
        if ($Pids.backend_pid) {
            Stop-Process -Id $Pids.backend_pid -Force -ErrorAction SilentlyContinue
            Write-Host "  Stopped backend process (PID: $($Pids.backend_pid))" -ForegroundColor Gray
        }
        if ($Pids.worker_pid) {
            Stop-Process -Id $Pids.worker_pid -Force -ErrorAction SilentlyContinue
            Write-Host "  Stopped worker process (PID: $($Pids.worker_pid))" -ForegroundColor Gray
        }
        if ($Pids.frontend_pid) {
            Stop-Process -Id $Pids.frontend_pid -Force -ErrorAction SilentlyContinue
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
            Stop-Process -Id $pidToKill -Force -ErrorAction SilentlyContinue
            Write-Host "  Cleared residual process on port $port (PID: $pidToKill)" -ForegroundColor Gray
        }
    }
}

Write-Host "All ArthLens application services stopped successfully." -ForegroundColor Green

