#!/usr/bin/env bash
# Fello AI Account Intelligence — Start Script (Linux/macOS)
# Starts both backend and frontend in background processes.
#
# Usage:
#   ./start.sh              # Start both backend and frontend
#   ./start.sh --backend    # Start backend only
#   ./start.sh --frontend   # Start frontend only

set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_ONLY=false
FRONTEND_ONLY=false

for arg in "$@"; do
    case $arg in
        --backend) BACKEND_ONLY=true ;;
        --frontend) FRONTEND_ONLY=true ;;
    esac
done

echo ""
echo "  Fello AI Account Intelligence"
echo "  =============================="
echo ""

# ── Prerequisite checks ────────────────────────────────────────────────────────

if ! command -v python3 &>/dev/null && ! command -v python &>/dev/null; then
    echo "  ERROR: Python not found. Install Python 3.11+ from https://python.org" >&2
    exit 1
fi

PYTHON=$(command -v python3 || command -v python)

if ! command -v node &>/dev/null && [ "$BACKEND_ONLY" = false ]; then
    echo "  ERROR: Node.js not found. Install from https://nodejs.org" >&2
    exit 1
fi

# ── Backend setup ──────────────────────────────────────────────────────────────

if [ "$FRONTEND_ONLY" = false ]; then
    echo "  [Backend] Checking environment..."

    ENV_FILE="$ROOT/backend/.env"
    if [ ! -f "$ENV_FILE" ]; then
        echo "  WARNING: backend/.env not found. Copying from .env.example..."
        if [ -f "$ROOT/.env.example" ]; then
            cp "$ROOT/.env.example" "$ENV_FILE"
            echo "  Created backend/.env — edit it and add your API keys before continuing."
            echo "  Required: GEMINI_API_KEY or OPENAI_API_KEY, TAVILY_API_KEY"
            exit 1
        else
            echo "  ERROR: .env.example not found. Create backend/.env manually." >&2
            exit 1
        fi
    fi

    echo "  [Backend] Installing Python dependencies..."
    cd "$ROOT"
    $PYTHON -m pip install -r requirements.txt -r requirements-dev.txt -q

    # Create data directory for SQLite
    mkdir -p "$ROOT/data"

    echo "  [Backend] Starting FastAPI server on http://localhost:8000 ..."
    cd "$ROOT"
    $PYTHON -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
    BACKEND_PID=$!
    echo "  Backend PID: $BACKEND_PID"
    sleep 3
fi

# ── Frontend setup ─────────────────────────────────────────────────────────────

if [ "$BACKEND_ONLY" = false ]; then
    FRONTEND_DIR="$ROOT/frontend"
    echo "  [Frontend] Installing Node dependencies..."
    cd "$FRONTEND_DIR"
    npm install --silent

    echo "  [Frontend] Starting Next.js dev server on http://localhost:3000 ..."
    npm run dev &
    FRONTEND_PID=$!
    echo "  Frontend PID: $FRONTEND_PID"
fi

echo ""
echo "  Services starting..."
echo ""
[ "$FRONTEND_ONLY" = false ] && echo "  Backend API:  http://localhost:8000"
[ "$FRONTEND_ONLY" = false ] && echo "  API Docs:     http://localhost:8000/docs"
[ "$BACKEND_ONLY" = false ]  && echo "  Frontend UI:  http://localhost:3000"
echo ""
echo "  Allow 10-15 seconds for both services to fully start."
echo "  Press Ctrl+C to stop all services."
echo ""

# Wait for all background processes
wait
