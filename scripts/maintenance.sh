#!/bin/bash
# Hybrid DNS Server Maintenance Script
# Runs daily maintenance tasks

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="/var/log/hybrid-dns/maintenance.log"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Rotate logs older than 30 days
rotate_logs() {
    log "Starting log rotation..."
    
    # Rotate BIND logs
    find /var/log/bind -name "*.log" -mtime +30 -delete
    
    # Rotate application logs
    find /var/log/hybrid-dns -name "*.log" -mtime +30 -delete
    
    # Compress logs older than 7 days
    find /var/log/bind -name "*.log" -mtime +7 -exec gzip {} \;
    find /var/log/hybrid-dns -name "*.log" -mtime +7 -exec gzip {} \;
    
    log "Log rotation completed"
}

# Clean old database records
clean_database() {
    log "Starting database cleanup..."
    
    # Connect to database and clean old records
    psql "$DATABASE_URL" -c "
        DELETE FROM dns_logs WHERE timestamp < NOW() - INTERVAL '90 days';
        DELETE FROM audit_logs WHERE timestamp < NOW() - INTERVAL '365 days';
        VACUUM ANALYZE dns_logs;
        VACUUM ANALYZE audit_logs;
    " 2>&1 | tee -a "$LOG_FILE"
    
    log "Database cleanup completed"
}

# Update threat intelligence feeds
update_threat_feeds() {
    log "Starting threat feed update..."
    
    # Download malware domains
    curl -s https://mirror1.malwaredomains.com/files/justdomains > /tmp/malware_domains.txt
    if [[ -s /tmp/malware_domains.txt ]]; then
        # Update RPZ malware zone
        {
            echo '$TTL 300'
            echo '@   IN  SOA localhost. admin.localhost. ('
            echo '    2023010101  ; serial'
            echo '    3600        ; refresh'
            echo '    1800        ; retry'
            echo '    604800      ; expire'
            echo '    300 )       ; minimum'
            echo '    IN  NS  localhost.'
            
            while read -r domain; do
                [[ -n "$domain" && ! "$domain" =~ ^# ]] && echo "$domain CNAME ."
            done < /tmp/malware_domains.txt
        } > /etc/bind/rpz/db.rpz.malware.new
        
        mv /etc/bind/rpz/db.rpz.malware.new /etc/bind/rpz/db.rpz.malware
        chown bind:bind /etc/bind/rpz/db.rpz.malware
        
        # Reload BIND
        systemctl reload bind9
        
        log "Updated malware domains list"
    fi
    
    # Download phishing domains
    curl -s https://openphish.com/feed.txt > /tmp/phishing_domains.txt
    if [[ -s /tmp/phishing_domains.txt ]]; then
        # Extract domains and update RPZ phishing zone
        {
            echo '$TTL 300'
            echo '@   IN  SOA localhost. admin.localhost. ('
            echo '    2023010101  ; serial'
            echo '    3600        ; refresh'
            echo '    1800        ; retry'
            echo '    604800      ; expire'
            echo '    300 )       ; minimum'
            echo '    IN  NS  localhost.'
            
            while read -r url; do
                domain=$(echo "$url" | sed -n 's|^https\?://\([^/]*\).*|\1|p')
                [[ -n "$domain" ]] && echo "$domain CNAME ."
            done < /tmp/phishing_domains.txt | sort -u
        } > /etc/bind/rpz/db.rpz.phishing.new
        
        mv /etc/bind/rpz/db.rpz.phishing.new /etc/bind/rpz/db.rpz.phishing
        chown bind:bind /etc/bind/rpz/db.rpz.phishing
        
        # Reload BIND
        systemctl reload bind9
        
        log "Updated phishing domains list"
    fi
    
    log "Threat feed update completed"
}

# Backup configuration
backup_config() {
    log "Starting configuration backup..."
    
    BACKUP_DIR="/opt/hybrid-dns-server/backups/$(date +%Y%m%d)"
    mkdir -p "$BACKUP_DIR"
    
    # Backup BIND configuration
    cp -r /etc/bind "$BACKUP_DIR/"
    
    # Backup database
    pg_dump "$DATABASE_URL" | gzip > "$BACKUP_DIR/database_backup.sql.gz"
    
    # Backup application configuration
    cp -r "$BASE_DIR/backend/app/core/config.py" "$BACKUP_DIR/"
    
    # Remove backups older than 30 days
    find /opt/hybrid-dns-server/backups -type d -mtime +30 -exec rm -rf {} \; 2>/dev/null || true
    
    log "Configuration backup completed"
}

# Health check
health_check() {
    log "Starting health check..."
    
    # Check BIND9 status
    if systemctl is-active --quiet bind9; then
        log "✓ BIND9 is running"
    else
        log "✗ BIND9 is not running"
    fi
    
    # Check backend API
    if systemctl is-active --quiet hybrid-dns-backend; then
        log "✓ Backend API is running"
    else
        log "✗ Backend API is not running"
    fi
    
    # Check monitoring service
    if systemctl is-active --quiet hybrid-dns-monitoring; then
        log "✓ Monitoring service is running"
    else
        log "✗ Monitoring service is not running"
    fi
    
    # Check database connectivity
    if psql "$DATABASE_URL" -c "SELECT 1" >/dev/null 2>&1; then
        log "✓ Database is accessible"
    else
        log "✗ Database is not accessible"
    fi
    
    # Test DNS resolution
    if dig @localhost google.com +short >/dev/null 2>&1; then
        log "✓ DNS resolution working"
    else
        log "✗ DNS resolution failed"
    fi
    
    log "Health check completed"
}

# Main execution
main() {
    log "Starting maintenance tasks..."
    
    # Create log directory if it doesn't exist
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Run maintenance tasks
    rotate_logs
    clean_database
    update_threat_feeds
    backup_config
    health_check
    
    log "All maintenance tasks completed successfully"
}

# Run main function
main "$@"