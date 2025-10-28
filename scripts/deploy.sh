#!/bin/bash
# Deployment bootstrap script for Qwen3 Fine-tuner
# Combines environment preparation and service startup in a single command

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -f "requirements.txt" ]; then
    echo "⚠️  Please run this script from the project root directory."
    exit 1
fi

echo "🚀 Deploy: Qwen3 Fine-tuner"

echo "🔧 Preparing Python environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

pip install --upgrade pip setuptools wheel >/dev/null
pip install -r requirements.txt

if [ -f ".env.example" ] && [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✅ Created .env from template (update credentials as needed)."
fi

echo "📁 Ensuring runtime directories exist..."
mkdir -p backend/data backend/outputs backend/logs frontend/node_modules

if [ -f "test_imports.py" ]; then
    echo "🔍 Verifying optional dependencies..."
    if ! python test_imports.py; then
        echo "⚠️  Optional dependency check failed; continuing anyway."
    fi
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

sleep 3

if command -v npm >/dev/null 2>&1; then
    echo "🌐 Starting frontend (Vite) dev server..."
    pushd frontend >/dev/null
    npm install >/dev/null 2>&1 || true
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

echo "\nPress Ctrl+C to stop all services."
wait
