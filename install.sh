#!/bin/bash

# Hybrid DNS Server Installation Script
# For Debian/Ubuntu systems
# Author: MR-WOLF-GB
# Version: 1.1.0 - Added resume functionality
#
# Usage:
#   sudo ./install.sh           # Start new installation
#   sudo ./install.sh --resume  # Resume from checkpoint
#   sudo ./install.sh --fresh   # Force fresh start
#   sudo ./install.sh --status  # Check installation status

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/opt/hybrid-dns-server"
SERVICE_USER="dns-server"
DB_NAME="hybrid_dns"
DB_USER="dns_user"
FRONTEND_PORT="3000"
BACKEND_PORT="8000"
NGINX_AVAILABLE="/etc/nginx/sites-available"
NGINX_ENABLED="/etc/nginx/sites-enabled"

# Server IP Configuration
SERVER_IP=""
DOMAIN_NAME=""

# Logging and Checkpoints
LOG_FILE="/tmp/hybrid-dns-install.log"
CHECKPOINT_FILE="/tmp/hybrid-dns-install.checkpoint"

# Admin User Configuration (can be overridden by environment variables)
# Set these before running the script to customize admin credentials:
# export ADMIN_USERNAME="your_admin"
# export ADMIN_PASSWORD="your_secure_password"
# export ADMIN_EMAIL="admin@yourdomain.com"
# export ADMIN_FULL_NAME="Your Name"

# Functions
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - [INFO] $1" >> "$LOG_FILE"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - [SUCCESS] $1" >> "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - [WARNING] $1" >> "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - [ERROR] $1" >> "$LOG_FILE"
    exit 1
}

# Silent execution with error checking
silent_exec() {
    local cmd="$1"
    local description="$2"
    
    if eval "$cmd" >> "$LOG_FILE" 2>&1; then
        return 0
    else
        error "$description failed. Check $LOG_FILE for details."
        return 1
    fi
}

# Checkpoint functions
save_checkpoint() {
    echo "$1" > "$CHECKPOINT_FILE"
    log "Checkpoint saved: $1"
}

get_checkpoint() {
    if [[ -f "$CHECKPOINT_FILE" ]]; then
        cat "$CHECKPOINT_FILE"
    else
        echo "start"
    fi
}

clear_checkpoint() {
    rm -f "$CHECKPOINT_FILE"
    log "Installation completed - checkpoint cleared"
}

show_resume_menu() {
    local current_step=$(get_checkpoint)
    echo
    echo "🔄 Previous installation detected!"
    echo "Last completed step: $current_step"
    echo
    echo "Choose an option:"
    echo "1) Resume from where it left off"
    echo "2) Start fresh (will clear previous progress)"
    echo "3) Exit"
    echo
    read -p "Enter your choice (1-3): " -n 1 -r
    echo
    
    case $REPLY in
        1)
            info "Resuming installation from: $current_step"
            return 0
            ;;
        2)
            warning "Starting fresh installation..."
            clear_checkpoint
            return 0
            ;;
        3)
            echo "Installation cancelled."
            exit 0
            ;;
        *)
            error "Invalid choice. Please run the script again."
            ;;
    esac
}

run_step() {
    local step_name="$1"
    local step_function="$2"
    local current_checkpoint=$(get_checkpoint)
    
    # Define step order
    local steps=(
        "start"
        "server_configured"
        "system_updated"
        "dependencies_installed"
        "user_created"
        "database_setup"
        "application_downloaded"
        "application_installed"
        "bind9_configured"
        "nginx_configured"
        "systemd_created"
        "firewall_configured"
        "fail2ban_configured"
        "database_initialized"
        "services_started"
        "admin_created"
        "threat_feeds_imported"
        "completed"
    )
    
    # Find current step index
    local current_index=0
    local target_index=0
    
    for i in "${!steps[@]}"; do
        if [[ "${steps[$i]}" == "$current_checkpoint" ]]; then
            current_index=$i
        fi
        if [[ "${steps[$i]}" == "$step_name" ]]; then
            target_index=$i
        fi
    done
    
    # Only run if we haven't passed this step yet
    if [[ $target_index -gt $current_index ]]; then
        log "Running step: $step_name"
        $step_function
        save_checkpoint "$step_name"
    else
        log "Skipping completed step: $step_name"
    fi
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root. Use: sudo $0"
    fi
}

check_os() {
    if [[ ! -f /etc/debian_version ]]; then
        error "This script only supports Debian/Ubuntu systems"
    fi
    
    . /etc/os-release
    log "Detected OS: $NAME $VERSION"
    
    # Ubuntu 24.04 specific checks and warnings
    if [[ "$VERSION_ID" == "24.04" ]]; then
        log "Ubuntu 24.04 LTS detected - applying compatibility fixes"
        
        # Check for snap-installed packages that might conflict
        if command -v snap &> /dev/null; then
            if snap list 2>/dev/null | grep -q "node\|postgresql"; then
                warning "Snap packages detected for Node.js or PostgreSQL - may cause conflicts"
            fi
        fi
        
        # Check Python version (Ubuntu 24.04 uses Python 3.12)
        python_version=$(python3 --version 2>/dev/null | cut -d' ' -f2 | cut -d'.' -f1,2)
        if [[ "$python_version" == "3.12" ]]; then
            log "Python 3.12 detected - ensuring compatibility"
        fi
    fi
}

load_server_configuration() {
    # Try to load server configuration from existing .env file
    if [[ -f "$INSTALL_DIR/.env" ]]; then
        source "$INSTALL_DIR/.env" 2>/dev/null || true
        if [[ -n "$SERVER_IP" ]]; then
            log "Loaded server configuration from existing installation: IP=$SERVER_IP, DOMAIN=$DOMAIN_NAME"
            return 0
        fi
    fi
    return 1
}

get_server_configuration() {
    info "Configuring server network settings..."
    
    # Try to load existing configuration first
    if load_server_configuration; then
        echo
        read -p "Use existing server configuration? (Y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            # User wants to reconfigure
            SERVER_IP=""
            DOMAIN_NAME=""
        else
            success "Using existing server configuration"
            return 0
        fi
    fi
    
    # Auto-detect primary IP address
    local detected_ip=$(hostname -I | awk '{print $1}')
    
    echo
    echo "🌐 Network Configuration"
    echo "========================"
    echo
    echo "Detected IP address: $detected_ip"
    echo
    read -p "Enter server IP address (press Enter to use detected IP): " input_ip
    
    if [[ -n "$input_ip" ]]; then
        SERVER_IP="$input_ip"
    else
        SERVER_IP="$detected_ip"
    fi
    
    # Validate IP address format
    if [[ ! $SERVER_IP =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        error "Invalid IP address format: $SERVER_IP"
    fi
    
    echo
    read -p "Enter domain name (optional, press Enter to skip): " DOMAIN_NAME
    
    info "Server will be configured with:"
    info "  IP Address: $SERVER_IP"
    if [[ -n "$DOMAIN_NAME" ]]; then
        info "  Domain Name: $DOMAIN_NAME"
    else
        info "  Domain Name: Not configured (will use IP address)"
    fi
    
    echo
    read -p "Continue with these settings? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        error "Installation cancelled by user"
    fi
    
    # Save server configuration to temporary file for resume functionality
    cat > "/tmp/hybrid-dns-server-config" << EOF
export SERVER_IP="$SERVER_IP"
export DOMAIN_NAME="$DOMAIN_NAME"
EOF
    
    success "Network configuration completed"
}

check_requirements() {
    log "Checking system requirements..."
    
    # Check available memory (minimum 2GB)
    local mem_gb=$(free -g | awk '/^Mem:/{print $2}')
    if [[ $mem_gb -lt 2 ]]; then
        warning "System has less than 2GB RAM. Performance may be affected."
    fi
    
    # Check available disk space (minimum 5GB)
    local disk_gb=$(df -BG / | awk 'NR==2{print $4}' | sed 's/G//')
    if [[ $disk_gb -lt 5 ]]; then
        error "Insufficient disk space. At least 5GB required."
    fi
    
    log "System requirements check passed"
}

update_system() {
    info "Updating system packages..."
    silent_exec "apt-get update -qq" "System package update"
    silent_exec "apt-get upgrade -y -qq" "System package upgrade"
    success "System updated"
}

install_dependencies() {
    info "Installing system dependencies..."
    
    # Essential packages
    silent_exec "apt-get install -y -qq curl wget gnupg software-properties-common apt-transport-https ca-certificates lsb-release ufw fail2ban unzip git htop nano vim sudo systemd dbus apparmor-utils" "Essential packages installation"
    
    # BIND9 and DNS tools
    silent_exec "apt-get install -y -qq bind9 bind9utils bind9-doc dnsutils" "BIND9 installation"
    
    # Verify BIND9 installation
    if ! command -v named &> /dev/null; then
        error "BIND9 named daemon installation failed"
    fi
    if ! command -v rndc &> /dev/null; then
        error "BIND9 rndc tool installation failed"
    fi
    if ! command -v named-checkconf &> /dev/null; then
        error "BIND9 named-checkconf tool installation failed"
    fi
    if ! command -v named-checkzone &> /dev/null; then
        error "BIND9 named-checkzone tool installation failed"
    fi
    log "BIND9 version: $(named -v 2>&1 | head -1)"
    
    # PostgreSQL
    silent_exec "apt-get install -y -qq postgresql postgresql-contrib postgresql-client libpq-dev postgresql-server-dev-all" "PostgreSQL installation"
    
    # Verify PostgreSQL installation
    if ! command -v psql &> /dev/null; then
        error "PostgreSQL installation failed"
    fi
    log "PostgreSQL version: $(psql --version)"
    
    # Python
    silent_exec "apt-get install -y -qq python3 python3-pip python3-venv python3-dev python3-setuptools python3-wheel build-essential pkg-config libffi-dev libssl-dev" "Python installation"
    
    # Verify Python installation
    if ! command -v python3 &> /dev/null; then
        error "Python3 installation failed"
    fi
    log "Python version: $(python3 --version)"
    
    # Node.js
    silent_exec "curl -fsSL https://deb.nodesource.com/setup_20.x | bash -" "Node.js repository setup"
    silent_exec "apt-get install -y -qq nodejs" "Node.js installation"
    
    # Verify Node.js installation
    if ! command -v node &> /dev/null; then
        error "Node.js installation failed"
    fi
    if ! command -v npm &> /dev/null; then
        error "npm installation failed"
    fi
    log "Node.js version: $(node --version)"
    
    # Redis Server
    silent_exec "apt-get install -y -qq redis-server" "Redis installation"
    
    # Verify Redis installation
    if ! command -v redis-server &> /dev/null; then
        error "Redis installation failed"
    fi
    log "Redis version: $(redis-server --version)"
    
    # Nginx
    silent_exec "apt-get install -y -qq nginx" "Nginx installation"
    
    success "Dependencies installed"
}

create_user() {
    info "Creating service user..."
    
    if ! id "$SERVICE_USER" &>/dev/null; then
        silent_exec "useradd -r -s /bin/bash -d '$INSTALL_DIR' -m '$SERVICE_USER'" "Service user creation"
        success "User $SERVICE_USER created"
    else
        log "User $SERVICE_USER already exists"
    fi
    
    # Add service user to bind group for BIND9 file access
    silent_exec "usermod -a -G bind '$SERVICE_USER'" "Adding user to bind group"
    
    # Add www-data to dns-server group for file access
    silent_exec "usermod -a -G '$SERVICE_USER' www-data" "Adding www-data to service group"
    
    success "User configuration completed"
}

setup_database() {
    info "Setting up PostgreSQL database..."
    
    # Start PostgreSQL
    silent_exec "systemctl start postgresql" "PostgreSQL service start"
    silent_exec "systemctl enable postgresql" "PostgreSQL service enable"
    
    # Start and enable Redis
    silent_exec "systemctl start redis-server" "Redis service start"
    silent_exec "systemctl enable redis-server" "Redis service enable"
    
    # Verify Redis is running
    if ! systemctl is-active --quiet redis-server; then
        error "Redis service failed to start"
    fi
    
    log "Redis service started and enabled"
    
    # Generate random password for database user
    local db_password=$(openssl rand -base64 32)
    
    # Create database and user
    sudo -u postgres psql << EOF
DROP DATABASE IF EXISTS $DB_NAME;
DROP USER IF EXISTS $DB_USER;
CREATE USER $DB_USER WITH PASSWORD '$db_password';
CREATE DATABASE $DB_NAME OWNER $DB_USER;
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
\q
EOF
    
    # Generate secure keys
    local secret_key=$(openssl rand -base64 64 | tr -d '\n')
    local jwt_secret_key=$(openssl rand -base64 64 | tr -d '\n')
    
    # Save database credentials and server configuration
    cat > "$INSTALL_DIR/.env" << EOF
# Database Configuration
DATABASE_URL=postgresql://$DB_USER:$db_password@localhost:5432/$DB_NAME

# Security Configuration
SECRET_KEY=$secret_key
JWT_SECRET_KEY=$jwt_secret_key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Application Configuration
BACKEND_HOST=0.0.0.0
BACKEND_PORT=$BACKEND_PORT
FRONTEND_PORT=$FRONTEND_PORT
DEBUG=false
LOG_LEVEL=INFO

# Server Configuration
SERVER_IP=$SERVER_IP
DOMAIN_NAME=$DOMAIN_NAME
VITE_API_URL=https://$SERVER_IP
ALLOWED_HOSTS=localhost,127.0.0.1,$SERVER_IP$(if [[ -n "$DOMAIN_NAME" ]]; then echo ",$DOMAIN_NAME"; fi),*

# BIND9 Configuration
BIND_CONFIG_DIR=/etc/bind
BIND_ZONES_DIR=/etc/bind/zones
BIND_RPZ_DIR=/etc/bind/rpz
BIND_SERVICE_NAME=bind9

# Monitoring Configuration
MONITORING_ENABLED=true
MONITORING_INTERVAL=60
HEALTH_CHECK_INTERVAL=300

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=100

# 2FA Configuration
TOTP_ISSUER_NAME="Hybrid DNS Server"
TOTP_VALID_WINDOW=1

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Backup Configuration
BACKUP_ENABLED=true
BACKUP_RETENTION_DAYS=30
BACKUP_SCHEDULE="0 2 * * *"

# Threat Intelligence
THREAT_FEED_UPDATE_INTERVAL=3600
EOF
    
    chown "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR/.env"
    chmod 600 "$INSTALL_DIR/.env"
    
    success "Database configured"
}

download_application() {
    info "Downloading application files..."
    
    # Create temporary directory for download
    local temp_dir=$(mktemp -d)
    cd "$temp_dir"
    
    # Download the latest release or main branch
    if ! silent_exec "wget -q 'https://github.com/mr-wolf-gb/hybrid-dns-server/archive/refs/heads/main.zip' -O hybrid-dns-server.zip" "GitHub download"; then
        error "Failed to download application files from GitHub"
    fi
    
    # Extract files
    if ! silent_exec "unzip -q hybrid-dns-server.zip" "File extraction"; then
        error "Failed to extract application files"
    fi
    
    # Move files to installation directory
    silent_exec "mkdir -p '$INSTALL_DIR'" "Installation directory creation"
    silent_exec "cp -r hybrid-dns-server-main/* '$INSTALL_DIR/'" "File installation"
    
    # Clean up
    cd /
    rm -rf "$temp_dir"
    
    success "Application files downloaded"
}

install_application() {
    info "Installing Hybrid DNS Server application..."
    
    # Download application files if not already present
    if [[ ! -d "$INSTALL_DIR/backend" ]] || [[ ! -d "$INSTALL_DIR/frontend" ]] || [[ ! -d "$INSTALL_DIR/bind9" ]]; then
        download_application
    fi
    
    # Set ownership and basic permissions
    chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
    # Ensure directories are accessible by nginx (www-data needs execute permission on directories)
    chmod 755 "$INSTALL_DIR"
    find "$INSTALL_DIR" -type d -exec chmod 755 {} \;
    
    # Install Python dependencies
    info "Installing Python dependencies..."
    if ! sudo -u "$SERVICE_USER" bash << EOF >> "$LOG_FILE" 2>&1
cd "$INSTALL_DIR/backend"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# Verify critical dependencies
python -c "import fastapi; print('FastAPI:', fastapi.__version__)"
python -c "import sqlalchemy; print('SQLAlchemy:', sqlalchemy.__version__)"
python -c "import uvicorn; print('Uvicorn installed successfully')"
EOF
    then
        error "Python dependencies installation failed. Check $LOG_FILE for details."
    fi
    
    # Verify virtual environment was created successfully
    if [[ ! -f "$INSTALL_DIR/backend/venv/bin/python" ]]; then
        error "Python virtual environment creation failed"
    fi
    
    success "Python dependencies installed"
    
    # Configure frontend environment
    log "Configuring frontend environment..."
    if ! sudo -u "$SERVICE_USER" bash << EOF >> "$LOG_FILE" 2>&1
cd "$INSTALL_DIR/frontend"
echo "VITE_API_URL=https://$SERVER_IP" > .env
echo "VITE_API_URL=https://$SERVER_IP" > .env.production
EOF
    then
        error "Frontend environment configuration failed"
    fi
    
    # Validate vite.config.ts syntax
    log "Validating Vite configuration..."
    if [[ -f "$INSTALL_DIR/frontend/vite.config.ts" ]]; then
        # Basic syntax check - ensure the file has proper structure
        if ! grep -q "export default defineConfig" "$INSTALL_DIR/frontend/vite.config.ts"; then
            warning "vite.config.ts may have syntax issues"
        fi
    else
        warning "vite.config.ts not found, frontend build may fail"
    fi
    
    # Install Node.js dependencies and build frontend
    info "Building frontend application..."
    
    # Clean any existing build artifacts
    sudo -u "$SERVICE_USER" rm -rf "$INSTALL_DIR/frontend/node_modules" "$INSTALL_DIR/frontend/package-lock.json" "$INSTALL_DIR/frontend/dist" 2>/dev/null || true
    
    # Set npm configuration for better compatibility
    sudo -u "$SERVICE_USER" bash -c "cd '$INSTALL_DIR/frontend' && npm config set fund false && npm config set audit false" >> "$LOG_FILE" 2>&1
    
    # Install with legacy peer deps for better compatibility
    if ! sudo -u "$SERVICE_USER" bash -c "cd '$INSTALL_DIR/frontend' && npm install --legacy-peer-deps --no-audit --no-fund" >> "$LOG_FILE" 2>&1; then
        log "npm install with legacy-peer-deps failed, trying without..."
        if ! sudo -u "$SERVICE_USER" bash -c "cd '$INSTALL_DIR/frontend' && npm install --no-audit --no-fund" >> "$LOG_FILE" 2>&1; then
            error "Failed to install frontend dependencies. Check $LOG_FILE for details."
        fi
    fi
    
    # Build the application
    export NODE_OPTIONS="--max-old-space-size=4096"
    
    if ! sudo -u "$SERVICE_USER" bash -c "cd '$INSTALL_DIR/frontend' && NODE_OPTIONS='--max-old-space-size=4096' npm run build" >> "$LOG_FILE" 2>&1; then
        log "Frontend build failed, trying with legacy OpenSSL..."
        if ! sudo -u "$SERVICE_USER" bash -c "cd '$INSTALL_DIR/frontend' && NODE_OPTIONS='--max-old-space-size=4096 --openssl-legacy-provider' npm run build" >> "$LOG_FILE" 2>&1; then
            error "Frontend build failed. Check $LOG_FILE for details."
        fi
    fi
    
    # Verify build output
    if [[ ! -f "$INSTALL_DIR/frontend/dist/index.html" ]]; then
        error "Frontend build completed but dist/index.html not found"
    fi
    
    success "Frontend build completed"
    
    # Fix permissions for nginx to access frontend files
    log "Setting proper permissions for web files..."
    if [[ -d "$INSTALL_DIR/frontend/dist" ]]; then
        # Set proper ownership and permissions for nginx access
        silent_exec "chown -R '$SERVICE_USER:www-data' '$INSTALL_DIR/frontend/dist'" "Frontend file ownership"
        silent_exec "find '$INSTALL_DIR/frontend/dist' -type d -exec chmod 755 {} \\;" "Frontend directory permissions"
        silent_exec "find '$INSTALL_DIR/frontend/dist' -type f -exec chmod 644 {} \\;" "Frontend file permissions"
        silent_exec "chmod 755 '$INSTALL_DIR/frontend'" "Frontend parent directory permissions"
        
        log "Frontend file permissions set correctly"
    else
        error "Frontend dist directory not found - frontend build failed"
    fi
    
    success "Application installed"
}

configure_bind9() {
    info "Configuring BIND9..."
    
    # Backup original configuration
    silent_exec "cp /etc/bind/named.conf /etc/bind/named.conf.backup" "BIND9 config backup"
    silent_exec "cp /etc/bind/named.conf.options /etc/bind/named.conf.options.backup" "BIND9 options backup"
    silent_exec "cp /etc/bind/named.conf.local /etc/bind/named.conf.local.backup" "BIND9 local config backup"
    
    # Copy our BIND9 configuration
    silent_exec "cp '$INSTALL_DIR/bind9/named.conf.options' /etc/bind/" "BIND9 options copy"
    silent_exec "cp '$INSTALL_DIR/bind9/named.conf.local' /etc/bind/" "BIND9 local config copy"
    
    # Validate that zones.conf is not included in both named.conf and named.conf.local
    info "Validating BIND9 configuration for duplicate includes..."
    
    main_has_zones=$(($(grep -c 'include "/etc/bind/zones.conf"' /etc/bind/named.conf 2>/dev/null || echo "0")))
    local_has_zones=$(($(grep -c 'include "/etc/bind/zones.conf"' /etc/bind/named.conf.local 2>/dev/null || echo "0")))
    
    if [[ "$main_has_zones" -gt 0 && "$local_has_zones" -gt 0 ]]; then
        warning "Detected duplicate zones.conf includes - fixing automatically"
        # Remove the include from named.conf.local and comment it out
        sed -i 's|include "/etc/bind/zones.conf";|// REMOVED DUPLICATE: include "/etc/bind/zones.conf";|g' /etc/bind/named.conf.local
        success "Fixed duplicate zones.conf include in named.conf.local"
    elif [[ "$main_has_zones" -eq 0 && "$local_has_zones" -eq 0 ]]; then
        # Add include to named.conf if it's missing
        if ! grep -q 'include "/etc/bind/zones.conf"' /etc/bind/named.conf; then
            echo 'include "/etc/bind/zones.conf";' >> /etc/bind/named.conf
            success "Added zones.conf include to named.conf"
        fi
    fi
    
    # Create clean zones.conf to prevent duplicate zone issues
    cat > /etc/bind/zones.conf << 'EOF'
//
// Dynamic Zones Configuration
// This file is automatically managed by the Hybrid DNS Server web interface
// Do not edit manually - changes will be overwritten
//
// Generated at: Installation
// Configuration version: 1.0
//

// === AUTHORITATIVE ZONES SECTION ===
// Managed via Web Interface
// Local zones hosted on this server
// (Zones will be populated automatically when created via web interface)

// Last updated: Installation (managed by web interface)
// Total zones configured: 0
EOF
    
    # Create forwarders.conf
    cat > /etc/bind/forwarders.conf << 'EOF'
//
// Forwarders Configuration
// This file is automatically managed by the Hybrid DNS Server web interface
// Do not edit manually - changes will be overwritten
//

// No forwarders configured
EOF
    
    # Create directories with proper permissions
    silent_exec "mkdir -p /etc/bind/zones /etc/bind/rpz /var/log/bind /etc/bind/backups" "BIND9 directories creation"
    silent_exec "mkdir -p /var/lib/bind/zones /var/lib/bind/rpz" "BIND9 data directories creation"
    
    # Create RPZ policy file
    cat > /etc/bind/rpz-policy.conf << 'EOF'
// Response Policy Zone (RPZ) Configuration
// Generated automatically by Hybrid DNS Server
// This file will be managed by the web interface

response-policy {
    // RPZ zones will be added here by the web interface
    // Default empty configuration
} qname-wait-recurse no;

// RPZ Configuration Summary:
// Enabled: false (will be enabled when policies are configured)
// Break DNSSEC: false
// Max Policy TTL: 300
// QName Wait Recurse: false
EOF
    
    # Copy zone files
    silent_exec "cp -r '$INSTALL_DIR/bind9/zones/'* /etc/bind/zones/" "Zone files copy"
    silent_exec "cp -r '$INSTALL_DIR/bind9/rpz/'* /etc/bind/rpz/" "RPZ files copy"
    
    # Fix zone files that don't end with newlines
    silent_exec "find /etc/bind/zones -name 'db.*' -exec sh -c 'echo \"\" >> \"\$1\"' _ {} \\;" "Zone files newline fix"
    silent_exec "find /etc/bind/rpz -name 'db.*' -exec sh -c 'echo \"\" >> \"\$1\"' _ {} \\;" "RPZ files newline fix"
    
    # Set comprehensive permissions - dns-server user owns files, bind group has access
    silent_exec "chown -R '$SERVICE_USER:bind' /etc/bind/" "BIND9 root ownership"
    silent_exec "chown -R '$SERVICE_USER:bind' /etc/bind/zones" "Zone files ownership"
    silent_exec "chown -R '$SERVICE_USER:bind' /etc/bind/rpz" "RPZ files ownership"
    silent_exec "chown -R bind:bind /var/lib/bind/" "BIND9 data ownership (BIND9 internal)"
    silent_exec "chown -R bind:bind /var/log/bind" "BIND9 log ownership (BIND9 writes logs)"
    silent_exec "chown -R '$SERVICE_USER:bind' /etc/bind/backups" "BIND9 backup ownership"
    
    # Allow service user to manage BIND9 files
    silent_exec "usermod -a -G bind '$SERVICE_USER'" "Adding service user to bind group"
    
    # Set directory permissions
    silent_exec "chmod 775 /etc/bind/zones" "Zone directory permissions"
    silent_exec "chmod 775 /etc/bind/rpz" "RPZ directory permissions"
    silent_exec "chmod 755 /var/log/bind" "BIND9 log permissions"
    silent_exec "chmod 775 /etc/bind/backups" "BIND9 backup permissions"
    
    # Set file permissions
    silent_exec "chmod 644 /etc/bind/*.conf" "BIND9 config permissions"
    chmod 644 /etc/bind/*.key 2>/dev/null || true
    chmod 664 /etc/bind/zones/db.* 2>/dev/null || true
    chmod 664 /etc/bind/rpz/db.* 2>/dev/null || true
    
    # Create forwarders.conf with proper permissions for backend service
    silent_exec "touch /etc/bind/forwarders.conf" "Create forwarders.conf"
    silent_exec "chown '$SERVICE_USER:bind' /etc/bind/forwarders.conf" "Set forwarders.conf ownership"
    silent_exec "chmod 664 /etc/bind/forwarders.conf" "Set forwarders.conf permissions"
    
    # Ensure backend service user can write to BIND config files
    silent_exec "chmod g+w /etc/bind" "Enable group write on /etc/bind"
    silent_exec "find /etc/bind -type d -exec chmod g+s {} \\;" "Set setgid on BIND directories"
    
    # Create backup subdirectories with proper permissions
    silent_exec "mkdir -p /etc/bind/backups/zone_file /etc/bind/backups/rpz_file /etc/bind/backups/configuration /etc/bind/backups/full_config" "Backup subdirectories creation"
    silent_exec "chown -R '$SERVICE_USER:bind' /etc/bind/backups" "Backup subdirectories ownership"
    silent_exec "chmod -R 775 /etc/bind/backups" "Backup subdirectories permissions"
    
    # Fix AppArmor profile if it exists (Ubuntu 24.04 specific)
    if [[ -f /etc/apparmor.d/usr.sbin.named ]]; then
    log "Updating AppArmor profile for BIND9..."
    
    # Add necessary permissions to AppArmor profile
    if ! grep -q "/var/log/bind/" /etc/apparmor.d/usr.sbin.named; then
        # Create a backup of the original profile
        cp /etc/apparmor.d/usr.sbin.named /etc/apparmor.d/usr.sbin.named.backup
        
        # Create a temporary file with the additions
        cat > /tmp/apparmor_additions << 'EOF'
  # Additional permissions for Hybrid DNS Server
  /var/log/bind/ rw,
  /var/log/bind/** rw,
  /etc/bind/zones/ rw,
  /etc/bind/zones/** rw,
  /etc/bind/rpz/ rw,
  /etc/bind/rpz/** rw,
  /etc/bind/backups/ rw,
  /etc/bind/backups/** rw,
EOF
            
            # Insert rules just before the final closing brace
            awk '
                BEGIN { added=0 }
                /^}$/ && !added {
                    while ((getline line < "/tmp/apparmor_additions") > 0) {
                        print line
                    }
                    close("/tmp/apparmor_additions")
                    added=1
                }
                { print }
            ' /etc/apparmor.d/usr.sbin.named > /tmp/usr.sbin.named.new
                    
            # Validate the new profile syntax
            if apparmor_parser -Q /tmp/usr.sbin.named.new; then
                # Syntax is valid, replace the original
                mv /tmp/usr.sbin.named.new /etc/apparmor.d/usr.sbin.named
                
                # Reload AppArmor profile
                if apparmor_parser -r /etc/apparmor.d/usr.sbin.named >> "$LOG_FILE" 2>&1; then
                    log "AppArmor profile updated successfully"
                else
                    warning "Could not reload AppArmor profile - restoring backup"
                    mv /etc/apparmor.d/usr.sbin.named.backup /etc/apparmor.d/usr.sbin.named
                fi
            else
                warning "AppArmor profile syntax validation failed - keeping original profile"
                rm -f /tmp/usr.sbin.named.new
            fi
                
            # Clean up temporary files
            rm -f /tmp/apparmor_additions
        else
            log "AppArmor profile already contains required permissions"
        fi
    else
        log "AppArmor profile for BIND9 not found - skipping AppArmor configuration"
    fi
    
    # Fix statistics-channels configuration issue (remove problematic CIDR line)
    sed -i '/inet 192\.168\.0\.0\/16 port 8053 allow { 192\.168\.0\.0\/16; };/d' /etc/bind/named.conf.options
    
    # Remove duplicate zone definitions that conflict with default-zones
    sed -i '/^\/\/ ROOT HINTS/,$d' /etc/bind/named.conf.local
    
    # Temporarily disable logging configuration to avoid permission issues
    sed -i '/^\/\/ Logging Configuration/,/^};/s/^/\/\/ /' /etc/bind/named.conf.options
    
    # Update main configuration to include zones.conf
    # Note: zones.conf is included here in named.conf, not in named.conf.local to avoid duplicates
    if ! grep -q "include \"/etc/bind/zones.conf\";" /etc/bind/named.conf; then
        echo 'include "/etc/bind/zones.conf";' >> /etc/bind/named.conf
        log "Added zones.conf include to named.conf"
    fi
    
    # Create symlinks for BIND9 binaries to ensure they're in PATH
    log "Creating BIND9 binary symlinks..."
    for binary in named rndc named-checkconf named-checkzone; do
        if [[ -f /usr/sbin/$binary ]] && [[ ! -f /usr/bin/$binary ]]; then
            ln -sf /usr/sbin/$binary /usr/bin/$binary
            log "Created symlink for $binary"
        fi
    done
    
    # Final validation: Check for duplicate includes one more time
    info "Performing final BIND9 configuration validation..."
    
    main_zones_count=$(($(grep -c 'include "/etc/bind/zones.conf"' /etc/bind/named.conf 2>/dev/null || echo "0")))
    local_zones_count=$(($(grep -c 'include "/etc/bind/zones.conf"' /etc/bind/named.conf.local 2>/dev/null || echo "0")))
    
    if [[ "$main_zones_count" -gt 1 ]]; then
        error "Multiple zones.conf includes found in named.conf"
    elif [[ "$local_zones_count" -gt 0 ]]; then
        error "zones.conf include found in named.conf.local (should only be in named.conf)"
    elif [[ "$main_zones_count" -eq 0 ]]; then
        error "zones.conf include not found in named.conf"
    fi
    
    success "BIND9 include validation passed"
    
    # Test configuration
    if named-checkconf >> "$LOG_FILE" 2>&1; then
        success "BIND9 configuration is valid"
    else
        error "BIND9 configuration is invalid - check $LOG_FILE for details"
    fi
    
    # Start BIND9 (handle different service names and Ubuntu 24.04 specifics)
    # First determine the correct service name
    if systemctl list-unit-files | grep -q "^named.service"; then
        BIND_SERVICE="named"
    elif systemctl list-unit-files | grep -q "^bind9.service"; then
        BIND_SERVICE="bind9"
    else
        # Check for actual service files, not aliases
        if [[ -f /lib/systemd/system/named.service ]]; then
            BIND_SERVICE="named"
        elif [[ -f /lib/systemd/system/bind9.service ]]; then
            BIND_SERVICE="bind9"
        else
            # Default to named for most distributions
            BIND_SERVICE="named"
        fi
    fi
    
    log "Using BIND9 service name: $BIND_SERVICE"
    
    # Enable and start the service
    if systemctl enable $BIND_SERVICE >> "$LOG_FILE" 2>&1; then
        log "BIND9 service enabled successfully"
    else
        log "Could not enable BIND9 service - it may be an alias or masked"
        # Try to unmask if it's masked
        systemctl unmask $BIND_SERVICE >> "$LOG_FILE" 2>&1 || true
        # Try enabling again
        systemctl enable $BIND_SERVICE >> "$LOG_FILE" 2>&1 || log "BIND9 service enable failed - will try to start anyway"
    fi
    
    # Start the service
    if systemctl restart $BIND_SERVICE >> "$LOG_FILE" 2>&1; then
        log "BIND9 service started successfully"
    else
        log "Failed to start $BIND_SERVICE, trying alternative service names..."
        # Try alternative service names
        for service in named bind9; do
            if [[ "$service" != "$BIND_SERVICE" ]]; then
                if systemctl restart $service >> "$LOG_FILE" 2>&1; then
                    BIND_SERVICE="$service"
                    log "BIND9 started successfully as $service"
                    break
                fi
            fi
        done
    fi
    
    # Wait for service to start
    sleep 3
    
    # Check if BIND9 is running
    if systemctl is-active --quiet $BIND_SERVICE; then
        success "BIND9 started successfully"
    elif systemctl is-active --quiet named; then
        success "BIND9 (named) started successfully"
        BIND_SERVICE="named"
    elif systemctl is-active --quiet bind9; then
        success "BIND9 started successfully"
        BIND_SERVICE="bind9"
    else
        warning "BIND9 failed to start, checking logs..."
        journalctl -u $BIND_SERVICE --no-pager -n 10 >> "$LOG_FILE" 2>&1
        error "BIND9 failed to start - check $LOG_FILE for details"
    fi
    
    # Create RPZ policy configuration file
    info "Creating RPZ policy configuration..."
    cat > /etc/bind/rpz-policy.conf << 'EOF'
// Response Policy Zone (RPZ) Configuration
// Generated automatically by Hybrid DNS Server Installation
// This file will be managed by the web interface

response-policy {
    // RPZ zones will be added here by the web interface
    // Default empty configuration
} qname-wait-recurse no;

// RPZ Configuration Summary:
// Enabled: false (will be enabled when policies are configured)
// Break DNSSEC: false
// Max Policy TTL: 300
// QName Wait Recurse: false
EOF
    
    silent_exec "chown '$SERVICE_USER:bind' /etc/bind/rpz-policy.conf" "RPZ policy file ownership"
    silent_exec "chmod 664 /etc/bind/rpz-policy.conf" "RPZ policy file permissions"
    
    # Test DNS resolution
    log "Testing DNS resolution..."
    if dig @localhost google.com +short >> "$LOG_FILE" 2>&1; then
        log "DNS resolution test passed"
    else
        warning "DNS resolution test failed - may need manual configuration"
    fi
    
    success "BIND9 configured"
}

setup_nginx() {
    info "Configuring Nginx..."
    
    # Verify frontend files exist before configuring nginx
    if [[ ! -f "$INSTALL_DIR/frontend/dist/index.html" ]]; then
        error "Frontend files not found at $INSTALL_DIR/frontend/dist/index.html. Please ensure frontend build completed successfully."
    fi
    
    # Generate SSL certificate (self-signed for now)
    silent_exec "mkdir -p /etc/nginx/ssl" "SSL directory creation"
    local cert_cn="$SERVER_IP"
    if [[ -n "$DOMAIN_NAME" ]]; then
        cert_cn="$DOMAIN_NAME"
    fi
    
    silent_exec "openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /etc/nginx/ssl/dns-server.key -out /etc/nginx/ssl/dns-server.crt -subj '/C=US/ST=State/L=City/O=Hybrid DNS Server/CN=$cert_cn'" "SSL certificate generation"
    
    # Create Nginx configuration with dynamic server name
    local server_name="_"
    if [[ -n "$DOMAIN_NAME" ]]; then
        server_name="$DOMAIN_NAME"
    fi
    
    cat > "$NGINX_AVAILABLE/hybrid-dns-server" << EOF
# Hybrid DNS Server Nginx Configuration

# Rate limiting
limit_req_zone \$binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone \$binary_remote_addr zone=login:10m rate=5r/m;

# Upstream backend
upstream backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

# HTTP redirect to HTTPS
server {
    listen 80;
    server_name $server_name;
    return 301 https://\$host\$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name $server_name;

    # SSL Configuration
    ssl_certificate /etc/nginx/ssl/dns-server.crt;
    ssl_certificate_key /etc/nginx/ssl/dns-server.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin";
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; font-src 'self' data: https:; img-src 'self' data: https:; connect-src 'self'";

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/javascript
        application/xml+rss
        application/json;

    # Frontend static files
    location / {
        root /opt/hybrid-dns-server/frontend/dist;
        try_files \$uri \$uri/ /index.html;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # API endpoints (HTTP + WebSocket)
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        
        proxy_pass http://backend;
        proxy_http_version 1.1;
        # Upgrade when header present; keep-alive otherwise
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        
        # Timeouts (WS needs long read timeout)
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 3600s;
    }

    # Explicit WebSocket path for extra safety
    location /api/websocket/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    # Login rate limiting
    location /api/auth/login {
        limit_req zone=login burst=5 nodelay;
        
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
EOF
    
    # Enable site
    silent_exec "ln -sf '$NGINX_AVAILABLE/hybrid-dns-server' '$NGINX_ENABLED/'" "Nginx site enable"
    
    # Remove default site
    silent_exec "rm -f '$NGINX_ENABLED/default'" "Default site removal"
    
    # Test configuration
    if nginx -t >> "$LOG_FILE" 2>&1; then
        log "Nginx configuration is valid"
    else
        error "Nginx configuration is invalid. Check $LOG_FILE for details."
    fi
    
    # Restart Nginx
    silent_exec "systemctl restart nginx" "Nginx restart"
    silent_exec "systemctl enable nginx" "Nginx enable"
    
    # Verify nginx can access frontend files
    log "Verifying nginx can access frontend files..."
    if sudo -u www-data test -r "$INSTALL_DIR/frontend/dist/index.html"; then
        log "Frontend files are accessible by nginx"
    else
        error "Frontend files are not accessible by nginx. Check permissions manually."
    fi
    
    success "Nginx configured"
}

create_systemd_services() {
    info "Creating systemd services..."
    
    # Determine the correct BIND service name for systemd dependencies
    local bind_service_name="named.service"
    if systemctl list-unit-files | grep -q "^bind9.service"; then
        bind_service_name="bind9.service"
    elif [[ -f /lib/systemd/system/bind9.service ]]; then
        bind_service_name="bind9.service"
    fi
    
    # Backend service
    cat > /etc/systemd/system/hybrid-dns-backend.service << EOF
[Unit]
Description=Hybrid DNS Server Backend
After=network.target postgresql.service $bind_service_name
Wants=postgresql.service $bind_service_name
Requires=network.target

[Service]
Type=exec
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR/backend
Environment=PATH=$INSTALL_DIR/backend/venv/bin
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$INSTALL_DIR/backend/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port $BACKEND_PORT
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=hybrid-dns-backend

# Security settings
NoNewPrivileges=no
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=$INSTALL_DIR /etc/bind /var/log/bind /tmp
PrivateTmp=yes
PrivateDevices=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes

[Install]
WantedBy=multi-user.target
EOF

    # BIND9 reload service
    cat > /etc/systemd/system/bind9-reload.service << EOF
[Unit]
Description=BIND9 Configuration Reload Service
Documentation=man:named(8)
After=$bind_service_name
Requires=$bind_service_name

[Service]
Type=oneshot
User=bind
Group=bind
ExecStart=/usr/sbin/rndc reload
RemainAfterExit=no
TimeoutSec=30

[Install]
WantedBy=multi-user.target
EOF

    # BIND9 restart service
    cat > /etc/systemd/system/bind9-restart.service << EOF
[Unit]
Description=BIND9 Service Restart
Documentation=man:named(8)
After=$bind_service_name
Requires=$bind_service_name

[Service]
Type=oneshot
ExecStart=/bin/systemctl restart $bind_service_name
RemainAfterExit=no
TimeoutSec=60

[Install]
WantedBy=multi-user.target
EOF

    # Monitoring service - Use the existing monitoring script
    cat > /etc/systemd/system/hybrid-dns-monitor.service << EOF
[Unit]
Description=Hybrid DNS Server Monitoring
After=network.target hybrid-dns-backend.service $bind_service_name
Wants=hybrid-dns-backend.service $bind_service_name
Requires=network.target

[Service]
Type=exec
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR/monitoring
Environment=PATH=$INSTALL_DIR/backend/venv/bin
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$INSTALL_DIR/backend/venv/bin/python $INSTALL_DIR/monitoring/monitor.py
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal
SyslogIdentifier=hybrid-dns-monitor

# Security settings
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=$INSTALL_DIR /var/log/bind /tmp
PrivateTmp=yes
PrivateDevices=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes

[Install]
WantedBy=multi-user.target
EOF

    # Create backup script
    mkdir -p $INSTALL_DIR/scripts
    cat > $INSTALL_DIR/scripts/backup.sh << 'EOF'
#!/bin/bash

# Hybrid DNS Server Backup Script
set -e

# Load environment variables
if [ -f "/opt/hybrid-dns-server/.env" ]; then
    source /opt/hybrid-dns-server/.env
fi

INSTALL_DIR="/opt/hybrid-dns-server"
BACKUP_DIR="$INSTALL_DIR/backups/$(date +%Y-%m-%d)"

echo "Starting backup process..."
mkdir -p "$BACKUP_DIR"

# Backup database
if [ -n "$DATABASE_URL" ]; then
    pg_dump "$DATABASE_URL" > "$BACKUP_DIR/database.sql"
    echo "Database backup completed"
fi

# Backup BIND configuration
if [ -d "/etc/bind" ]; then
    tar -czf "$BACKUP_DIR/bind-config.tar.gz" -C /etc bind/
    echo "BIND configuration backup completed"
fi

# Backup application configuration
if [ -f "$INSTALL_DIR/.env" ]; then
    cp "$INSTALL_DIR/.env" "$BACKUP_DIR/"
    echo "Application configuration backup completed"
fi

# Clean old backups (keep 30 days)
find "$INSTALL_DIR/backups" -type d -mtime +30 -exec rm -rf {} \; 2>/dev/null || true
echo "Old backups cleaned"

echo "Backup completed: $BACKUP_DIR"
EOF

    chmod +x $INSTALL_DIR/scripts/backup.sh

    # Backup service
    cat > /etc/systemd/system/hybrid-dns-backup.service << EOF
[Unit]
Description=Hybrid DNS Server Backup
After=network.target postgresql.service

[Service]
Type=oneshot
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$INSTALL_DIR/scripts/backup.sh
StandardOutput=journal
StandardError=journal
SyslogIdentifier=hybrid-dns-backup

[Install]
WantedBy=multi-user.target
EOF

    # Backup timer
    cat > /etc/systemd/system/hybrid-dns-backup.timer << EOF
[Unit]
Description=Hybrid DNS Server Backup Timer
Requires=hybrid-dns-backup.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
EOF

    # Install BIND9 restart helper script
    info "Installing BIND9 management helper script..."
    cp "$INSTALL_DIR/scripts/restart-bind9.sh" /usr/local/bin/restart-bind9
    chmod 755 /usr/local/bin/restart-bind9
    chown root:bind /usr/local/bin/restart-bind9
    
    # Install polkit rules for dns-server user to control BIND9 services
    info "Installing polkit rules for BIND9 management..."
    mkdir -p /etc/polkit-1/rules.d
    cat > /etc/polkit-1/rules.d/10-dns-server.rules << 'EOF'
// Allow dns-server user to control BIND9 related services
polkit.addRule(function(action, subject) {
    if ((action.id == "org.freedesktop.systemd1.manage-units" ||
         action.id == "org.freedesktop.systemd1.manage-unit-files") &&
        subject.user == "dns-server") {
        
        // Allow control of BIND9 related services
        if (action.lookup("unit") == "bind9.service" ||
            action.lookup("unit") == "named.service" ||
            action.lookup("unit") == "bind9-reload.service" ||
            action.lookup("unit") == "bind9-restart.service") {
            return polkit.Result.YES;
        }
    }
});

// Allow dns-server user to reload BIND9 configuration
polkit.addRule(function(action, subject) {
    if (action.id == "org.freedesktop.systemd1.manage-units" &&
        subject.user == "dns-server" &&
        (action.lookup("verb") == "start" || 
         action.lookup("verb") == "restart" ||
         action.lookup("verb") == "reload")) {
        
        var unit = action.lookup("unit");
        if (unit == "bind9-reload.service" || unit == "bind9-restart.service") {
            return polkit.Result.YES;
        }
    }
});
EOF
    chmod 644 /etc/polkit-1/rules.d/10-dns-server.rules
    
    # Install sudoers configuration as fallback for systems without polkit
    info "Installing sudoers configuration for BIND9 management (fallback)..."
    cat > /etc/sudoers.d/dns-server << 'EOF'
# Allow dns-server user to manage BIND9 service without password
dns-server ALL=(ALL) NOPASSWD: /usr/local/bin/restart-bind9
dns-server ALL=(ALL) NOPASSWD: /usr/bin/systemctl start bind9
dns-server ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop bind9
dns-server ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart bind9
dns-server ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload bind9
dns-server ALL=(ALL) NOPASSWD: /usr/bin/systemctl status bind9
dns-server ALL=(ALL) NOPASSWD: /usr/bin/systemctl start bind9-reload.service
dns-server ALL=(ALL) NOPASSWD: /usr/bin/systemctl start bind9-restart.service
dns-server ALL=(ALL) NOPASSWD: /usr/sbin/rndc *
EOF
    chmod 440 /etc/sudoers.d/dns-server
    
    # Reload systemd and enable services
    silent_exec "systemctl daemon-reload" "Systemd daemon reload"
    silent_exec "systemctl enable hybrid-dns-backend.service" "Backend service enable"
    silent_exec "systemctl enable hybrid-dns-monitor.service" "Monitor service enable"
    silent_exec "systemctl enable hybrid-dns-backup.timer" "Backup timer enable"
    silent_exec "systemctl enable bind9-reload.service" "BIND9 reload service enable"
    silent_exec "systemctl enable bind9-restart.service" "BIND9 restart service enable"
    
    success "Systemd services created"
}

setup_firewall() {
    info "Configuring firewall..."
    
    # Reset UFW
    silent_exec "ufw --force reset" "UFW reset"
    
    # Default policies
    silent_exec "ufw default deny incoming" "UFW default deny incoming"
    silent_exec "ufw default allow outgoing" "UFW default allow outgoing"
    
    # Allow SSH
    silent_exec "ufw allow ssh" "UFW allow SSH"
    
    # Allow HTTP/HTTPS
    silent_exec "ufw allow 80/tcp" "UFW allow HTTP"
    silent_exec "ufw allow 443/tcp" "UFW allow HTTPS"
    
    # Allow DNS
    silent_exec "ufw allow 53/tcp" "UFW allow DNS TCP"
    silent_exec "ufw allow 53/udp" "UFW allow DNS UDP"
    
    # Enable firewall
    silent_exec "ufw --force enable" "UFW enable"
    
    success "Firewall configured"
}

setup_fail2ban() {
    info "Configuring Fail2ban..."
    
    # Create custom jail for our application
    cat > /etc/fail2ban/jail.d/hybrid-dns.conf << EOF
[hybrid-dns-auth]
enabled = true
port = 443
filter = hybrid-dns-auth
logpath = /var/log/nginx/access.log
maxretry = 5
bantime = 3600
findtime = 600

[hybrid-dns-api]
enabled = true
port = 443
filter = hybrid-dns-api
logpath = /var/log/nginx/access.log
maxretry = 20
bantime = 1800
findtime = 300
EOF

    # Create filters
    cat > /etc/fail2ban/filter.d/hybrid-dns-auth.conf << EOF
[Definition]
failregex = ^<HOST> -.*"POST /api/auth/login.*" (401|403|422)
ignoreregex =
EOF

    cat > /etc/fail2ban/filter.d/hybrid-dns-api.conf << EOF
[Definition]
failregex = ^<HOST> -.*"(GET|POST|PUT|DELETE) /api/.*" (429|500|502|503)
ignoreregex =
EOF

    silent_exec "systemctl restart fail2ban" "Fail2ban restart"
    silent_exec "systemctl enable fail2ban" "Fail2ban enable"
    
    success "Fail2ban configured"
}

configure_redis_security() {
    info "Configuring Redis security..."
    
    # Backup original Redis configuration
    silent_exec "cp /etc/redis/redis.conf /etc/redis/redis.conf.backup" "Redis config backup"
    
    # Configure Redis for security
    cat >> /etc/redis/redis.conf << EOF

# Hybrid DNS Server Redis Security Configuration
bind 127.0.0.1 ::1
protected-mode yes
port 6379
timeout 300
tcp-keepalive 300
maxmemory 256mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
EOF
    
    # Restart Redis with new configuration
    silent_exec "systemctl restart redis-server" "Redis restart"
    
    # Verify Redis is still running
    if ! systemctl is-active --quiet redis-server; then
        error "Redis service failed to restart with new configuration"
    fi
    
    success "Redis security configured"
}

initialize_database() {
    info "Initializing database..."
    
    # Copy .env file to backend directory for the initialization
    silent_exec "cp '$INSTALL_DIR/.env' '$INSTALL_DIR/backend/.env'" "Backend env file copy"
    silent_exec "chown '$SERVICE_USER:$SERVICE_USER' '$INSTALL_DIR/backend/.env'" "Backend env file ownership"
    silent_exec "chmod 600 '$INSTALL_DIR/backend/.env'" "Backend env file permissions"
    
    # Reinstall requirements to ensure alembic is available
    log "Ensuring all Python dependencies are installed..."
    if ! sudo -u "$SERVICE_USER" bash << EOF >> "$LOG_FILE" 2>&1
cd "$INSTALL_DIR/backend"
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
EOF
    then
        error "Python dependencies installation failed. Check $LOG_FILE for details."
    fi
    
    # Run database initialization
    log "Running database initialization script..."
    if sudo -u "$SERVICE_USER" bash << EOF >> "$LOG_FILE" 2>&1
cd "$INSTALL_DIR/backend"
source venv/bin/activate

# Set PYTHONPATH to ensure imports work
export PYTHONPATH="\$PWD:\$PYTHONPATH"

# Initialize database tables
python scripts/database/init_db.py
EOF
    then
        log "Database tables created successfully"
    else
        warning "Database initialization script failed, but continuing..."
    fi
    
    # Alembic is no longer required; migrations handled in-app
    log "Skipping Alembic migrations (managed by application)"
    
    # Verify database initialization
    log "Verifying database health..."
    if sudo -u "$SERVICE_USER" bash -c "cd '$INSTALL_DIR/backend' && source venv/bin/activate && python -c 'import asyncio; from app.core.database import check_database_health; print(asyncio.run(check_database_health()))'" >> "$LOG_FILE" 2>&1; then
        log "Database initialization verified"
    else
        warning "Database initialization completed but verification failed"
    fi
    
    # Remove the temporary .env file from backend directory
    silent_exec "rm -f '$INSTALL_DIR/backend/.env'" "Temporary env file cleanup"
    
    success "Database initialized"
}

start_services() {
    info "Starting services..."
    
    # Start backend service first
    if systemctl start hybrid-dns-backend >> "$LOG_FILE" 2>&1; then
        log "Backend service start command executed"
    else
        warning "Backend service start command failed"
    fi
    
    # Wait a moment for backend to start
    sleep 3
    
    # Check backend service status
    if systemctl is-active --quiet hybrid-dns-backend; then
        success "Backend service is running"
    else
        warning "Backend service failed to start, checking logs..."
        journalctl -u hybrid-dns-backend --no-pager -n 20 >> "$LOG_FILE" 2>&1
        error "Failed to start backend service - check $LOG_FILE for details"
    fi
    
    # Start monitoring service
    if systemctl start hybrid-dns-monitor >> "$LOG_FILE" 2>&1; then
        log "Monitoring service start command executed"
    else
        warning "Monitoring service start command failed"
    fi
    
    # Start backup timer
    if systemctl start hybrid-dns-backup.timer >> "$LOG_FILE" 2>&1; then
        log "Backup timer started"
    else
        warning "Backup timer failed to start"
    fi
    
    # Wait a moment for services to start
    sleep 2
    
    # Final status check
    if systemctl is-active --quiet hybrid-dns-monitor; then
        log "Monitoring service is running"
    else
        warning "Monitoring service not started - check logs: journalctl -u hybrid-dns-monitor"
    fi
    
    success "Services started"
    
    # Give services a moment to fully start
    sleep 10
    
    # Check if backend is responding
    log "Testing backend API..."
    local retry_count=0
    local max_retries=30
    
    while [[ $retry_count -lt $max_retries ]]; do
        if curl -f -s "http://localhost:$BACKEND_PORT/health" >> "$LOG_FILE" 2>&1; then
            success "Backend API is responding"
            break
        else
            ((retry_count++))
            if [[ $retry_count -eq $max_retries ]]; then
                warning "Backend API not responding after $max_retries attempts"
                journalctl -u hybrid-dns-backend --no-pager -n 20 >> "$LOG_FILE" 2>&1
                warning "Backend may need manual troubleshooting - check $LOG_FILE"
            else
                sleep 2
            fi
        fi
    done
    
    # Test web interface accessibility
    log "Testing web interface..."
    if curl -f -s -k "https://localhost/health" >> "$LOG_FILE" 2>&1; then
        log "Web interface is accessible"
    else
        warning "Web interface may not be fully accessible yet"
    fi
}

create_admin_user() {
    info "Creating admin user..."
    
    # Copy .env file to backend directory for admin creation
    silent_exec "cp '$INSTALL_DIR/.env' '$INSTALL_DIR/backend/.env'" "Admin env file copy"
    silent_exec "chown '$SERVICE_USER:$SERVICE_USER' '$INSTALL_DIR/backend/.env'" "Admin env file ownership"
    silent_exec "chmod 600 '$INSTALL_DIR/backend/.env'" "Admin env file permissions"
    
    if ! sudo -u "$SERVICE_USER" bash << EOF >> "$LOG_FILE" 2>&1
cd "$INSTALL_DIR/backend"
source venv/bin/activate

# Set PYTHONPATH to ensure imports work
export PYTHONPATH="\$PWD:\$PYTHONPATH"

# Create admin user
python scripts/database/create_admin.py --username "$ADMIN_USERNAME" --password "$ADMIN_PASSWORD" --email "$ADMIN_EMAIL" --full-name "$ADMIN_FULL_NAME"
EOF
    then
        error "Admin user creation failed. Check $LOG_FILE for details."
    fi
    
    # Remove the temporary .env file from backend directory
    silent_exec "rm -f '$INSTALL_DIR/backend/.env'" "Admin env file cleanup"
    
    success "Admin user created successfully"
    log "Admin credentials: Username=$ADMIN_USERNAME, Email=$ADMIN_EMAIL"
}

import_default_threat_feeds() {
    info "Importing default threat intelligence feeds..."
    
    # Wait a moment for services to be fully ready
    sleep 5
    
    # Check if services are running before attempting import
    if ! systemctl is-active --quiet hybrid-dns-backend; then
        warning "Backend service is not running - starting it first..."
        systemctl start hybrid-dns-backend
        sleep 10
    fi
    
    # Import recommended threat feeds using the import script
    if ! sudo -u "$SERVICE_USER" bash << EOF >> "$LOG_FILE" 2>&1
cd "$INSTALL_DIR/backend"
source venv/bin/activate
source "$INSTALL_DIR/.env"

# Verify database connection first
python -c "
import sys
sys.path.insert(0, '.')
from app.core.database import get_database_session
try:
    db_gen = get_database_session()
    db = next(db_gen)
    db.close()
    print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}')
    sys.exit(1)
"

# Import the feeds
python scripts/import_default_feeds.py --import
EOF
    then
        warning "Default threat feeds import failed. You can import them manually later using:"
        warning "  cd $INSTALL_DIR/backend && source venv/bin/activate && python scripts/import_default_feeds.py --import"
        log "Threat feeds import failed - continuing with installation"
        return 0  # Don't fail the entire installation
    fi
    
    success "Default threat intelligence feeds imported successfully"
    log "Threat feeds imported: Malware Domain List, Phishing Army, Feodo Tracker, OpenPhish, Ransomware Tracker, Bambenek C2"
}

print_summary() {
    echo
    echo "================================================"
    echo "🎉 Hybrid DNS Server Installation Complete! 🎉"
    echo "================================================"
    echo
    echo "Services Status:"
    echo "• BIND9 DNS Server: $(systemctl is-active bind9)"
    echo "• Backend API: $(systemctl is-active hybrid-dns-backend)"
    echo "• Monitoring: $(systemctl is-active hybrid-dns-monitor)"
    echo "• Nginx Web Server: $(systemctl is-active nginx)"
    echo "• PostgreSQL Database: $(systemctl is-active postgresql)"
    echo "• Redis Server: $(systemctl is-active redis-server)"
    echo
    echo "Access Information:"
    if [[ -n "$DOMAIN_NAME" ]]; then
        echo "• Web Interface: https://$DOMAIN_NAME"
        echo "• API Endpoint: https://$DOMAIN_NAME/api"
        echo "• DNS Server: $SERVER_IP:53 ($DOMAIN_NAME)"
    else
        echo "• Web Interface: https://$SERVER_IP"
        echo "• API Endpoint: https://$SERVER_IP/api"
        echo "• DNS Server: $SERVER_IP:53"
    fi
    echo "• Installation Directory: $INSTALL_DIR"
    echo "• Configuration File: $INSTALL_DIR/.env"
    echo "• Log Files: /var/log/bind/, /var/log/nginx/"
    echo
    echo "Admin Login Credentials:"
    echo "• Username: $ADMIN_USERNAME"
    echo "• Email: $ADMIN_EMAIL"
    echo "• Password: [Set during installation]"
    echo
    echo "Useful Commands:"
    echo "• Check services: systemctl status hybrid-dns-backend"
    echo "• View logs: journalctl -u hybrid-dns-backend -f"
    echo "• Restart services: systemctl restart hybrid-dns-backend"
    echo "• BIND configuration: /etc/bind/"
    echo "• Manual backup: systemctl start hybrid-dns-backup"
    echo
    echo "Security:"
    echo "• Firewall (UFW): $(ufw status | head -1)"
    echo "• Fail2ban: $(systemctl is-active fail2ban)"
    echo "• SSL Certificate: Self-signed (consider using Let's Encrypt)"
    echo
    echo "Configuration:"
    echo "• Frontend API URL: https://$SERVER_IP/api"
    echo "• Backend Direct: http://localhost:$BACKEND_PORT (internal only)"
    echo "• Allowed CORS Hosts: localhost, 127.0.0.1, $SERVER_IP$(if [[ -n "$DOMAIN_NAME" ]]; then echo ", $DOMAIN_NAME"; fi)"
    echo
    echo "Quick Start:"
    echo "• Test DNS: dig @$SERVER_IP example.com"
    echo "• API Docs: https://$SERVER_IP/docs"
    echo "• WebSocket Metrics: https://$SERVER_IP/api/websocket/metrics/summary"
    echo "• Real-time Monitoring: /ws/queries, /ws/metrics, /ws/events"
    echo
    echo "Essential Commands:"
    echo "• Check services: systemctl status hybrid-dns-backend"
    echo "• View logs: journalctl -u hybrid-dns-backend -f"
    echo "• Restart services: systemctl restart hybrid-dns-backend bind9"
    echo "• BIND config check: named-checkconf"
    echo
    echo "Threat Intelligence:"
    echo "• Default feeds imported: Phishing Army, Malware Domains, OpenPhish"
    echo "• RPZ security policies: Active and ready"
    echo "• Feed management: Available in web interface"
    echo
    echo "Next Steps:"
    echo "1. Configure clients to use DNS server: $SERVER_IP:53"
    echo "2. Set up SSL certificates (Let's Encrypt recommended)"
    echo "3. Review and configure additional threat feeds"
    echo
    echo "Documentation: $INSTALL_DIR/README.md"
    echo "Support: https://github.com/mr-wolf-gb/hybrid-dns-server"
    echo
    echo "Happy DNS serving! 🚀"
}

# Show help information
show_help() {
    echo "Hybrid DNS Server Installation Script"
    echo "Usage: sudo ./install.sh [OPTIONS]"
    echo
    echo "Options:"
    echo "  --resume    Resume installation from last checkpoint"
    echo "  --fresh     Force fresh installation (ignore checkpoints)"
    echo "  --status    Check installation status"
    echo "  --help      Show this help message"
    echo
    echo "Environment Variables (optional):"
    echo "  ADMIN_USERNAME    Admin username (default: prompted)"
    echo "  ADMIN_PASSWORD    Admin password (default: prompted)"
    echo "  ADMIN_EMAIL       Admin email (default: prompted)"
    echo "  ADMIN_FULL_NAME   Admin full name (default: prompted)"
    echo
    echo "Examples:"
    echo "  sudo ./install.sh                    # Interactive installation"
    echo "  sudo ./install.sh --resume           # Resume from checkpoint"
    echo "  sudo ADMIN_USERNAME=admin ./install.sh  # Pre-set admin username"
    echo
}

# Command line argument parsing
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help|-h)
                show_help
                exit 0
                ;;
            --resume)
                if [[ -f "$CHECKPOINT_FILE" ]]; then
                    info "Resuming installation from checkpoint: $(get_checkpoint)"
                else
                    warning "No checkpoint found. Starting fresh installation."
                fi
                shift
                ;;
            --fresh)
                warning "Starting fresh installation (clearing any existing checkpoint)"
                clear_checkpoint
                shift
                ;;
            --status)
                if [[ -f "$CHECKPOINT_FILE" ]]; then
                    echo "Installation status: Incomplete"
                    echo "Last completed step: $(get_checkpoint)"
                    echo "To resume: sudo $0 --resume"
                    echo "To start fresh: sudo $0 --fresh"
                else
                    echo "Installation status: Not started or completed"
                    echo "To start: sudo $0"
                fi
                exit 0
                ;;
            --help|-h)
                echo "Hybrid DNS Server Installation Script"
                echo
                echo "Usage: $0 [OPTIONS]"
                echo
                echo "Options:"
                echo "  --resume    Resume installation from last checkpoint"
                echo "  --fresh     Start fresh installation (clear checkpoint)"
                echo "  --status    Show installation status"
                echo "  --help, -h  Show this help message"
                echo
                echo "Examples:"
                echo "  sudo $0                # Start new installation"
                echo "  sudo $0 --resume       # Resume from checkpoint"
                echo "  sudo $0 --fresh        # Force fresh start"
                echo "  sudo $0 --status       # Check status"
                exit 0
                ;;
            *)
                warning "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
}

# Prompt for admin credentials
prompt_admin_credentials() {
    echo
    echo "🔐 Admin Account Setup"
    echo "====================="
    echo "Please configure the administrator account for the DNS server:"
    echo
    
    # Username
    if [[ -z "${ADMIN_USERNAME:-}" ]]; then
        read -p "Admin Username [admin]: " input_username
        export ADMIN_USERNAME="${input_username:-admin}"
    fi
    
    # Password
    if [[ -z "${ADMIN_PASSWORD:-}" ]]; then
        while true; do
            echo -n "Admin Password: "
            read -s admin_password
            echo
            if [[ ${#admin_password} -lt 6 ]]; then
                echo "❌ Password must be at least 6 characters long"
                continue
            fi
            echo -n "Confirm Password: "
            read -s admin_password_confirm
            echo
            if [[ "$admin_password" != "$admin_password_confirm" ]]; then
                echo "❌ Passwords do not match"
                continue
            fi
            export ADMIN_PASSWORD="$admin_password"
            break
        done
    fi
    
    # Email
    if [[ -z "${ADMIN_EMAIL:-}" ]]; then
        while true; do
            read -p "Admin Email: " admin_email
            if [[ "$admin_email" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
                export ADMIN_EMAIL="$admin_email"
                break
            else
                echo "❌ Please enter a valid email address"
            fi
        done
    fi
    
    # Full Name
    if [[ -z "${ADMIN_FULL_NAME:-}" ]]; then
        read -p "Admin Full Name [System Administrator]: " input_fullname
        export ADMIN_FULL_NAME="${input_fullname:-System Administrator}"
    fi
    
    echo
    echo "✅ Admin account configured:"
    echo "   Username: $ADMIN_USERNAME"
    echo "   Email: $ADMIN_EMAIL"
    echo "   Full Name: $ADMIN_FULL_NAME"
    echo
}

# Main installation process
main() {
    echo "🚀 Hybrid DNS Server Installation Script"
    echo "========================================"
    echo "📝 Detailed logs: $LOG_FILE"
    echo
    
    # Check for previous installation
    if [[ -f "$CHECKPOINT_FILE" ]]; then
        show_resume_menu
    fi
    
    log "Starting/resuming installation at $(date)"
    
    check_root
    check_os
    check_requirements
    
    # Load server configuration if resuming
    if [[ -f "/tmp/hybrid-dns-server-config" ]]; then
        source "/tmp/hybrid-dns-server-config"
        info "Loaded server configuration from previous session"
    fi
    
    # Ensure SERVER_IP is set for fresh installations
    if [[ -z "${SERVER_IP:-}" ]]; then
        SERVER_IP=""
        DOMAIN_NAME=""
    fi
    
    local current_checkpoint=$(get_checkpoint)
    if [[ "$current_checkpoint" == "start" ]]; then
        echo "This will install and configure:"
        echo "• BIND9 DNS Server with RPZ security"
        echo "• FastAPI backend with PostgreSQL database"
        echo "• React frontend with Nginx"
        echo "• Monitoring and health checks"
        echo "• Automated backups and security"
        echo
        read -p "Continue with installation? (y/N): " -n 1 -r
        echo
        
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Installation cancelled."
            exit 0
        fi
        
        # Prompt for admin credentials only on fresh installation
        prompt_admin_credentials
    else
        info "Resuming installation from checkpoint: $current_checkpoint"
        # Load admin credentials from previous session if available
        if [[ -f "/tmp/hybrid-dns-admin-creds" ]]; then
            source "/tmp/hybrid-dns-admin-creds"
            info "Using admin credentials from previous session"
        else
            warning "Admin credentials not found from previous session, using defaults"
            export ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
            export ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin123}"
            export ADMIN_EMAIL="${ADMIN_EMAIL:-admin@localhost}"
            export ADMIN_FULL_NAME="${ADMIN_FULL_NAME:-System Administrator}"
        fi
    fi
    
    # Save admin credentials for resume functionality
    cat > "/tmp/hybrid-dns-admin-creds" << EOF
export ADMIN_USERNAME="$ADMIN_USERNAME"
export ADMIN_PASSWORD="$ADMIN_PASSWORD"
export ADMIN_EMAIL="$ADMIN_EMAIL"
export ADMIN_FULL_NAME="$ADMIN_FULL_NAME"
EOF
    
    # Installation steps with checkpoint support
    run_step "server_configured" get_server_configuration
    run_step "system_updated" update_system
    run_step "dependencies_installed" install_dependencies
    run_step "user_created" create_user
    run_step "database_setup" setup_database
    run_step "application_downloaded" download_application
    run_step "application_installed" install_application
    run_step "bind9_configured" configure_bind9
    run_step "nginx_configured" setup_nginx
    run_step "systemd_created" create_systemd_services
    run_step "firewall_configured" setup_firewall
    run_step "fail2ban_configured" setup_fail2ban
    run_step "database_initialized" initialize_database
    run_step "services_started" start_services
    run_step "admin_created" create_admin_user
    run_step "threat_feeds_imported" import_default_threat_feeds
    
    # Mark as completed and clean up
    save_checkpoint "completed"
    clear_checkpoint
    
    # Clean up temporary files
    rm -f "/tmp/hybrid-dns-admin-creds"
    rm -f "/tmp/hybrid-dns-server-config"
    
    log "Installation completed at $(date)"
    print_summary
}

# Parse command line arguments and run main function
parse_arguments "$@"
main