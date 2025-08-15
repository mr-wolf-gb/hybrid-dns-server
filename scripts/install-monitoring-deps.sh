#!/bin/bash
# Install monitoring dependencies in backend virtual environment

set -e

BACKEND_DIR="/opt/hybrid-dns-server/backend"
MONITORING_DIR="/opt/hybrid-dns-server/monitoring"

echo "Installing monitoring dependencies..."

# Activate backend virtual environment and install monitoring requirements
cd "$BACKEND_DIR"
source venv/bin/activate

# Install monitoring-specific dependencies
pip install asyncpg==0.29.0 python-dateutil==2.8.2 aiofiles==23.2.1

echo "Monitoring dependencies installed successfully"