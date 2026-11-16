# ==============================================================================
# ArthLens Complete Dynamic Verification Script
# Dynamic Verification Suite for ArthLens Business Operating System & Decision Intelligence Platform
# Checks:
# 1. PostgreSQL Alembic Head & Database Schema Synchronization
# 2. Dynamic Backend Pytest Suite (Unit, Integration, Security, RBAC, Attributions)
# 3. Frontend Vitest Test Suites
# 4. TypeScript Strict Compiler Check (tsc --noEmit)
# 5. Next.js 14 Production Build across all routes
# 6. Playwright E2E Specification Readiness
# ==============================================================================

$ErrorActionPreference = "Continue"

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "  ARTHLENS BUSINESS OS & DECISION INTELLIGENCE -- MASTER VERIFICATION SUITE" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "Timestamp: $((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ'))" -ForegroundColor Gray

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

$pythonExe = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$pytestExe = Join-Path $RepoRoot ".venv\Scripts\pytest.exe"
$tscExe = Join-Path $RepoRoot "frontend\node_modules\.bin\tsc.cmd"

# ------------------------------------------------------------------------------
# 1. Database Migration & Schema Check
# ------------------------------------------------------------------------------
Write-Host "`n[1/6] Verifying PostgreSQL Alembic Migrations & Schema..." -ForegroundColor Yellow
if (-not (Test-Path $pythonExe)) {
    Write-Host "Required project Python interpreter not found: $pythonExe" -ForegroundColor Red
    exit 1
}
$alembicOutput = & $pythonExe -m alembic -c backend/alembic.ini current 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "`nAlembic migration verification failed!" -ForegroundColor Red
    Write-Host $alembicOutput
    exit 1
}

$currentHead = ($alembicOutput | Where-Object { $_ -match "\b[0-9]+_[a-zA-Z0-9_]+\b" } | Select-Object -First 1)
if (-not $currentHead) {
    Write-Host "Alembic returned success without a current revision; schema status is unknown." -ForegroundColor Red
    Write-Host $alembicOutput
    exit 1
}
$currentHead = $currentHead.Trim()

$tableCountOutput = & $pythonExe -c "from backend.arthlens.infra.models import Base; print(len(Base.metadata.tables))" 2>&1
if ($LASTEXITCODE -ne 0 -or $tableCountOutput -notmatch "^\d+$") {
    Write-Host "Could not enumerate ORM metadata tables; schema status is unknown." -ForegroundColor Red
    Write-Host $tableCountOutput
    exit 1
}
$totalTables = $tableCountOutput.Trim()

Write-Host "[PASS] Alembic reports current database revision: $currentHead" -ForegroundColor Green
Write-Host "       ORM metadata declares $totalTables tables (this does not compare live schema)." -ForegroundColor Gray

# ------------------------------------------------------------------------------
# 2. Backend Pytest Suite with Dynamic Metric Capture
# ------------------------------------------------------------------------------
Write-Host "`n[2/6] Executing Backend Pytest Suite (Dynamic Execution & Metric Capture)..." -ForegroundColor Yellow
$pytestStart = Get-Date
$pytestRaw = & $pytestExe backend/tests/contract backend/tests/unit backend/tests/integration -v --tb=short 2>&1
$pytestExit = $LASTEXITCODE
$pytestDuration = [math]::Round(((Get-Date) - $pytestStart).TotalSeconds, 2)

if ($pytestExit -ne 0) {
    Write-Host "`nBackend test suite failed with exit code $pytestExit!" -ForegroundColor Red
    $pytestRaw | Select-Object -Last 30 | Write-Host
    exit $pytestExit
}

# Dynamically parse passed/failed counts from pytest output
$summaryLine = ($pytestRaw | Where-Object { $_ -match "==+ .* in [0-9.]+s" } | Select-Object -Last 1)
if (-not $summaryLine -or $summaryLine -notmatch "([0-9]+)\s+passed") {
    Write-Host "Pytest exited successfully without a parseable test summary; result is unknown." -ForegroundColor Red
    $pytestRaw | Select-Object -Last 30 | Write-Host
    exit 1
}
$passedCount = $matches[1]

Write-Host "[PASS] Backend Pytest Suite Succeeded: $passedCount tests passed dynamically ($($pytestDuration)s)." -ForegroundColor Green

# ------------------------------------------------------------------------------
# 3. Frontend Vitest Suites
# ------------------------------------------------------------------------------
Write-Host "`n[3/6] Running Frontend Vitest Component Suites..." -ForegroundColor Yellow
$vitestStart = Get-Date
$vitestRaw = npm --prefix frontend test 2>&1
$vitestExit = $LASTEXITCODE
$vitestDuration = [math]::Round(((Get-Date) - $vitestStart).TotalSeconds, 2)

if ($vitestExit -ne 0) {
    Write-Host "`nFrontend Vitest tests failed!" -ForegroundColor Red
    $vitestRaw | Select-Object -Last 20 | Write-Host
    exit $vitestExit
}

$vitestTestsLine = ($vitestRaw | Where-Object { $_ -match "Tests\s+([0-9]+)\s+passed" } | Select-Object -Last 1)
if (-not $vitestTestsLine -or $vitestTestsLine -notmatch "([0-9]+)\s+passed") {
    Write-Host "Vitest exited successfully without a parseable test summary; result is unknown." -ForegroundColor Red
    $vitestRaw | Select-Object -Last 20 | Write-Host
    exit 1
}
$vitestPassed = $matches[1]

Write-Host "[PASS] Frontend Vitest Suites Succeeded: $vitestPassed tests passed dynamically ($($vitestDuration)s)." -ForegroundColor Green

# ------------------------------------------------------------------------------
# 4. TypeScript Strict Compiler Verification (tsc --noEmit)
# ------------------------------------------------------------------------------
Write-Host "`n[4/6] Running TypeScript Strict Type Check (tsc --noEmit)..." -ForegroundColor Yellow
if (Test-Path $tscExe) {
    $tscOutput = & $tscExe --project frontend/tsconfig.json --noEmit 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`nTypeScript strict typecheck failed!" -ForegroundColor Red
        Write-Host $tscOutput
        exit $LASTEXITCODE
    }
} else {
    $tscOutput = npx --yes --prefix frontend tsc --project frontend/tsconfig.json --noEmit 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "TypeScript strict typecheck failed!" -ForegroundColor Red
        Write-Host $tscOutput
        exit $LASTEXITCODE
    }
}
Write-Host "[PASS] TypeScript compilation verified with 0 type errors." -ForegroundColor Green

# ------------------------------------------------------------------------------
# 5. Next.js 14 Production Build across all routes
# ------------------------------------------------------------------------------
Write-Host "`n[5/6] Running Next.js 14 Production Build across all routes..." -ForegroundColor Yellow
$buildStart = Get-Date
$buildRaw = npm --prefix frontend run build 2>&1
$buildExit = $LASTEXITCODE
$buildDuration = [math]::Round(((Get-Date) - $buildStart).TotalSeconds, 2)

if ($buildExit -ne 0) {
    Write-Host "`nNext.js production build failed!" -ForegroundColor Red
    $buildRaw | Select-Object -Last 25 | Write-Host
    exit $buildExit
}
Write-Host "[PASS] Next.js 14 Production Build Succeeded across all routes ($($buildDuration)s)." -ForegroundColor Green

# ------------------------------------------------------------------------------
# 6. Playwright E2E Dynamic Test Execution (Audit Item 5)
# ------------------------------------------------------------------------------
Write-Host "`n[6/6] Executing Playwright E2E Tests (Dynamic Browser Journeys)..." -ForegroundColor Yellow
$e2eStart = Get-Date
$e2eRaw = cmd.exe /c "set PLAYWRIGHT_EXTERNAL_SERVER=true&& cd frontend&& npx playwright test" 2>&1
$e2eExit = $LASTEXITCODE
$e2eDuration = [math]::Round(((Get-Date) - $e2eStart).TotalSeconds, 2)

if ($e2eExit -ne 0) {
    Write-Host "`nPlaywright E2E tests failed with exit code $e2eExit!" -ForegroundColor Red
    $e2eRaw | Write-Host
    exit $e2eExit
}

$e2eSummary = ($e2eRaw | Where-Object { $_ -match "(\d+)\s+passed" } | Select-Object -Last 1)
if (-not $e2eSummary -or $e2eSummary -notmatch "(\d+)\s+passed") {
    Write-Host "Playwright exited successfully without a parseable test summary; result is unknown." -ForegroundColor Red
    $e2eRaw | Write-Host
    exit 1
}
$e2ePassed = [int]$matches[1]
if ($e2ePassed -eq 0) {
    Write-Host "Playwright reported zero passing journeys; verification failed." -ForegroundColor Red
    $e2eRaw | Write-Host
    exit 1
}

Write-Host "[PASS] Playwright E2E Test Suite Succeeded: $e2ePassed journeys passed dynamically ($($e2eDuration)s)." -ForegroundColor Green

# ------------------------------------------------------------------------------
# Final Dynamic Summary Table
# ------------------------------------------------------------------------------
Write-Host "`n================================================================================" -ForegroundColor Cyan
Write-Host "               ARTHLENS MASTER VERIFICATION SUMMARY REPORT                     " -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ("  {0,-35} | {1,-12} | {2,-24}" -f "Verification Gate", "Status", "Dynamic Metric") -ForegroundColor White
Write-Host ("  {0,-35} | {1,-12} | {2,-24}" -f ("-" * 35), ("-" * 12), ("-" * 24)) -ForegroundColor Gray
Write-Host ("  {0,-35} | {1,-12} | {2,-24}" -f "1. Alembic Current Revision", "PASS", "$currentHead ($totalTables ORM tables)") -ForegroundColor Green
Write-Host ("  {0,-35} | {1,-12} | {2,-24}" -f "2. Backend Pytest Test Suite", "PASS", "$passedCount tests ($($pytestDuration)s)") -ForegroundColor Green
Write-Host ("  {0,-35} | {1,-12} | {2,-24}" -f "3. Frontend Vitest Test Suites", "PASS", "$vitestPassed tests ($($vitestDuration)s)") -ForegroundColor Green
Write-Host ("  {0,-35} | {1,-12} | {2,-24}" -f "4. TypeScript Typecheck (tsc)", "PASS", "0 Errors (Strict)") -ForegroundColor Green
Write-Host ("  {0,-35} | {1,-12} | {2,-24}" -f "5. Next.js 14 Production Build", "PASS", "Build succeeded ($($buildDuration)s)") -ForegroundColor Green
Write-Host ("  {0,-35} | {1,-12} | {2,-24}" -f "6. Playwright E2E Execution", "PASS", "$e2ePassed journeys ($($e2eDuration)s)") -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "  RESULT: PASS -- all configured verification gates completed successfully" -ForegroundColor Green
Write-Host "================================================================================`n" -ForegroundColor Cyan
