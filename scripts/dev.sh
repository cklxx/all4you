#!/bin/bash
# Developer convenience script for running backend and frontend with existing dependencies

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -f "requirements.txt" ]; then
    echo "⚠️  Please run this script from the project root directory."
    exit 1
fi

if [ -d "venv" ]; then
    source venv/bin/activate
elif command -v poetry >/dev/null 2>&1 && [ -f "pyproject.toml" ]; then
    echo "ℹ️  Detected Poetry project; ensure 'poetry run' is used when starting backend manually."
else
    echo "⚠️  Python virtual environment not found. Activate your environment before running this script."
fi

cleanup() {
    echo "\n🛑 Stopping services..."
    if [ -n "${BACKEND_PID:-}" ] && ps -p "$BACKEND_PID" >/dev/null 2>&1; then
        kill "$BACKEND_PID" || true
    fi
    if [ -n "${FRONTEND_PID:-}" ] && ps -p "$FRONTEND_PID" >/dev/null 2>&1; then
        kill "$FRONTEND_PID" || true
    fi
}
trap cleanup EXIT INT TERM

echo "🔥 Starting backend server..."
python backend/app.py &
BACKEND_PID=$!

sleep 2

if command -v npm >/dev/null 2>&1; then
    echo "🌐 Starting frontend (Vite) dev server..."
    pushd frontend >/dev/null
    npm run dev -- --host 0.0.0.0 &
    FRONTEND_PID=$!
    popd >/dev/null

    echo "\n✅ Services are up and running!"
    echo "   Backend:  http://localhost:8000"
    echo "   Frontend: http://localhost:5173"
    echo "   Docs:     http://localhost:8000/docs"
else
    echo "\n⚠️  npm is not installed. Only the backend API is running."
    echo "   Backend:  http://localhost:8000"
    echo "   Docs:     http://localhost:8000/docs"
    echo "   Install Node.js to enable the web UI (https://nodejs.org/)."
fi

wait
