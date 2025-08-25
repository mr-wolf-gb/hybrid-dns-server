# Tools Directory

This directory contains utility scripts and tools for the Hybrid DNS Server project.

## Scripts

### Development Setup
- **`setup-dev.sh`** - Linux/macOS development environment setup
- **`setup-dev.bat`** - Windows development environment setup

These scripts:
- Create `.env` file from template
- Set up Python virtual environment
- Install dependencies
- Initialize development database

### Emergency Tools
- **`emergency_rollback.ps1`** - PowerShell emergency WebSocket rollback
- **`emergency_rollback.bat`** - Windows batch emergency WebSocket rollback

Use these scripts to quickly rollback to the legacy WebSocket system in case of issues.

### Verification
- **`verify_installation.py`** - Installation verification script

Runs comprehensive checks to verify that all components are working correctly after installation.

## Usage

### Development Setup
```bash
# Linux/macOS
./tools/setup-dev.sh

# Windows
tools\setup-dev.bat
```

### Emergency Rollback
```bash
# PowerShell
.\tools\emergency_rollback.ps1

# Windows Command Prompt
tools\emergency_rollback.bat
```

### Installation Verification
```bash
python3 tools/verify_installation.py
```

## Notes

- All scripts should be run from the project root directory
- Development setup scripts will create a `venv` directory (ignored by git)
- Emergency rollback scripts require the backend WebSocket rollback script to be available
- Verification script checks services, ports, API health, and configuration validity