# Production Deployment Guide

This guide covers deploying the Hybrid DNS Server to a production Ubuntu server.

## Prerequisites

- Ubuntu 20.04+ server
- PostgreSQL 12+ installed and configured
- Redis server (optional, for caching)
- BIND9 DNS server
- Python 3.10+
- Nginx (for reverse proxy)

## Installation Steps

### 1. Database Setup

```bash
# Run database initialization (creates/updates schema automatically)
cd /opt/hybrid-dns-server/backend
python init_db.py
```

### 2. Environment Configuration

Create `/opt/hybrid-dns-server/.env`:

```env
# Database Configuration
DATABASE_URL=postgresql://dns_user:your_password@localhost:5432/hybrid_dns

# Security
SECRET_KEY=your-super-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# BIND9 Configuration
BIND_CONFIG_PATH=/etc/bind
BIND_ZONES_PATH=/etc/bind/zones
BIND_RPZ_PATH=/etc/bind/rpz

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/hybrid-dns/app.log

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# Production Settings
ENVIRONMENT=production
DEBUG=false
```

### 3. System Services

The systemd services should already be configured. Start them:

```bash
# Start backend service
sudo systemctl start hybrid-dns-backend
sudo systemctl enable hybrid-dns-backend

# Start maintenance service
sudo systemctl start hybrid-dns-maintenance
sudo systemctl enable hybrid-dns-maintenance

# Verify services are running
sudo systemctl status hybrid-dns-backend
sudo systemctl status hybrid-dns-maintenance
```

### 4. BIND9 Configuration

Ensure BIND9 is configured to include the generated configuration:

```bash
# Check BIND9 configuration
sudo named-checkconf

# Restart BIND9
sudo systemctl restart bind9
sudo systemctl enable bind9
```

### 5. Nginx Configuration (Optional)

Create `/etc/nginx/sites-available/hybrid-dns`:

```nginx
server {
    listen 80;
    server_name your-dns-server.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/hybrid-dns /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Production API Endpoints

The following endpoints are available in production:

### Core DNS Management
- `/api/auth/*` - Authentication and user management
- `/api/zones/*` - DNS zone management
- `/api/records/*` - DNS record management
- `/api/forwarders/*` - Conditional forwarding configuration
- `/api/rpz/*` - Response Policy Zone management

### Monitoring & Analytics
- `/api/health/*` - System health monitoring
- `/api/analytics/*` - DNS analytics and performance metrics
- `/api/reports/*` - Report generation
- `/api/realtime/*` - Real-time monitoring data

### System Administration
- `/api/system/*` - System configuration
- `/api/backup/*` - Configuration backup/restore
- `/api/events/*` - Event management and broadcasting

### WebSocket Endpoints
- `/api/websocket/*` - Real-time WebSocket connections

## Security Considerations

### 1. Firewall Configuration

```bash
# Allow SSH
sudo ufw allow ssh

# Allow DNS
sudo ufw allow 53

# Allow HTTP/HTTPS (if using Nginx)
sudo ufw allow 80
sudo ufw allow 443

# Allow API access (adjust as needed)
sudo ufw allow 8000

# Enable firewall
sudo ufw enable
```

### 2. Database Security

- Use strong passwords for database users
- Restrict database access to localhost only
- Enable SSL for database connections if needed
- Regular database backups

### 3. Application Security

- Use strong JWT secret keys
- Enable HTTPS in production
- Configure proper CORS settings
- Regular security updates

## Monitoring

### Log Files

- Application logs: `/var/log/hybrid-dns/app.log`
- BIND9 logs: `/var/log/bind/`
- System logs: `journalctl -u hybrid-dns-backend`

### Health Checks

```bash
# Check API health
curl http://localhost:8000/api/health/status

# Check database connectivity
curl http://localhost:8000/api/health/database

# Check BIND9 status
curl http://localhost:8000/api/health/bind
```

### Performance Monitoring

- Use `/api/analytics/performance` for DNS performance metrics
- Monitor system resources with standard tools (htop, iotop, etc.)
- Set up log rotation for application logs

## Backup Strategy

### Automated Backups

The system includes automated backup functionality:

```bash
# Manual backup
curl -X POST http://localhost:8000/api/backup/create

# List backups
curl http://localhost:8000/api/backup/list

# Restore from backup
curl -X POST http://localhost:8000/api/backup/restore/backup_id
```

### Database Backups

```bash
# Create database backup
pg_dump hybrid_dns > /backup/hybrid_dns_$(date +%Y%m%d_%H%M%S).sql

# Restore database backup
psql hybrid_dns < /backup/hybrid_dns_backup.sql
```

## Troubleshooting

### Common Issues

1. **Service won't start**: Check logs with `journalctl -u hybrid-dns-backend -f`
2. **Database connection errors**: Verify PostgreSQL is running and credentials are correct
3. **BIND9 configuration errors**: Run `named-checkconf` to validate configuration
4. **Permission issues**: Ensure proper file ownership and permissions

### Debug Mode

To enable debug mode temporarily:

```bash
# Edit environment file
sudo nano /opt/hybrid-dns-server/.env

# Set DEBUG=true and LOG_LEVEL=DEBUG
# Restart service
sudo systemctl restart hybrid-dns-backend
```

## Maintenance

### Regular Tasks

- Monitor disk space and log rotation
- Update system packages regularly
- Review and rotate JWT secrets periodically
- Monitor DNS query patterns and performance
- Regular backup verification

### Updates

```bash
# Stop services
sudo systemctl stop hybrid-dns-backend

# Update code (if using git)
cd /opt/hybrid-dns-server
git pull

# Install dependencies
cd backend
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start services
sudo systemctl start hybrid-dns-backend
```

## Support

For issues and support:
- Check application logs first
- Review this deployment guide
- Verify all prerequisites are met
- Test individual components (database, BIND9, etc.)