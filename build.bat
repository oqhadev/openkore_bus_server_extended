@echo off
echo 🔨 Building OpenKore Bus Server Extended...
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python not found! Please install Python 3.x
    pause
    exit /b 1
)

REM Install dependencies if needed
echo 📦 Installing dependencies...
pip install -r requirements.txt

REM Build the executable
echo 🚀 Building executable...
python build.py

echo.
echo ✅ Build complete!
echo 📁 Check the dist/ folder for openkore-bus-server.exe
echo.
pause
