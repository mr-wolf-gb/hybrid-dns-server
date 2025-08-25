@echo off
REM Emergency WebSocket Rollback Script for Windows
REM This script performs an immediate rollback to the legacy WebSocket system

echo.
echo ========================================
echo   EMERGENCY WEBSOCKET ROLLBACK
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not available in PATH
    echo Please ensure Python is installed and accessible
    pause
    exit /b 1
)

REM Check if we're in the correct directory
if not exist "backend\scripts\websocket\rollback_websocket.py" (
    echo ERROR: rollback_websocket.py not found
    echo Please run this script from the project root directory
    pause
    exit /b 1
)

echo Initiating emergency rollback...
echo.

REM Run the rollback script
cd backend
python scripts/websocket/rollback_websocket.py emergency --reason "Emergency rollback via batch script"

if errorlevel 1 (
    echo.
    echo ERROR: Rollback script failed
    echo Please check the logs and try manual rollback
    pause
    exit /b 1
)

echo.
echo ========================================
echo   ROLLBACK COMPLETED
echo ========================================
echo.
echo Next steps:
echo 1. Restart the backend service
echo 2. Monitor system logs
echo 3. Verify all connections are working
echo 4. Investigate the cause of the rollback
echo.

pause