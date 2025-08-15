# Installation Guide

This guide provides detailed instructions for installing the Hybrid DNS Server on Ubuntu/Debian systems.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Automated Installation](#automated-installation)
- [Manual Installation](#manual-installation)
- [Docker Installation](#docker-installation)
- [Post-Installation Setup](#post-installation-setup)
- [Verification](#verification)

## Prerequisites

### System Requirements
- **Operating System**: Ubuntu 20.04+ or Debian 11+
- **Architecture**: x86_64 (amd64)
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 20GB available space minimum, 50GB+ recommended
- **Network**: Static IP address recommended

### Network Considerations
- Port 53 (DNS) must be available
- Port 443/80 (Web interface) must be available
- Firewall should allow DNS queries from client networks
- Consider DNS forwarder requirements for AD/internal networks

### User Permissions
- Root access required for installation
- Service will run under dedicated `dns-admin` user (created during installation)

## Automated Installation

The automated installation script handles all dependencies and configuration.

### Download and Run

```bash
# Download installation script
wget https://raw.githubusercontent.com/user/hybrid-dns-server/main/install.sh

# Make executable
chmod +x install.sh

# Run installation (requires root)
sudo ./install.sh
```

### Installation Process

The script will:

1. **Update system packages**
2. **Install dependencies**:
   - BIND9 DNS server
   - PostgreSQL database
   - Python 3.10+ and pip
   - Node.js and npm
   - Nginx web server
   - Redis cache
   - Security tools (UFW, Fail2ban)

3. **Create system user** (`dns-admin`)
4. **Setup database** with random passwords
5. **Configure BIND9** with security hardening
6. **Deploy applications**:
   - FastAPI backend service
   - React frontend with Nginx
   - Monitoring service

7. **Configure security**:
   - UFW firewall rules
   - Fail2ban intrusion detection
   - SSL certificate generation

8. **Create systemd services**
9. **Setup automated maintenance**

### Interactive Prompts

During installation, you'll be prompted for:

```
Enter admin password for web interface: ********
Confirm admin password: ********

Configure firewall automatically? [Y/n]: Y

Allow SSH access? [Y/n]: Y
SSH port [22]: 22

Configure SSL certificate? [Y/n]: Y
Domain name (or IP): dns.example.com

Setup automated backups? [Y/n]: Y
Backup retention days [30]: 30

Configure monitoring email alerts? [y/N]: N
```

### Installation Logs

Installation logs are saved to `/tmp/hybrid-dns-install.log` for troubleshooting.

## Manual Installation

For advanced users who prefer manual control over the installation process.

### Step 1: System Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install basic dependencies
sudo apt install -y curl wget gnupg2 software-properties-common apt-transport-https
```

### Step 2: Install Core Services

#### BIND9 DNS Server
```bash
# Install BIND9
sudo apt install -y bind9 bind9utils bind9-doc

# Enable and start service
sudo systemctl enable bind9
sudo systemctl start bind9
```

#### PostgreSQL Database
```bash
# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Start and enable service
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

#### Python Environment
```bash
# Install Python 3.10+ (Ubuntu 22.04+)
sudo apt install -y python3 python3-pip python3-venv python3-dev

# For Ubuntu 20.04, add Python 3.10 repository
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install -y python3.10 python3.10-venv python3.10-dev
```

#### Node.js
```bash
# Install Node.js 18 LTS
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

#### Nginx Web Server
```bash
# Install Nginx
sudo apt install -y nginx

# Enable service
sudo systemctl enable nginx
```

#### Redis Cache
```bash
# Install Redis
sudo apt install -y redis-server

# Configure and start
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

### Step 3: Create System User

```bash
# Create dns-admin user
sudo useradd --system --create-home --shell /bin/bash dns-admin
sudo usermod -aG bind dns-admin
```

### Step 4: Database Setup

```bash
# Switch to postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE hybrid_dns;
CREATE USER dns_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE hybrid_dns TO dns_user;
ALTER USER dns_user CREATEDB;
\q
```

### Step 5: Application Deployment

#### Clone Repository
```bash
# Clone to system location
sudo git clone https://github.com/user/hybrid-dns-server.git /opt/hybrid-dns-server
sudo chown -R dns-admin:dns-admin /opt/hybrid-dns-server
```

#### Backend Setup
```bash
# Switch to dns-admin user
sudo -u dns-admin -i

# Setup Python environment
cd /opt/hybrid-dns-server/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Setup environment file
cp .env.example .env
nano .env  # Edit configuration
```

#### Frontend Setup
```bash
# Build frontend
cd /opt/hybrid-dns-server/frontend
npm install
npm run build

# Copy to Nginx directory
sudo cp -r dist/* /var/www/html/
```

#### BIND9 Configuration
```bash
# Copy configuration files
sudo cp /opt/hybrid-dns-server/bind9/named.conf.options /etc/bind/
sudo cp /opt/hybrid-dns-server/bind9/named.conf.local /etc/bind/
sudo cp -r /opt/hybrid-dns-server/bind9/zones /etc/bind/
sudo cp -r /opt/hybrid-dns-server/bind9/rpz /etc/bind/

# Set permissions
sudo chown -R bind:bind /etc/bind
sudo chmod 644 /etc/bind/named.conf.*

# Validate configuration
sudo named-checkconf
```

### Step 6: Service Configuration

#### Install Systemd Services
```bash
# Copy service files
sudo cp /opt/hybrid-dns-server/systemd/*.service /etc/systemd/system/
sudo cp /opt/hybrid-dns-server/systemd/*.timer /etc/systemd/system/

# Reload systemd and enable services
sudo systemctl daemon-reload
sudo systemctl enable hybrid-dns-backend
sudo systemctl enable hybrid-dns-monitoring
sudo systemctl enable hybrid-dns-maintenance.timer
```

#### Configure Nginx
```bash
# Copy Nginx configuration
sudo cp /opt/hybrid-dns-server/nginx/hybrid-dns.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/hybrid-dns.conf /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

### Step 7: Security Configuration

#### UFW Firewall
```bash
# Enable UFW
sudo ufw --force enable

# Allow SSH (adjust port as needed)
sudo ufw allow 22/tcp

# Allow DNS
sudo ufw allow 53/tcp
sudo ufw allow 53/udp

# Allow web interface
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow from internal networks (adjust as needed)
sudo ufw allow from 192.168.0.0/16
sudo ufw allow from 10.0.0.0/8
sudo ufw allow from 172.16.0.0/12
```

#### Fail2ban
```bash
# Install Fail2ban
sudo apt install -y fail2ban

# Copy configuration
sudo cp /opt/hybrid-dns-server/fail2ban/hybrid-dns.conf /etc/fail2ban/jail.d/

# Restart Fail2ban
sudo systemctl restart fail2ban
```

### Step 8: Start Services

```bash
# Start all services
sudo systemctl start hybrid-dns-backend
sudo systemctl start hybrid-dns-monitoring
sudo systemctl restart bind9

# Start maintenance timer
sudo systemctl start hybrid-dns-maintenance.timer

# Verify services are running
sudo systemctl status bind9
sudo systemctl status hybrid-dns-backend
sudo systemctl status hybrid-dns-monitoring
```

## Docker Installation

For containerized deployment using Docker Compose.

### Prerequisites
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add user to docker group
sudo usermod -aG docker $USER
```

### Deployment Steps

```bash
# Clone repository
git clone https://github.com/user/hybrid-dns-server.git
cd hybrid-dns-server

# Copy environment configuration
cp .env.example .env

# Edit configuration
nano .env
```

Example `.env` configuration:
```bash
# Database Configuration
POSTGRES_DB=hybrid_dns
POSTGRES_USER=dns_user
POSTGRES_PASSWORD=your_secure_password

# Application Configuration
SECRET_KEY=your_jwt_secret_key
ADMIN_PASSWORD=your_admin_password
DOMAIN_NAME=dns.example.com

# DNS Configuration
DNS_RECURSION_ALLOWED=192.168.0.0/16;10.0.0.0/8;172.16.0.0/12
DNS_FORWARDERS=1.1.1.1;1.0.0.1;8.8.8.8;8.8.4.4

# Security Configuration
ENABLE_2FA=true
ENABLE_QUERY_LOGGING=true
```

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### Docker Service Management

```bash
# Stop services
docker-compose down

# Update services
docker-compose pull
docker-compose up -d

# Backup data
docker-compose exec postgres pg_dump -U dns_user hybrid_dns > backup.sql

# View individual service logs
docker-compose logs -f backend
docker-compose logs -f bind9
docker-compose logs -f monitoring
```

## Post-Installation Setup

### Initial Configuration

1. **Access Web Interface**
   ```
   https://your-server-ip
   ```

2. **Login with Admin Account**
   - Username: `admin`
   - Password: Set during installation

3. **Configure DNS Forwarders**
   - Navigate to Forwarders section
   - Add Active Directory servers
   - Add internal DNS servers
   - Configure public DNS servers

4. **Setup Security Policies**
   - Enable RPZ security zones
   - Configure category filtering
   - Enable SafeSearch enforcement
   - Import custom block/allow lists

5. **Create DNS Zones**
   - Add internal zones
   - Create DNS records
   - Configure reverse DNS zones

### Network Configuration

#### Client DNS Settings
Configure clients to use the new DNS server:

**Windows (via Group Policy)**:
```
Computer Configuration → Administrative Templates → Network → DNS Client
Set DNS Server Addresses: [DNS-SERVER-IP]
```

**Linux (systemd-resolved)**:
```bash
sudo systemctl edit systemd-resolved
# Add:
[Resolve]
DNS=YOUR_DNS_SERVER_IP
sudo systemctl restart systemd-resolved
```

**Router/DHCP Configuration**:
Set DNS server option to point to your new DNS server.

## Verification

### Service Health Check
```bash
# Check all services
sudo systemctl status bind9 hybrid-dns-backend hybrid-dns-monitoring

# Check DNS resolution
dig @localhost google.com
nslookup google.com localhost

# Check web interface
curl -k https://localhost/health
```

### DNS Resolution Tests
```bash
# Test recursive resolution
dig @YOUR_DNS_SERVER google.com

# Test authoritative zone (if configured)
dig @YOUR_DNS_SERVER internal.local

# Test forwarder (AD domain)
dig @YOUR_DNS_SERVER corp.local

# Test RPZ blocking
dig @YOUR_DNS_SERVER malware-test.com
```

### Log Verification
```bash
# DNS query logs
sudo tail -f /var/log/bind/queries.log

# Backend logs
sudo journalctl -u hybrid-dns-backend -f

# Security logs
sudo tail -f /var/log/bind/security.log
```

### Performance Testing
```bash
# DNS performance test
time dig @YOUR_DNS_SERVER google.com

# Load testing with dnsperf (if available)
dnsperf -s YOUR_DNS_SERVER -d /tmp/query_list.txt
```

## Troubleshooting Installation

### Common Issues

**BIND9 fails to start**:
```bash
# Check configuration syntax
sudo named-checkconf

# Check zone files
sudo named-checkzone internal.local /etc/bind/zones/db.internal.local

# Check permissions
ls -la /etc/bind/
sudo chown -R bind:bind /etc/bind
```

**Backend service fails**:
```bash
# Check Python environment
sudo -u dns-admin /opt/hybrid-dns-server/backend/venv/bin/python --version

# Check database connectivity
sudo -u dns-admin psql $DATABASE_URL -c "SELECT 1"

# Check logs
sudo journalctl -u hybrid-dns-backend --no-pager
```

**Web interface not accessible**:
```bash
# Check Nginx status
sudo systemctl status nginx
sudo nginx -t

# Check firewall
sudo ufw status
```

**Database connection issues**:
```bash
# Check PostgreSQL service
sudo systemctl status postgresql

# Test connection
sudo -u postgres psql hybrid_dns -c "SELECT version();"

# Check user permissions
sudo -u postgres psql -c "\\du dns_user"
```

### Getting Help

If you encounter issues during installation:

1. Check the installation log: `/tmp/hybrid-dns-install.log`
2. Review service logs: `sudo journalctl -u SERVICE_NAME`
3. Consult the [Troubleshooting Guide](troubleshooting.md)
4. Create an issue on GitHub with logs and error messages

## Next Steps

After successful installation:

1. Review the [Configuration Guide](configuration.md)
2. Set up [monitoring and alerting](monitoring.md)
3. Configure [backup procedures](backup-recovery.md)
4. Review [security best practices](security.md)

---

**Installation complete!** Your Hybrid DNS Server is now ready for production use.