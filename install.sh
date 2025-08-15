#!/bin/bash

# Hybrid DNS Server Installation Script
# For Debian/Ubuntu systems
# Author: Scout AI
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
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
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
        info "Running step: $step_name"
        $step_function
        save_checkpoint "$step_name"
    else
        info "Skipping completed step: $step_name"
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
    info "Detected OS: $NAME $VERSION"
}

check_requirements() {
    info "Checking system requirements..."
    
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
    
    success "System requirements check passed"
}

update_system() {
    info "Updating system packages..."
    apt-get update -qq
    apt-get upgrade -y -qq
    success "System updated"
}

install_dependencies() {
    info "Installing system dependencies..."
    
    # Essential packages
    apt-get install -y -qq \
        curl \
        wget \
        gnupg \
        software-properties-common \
        apt-transport-https \
        ca-certificates \
        lsb-release \
        ufw \
        fail2ban \
        unzip \
        git \
        htop \
        nano \
        vim \
        sudo
    
    # BIND9 and DNS tools
    apt-get install -y -qq \
        bind9 \
        bind9utils \
        bind9-doc \
        dnsutils
    
    # PostgreSQL
    apt-get install -y -qq \
        postgresql \
        postgresql-contrib \
        libpq-dev
    
    # Python
    apt-get install -y -qq \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        build-essential
    
    # Node.js (via NodeSource)
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y -qq nodejs
    
    # Nginx
    apt-get install -y -qq nginx
    
    # Install npm (already included with Node.js)
    
    success "Dependencies installed"
}

create_user() {
    info "Creating service user..."
    
    if ! id "$SERVICE_USER" &>/dev/null; then
        useradd -r -s /bin/bash -d "$INSTALL_DIR" -m "$SERVICE_USER"
        success "User $SERVICE_USER created"
    else
        info "User $SERVICE_USER already exists"
    fi
}

setup_database() {
    info "Setting up PostgreSQL database..."
    
    # Start PostgreSQL
    systemctl start postgresql
    systemctl enable postgresql
    
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
    
    # Save database credentials
    cat > "$INSTALL_DIR/.env" << EOF
# Database Configuration
DATABASE_URL=postgresql://$DB_USER:$db_password@localhost:5432/$DB_NAME

# Security Configuration
SECRET_KEY=$(openssl rand -base64 64)
JWT_SECRET_KEY=$(openssl rand -base64 64)
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Application Configuration
BACKEND_HOST=0.0.0.0
BACKEND_PORT=$BACKEND_PORT
FRONTEND_PORT=$FRONTEND_PORT
DEBUG=false
LOG_LEVEL=INFO

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

# Backup Configuration
BACKUP_ENABLED=true
BACKUP_RETENTION_DAYS=30
BACKUP_SCHEDULE="0 2 * * *"
EOF
    
    chown "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR/.env"
    chmod 600 "$INSTALL_DIR/.env"
    
    success "Database configured"
}

download_application() {
    info "Downloading Hybrid DNS Server application..."
    
    # Create temporary directory for download
    local temp_dir=$(mktemp -d)
    cd "$temp_dir"
    
    # Download the latest release or main branch
    info "Downloading from GitHub repository..."
    if ! wget -q "https://github.com/mr-wolf-gb/hybrid-dns-server/archive/refs/heads/main.zip" -O hybrid-dns-server.zip; then
        error "Failed to download application files from GitHub"
    fi
    
    # Extract files
    if ! unzip -q hybrid-dns-server.zip; then
        error "Failed to extract application files"
    fi
    
    # Move files to installation directory
    mkdir -p "$INSTALL_DIR"
    cp -r hybrid-dns-server-main/* "$INSTALL_DIR/"
    
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
    
    # Set ownership
    chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
    
    # Install Python dependencies
    info "Installing Python dependencies..."
    sudo -u "$SERVICE_USER" bash << EOF
cd "$INSTALL_DIR/backend"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
EOF
    
    # Install Node.js dependencies and build frontend
    info "Building frontend application..."
    sudo -u "$SERVICE_USER" bash << EOF
cd "$INSTALL_DIR/frontend"
npm install
npm run build
EOF
    
    success "Application installed"
}

configure_bind9() {
    info "Configuring BIND9..."
    
    # Backup original configuration
    cp /etc/bind/named.conf /etc/bind/named.conf.backup
    cp /etc/bind/named.conf.options /etc/bind/named.conf.options.backup
    cp /etc/bind/named.conf.local /etc/bind/named.conf.local.backup
    
    # Copy our BIND9 configuration
    cp "$INSTALL_DIR/bind9/named.conf.options" /etc/bind/
    cp "$INSTALL_DIR/bind9/named.conf.local" /etc/bind/
    cp "$INSTALL_DIR/bind9/zones.conf" /etc/bind/
    
    # Create directories with proper permissions
    mkdir -p /etc/bind/zones
    mkdir -p /etc/bind/rpz
    mkdir -p /var/log/bind
    
    # Copy zone files
    cp -r "$INSTALL_DIR/bind9/zones/"* /etc/bind/zones/
    cp -r "$INSTALL_DIR/bind9/rpz/"* /etc/bind/rpz/
    
    # Fix zone files that don't end with newlines
    find /etc/bind/zones -name "db.*" -exec sh -c 'echo "" >> "$1"' _ {} \;
    find /etc/bind/rpz -name "db.*" -exec sh -c 'echo "" >> "$1"' _ {} \;
    
    # Set comprehensive permissions
    chown -R root:bind /etc/bind/
    chown -R bind:bind /etc/bind/zones
    chown -R bind:bind /etc/bind/rpz
    chown -R bind:bind /var/log/bind
    chmod 755 /etc/bind/zones
    chmod 755 /etc/bind/rpz
    chmod 755 /var/log/bind
    chmod 644 /etc/bind/*.conf
    chmod 644 /etc/bind/*.key
    chmod 644 /etc/bind/zones/db.*
    chmod 644 /etc/bind/rpz/db.*
    
    # Fix statistics-channels configuration issue (remove problematic CIDR line)
    sed -i '/inet 192\.168\.0\.0\/16 port 8053 allow { 192\.168\.0\.0\/16; };/d' /etc/bind/named.conf.options
    
    # Remove duplicate zone definitions that conflict with default-zones
    sed -i '/^\/\/ ROOT HINTS/,$d' /etc/bind/named.conf.local
    
    # Temporarily disable logging configuration to avoid permission issues
    sed -i '/^\/\/ Logging Configuration/,/^};/s/^/\/\/ /' /etc/bind/named.conf.options
    
    # Update main configuration
    if ! grep -q "include \"/etc/bind/zones.conf\";" /etc/bind/named.conf; then
        echo 'include "/etc/bind/zones.conf";' >> /etc/bind/named.conf
    fi
    
    # Test configuration
    if named-checkconf; then
        success "BIND9 configuration is valid"
    else
        error "BIND9 configuration is invalid"
    fi
    
    # Start BIND9 (handle different service names)
    if systemctl list-unit-files | grep -q "^named.service"; then
        systemctl restart named
        systemctl enable named
        BIND_SERVICE="named"
    else
        systemctl restart bind9
        # Try to enable, but don't fail if it's an alias
        systemctl enable bind9 2>/dev/null || systemctl enable named 2>/dev/null || true
        BIND_SERVICE="bind9"
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
        error "BIND9 failed to start"
    fi
    
    success "BIND9 configured"
}

setup_nginx() {
    info "Configuring Nginx..."
    
    # Generate SSL certificate (self-signed for now)
    mkdir -p /etc/nginx/ssl
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/nginx/ssl/dns-server.key \
        -out /etc/nginx/ssl/dns-server.crt \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=dns-server.local"
    
    # Create Nginx configuration
    cat > "$NGINX_AVAILABLE/hybrid-dns-server" << 'EOF'
# Hybrid DNS Server Nginx Configuration

# Rate limiting
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;

# Upstream backend
upstream backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

# HTTP redirect to HTTPS
server {
    listen 80;
    server_name _;
    return 301 https://$host$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name _;

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
        try_files $uri $uri/ /index.html;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # API endpoints
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    # Login rate limiting
    location /api/auth/login {
        limit_req zone=login burst=5 nodelay;
        
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
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
    ln -sf "$NGINX_AVAILABLE/hybrid-dns-server" "$NGINX_ENABLED/"
    
    # Remove default site
    rm -f "$NGINX_ENABLED/default"
    
    # Test configuration
    if nginx -t; then
        success "Nginx configuration is valid"
    else
        error "Nginx configuration is invalid"
    fi
    
    # Restart Nginx
    systemctl restart nginx
    systemctl enable nginx
    
    success "Nginx configured"
}

create_systemd_services() {
    info "Creating systemd services..."
    
    # Backend service
    cat > /etc/systemd/system/hybrid-dns-backend.service << EOF
[Unit]
Description=Hybrid DNS Server Backend
After=network.target postgresql.service bind9.service
Wants=postgresql.service bind9.service
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
NoNewPrivileges=yes
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

    # Monitoring service
    cat > /etc/systemd/system/hybrid-dns-monitor.service << EOF
[Unit]
Description=Hybrid DNS Server Monitoring
After=network.target hybrid-dns-backend.service
Wants=hybrid-dns-backend.service
Requires=network.target

[Service]
Type=exec
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR/backend
Environment=PATH=$INSTALL_DIR/backend/venv/bin
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=/bin/bash -c 'cd $INSTALL_DIR/backend && source venv/bin/activate && python -c "import asyncio; from app.services.monitoring_service import MonitoringService; from app.services.health_service import HealthService; asyncio.run(asyncio.gather(MonitoringService().start_monitoring(), HealthService().start_health_checks()))"'
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

    # Reload systemd and enable services
    systemctl daemon-reload
    systemctl enable hybrid-dns-backend.service
    systemctl enable hybrid-dns-monitor.service
    systemctl enable hybrid-dns-backup.timer
    
    success "Systemd services created"
}

setup_firewall() {
    info "Configuring firewall..."
    
    # Reset UFW
    ufw --force reset
    
    # Default policies
    ufw default deny incoming
    ufw default allow outgoing
    
    # Allow SSH
    ufw allow ssh
    
    # Allow HTTP/HTTPS
    ufw allow 80/tcp
    ufw allow 443/tcp
    
    # Allow DNS
    ufw allow 53/tcp
    ufw allow 53/udp
    
    # Enable firewall
    ufw --force enable
    
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

    systemctl restart fail2ban
    systemctl enable fail2ban
    
    success "Fail2ban configured"
}

initialize_database() {
    info "Initializing database..."
    
    # Copy .env file to backend directory for the initialization
    cp "$INSTALL_DIR/.env" "$INSTALL_DIR/backend/.env"
    chown "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR/backend/.env"
    chmod 600 "$INSTALL_DIR/backend/.env"
    
    sudo -u "$SERVICE_USER" bash << EOF
cd "$INSTALL_DIR/backend"
source venv/bin/activate
python init_db.py
EOF
    
    # Remove the temporary .env file from backend directory
    rm -f "$INSTALL_DIR/backend/.env"
    
    success "Database initialized"
}

start_services() {
    info "Starting services..."
    
    # Start all services
    systemctl start hybrid-dns-backend
    systemctl start hybrid-dns-monitor
    systemctl start hybrid-dns-backup.timer
    
    # Wait a moment for services to start
    sleep 5
    
    # Check service status
    if systemctl is-active --quiet hybrid-dns-backend; then
        success "Backend service started"
    else
        error "Failed to start backend service"
    fi
    
    if systemctl is-active --quiet hybrid-dns-monitor; then
        success "Monitoring service started"
    else
        warning "Monitoring service not started"
    fi
    
    success "Services started"
}

create_admin_user() {
    info "Creating admin user..."
    
    sudo -u "$SERVICE_USER" bash << EOF
cd "$INSTALL_DIR/backend"
source venv/bin/activate
export ADMIN_USERNAME="$ADMIN_USERNAME"
export ADMIN_PASSWORD="$ADMIN_PASSWORD"
export ADMIN_EMAIL="$ADMIN_EMAIL"
export ADMIN_FULL_NAME="$ADMIN_FULL_NAME"
python create_admin.py --username "$ADMIN_USERNAME" --password "$ADMIN_PASSWORD" --email "$ADMIN_EMAIL" --full-name "$ADMIN_FULL_NAME"
EOF
    
    success "Admin user created successfully"
    info "Admin credentials:"
    info "  Username: $ADMIN_USERNAME"
    info "  Email: $ADMIN_EMAIL"
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
    echo
    echo "Access Information:"
    echo "• Web Interface: https://$(hostname -I | awk '{print $1}')"
    echo "• DNS Server: $(hostname -I | awk '{print $1}'):53"
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
    echo "Next Steps:"
    echo "1. Configure your clients to use this DNS server"
    echo "2. Set up proper SSL certificates (Let's Encrypt recommended)"
    echo "3. Configure external threat feed sources"
    echo "4. Review and customize security settings"
    echo
    echo "Documentation: $INSTALL_DIR/README.md"
    echo "Support: Check the GitHub repository for issues and updates"
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
    echo
    
    # Check for previous installation
    if [[ -f "$CHECKPOINT_FILE" ]]; then
        show_resume_menu
    fi
    
    log "Starting/resuming installation at $(date)"
    
    check_root
    check_os
    check_requirements
    
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
    
    # Mark as completed and clean up
    save_checkpoint "completed"
    clear_checkpoint
    
    # Clean up temporary credentials file
    rm -f "/tmp/hybrid-dns-admin-creds"
    
    log "Installation completed at $(date)"
    print_summary
}

# Parse command line arguments and run main function
parse_arguments "$@"
main