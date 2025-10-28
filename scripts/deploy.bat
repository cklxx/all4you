@echo off
setlocal enabledelayedexpansion

rem Deployment bootstrap script for Qwen3 Fine-tuner on Windows

pushd %~dp0..
if not exist requirements.txt (
    echo ⚠️  Please run this script from the project root directory.
    popd
    exit /b 1
)

echo 🚀 Deploy: Qwen3 Fine-tuner

echo 🔧 Preparing Python environment...
if not exist venv (
    python -m venv venv
)
call venv\Scripts\activate.bat

python -m pip install --upgrade pip setuptools wheel >nul
pip install -r requirements.txt

if exist .env.example if not exist .env (
    copy /Y .env.example .env >nul
    echo ✅ Created .env from template ^(update credentials as needed^).
)

echo 📁 Ensuring runtime directories exist...
if not exist backend\data mkdir backend\data
if not exist backend\outputs mkdir backend\outputs
if not exist backend\logs mkdir backend\logs
if not exist frontend\node_modules mkdir frontend\node_modules

if exist test_imports.py (
    echo 🔍 Verifying optional dependencies...
    python test_imports.py
    if errorlevel 1 (
        echo ⚠️  Optional dependency check failed; continuing anyway.
    )
)

echo 🔥 Starting backend server...
start "Qwen3 Backend" cmd /c "call venv\Scripts\activate.bat ^&^& python backend\app.py"

timeout /t 3 /nobreak >nul

where npm >nul 2>nul
if %errorlevel%==0 (
    echo 🌐 Starting frontend ^(Vite^) dev server...
    pushd frontend
    call npm install >nul 2>nul
    start "Qwen3 Frontend" cmd /c "call ..\venv\Scripts\activate.bat ^&^& npm run dev"
    popd

    echo.
    echo ✅ Services are up and running!
    echo    Backend:  http://localhost:8000
    echo    Frontend: http://localhost:5173
    echo    Docs:     http://localhost:8000/docs
) else (
    echo.
    echo ⚠️  npm is not installed. Only the backend API is running.
    echo    Backend:  http://localhost:8000
    echo    Docs:     http://localhost:8000/docs
    echo    Install Node.js to enable the web UI ^(https://nodejs.org/^).
)

echo.
echo Close the spawned windows or press Ctrl+C to exit.
popd
endlocal
