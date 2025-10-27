#!/bin/bash

# Qwen3 Fine-tuner Startup Script

echo "🚀 Starting Qwen3 Fine-tuner..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create directories
mkdir -p backend/data backend/outputs backend/logs frontend/node_modules

# Start backend
echo "Starting backend server..."
cd backend
python app.py &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 3

# Start frontend (if Node.js is installed)
if command -v node &> /dev/null; then
    echo "Starting frontend server..."
    cd frontend
    npm install 2>/dev/null
    npm run dev &
    FRONTEND_PID=$!
    cd ..

    echo ""
    echo "✅ Qwen3 Fine-tuner started successfully!"
    echo ""
    echo "Backend:  http://localhost:8000"
    echo "Frontend: http://localhost:5173"
    echo "API Docs: http://localhost:8000/docs"
    echo ""
    echo "Press Ctrl+C to stop all services..."

    # Wait for both processes
    wait $BACKEND_PID $FRONTEND_PID
else
    echo ""
    echo "✅ Backend started successfully!"
    echo ""
    echo "Backend:  http://localhost:8000"
    echo "API Docs: http://localhost:8000/docs"
    echo ""
    echo "Note: To run the frontend, install Node.js and run:"
    echo "  cd frontend && npm install && npm run dev"
    echo ""

    wait $BACKEND_PID
fi
