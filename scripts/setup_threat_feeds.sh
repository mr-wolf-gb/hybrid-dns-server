#!/bin/bash

# Manual Threat Feed Setup Script
# Use this if the automatic import during installation failed

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

INSTALL_DIR="/opt/hybrid-dns-server"
SERVICE_USER="dns-server"

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root. Use: sudo $0"
    fi
}

check_installation() {
    if [[ ! -d "$INSTALL_DIR" ]]; then
        error "Hybrid DNS Server installation not found at $INSTALL_DIR"
    fi
    
    if ! id "$SERVICE_USER" &>/dev/null; then
        error "Service user $SERVICE_USER not found"
    fi
    
    if [[ ! -f "$INSTALL_DIR/.env" ]]; then
        error "Configuration file not found at $INSTALL_DIR/.env"
    fi
}

check_services() {
    info "Checking service status..."
    
    if ! systemctl is-active --quiet hybrid-dns-backend; then
        warning "Backend service is not running - attempting to start..."
        systemctl start hybrid-dns-backend
        sleep 5
        
        if ! systemctl is-active --quiet hybrid-dns-backend; then
            error "Failed to start backend service. Check: journalctl -u hybrid-dns-backend"
        fi
    fi
    
    success "Backend service is running"
}

import_feeds() {
    info "Importing default threat intelligence feeds..."
    
    # Show available feeds first
    echo
    info "Available default threat feeds:"
    sudo -u "$SERVICE_USER" bash -c "
        cd '$INSTALL_DIR/backend'
        source venv/bin/activate
        source '$INSTALL_DIR/.env'
        python scripts/import_default_feeds.py --list
    "
    
    echo
    read -p "Do you want to import the recommended active feeds? (Y/n): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        info "You can import feeds manually using:"
        info "  cd $INSTALL_DIR/backend && source venv/bin/activate && python scripts/import_default_feeds.py --help"
        exit 0
    fi
    
    # Import recommended feeds
    if sudo -u "$SERVICE_USER" bash -c "
        cd '$INSTALL_DIR/backend'
        source venv/bin/activate
        source '$INSTALL_DIR/.env'
        python scripts/import_default_feeds.py --import
    "; then
        success "Threat feeds imported successfully!"
        
        # Show imported feeds
        echo
        info "Imported feeds status:"
        sudo -u "$SERVICE_USER" bash -c "
            cd '$INSTALL_DIR/backend'
            source venv/bin/activate
            source '$INSTALL_DIR/.env'
            python scripts/import_default_feeds.py --list | grep 'IMPORTED'
        "
    else
        error "Failed to import threat feeds. Check the logs for details."
    fi
}

show_help() {
    echo "Manual Threat Feed Setup Script"
    echo "Usage: sudo $0 [OPTIONS]"
    echo
    echo "This script helps you manually import default threat intelligence feeds"
    echo "if the automatic import during installation failed."
    echo
    echo "Options:"
    echo "  --help      Show this help message"
    echo
    echo "The script will:"
    echo "1. Check that Hybrid DNS Server is properly installed"
    echo "2. Verify that required services are running"
    echo "3. Import recommended threat intelligence feeds"
    echo
    echo "Manual commands:"
    echo "  List feeds:    cd $INSTALL_DIR/backend && python scripts/import_default_feeds.py --list"
    echo "  Import all:    cd $INSTALL_DIR/backend && python scripts/import_default_feeds.py --all"
    echo "  Import some:   cd $INSTALL_DIR/backend && python scripts/import_default_feeds.py --import \"Feed Name\""
}

main() {
    echo "🛡️  Hybrid DNS Server - Threat Feed Setup"
    echo "=========================================="
    echo
    
    check_root
    check_installation
    check_services
    import_feeds
    
    echo
    success "Threat feed setup completed!"
    echo
    info "You can now:"
    info "• Access the web interface to manage feeds"
    info "• View threat feed status in the dashboard"
    info "• Configure additional feeds as needed"
    echo
    info "For more options: cd $INSTALL_DIR/backend && python scripts/import_default_feeds.py --help"
}

# Parse arguments
if [[ $# -gt 0 ]]; then
    case "$1" in
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            error "Unknown option: $1. Use --help for usage information."
            ;;
    esac
fi

main