#!/bin/bash
# Hybrid DNS Server Backup Script
# Creates comprehensive backup of the DNS server configuration and data

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_BASE="/opt/hybrid-dns-server/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$BACKUP_BASE/$TIMESTAMP"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Create backup directory
create_backup_dir() {
    log "Creating backup directory: $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"
}

# Backup BIND9 configuration
backup_bind() {
    log "Backing up BIND9 configuration..."
    
    # Create BIND backup directory
    mkdir -p "$BACKUP_DIR/bind9"
    
    # Copy configuration files
    cp -r /etc/bind/* "$BACKUP_DIR/bind9/" 2>/dev/null || true
    
    # Backup zone files with proper permissions
    if [[ -d /etc/bind/zones ]]; then
        cp -r /etc/bind/zones "$BACKUP_DIR/bind9/"
    fi
    
    # Backup RPZ files
    if [[ -d /etc/bind/rpz ]]; then
        cp -r /etc/bind/rpz "$BACKUP_DIR/bind9/"
    fi
    
    log "BIND9 configuration backup completed"
}

# Backup database
backup_database() {
    log "Backing up PostgreSQL database..."
    
    # Create database backup directory
    mkdir -p "$BACKUP_DIR/database"
    
    # Full database dump
    if [[ -n "${DATABASE_URL:-}" ]]; then
        pg_dump "$DATABASE_URL" | gzip > "$BACKUP_DIR/database/full_backup.sql.gz"
    else
        # Fallback if DATABASE_URL not set
        sudo -u postgres pg_dump hybrid_dns | gzip > "$BACKUP_DIR/database/full_backup.sql.gz"
    fi
    
    # Schema-only backup
    if [[ -n "${DATABASE_URL:-}" ]]; then
        pg_dump --schema-only "$DATABASE_URL" > "$BACKUP_DIR/database/schema_backup.sql"
    else
        sudo -u postgres pg_dump --schema-only hybrid_dns > "$BACKUP_DIR/database/schema_backup.sql"
    fi
    
    log "Database backup completed"
}

# Backup application configuration
backup_application() {
    log "Backing up application configuration..."
    
    # Create application backup directory
    mkdir -p "$BACKUP_DIR/application"
    
    # Backend configuration
    if [[ -f "$BASE_DIR/backend/app/core/config.py" ]]; then
        cp "$BASE_DIR/backend/app/core/config.py" "$BACKUP_DIR/application/"
    fi
    
    # Environment files (excluding sensitive data)
    if [[ -f "$BASE_DIR/.env" ]]; then
        # Create sanitized env file
        grep -v -E "(PASSWORD|SECRET|KEY)" "$BASE_DIR/.env" > "$BACKUP_DIR/application/env.example" 2>/dev/null || true
    fi
    
    # Systemd service files
    if [[ -d "$BASE_DIR/systemd" ]]; then
        cp -r "$BASE_DIR/systemd" "$BACKUP_DIR/application/"
    fi
    
    # Docker configuration
    if [[ -f "$BASE_DIR/docker-compose.yml" ]]; then
        cp "$BASE_DIR/docker-compose.yml" "$BACKUP_DIR/application/"
    fi
    
    log "Application configuration backup completed"
}

# Backup logs (last 7 days)
backup_logs() {
    log "Backing up recent logs..."
    
    # Create logs backup directory
    mkdir -p "$BACKUP_DIR/logs"
    
    # BIND logs
    if [[ -d /var/log/bind ]]; then
        find /var/log/bind -name "*.log" -mtime -7 -exec cp {} "$BACKUP_DIR/logs/" \; 2>/dev/null || true
    fi
    
    # Application logs
    if [[ -d /var/log/hybrid-dns ]]; then
        find /var/log/hybrid-dns -name "*.log" -mtime -7 -exec cp {} "$BACKUP_DIR/logs/" \; 2>/dev/null || true
    fi
    
    # System logs related to DNS
    journalctl --since="7 days ago" --unit=bind9 > "$BACKUP_DIR/logs/bind9_journal.log" 2>/dev/null || true
    journalctl --since="7 days ago" --unit=hybrid-dns-backend > "$BACKUP_DIR/logs/backend_journal.log" 2>/dev/null || true
    journalctl --since="7 days ago" --unit=hybrid-dns-monitoring > "$BACKUP_DIR/logs/monitoring_journal.log" 2>/dev/null || true
    
    log "Logs backup completed"
}

# Create backup manifest
create_manifest() {
    log "Creating backup manifest..."
    
    cat > "$BACKUP_DIR/MANIFEST.txt" << EOF
Hybrid DNS Server Backup
========================

Backup Date: $(date)
Backup Directory: $BACKUP_DIR
Hostname: $(hostname)
OS: $(lsb_release -d 2>/dev/null | cut -f2 || echo "Unknown")

Contents:
- bind9/          BIND9 configuration and zone files
- database/       PostgreSQL database dumps
- application/    Application configuration files
- logs/          Recent log files (last 7 days)

Services Status at Backup Time:
- BIND9: $(systemctl is-active bind9 2>/dev/null || echo "unknown")
- Backend: $(systemctl is-active hybrid-dns-backend 2>/dev/null || echo "unknown")
- Monitoring: $(systemctl is-active hybrid-dns-monitoring 2>/dev/null || echo "unknown")
- PostgreSQL: $(systemctl is-active postgresql 2>/dev/null || echo "unknown")

Disk Usage:
$(du -sh "$BACKUP_DIR")

Files:
$(find "$BACKUP_DIR" -type f | sort)

EOF

    log "Backup manifest created"
}

# Compress backup
compress_backup() {
    log "Compressing backup..."
    
    cd "$BACKUP_BASE"
    tar -czf "${TIMESTAMP}_hybrid_dns_backup.tar.gz" "$TIMESTAMP"
    
    # Verify archive
    if tar -tzf "${TIMESTAMP}_hybrid_dns_backup.tar.gz" >/dev/null 2>&1; then
        log "Backup archive created successfully: ${TIMESTAMP}_hybrid_dns_backup.tar.gz"
        rm -rf "$BACKUP_DIR"
    else
        log "ERROR: Backup archive verification failed"
        exit 1
    fi
}

# Cleanup old backups
cleanup_old_backups() {
    log "Cleaning up old backups..."
    
    # Keep last 30 days of backups
    find "$BACKUP_BASE" -name "*_hybrid_dns_backup.tar.gz" -mtime +30 -delete 2>/dev/null || true
    
    # Keep last 7 uncompressed backups
    find "$BACKUP_BASE" -type d -name "20*" -mtime +7 -exec rm -rf {} \; 2>/dev/null || true
    
    log "Old backups cleaned up"
}

# Validate prerequisites
validate_prerequisites() {
    log "Validating prerequisites..."
    
    # Check if running as appropriate user
    if [[ $EUID -eq 0 ]]; then
        log "WARNING: Running as root. Consider running as dns-admin user."
    fi
    
    # Check required commands
    for cmd in pg_dump tar gzip; do
        if ! command -v "$cmd" &> /dev/null; then
            log "ERROR: Required command '$cmd' not found"
            exit 1
        fi
    done
    
    # Check backup directory permissions
    if [[ ! -w "$(dirname "$BACKUP_BASE")" ]]; then
        log "ERROR: Cannot write to backup directory: $(dirname "$BACKUP_BASE")"
        exit 1
    fi
    
    log "Prerequisites validated"
}

# Main execution
main() {
    log "Starting Hybrid DNS Server backup..."
    
    validate_prerequisites
    create_backup_dir
    backup_bind
    backup_database
    backup_application
    backup_logs
    create_manifest
    
    if [[ "${1:-}" == "--compress" ]]; then
        compress_backup
    fi
    
    cleanup_old_backups
    
    log "Backup completed successfully"
    log "Backup location: $BACKUP_DIR"
    
    if [[ "${1:-}" == "--compress" ]]; then
        log "Compressed archive: ${BACKUP_BASE}/${TIMESTAMP}_hybrid_dns_backup.tar.gz"
    fi
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [--compress] [--help]"
        echo "Options:"
        echo "  --compress    Create compressed archive and remove uncompressed backup"
        echo "  --help        Show this help message"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac