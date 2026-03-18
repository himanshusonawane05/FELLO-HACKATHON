# Fello AI Account Intelligence — Start Script (Windows PowerShell)
# Starts both backend and frontend in separate terminal windows.
#
# Usage:
#   .\start.ps1              # Start both backend and frontend
#   .\start.ps1 -BackendOnly # Start backend only
#   .\start.ps1 -FrontendOnly # Start frontend only

param(
    [switch]$BackendOnly,
    [switch]$FrontendOnly
)

$Root = $PSScriptRoot

Write-Host ""
Write-Host "  Fello AI Account Intelligence" -ForegroundColor Cyan
Write-Host "  ==============================" -ForegroundColor Cyan
Write-Host ""

# Prerequisite checks

function Check-Command($cmd) {
    return (Get-Command $cmd -ErrorAction SilentlyContinue) -ne $null
}

if (-not (Check-Command "python")) {
    Write-Host "  ERROR: Python not found. Install Python 3.11+ from https://python.org" -ForegroundColor Red
    exit 1
}

if (-not (Check-Command "node") -and -not $BackendOnly) {
    Write-Host "  ERROR: Node.js not found. Install from https://nodejs.org" -ForegroundColor Red
    exit 1
}

# Backend setup

if (-not $FrontendOnly) {
    Write-Host "  [Backend] Checking environment..." -ForegroundColor Yellow

    $EnvFile = Join-Path $Root 'backend\.env'
    if (-not (Test-Path $EnvFile)) {
        Write-Host "  WARNING: backend/.env not found. Copying from .env.example..." -ForegroundColor Yellow
        $ExampleFile = Join-Path $Root ".env.example"
        if (Test-Path $ExampleFile) {
            Copy-Item $ExampleFile $EnvFile
            Write-Host "  Created backend/.env - edit it and add your API keys before continuing." -ForegroundColor Red
            Write-Host "  Required: GEMINI_API_KEY or OPENAI_API_KEY, TAVILY_API_KEY" -ForegroundColor Red
            exit 1
        } else {
            Write-Host "  ERROR: .env.example not found either. Create backend/.env manually." -ForegroundColor Red
            exit 1
        }
    }

    # Check for API keys
    $EnvContent = Get-Content $EnvFile -Raw
    $HasLLM = ($EnvContent -match "GEMINI_API_KEY=AIza") -or ($EnvContent -match "OPENAI_API_KEY=sk-")
    if (-not $HasLLM) {
        Write-Host "  WARNING: No LLM API key found in backend/.env" -ForegroundColor Yellow
        Write-Host "  Set GEMINI_API_KEY or OPENAI_API_KEY for full functionality." -ForegroundColor Yellow
    }

    # Install Python dependencies
    Write-Host "  [Backend] Installing Python dependencies..." -ForegroundColor Yellow
    Push-Location $Root
    python -m pip install -r requirements.txt -r requirements-dev.txt -q
    Pop-Location

    # Create data directory for SQLite
    $DataDir = Join-Path $Root 'data'
    if (-not (Test-Path $DataDir)) {
        New-Item -ItemType Directory -Path $DataDir | Out-Null
    }

    Write-Host "  [Backend] Starting FastAPI server on http://localhost:8000 ..." -ForegroundColor Green
    $BackendCmd = "cd '$Root'; python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $BackendCmd -WindowStyle Normal
    Start-Sleep -Seconds 3
}

# Frontend setup

if (-not $BackendOnly) {
    $FrontendDir = Join-Path $Root 'frontend'
    Write-Host "  [Frontend] Installing Node dependencies..." -ForegroundColor Yellow
    Push-Location $FrontendDir
    npm install --silent
    Pop-Location

    Write-Host "  [Frontend] Starting Next.js dev server on http://localhost:3000 ..." -ForegroundColor Green
    $FrontendCmd = "cd '$FrontendDir'; npm run dev"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $FrontendCmd -WindowStyle Normal
}

Write-Host ""
Write-Host "  Services starting..." -ForegroundColor Cyan
Write-Host ""
if (-not $FrontendOnly) {
    Write-Host "  Backend API:  http://localhost:8000" -ForegroundColor White
    Write-Host "  API Docs:     http://localhost:8000/docs" -ForegroundColor White
}
if (-not $BackendOnly) {
    Write-Host "  Frontend UI:  http://localhost:3000" -ForegroundColor White
}
Write-Host ""
Write-Host "  Allow 10-15 seconds for both services to fully start." -ForegroundColor Yellow
Write-Host ""
