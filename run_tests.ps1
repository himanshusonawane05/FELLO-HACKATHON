# Fello AI Account Intelligence - Test Runner (Windows PowerShell)
#
# Usage:
#   .\run_tests.ps1              # Run all fast unit + integration tests
#   .\run_tests.ps1 -Fast        # Run only domain + storage tests (no LLM/network)
#   .\run_tests.ps1 -E2E         # Run end-to-end API validation (requires running backend)
#   .\run_tests.ps1 -All         # Run everything including pipeline tests

param(
    [switch]$Fast,
    [switch]$E2E,
    [switch]$All,
    [string]$BaseUrl = "http://localhost:8000/api/v1"
)

$Root = $PSScriptRoot

Write-Host ""
Write-Host "  Fello AI - Test Runner" -ForegroundColor Cyan
Write-Host "  =======================" -ForegroundColor Cyan
Write-Host ""

# Install test dependencies
Write-Host "  Installing test dependencies..." -ForegroundColor Yellow
$req = Join-Path $Root 'requirements.txt'
$reqDev = Join-Path $Root 'requirements-dev.txt'
python -m pip install -r $req -r $reqDev -q

if ($E2E) {
    Write-Host "  Running E2E API validation against $BaseUrl ..." -ForegroundColor Yellow
    $script = Join-Path $Root 'e2e-tests\validate_api.py'
    python $script --base-url $BaseUrl
    exit $LASTEXITCODE
}

if ($Fast) {
    Write-Host "  Running fast tests (domain + storage, no LLM/network)..." -ForegroundColor Yellow
    $p1 = Join-Path $Root 'tests\test_domain.py'
    $p2 = Join-Path $Root 'tests\test_storage.py'
    $p3 = Join-Path $Root 'tests\test_sqlite_store.py'
    python -m pytest $p1 $p2 $p3 -v --tb=short
    exit $LASTEXITCODE
}

if ($All) {
    Write-Host "  Running ALL tests (includes pipeline tests that call real LLM)..." -ForegroundColor Yellow
    Write-Host "  NOTE: Pipeline tests may take 5-10 minutes." -ForegroundColor Yellow
    $testsDir = Join-Path $Root 'tests'
    python -m pytest $testsDir -v --tb=short
    exit $LASTEXITCODE
}

# Default: run all tests except slow pipeline tests
Write-Host "  Running unit + API tests (excludes slow pipeline tests)..." -ForegroundColor Yellow
Write-Host "  Use -All to include pipeline tests, -Fast for storage/domain only." -ForegroundColor Yellow
Write-Host ""
$p1 = Join-Path $Root 'tests\test_domain.py'
$p2 = Join-Path $Root 'tests\test_storage.py'
$p3 = Join-Path $Root 'tests\test_sqlite_store.py'
$p4 = Join-Path $Root 'tests\test_api.py'
python -m pytest $p1 $p2 $p3 $p4 -v --tb=short -x

exit $LASTEXITCODE
