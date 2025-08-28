#!/bin/bash

# Fix BIND9 reload issues for existing installations
# This script addresses the "no new privileges" sudo issue

set -e

INSTALL_DIR="/opt/hybrid-dns-server"
SERVICE_USER="dns-server"

echo "Fixing BIND9 reload issues..."

# Determine the correct BIND service name
bind_service_name="named.service"
if systemctl list-unit-files | grep -q "^bind9.service"; then
    bind_service_name="bind9.service"
elif [[ -f /lib/systemd/system/bind9.service ]]; then
    bind_service_name="bind9.service"
fi

echo "Detected BIND service: $bind_service_name"

# Stop the backend service temporarily
echo "Stopping backend service..."
systemctl stop hybrid-dns-backend.service || true

# Update the main backend service to allow privilege escalation
echo "Updating backend service configuration..."
cat > /etc/systemd/system/hybrid-dns-backend.service << EOF
[Unit]
Description=Hybrid DNS Server Backend API
Documentation=https://github.com/user/hybrid-dns-server
After=network.target postgresql.service
Requires=postgresql.service
Wants=hybrid-dns-monitoring.service

[Service]
Type=exec
User=dns-server
Group=dns-server
WorkingDirectory=/opt/hybrid-dns-server/backend

# Environment
Environment=DATABASE_URL=postgresql://dns_user:\${DB_PASSWORD}@localhost/hybrid_dns
Environment=SECRET_KEY=\${SECRET_KEY}
Environment=ADMIN_PASSWORD=\${ADMIN_PASSWORD}
Environment=REDIS_URL=redis://localhost:6379/0
Environment=PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# Security
NoNewPrivileges=no
PrivateTmp=yes
ProtectSystem=false
ProtectHome=yes
ReadWritePaths=/opt/hybrid-dns-server/backend/logs
ReadWritePaths=/var/log/hybrid-dns
ReadWritePaths=/etc/bind
SupplementaryGroups=bind

# Resource limits
LimitNOFILE=65536
TasksMax=4096

# Start command
ExecStart=/opt/hybrid-dns-server/backend/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 2
ExecReload=/bin/kill -HUP \$MAINPID
KillMode=mixed
Restart=on-failure
RestartSec=5
TimeoutStopSec=30

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=hybrid-dns-backend

[Install]
WantedBy=multi-user.target
EOF

# Create BIND9 reload service
echo "Creating BIND9 reload service..."
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

# Create BIND9 restart service
echo "Creating BIND9 restart service..."
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

# Install polkit rules
echo "Installing polkit rules..."
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

# Update sudoers as fallback
echo "Updating sudoers configuration..."
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

# Reload systemd and enable new services
echo "Reloading systemd and enabling services..."
systemctl daemon-reload
systemctl enable bind9-reload.service
systemctl enable bind9-restart.service

# Restart polkit to apply new rules
echo "Restarting polkit..."
systemctl restart polkit || true

# Start the backend service
echo "Starting backend service..."
systemctl start hybrid-dns-backend.service

echo "Fix completed! The backend service should now be able to reload BIND9 configuration."
echo "You can test this by creating a new DNS zone through the web interface."