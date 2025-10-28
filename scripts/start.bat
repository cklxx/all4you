@echo off
pushd %~dp0..
echo.
echo 🚀 Starting Qwen3 Fine-tuner...
echo.

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Create directories
if not exist "backend\data" mkdir backend\data
if not exist "backend\outputs" mkdir backend\outputs
if not exist "backend\logs" mkdir backend\logs
if not exist "frontend\node_modules" mkdir frontend\node_modules

REM Start backend
echo Starting backend server...
cd backend
start python app.py
cd ..

REM Wait for backend to start
timeout /t 3 /nobreak

REM Start frontend (if Node.js is installed)
where node >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo Starting frontend server...
    cd frontend
    call npm install 2>nul
    start npm run dev
    cd ..

    echo.
    echo ✅ Qwen3 Fine-tuner started successfully!
    echo.
    echo Backend:  http://localhost:8000
    echo Frontend: http://localhost:5173
    echo API Docs: http://localhost:8000/docs
    echo.
    echo Press Ctrl+C in the terminal windows to stop services...
) else (
    echo.
    echo ✅ Backend started successfully!
    echo.
    echo Backend:  http://localhost:8000
    echo API Docs: http://localhost:8000/docs
    echo.
    echo Note: To run the frontend, install Node.js and run:
    echo   cd frontend ^&^& npm install ^&^& npm run dev
)

pause
popd
