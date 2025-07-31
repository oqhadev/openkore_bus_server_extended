# OpenKore Bus Server Extended - Build Script
# PowerShell version for Windows

Write-Host "Building OpenKore Bus Server Extended..." -ForegroundColor Cyan
Write-Host ""

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "Python not found! Please install Python 3.x" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Install dependencies if needed
Write-Host "Installing dependencies..." -ForegroundColor Yellow
try {
    pip install -r requirements.txt | Out-Null
    Write-Host "Dependencies installed" -ForegroundColor Green
} catch {
    Write-Host "Failed to install dependencies" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Build the executable
Write-Host "Building executable..." -ForegroundColor Yellow
try {
    python build.py
    Write-Host "Build complete!" -ForegroundColor Green
} catch {
    Write-Host "Build failed" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "Build completed successfully!" -ForegroundColor Green
Write-Host "Check the dist/ folder for your executable" -ForegroundColor Cyan
Write-Host ""
Read-Host "Press Enter to exit"
