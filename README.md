# Hybrid DNS Server

A production-ready hybrid DNS server solution running on Linux (Debian/Ubuntu), based on BIND9, providing a complete DNS platform with multi-source conditional forwarding, authoritative zone management, RPZ-based client security, and a modern React-based web management interface.

![Hybrid DNS Server Dashboard](docs/images/dashboard-preview.png)

## 🌟 Features

### Multi-source Conditional Forwarding
- **Active Directory Integration**: Forward AD domains to multiple domain controllers with automatic failover
- **Intranet Zone Support**: Route internal network queries to dedicated internal DNS servers  
- **Public DNS Redundancy**: Multiple upstream public DNS providers (Cloudflare, Google, Quad9)
- **Health Monitoring**: Automatic failover between forwarders with real-time health checks

### Authoritative Zone Management
- **Master Zone Hosting**: Create and manage internal DNS zones directly on the server
- **Full Record Support**: A, AAAA, CNAME, MX, TXT, SRV, PTR records with web-based management
- **Automatic Zone Deployment**: Changes via UI automatically update BIND9 and reload service
- **Secondary Zone Support**: High availability with backup zone configurations

### DNS Security & Filtering (RPZ)
- **Malware Protection**: Automatic blocking of known malicious domains
- **Phishing Protection**: Real-time threat intelligence integration
- **Category Filtering**: Block social media, adult content, gambling, streaming
- **SafeSearch Enforcement**: Force safe search on Google, YouTube, DuckDuckGo
- **Custom Rules**: Create allow/block lists with wildcard support

### Modern Web Interface
- **Real-time Dashboard**: Live DNS statistics, query analytics, system health
- **Responsive Design**: Mobile-friendly interface with dark/light themes
- **Secure Authentication**: 2FA support with TOTP (Google Authenticator, Authy)
- **Role-based Access**: Admin and user roles with granular permissions
- **Live Monitoring**: Real-time query logs with search and filtering

### Performance & Security
- **Intelligent Caching**: 24-hour cache with smart prefetching
- **Rate Limiting**: Protection against DNS amplification attacks
- **DNSSEC Support**: Optional DNSSEC validation
- **Access Control**: Restrict recursive queries to internal networks
- **Audit Logging**: Complete audit trail of configuration changes

## 📋 System Requirements

### Minimum Requirements
- **OS**: Ubuntu 22.04+ or Debian 11+ (Tested on Ubuntu 24.04 LTS)
- **CPU**: 2 cores (x86_64)
- **RAM**: 4GB RAM
- **Storage**: 20GB available disk space
- **Network**: Static IP recommended

### Recommended Production Setup
- **CPU**: 4+ cores
- **RAM**: 8GB+ RAM  
- **Storage**: 50GB+ SSD storage
- **Network**: Dual NICs for redundancy

### Software Dependencies
- BIND9 9.16+ (Ubuntu 24.04 includes BIND9 9.18+)
- PostgreSQL 12+ (Ubuntu 24.04 includes PostgreSQL 16)
- Python 3.10+ (Ubuntu 24.04 includes Python 3.12)
- Node.js 18+ (Installed via NodeSource)
- Nginx 1.18+
- Redis 6+ (Optional, for caching)

## 🚀 Quick Start

### Option 1: Automated Installation (Recommended)

1. **Clone the repository and run the installation script:**
   ```bash
   git clone https://github.com/mr-wolf-gb/hybrid-dns-server.git
   cd hybrid-dns-server
   sudo ./install.sh
   ```
   
   The script will install all dependencies and configure the system automatically.

2. **For quick deployment (download installer only):**
   ```bash
   wget https://raw.githubusercontent.com/mr-wolf-gb/hybrid-dns-server/main/install.sh
   chmod +x install.sh
   sudo ./install.sh
   ```
   
   Note: This will download the full repository during installation.

3. **Installation Features:**
   - **Ubuntu 24.04 Compatible**: Fully tested and optimized for Ubuntu 24.04 LTS
   - **Resume Support**: Installation can be resumed from checkpoints if interrupted
   - **Automatic Configuration**: Handles BIND9, database, and service configuration
   - **Comprehensive Setup**: Installs all dependencies and configures services
   - **Security Hardening**: Configures firewall, fail2ban, SSL certificates, and AppArmor

4. **Installation Options:**
   ```bash
   sudo ./install.sh           # Start new installation
   sudo ./install.sh --resume  # Resume from checkpoint
   sudo ./install.sh --fresh   # Force fresh start
   sudo ./install.sh --status  # Check installation status
   ```

5. **Follow the interactive prompts:**
   - Configure server IP address and domain name
   - Set admin username, password, email, and full name
   - Installation will automatically handle all dependencies

6. **What gets installed:**
   - BIND9 DNS server with custom configuration
   - PostgreSQL database with initialized schema
   - Python FastAPI backend with virtual environment
   - React frontend built and served via Nginx
   - Systemd services for automatic startup
   - UFW firewall rules and Fail2ban protection
   - SSL certificates (self-signed, upgrade to Let's Encrypt recommended)

7. **Access the web interface:**
   ```
   https://your-server-ip
   ```
   Use the admin credentials you set during installation.

### Option 2: Docker Deployment

1. **Clone the repository:**
   ```bash
   git clone https://github.com/mr-wolf-gb/hybrid-dns-server.git
   cd hybrid-dns-server
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   nano .env  # Edit configuration
   ```

3. **Start services:**
   ```bash
   docker-compose up -d
   ```

4. **Access the interface:**
   ```
   https://your-server-ip
   ```

## 📚 Documentation

### Quick Links
- [Installation Guide](docs/installation.md) - Detailed setup instructions
- [Configuration Guide](docs/configuration.md) - DNS and service configuration
- [API Documentation](docs/api.md) - REST API reference
- [Security Guide](docs/security.md) - Security best practices
- [Troubleshooting](docs/troubleshooting.md) - Common issues and solutions
- [Backup & Recovery](docs/backup-recovery.md) - Data protection procedures

### Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web UI        │    │   FastAPI       │    │   PostgreSQL    │
│   (React)       │◄──►│   Backend       │◄──►│   Database      │
│   Port 443/80   │    │   Port 8000     │    │   Port 5432     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                        BIND9 DNS Server                         │
│                         Port 53 UDP/TCP                        │
├─────────────────┬─────────────────┬─────────────────────────────┤
│  Conditional    │  Authoritative  │    Response Policy Zones    │
│  Forwarding     │     Zones       │      (RPZ Security)         │
│                 │                 │                             │
│ • AD Domains    │ • Internal      │ • Malware Blocking          │
│ • Intranet      │   Zones         │ • Phishing Protection       │  
│ • Public DNS    │ • Custom        │ • Category Filtering        │
│                 │   Records       │ • SafeSearch Enforcement    │
└─────────────────┴─────────────────┴─────────────────────────────┘
```

## 🔧 Configuration Examples

### Multi-source Conditional Forwarding

Configure different DNS sources for different domain types:

```yaml
# Active Directory Domains
corp.local:
  forwarders: [192.168.1.10, 192.168.1.11, 192.168.1.12]
  type: active_directory
  
subsidiary.corp:
  forwarders: [192.168.50.5, 192.168.50.6]
  type: active_directory

# Internal Network Zones  
intranet.company:
  forwarders: [10.10.10.5, 10.10.10.6]
  type: intranet
  
research.local:
  forwarders: [10.20.0.1, 10.20.0.2]
  type: intranet

# Public DNS (fallback)
default:
  forwarders: [1.1.1.1, 1.0.0.1, 8.8.8.8, 8.8.4.4, 9.9.9.9]
  type: public
```

### Security Policies (RPZ)

Block malicious content and enforce policies:

```yaml
# Malware & Phishing Protection
malware_domains:
  - "*.malware-example.com"
  - "phishing-site.net"
  
# Category Blocking
social_media:
  enabled: true
  domains: 
    - "facebook.com"
    - "twitter.com"
    - "instagram.com"
    
adult_content:
  enabled: true
  
gambling:
  enabled: false

# SafeSearch Enforcement
safesearch:
  google: true
  youtube: true
  duckduckgo: true
```

## 🔐 Security Features

### Authentication & Authorization
- **Multi-factor Authentication**: TOTP-based 2FA integration
- **Session Management**: Secure JWT tokens with automatic refresh
- **Account Lockout**: Brute force protection with progressive delays
- **Audit Logging**: Complete audit trail of user actions

### DNS Security
- **Response Policy Zones**: Block malicious domains at DNS level
- **Rate Limiting**: Protect against DNS amplification attacks
- **Access Control Lists**: Restrict recursive queries to authorized networks
- **DNSSEC Validation**: Optional cryptographic verification of DNS responses

### Infrastructure Security
- **Firewall Integration**: Automatic UFW firewall configuration
- **Fail2ban**: Intrusion detection and prevention
- **SSL/TLS**: HTTPS encryption for web interface
- **Secure Headers**: HSTS, CSP, and other security headers

## 📊 Monitoring & Analytics

### Real-time Dashboard
- **Query Statistics**: Requests per second, response times, cache hit rates
- **Top Domains**: Most frequently requested domains
- **Client Analytics**: Query distribution by client IP
- **Blocked Queries**: Security events and policy violations
- **System Health**: CPU, memory, disk usage, and service status

### Query Logging
- **Live Query Stream**: Real-time DNS query monitoring
- **Advanced Filtering**: Filter by client, domain, record type, timestamp
- **Export Capabilities**: CSV export for external analysis
- **Search Functionality**: Full-text search across query logs

### Health Monitoring
- **Forwarder Health**: Automatic monitoring of upstream DNS servers
- **Service Monitoring**: Real-time status of all system components
- **Performance Metrics**: Response time tracking and SLA monitoring
- **Alerting**: Configurable alerts for system issues

## 🔄 Backup & Recovery

### Automated Backups
- **Daily Backups**: Automated backup of configuration and data
- **Retention Policy**: Configurable retention periods
- **Compression**: Efficient storage with gzip compression
- **Verification**: Automatic backup integrity checks

### Manual Backup
```bash
# Create immediate backup
sudo systemctl start hybrid-dns-backup

# View backup files
ls -la /opt/hybrid-dns-server/backups/

# Backup script location
sudo /opt/hybrid-dns-server/scripts/backup.sh
```

### Recovery Procedures
- [Database Recovery](docs/backup-recovery.md#database-recovery)
- [Configuration Recovery](docs/backup-recovery.md#configuration-recovery)  
- [Disaster Recovery](docs/backup-recovery.md#disaster-recovery)

## 🛠️ Maintenance

### Daily Maintenance (Automated)
- Log rotation and cleanup
- Database maintenance (VACUUM, analyze)
- Threat intelligence feed updates
- System health checks
- Configuration backups

### Manual Maintenance
```bash
# View service status
sudo systemctl status hybrid-dns-backend
sudo systemctl status hybrid-dns-monitor
sudo systemctl status bind9

# View logs
sudo journalctl -u bind9 -f
sudo journalctl -u hybrid-dns-backend -f

# Manual backup
sudo systemctl start hybrid-dns-backup

# Cache management
sudo rndc flush  # Clear DNS cache
sudo rndc stats  # View statistics
```

## 🐛 Troubleshooting

### Common Issues

**DNS Resolution Not Working**
```bash
# Check BIND9 status
sudo systemctl status bind9
sudo named-checkconf

# Test DNS resolution
dig @localhost google.com
nslookup google.com localhost

# Common fixes for BIND9 issues
sudo chown -R bind:bind /var/log/bind
sudo chmod 755 /var/log/bind
sudo systemctl restart bind9
```

**Installation Issues**
```bash
# Check installation status
sudo ./install.sh --status

# Resume interrupted installation
sudo ./install.sh --resume

# Start fresh if needed
sudo ./install.sh --fresh

# Check installation logs
tail -f /tmp/hybrid-dns-install.log

# Test database connection
sudo -u dns-server bash -c "cd /opt/hybrid-dns-server/backend && source venv/bin/activate && python -c 'from app.core.database import check_database_health; import asyncio; print(asyncio.run(check_database_health()))'"
```

**Web Interface Not Accessible**
```bash
# Check backend service
sudo systemctl status hybrid-dns-backend
curl http://localhost:8000/health

# Check Nginx configuration
sudo nginx -t
sudo systemctl status nginx
```

**High Memory Usage**
```bash
# Check cache size
sudo rndc status | grep "cache usage"

# Adjust cache limits in named.conf.options
max-cache-size 512M;
```

For more troubleshooting guidance, see the [Troubleshooting Guide](docs/troubleshooting.md).

## 🏗️ Project Structure

```
hybrid-dns-server/
├── 📄 README.md                     # Project documentation
├── 🚀 install.sh                   # Automated installation script
├── 🐳 docker-compose.yml           # Container orchestration
├── 📁 backend/                     # FastAPI backend application
│   ├── 📄 main.py                  # Application entry point
│   ├── 📄 init_db.py               # Database initialization
│   ├── 📄 create_admin.py          # Admin user creation
│   ├── 📄 alembic.ini              # Database migration config
│   ├── 📁 alembic/                 # Database migrations
│   ├── 📁 app/                     # Application source code
│   │   ├── 📁 api/                 # REST API endpoints
│   │   ├── 📁 core/                # Core configuration
│   │   ├── 📁 models/              # Database models
│   │   ├── 📁 schemas/             # Pydantic schemas
│   │   ├── 📁 services/            # Business logic
│   │   ├── 📁 templates/           # Jinja2 templates
│   │   └── 📁 websocket/           # WebSocket handling
│   └── 📁 examples/                # Sample data and imports
├── 📁 frontend/                    # React web interface
│   ├── 📄 package.json             # Node.js dependencies
│   ├── 📄 vite.config.ts           # Vite configuration
│   └── 📁 src/                     # React application source
├── 📁 bind9/                       # BIND9 DNS configuration
│   ├── 📄 named.conf.options       # Main BIND9 config
│   ├── 📄 named.conf.local         # Zone definitions
│   ├── 📁 zones/                   # DNS zone files
│   └── 📁 rpz/                     # Response Policy Zones
├── 📁 monitoring/                  # DNS monitoring service
├── 📁 systemd/                     # System service configs
└── 📁 scripts/                     # Maintenance scripts
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

#### Quick Development Setup

**Linux/macOS:**
```bash
# Clone repository
git clone https://github.com/mr-wolf-gb/hybrid-dns-server.git
cd hybrid-dns-server

# Run automated development setup
./setup-dev.sh
```

**Windows:**
```cmd
# Clone repository
git clone https://github.com/mr-wolf-gb/hybrid-dns-server.git
cd hybrid-dns-server

# Run automated development setup
setup-dev.bat
```

#### Manual Development Setup

```bash
# 1. Create environment configuration
cp .env.example .env
# Edit .env file and update SECRET_KEY, JWT_SECRET_KEY, and other settings

# 2. Backend development
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Initialize database
python init_db.py

# 4. Start development server
python main.py

# 5. Frontend development (in another terminal)
cd frontend
npm install
npm run dev
```

#### Environment Configuration

The application requires a `.env` file for configuration. **Never commit this file to git** as it contains sensitive information.

**Key settings to configure:**
- `SECRET_KEY` - Generate a secure random string (32+ characters)
- `JWT_SECRET_KEY` - Generate a secure random string (32+ characters)  
- `DATABASE_URL` - Database connection string
- `ALLOWED_HOSTS` - Comma-separated list of allowed hosts
- `DEBUG` - Set to `true` for development, `false` for production

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Community Support
- [GitHub Issues](https://github.com/mr-wolf-gb/hybrid-dns-server/issues) - Bug reports and feature requests
- [Discussions](https://github.com/mr-wolf-gb/hybrid-dns-server/discussions) - Community Q&A
- [Documentation](docs/) - Comprehensive guides and tutorials

### Installation Support
- Tested on fresh Ubuntu 24.04 LTS installations
- Comprehensive error handling and logging
- Resume capability for interrupted installations
- Automatic dependency resolution

## 📈 Roadmap

### Upcoming Features
- [ ] Kubernetes deployment support
- [ ] Active Directory integration for user management  
- [ ] DNS over HTTPS (DoH) and DNS over TLS (DoT)
- [ ] Geographic DNS routing
- [ ] Enhanced threat feed integration
- [ ] Mobile app for monitoring
- [ ] Load balancing between multiple DNS servers
- [ ] Advanced analytics and reporting
- [ ] Debian 12 support
- [ ] ARM64 architecture support

### Version History
- **v1.2.0** - Ubuntu 24.04 LTS support, enhanced installer, database migrations
- **v1.1.0** - Fixed BIND9 configuration issues, added installation resume support
- **v1.0.0** - Initial release with core functionality
- **v0.9.0** - Beta release with web interface
- **v0.5.0** - Alpha release with basic BIND9 integration

---

## 📞 Quick Reference

### Default Ports
- **DNS**: 53 (UDP/TCP)
- **Web Interface**: 443 (HTTPS), 80 (HTTP redirect)
- **API**: 8000 (internal)
- **Database**: 5432 (internal)

### Default Locations
- **Configuration**: `/etc/bind/` and `/opt/hybrid-dns-server/`
- **Logs**: `/var/log/bind/` and `/var/log/hybrid-dns/`
- **Backups**: `/opt/hybrid-dns-server/backups/`
- **Web Files**: `/opt/hybrid-dns-server/frontend/dist/`

### Key Commands
```bash
# Service management
sudo systemctl {start|stop|restart|status} bind9
sudo systemctl {start|stop|restart|status} hybrid-dns-backend

# DNS management
sudo rndc {reload|flush|stats|status}
sudo named-checkconf

# Log monitoring
sudo tail -f /var/log/bind/queries.log
sudo journalctl -u bind9 -f
```

---

Made with ❤️ by the Hybrid DNS Team
