# Emergency WebSocket Rollback Script for PowerShell
# This script performs an immediate rollback to the legacy WebSocket system

Write-Host ""
Write-Host "========================================"
Write-Host "   EMERGENCY WEBSOCKET ROLLBACK"
Write-Host "========================================"
Write-Host ""

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python found: $pythonVersion"
} catch {
    Write-Host "ERROR: Python is not available in PATH" -ForegroundColor Red
    Write-Host "Please ensure Python is installed and accessible" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if we're in the correct directory
if (-not (Test-Path "backend\scripts\websocket\rollback_websocket.py")) {
    Write-Host "ERROR: rollback_websocket.py not found" -ForegroundColor Red
    Write-Host "Please run this script from the project root directory" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Initiating emergency rollback..." -ForegroundColor Yellow
Write-Host ""

# Run the rollback script
Set-Location backend
try {
    $result = python scripts/websocket/rollback_websocket.py emergency --reason "Emergency rollback via PowerShell script"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "========================================"
        Write-Host "   ROLLBACK COMPLETED" -ForegroundColor Green
        Write-Host "========================================"
        Write-Host ""
        Write-Host "Next steps:" -ForegroundColor Cyan
        Write-Host "1. Restart the backend service" -ForegroundColor White
        Write-Host "2. Monitor system logs" -ForegroundColor White
        Write-Host "3. Verify all connections are working" -ForegroundColor White
        Write-Host "4. Investigate the cause of the rollback" -ForegroundColor White
        Write-Host ""
    } else {
        Write-Host ""
        Write-Host "ERROR: Rollback script failed" -ForegroundColor Red
        Write-Host "Please check the logs and try manual rollback" -ForegroundColor Red
        Write-Host ""
    }
} catch {
    Write-Host "ERROR: Failed to execute rollback script: $_" -ForegroundColor Red
    Write-Host "Please check the logs and try manual rollback" -ForegroundColor Red
}

# Return to original directory
Set-Location ..

Read-Host "Press Enter to exit"