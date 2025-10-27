@echo off
echo.
echo 🔧 Setting up Qwen3 Fine-tuner...
echo.

REM Check Python version
python --version
if %ERRORLEVEL% NEQ 0 (
    echo Error: Python not found. Please install Python 3.10 or higher.
    exit /b 1
)

REM Create virtual environment
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
) else (
    echo Virtual environment already exists
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip setuptools wheel

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Optional: Install Unsloth (not recommended on Windows)
set /p INSTALL_UNSLOTH="Install Unsloth for faster training? (y/n): "
if /i "%INSTALL_UNSLOTH%"=="y" (
    echo Installing Unsloth...
    pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
)

REM Create .env file if it doesn't exist
if not exist ".env" (
    echo Creating .env file from template...
    copy .env.example .env
    echo ⚠️  Please edit .env and add your Hugging Face token
)

REM Create necessary directories
echo Creating directories...
if not exist "backend\data" mkdir backend\data
if not exist "backend\outputs" mkdir backend\outputs
if not exist "backend\logs" mkdir backend\logs
if not exist "backend\configs" mkdir backend\configs

REM Test imports
echo.
echo Testing imports...
python test_imports.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ Setup completed successfully!
    echo.
    echo Next steps:
    echo   1. Edit .env and add your Hugging Face token (optional^)
    echo   2. Run 'start.bat' to start the application
    echo   3. Visit http://localhost:8000/docs for API documentation
) else (
    echo.
    echo ⚠️  Setup completed with warnings
    echo Some imports failed, but you can try running the application
)

pause
