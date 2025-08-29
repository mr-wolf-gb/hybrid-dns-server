#!/bin/bash

# Emergency IP Rollback Script
# Use this script if the main IP change script fails and you need to quickly restore connectivity

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    error "This script must be run as root (use sudo)"
    exit 1
fi

echo "=============================================="
echo "    Emergency IP Rollback Script"
echo "=============================================="
echo

# Find the most recent backup
BACKUP_DIR=$(find /opt/hybrid-dns-server/backups -name "ip-change-*" -type d | sort -r | head -n1)

if [[ -z "$BACKUP_DIR" ]]; then
    error "No IP change backups found in /opt/hybrid-dns-server/backups"
    echo
    echo "Manual rollback steps:"
    echo "1. Edit /etc/netplan/00-installer-config.yaml or /etc/netplan/01-netcfg.yaml"
    echo "2. Run: sudo netplan apply"
    echo "3. Restart services: sudo systemctl restart bind9 hybrid-dns-backend"
    exit 1
fi

log "Found backup: $BACKUP_DIR"

# Show current IP
CURRENT_IP=$(ip route get 8.8.8.8 | awk '{print $7; exit}')
log "Current IP address: $CURRENT_IP"

echo
read -p "Proceed with emergency rollback? (y/N): " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    log "Rollback cancelled"
    exit 0
fi

log "Starting emergency rollback..."

# Stop services first
log "Stopping services..."
systemctl stop hybrid-dns-backend 2>/dev/null || true
systemctl stop hybrid-dns-monitoring 2>/dev/null || true
systemctl stop bind9 2>/dev/null || true

# Rollback network configuration
log "Rolling back network configuration..."
if [[ -f "$BACKUP_DIR/00-installer-config.yaml" ]]; then
    cp "$BACKUP_DIR/00-installer-config.yaml" /etc/netplan/
    log "Restored netplan configuration"
elif [[ -f "$BACKUP_DIR/01-netcfg.yaml" ]]; then
    cp "$BACKUP_DIR/01-netcfg.yaml" /etc/netplan/
    log "Restored netplan configuration"
else
    error "No netplan backup found"
fi

# Apply network changes
log "Applying network configuration..."
netplan apply
sleep 5

# Rollback BIND configuration
if [[ -d "$BACKUP_DIR/bind" ]]; then
    log "Rolling back BIND configuration..."
    rm -rf /etc/bind.emergency-backup 2>/dev/null || true
    mv /etc/bind /etc/bind.emergency-backup 2>/dev/null || true
    cp -r "$BACKUP_DIR/bind" /etc/bind
    log "BIND configuration restored"
fi

# Rollback application configuration
if [[ -f "$BACKUP_DIR/.env" ]]; then
    log "Rolling back application configuration..."
    cp "$BACKUP_DIR/.env" /opt/hybrid-dns-server/
    log "Application configuration restored"
fi

# Rollback systemd services
log "Rolling back systemd services..."
for service_file in "$BACKUP_DIR"/*.service; do
    if [[ -f "$service_file" ]]; then
        cp "$service_file" /etc/systemd/system/
        log "Restored $(basename $service_file)"
    fi
done

systemctl daemon-reload

# Start services
log "Starting services..."
systemctl start bind9
sleep 2

if systemctl is-active --quiet bind9; then
    log "BIND9 started successfully"
else
    error "BIND9 failed to start"
fi

systemctl start hybrid-dns-backend 2>/dev/null || warn "Backend service not available"
systemctl start hybrid-dns-monitoring 2>/dev/null || warn "Monitoring service not available"

# Check new IP
NEW_IP=$(ip route get 8.8.8.8 | awk '{print $7; exit}')
log "New IP address: $NEW_IP"

# Test DNS
log "Testing DNS functionality..."
if nslookup google.com localhost >/dev/null 2>&1; then
    log "DNS test passed"
else
    warn "DNS test failed"
fi

echo
log "Emergency rollback completed!"
log "Backup used: $BACKUP_DIR"
log "Current IP: $NEW_IP"
echo
echo "Please verify:"
echo "  - Network connectivity: ping 8.8.8.8"
echo "  - DNS resolution: nslookup google.com"
echo "  - Web interface: http://$NEW_IP:3000"
echo "  - Service status: systemctl status bind9"