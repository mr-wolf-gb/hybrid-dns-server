#!/bin/bash

# Hybrid DNS Server IP Change Script
# This script changes the server's IP address and updates all necessary configurations

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO:${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Validate IP address format
validate_ip() {
    local ip=$1
    if [[ $ip =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        IFS='.' read -ra ADDR <<< "$ip"
        for i in "${ADDR[@]}"; do
            if [[ $i -gt 255 ]]; then
                return 1
            fi
        done
        return 0
    else
        return 1
    fi
}

# Get network interface
get_primary_interface() {
    ip route | grep default | awk '{print $5}' | head -n1
}

# Get current IP configuration
get_current_config() {
    local interface=$1
    CURRENT_IP=$(ip addr show $interface | grep "inet " | awk '{print $2}' | cut -d/ -f1 | head -n1)
    CURRENT_NETMASK=$(ip addr show $interface | grep "inet " | awk '{print $2}' | cut -d/ -f2 | head -n1)
    CURRENT_GATEWAY=$(ip route | grep default | awk '{print $3}' | head -n1)
}

# Backup current configuration
backup_configs() {
    local backup_dir="/opt/hybrid-dns-server/backups/ip-change-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$backup_dir"
    
    log "Creating backup in $backup_dir"
    
    # Backup network configuration
    if [[ -f /etc/netplan/00-installer-config.yaml ]]; then
        cp /etc/netplan/00-installer-config.yaml "$backup_dir/"
    fi
    if [[ -f /etc/netplan/01-netcfg.yaml ]]; then
        cp /etc/netplan/01-netcfg.yaml "$backup_dir/"
    fi
    
    # Backup DNS server configurations
    if [[ -d /etc/bind ]]; then
        cp -r /etc/bind "$backup_dir/"
    fi
    
    # Backup application configuration
    if [[ -f /opt/hybrid-dns-server/.env ]]; then
        cp /opt/hybrid-dns-server/.env "$backup_dir/"
    fi
    
    # Backup systemd services
    cp /etc/systemd/system/hybrid-dns-*.service "$backup_dir/" 2>/dev/null || true
    
    echo "$backup_dir" > /tmp/ip-change-backup-path
    log "Backup completed: $backup_dir"
}

# Update netplan configuration
update_netplan() {
    local interface=$1
    local new_ip=$2
    local netmask=$3
    local gateway=$4
    local dns1=$5
    local dns2=$6
    
    log "Updating netplan configuration for interface $interface"
    
    # Find netplan config file
    local netplan_file=""
    if [[ -f /etc/netplan/00-installer-config.yaml ]]; then
        netplan_file="/etc/netplan/00-installer-config.yaml"
    elif [[ -f /etc/netplan/01-netcfg.yaml ]]; then
        netplan_file="/etc/netplan/01-netcfg.yaml"
    else
        netplan_file="/etc/netplan/01-netcfg.yaml"
    fi
    
    # Create new netplan configuration
    cat > "$netplan_file" << EOF
network:
  version: 2
  renderer: networkd
  ethernets:
    $interface:
      dhcp4: false
      addresses:
        - $new_ip/$netmask
      gateway4: $gateway
      nameservers:
        addresses:
          - $dns1
          - $dns2
      dhcp6: false
EOF
    
    log "Netplan configuration updated: $netplan_file"
}

# Update BIND9 configuration
update_bind_config() {
    local old_ip=$1
    local new_ip=$2
    
    log "Updating BIND9 configuration files"
    
    # Update named.conf.options
    if [[ -f /etc/bind/named.conf.options ]]; then
        sed -i "s/$old_ip/$new_ip/g" /etc/bind/named.conf.options
        log "Updated /etc/bind/named.conf.options"
    fi
    
    # Update named.conf.local
    if [[ -f /etc/bind/named.conf.local ]]; then
        sed -i "s/$old_ip/$new_ip/g" /etc/bind/named.conf.local
        log "Updated /etc/bind/named.conf.local"
    fi
    
    # Update zone files
    if [[ -d /etc/bind/zones ]]; then
        find /etc/bind/zones -name "*.zone" -type f -exec sed -i "s/$old_ip/$new_ip/g" {} \;
        log "Updated zone files in /etc/bind/zones"
    fi
    
    # Update reverse zone files
    if [[ -d /etc/bind/zones ]]; then
        find /etc/bind/zones -name "*.rev" -type f -exec sed -i "s/$old_ip/$new_ip/g" {} \;
        log "Updated reverse zone files"
    fi
}

# Update application configuration
update_app_config() {
    local old_ip=$1
    local new_ip=$2
    
    log "Updating application configuration"
    
    # Update .env file
    if [[ -f /opt/hybrid-dns-server/.env ]]; then
        sed -i "s/$old_ip/$new_ip/g" /opt/hybrid-dns-server/.env
        log "Updated /opt/hybrid-dns-server/.env"
    fi
    
    # Update backend .env if exists
    if [[ -f /opt/hybrid-dns-server/backend/.env ]]; then
        sed -i "s/$old_ip/$new_ip/g" /opt/hybrid-dns-server/backend/.env
        log "Updated backend .env"
    fi
    
    # Update docker-compose.yml if exists
    if [[ -f /opt/hybrid-dns-server/docker-compose.yml ]]; then
        sed -i "s/$old_ip/$new_ip/g" /opt/hybrid-dns-server/docker-compose.yml
        log "Updated docker-compose.yml"
    fi
}

# Update systemd services
update_systemd_services() {
    local old_ip=$1
    local new_ip=$2
    
    log "Updating systemd service configurations"
    
    # Update service files
    for service_file in /etc/systemd/system/hybrid-dns-*.service; do
        if [[ -f "$service_file" ]]; then
            sed -i "s/$old_ip/$new_ip/g" "$service_file"
            log "Updated $(basename $service_file)"
        fi
    done
    
    # Reload systemd
    systemctl daemon-reload
    log "Systemd daemon reloaded"
}

# Apply network changes
apply_network_changes() {
    log "Applying network configuration changes"
    
    # Apply netplan
    netplan apply
    
    # Wait for network to stabilize
    sleep 5
    
    # Verify new IP is active
    local interface=$(get_primary_interface)
    local current_ip=$(ip addr show $interface | grep "inet " | awk '{print $2}' | cut -d/ -f1 | head -n1)
    
    if [[ "$current_ip" == "$NEW_IP" ]]; then
        log "Network configuration applied successfully. New IP: $current_ip"
    else
        error "Network configuration failed. Current IP: $current_ip, Expected: $NEW_IP"
        return 1
    fi
}

# Restart services
restart_services() {
    log "Restarting DNS and application services"
    
    # Stop services
    systemctl stop hybrid-dns-backend 2>/dev/null || true
    systemctl stop hybrid-dns-monitoring 2>/dev/null || true
    systemctl stop bind9
    
    # Start BIND9 first
    systemctl start bind9
    sleep 2
    
    # Start application services
    systemctl start hybrid-dns-backend 2>/dev/null || true
    systemctl start hybrid-dns-monitoring 2>/dev/null || true
    
    # Check service status
    if systemctl is-active --quiet bind9; then
        log "BIND9 service started successfully"
    else
        warn "BIND9 service failed to start"
    fi
    
    if systemctl is-active --quiet hybrid-dns-backend 2>/dev/null; then
        log "Backend service started successfully"
    else
        warn "Backend service not running or not installed"
    fi
}

# Verify DNS functionality
verify_dns() {
    local new_ip=$1
    
    log "Verifying DNS functionality"
    
    # Test DNS resolution
    if nslookup google.com $new_ip >/dev/null 2>&1; then
        log "DNS resolution test passed"
    else
        warn "DNS resolution test failed"
    fi
    
    # Test BIND9 status
    if named-checkconf; then
        log "BIND9 configuration syntax is valid"
    else
        error "BIND9 configuration has syntax errors"
    fi
}

# Update firewall rules
update_firewall() {
    local old_ip=$1
    local new_ip=$2
    
    log "Updating firewall rules"
    
    # Update UFW rules if UFW is active
    if command -v ufw >/dev/null 2>&1 && ufw status | grep -q "Status: active"; then
        # Remove old IP rules
        ufw --force delete allow from $old_ip 2>/dev/null || true
        
        # Add new IP rules
        ufw allow from $new_ip
        ufw allow to $new_ip port 53
        ufw allow to $new_ip port 8000
        ufw allow to $new_ip port 3000
        
        log "UFW firewall rules updated"
    fi
    
    # Update iptables rules if they exist
    if iptables -L | grep -q "$old_ip"; then
        warn "Manual iptables rules detected. Please update them manually:"
        info "Old IP: $old_ip -> New IP: $new_ip"
    fi
}

# Main execution
main() {
    echo "=============================================="
    echo "    Hybrid DNS Server IP Change Script"
    echo "=============================================="
    echo
    
    check_root
    
    # Get current network configuration
    INTERFACE=$(get_primary_interface)
    if [[ -z "$INTERFACE" ]]; then
        error "Could not determine primary network interface"
        exit 1
    fi
    
    get_current_config "$INTERFACE"
    
    echo "Current Configuration:"
    echo "  Interface: $INTERFACE"
    echo "  IP Address: $CURRENT_IP/$CURRENT_NETMASK"
    echo "  Gateway: $CURRENT_GATEWAY"
    echo
    
    # Get new IP configuration
    read -p "Enter new IP address: " NEW_IP
    if ! validate_ip "$NEW_IP"; then
        error "Invalid IP address format"
        exit 1
    fi
    
    read -p "Enter subnet mask (CIDR notation, e.g., 24): " NEW_NETMASK
    if ! [[ "$NEW_NETMASK" =~ ^[0-9]+$ ]] || [[ "$NEW_NETMASK" -lt 1 ]] || [[ "$NEW_NETMASK" -gt 32 ]]; then
        error "Invalid subnet mask. Use CIDR notation (1-32)"
        exit 1
    fi
    
    read -p "Enter gateway IP address [$CURRENT_GATEWAY]: " NEW_GATEWAY
    NEW_GATEWAY=${NEW_GATEWAY:-$CURRENT_GATEWAY}
    if ! validate_ip "$NEW_GATEWAY"; then
        error "Invalid gateway IP address"
        exit 1
    fi
    
    read -p "Enter primary DNS server [8.8.8.8]: " DNS1
    DNS1=${DNS1:-8.8.8.8}
    if ! validate_ip "$DNS1"; then
        error "Invalid primary DNS server IP"
        exit 1
    fi
    
    read -p "Enter secondary DNS server [8.8.4.4]: " DNS2
    DNS2=${DNS2:-8.8.4.4}
    if ! validate_ip "$DNS2"; then
        error "Invalid secondary DNS server IP"
        exit 1
    fi
    
    echo
    echo "New Configuration:"
    echo "  Interface: $INTERFACE"
    echo "  IP Address: $NEW_IP/$NEW_NETMASK"
    echo "  Gateway: $NEW_GATEWAY"
    echo "  DNS Servers: $DNS1, $DNS2"
    echo
    
    read -p "Proceed with IP change? (y/N): " CONFIRM
    if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
        info "Operation cancelled"
        exit 0
    fi
    
    echo
    log "Starting IP address change process..."
    
    # Create backup
    backup_configs
    
    # Update configurations
    update_netplan "$INTERFACE" "$NEW_IP" "$NEW_NETMASK" "$NEW_GATEWAY" "$DNS1" "$DNS2"
    update_bind_config "$CURRENT_IP" "$NEW_IP"
    update_app_config "$CURRENT_IP" "$NEW_IP"
    update_systemd_services "$CURRENT_IP" "$NEW_IP"
    
    # Apply network changes
    if apply_network_changes; then
        # Update firewall
        update_firewall "$CURRENT_IP" "$NEW_IP"
        
        # Restart services
        restart_services
        
        # Verify functionality
        verify_dns "$NEW_IP"
        
        echo
        log "IP address change completed successfully!"
        log "Old IP: $CURRENT_IP -> New IP: $NEW_IP"
        log "Backup location: $(cat /tmp/ip-change-backup-path 2>/dev/null || echo 'Unknown')"
        echo
        info "Please verify all services are working correctly:"
        info "  - Test DNS resolution: nslookup google.com $NEW_IP"
        info "  - Check web interface: http://$NEW_IP:3000"
        info "  - Check API: http://$NEW_IP:8000/docs"
        info "  - Monitor logs: journalctl -u bind9 -f"
        echo
    else
        error "Network configuration failed. Attempting rollback..."
        
        # Rollback network configuration
        if [[ -f "$(cat /tmp/ip-change-backup-path 2>/dev/null)/00-installer-config.yaml" ]]; then
            cp "$(cat /tmp/ip-change-backup-path)/00-installer-config.yaml" /etc/netplan/
            netplan apply
            log "Network configuration rolled back"
        fi
        
        exit 1
    fi
}

# Rollback function
rollback() {
    local backup_path="$1"
    
    if [[ -z "$backup_path" ]] || [[ ! -d "$backup_path" ]]; then
        error "Invalid backup path: $backup_path"
        exit 1
    fi
    
    log "Rolling back configuration from: $backup_path"
    
    # Rollback network configuration
    if [[ -f "$backup_path/00-installer-config.yaml" ]]; then
        cp "$backup_path/00-installer-config.yaml" /etc/netplan/
        netplan apply
        log "Network configuration rolled back"
    fi
    
    # Rollback BIND configuration
    if [[ -d "$backup_path/bind" ]]; then
        rm -rf /etc/bind.backup 2>/dev/null || true
        mv /etc/bind /etc/bind.backup
        cp -r "$backup_path/bind" /etc/bind
        log "BIND configuration rolled back"
    fi
    
    # Rollback application configuration
    if [[ -f "$backup_path/.env" ]]; then
        cp "$backup_path/.env" /opt/hybrid-dns-server/
        log "Application configuration rolled back"
    fi
    
    # Restart services
    restart_services
    
    log "Rollback completed"
}

# Handle command line arguments
case "${1:-}" in
    "rollback")
        if [[ -n "${2:-}" ]]; then
            rollback "$2"
        else
            error "Usage: $0 rollback <backup_path>"
            exit 1
        fi
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [rollback <backup_path>]"
        echo
        echo "Options:"
        echo "  (no args)              Run interactive IP change"
        echo "  rollback <backup_path> Rollback to previous configuration"
        echo "  help                   Show this help message"
        ;;
    "")
        main
        ;;
    *)
        error "Unknown option: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac