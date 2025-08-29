# IP Address Change Scripts

This directory contains scripts to safely change the Ubuntu server's IP address and update all necessary configurations for the Hybrid DNS Server to continue working properly.

## Scripts Overview

### 1. `change-server-ip.sh` - Main IP Change Script
**Purpose**: Comprehensive script to change server IP address and update all related configurations.

**Features**:
- Interactive IP configuration input with validation
- Automatic backup of all configurations before changes
- Updates netplan network configuration
- Updates BIND9 DNS server configurations
- Updates application configurations (.env files)
- Updates systemd service configurations
- Updates firewall rules (UFW)
- Applies changes and restarts services
- Verifies DNS functionality after changes
- Provides rollback capability

**Usage**:
```bash
sudo ./change-server-ip.sh
```

### 2. `emergency-ip-rollback.sh` - Emergency Rollback
**Purpose**: Quick rollback script if the IP change fails or causes connectivity issues.

**Features**:
- Finds the most recent backup automatically
- Quickly restores network configuration
- Restores BIND9 and application configurations
- Restarts all services
- Minimal user interaction for emergency situations

**Usage**:
```bash
sudo ./emergency-ip-rollback.sh
```

### 3. `verify-ip-change.sh` - Verification Script
**Purpose**: Comprehensive verification of DNS server functionality after IP change.

**Features**:
- Tests network connectivity
- Verifies DNS resolution
- Checks BIND9 service status
- Tests DNS server functionality
- Verifies application services
- Tests web interface accessibility
- Checks configuration files
- Reviews log files
- Examines firewall configuration
- Performance testing

**Usage**:
```bash
./verify-ip-change.sh
```

## Step-by-Step IP Change Process

### Pre-Change Preparation

1. **Document Current Configuration**:
   ```bash
   ip addr show
   ip route show
   cat /etc/netplan/*.yaml
   systemctl status bind9
   ```

2. **Ensure Backup Directory Exists**:
   ```bash
   sudo mkdir -p /opt/hybrid-dns-server/backups
   ```

3. **Stop Non-Essential Services** (optional):
   ```bash
   sudo systemctl stop hybrid-dns-monitoring
   ```

### Performing the IP Change

1. **Run the Main Script**:
   ```bash
   sudo ./change-server-ip.sh
   ```

2. **Follow Interactive Prompts**:
   - Enter new IP address
   - Enter subnet mask (CIDR notation)
   - Enter gateway IP
   - Enter DNS servers
   - Confirm changes

3. **Monitor the Process**:
   - The script will show progress for each step
   - Automatic backup is created before any changes
   - Network configuration is applied
   - Services are restarted automatically

### Post-Change Verification

1. **Run Verification Script**:
   ```bash
   ./verify-ip-change.sh
   ```

2. **Manual Verification**:
   ```bash
   # Test network connectivity
   ping 8.8.8.8
   
   # Test DNS resolution
   nslookup google.com
   nslookup google.com [NEW_IP]
   
   # Check services
   systemctl status bind9
   systemctl status hybrid-dns-backend
   
   # Test web interfaces
   curl http://[NEW_IP]:8000/health
   curl http://[NEW_IP]:3000
   ```

3. **Update Client Configurations**:
   - Update DNS settings on client machines
   - Update any hardcoded IP references
   - Test from client machines

### Emergency Rollback

If something goes wrong during or after the IP change:

1. **Immediate Rollback**:
   ```bash
   sudo ./emergency-ip-rollback.sh
   ```

2. **Manual Rollback** (if scripts fail):
   ```bash
   # Find backup directory
   ls -la /opt/hybrid-dns-server/backups/ip-change-*
   
   # Restore network config
   sudo cp /opt/hybrid-dns-server/backups/ip-change-[DATE]/00-installer-config.yaml /etc/netplan/
   sudo netplan apply
   
   # Restart services
   sudo systemctl restart bind9
   sudo systemctl restart hybrid-dns-backend
   ```

## Configuration Files Updated

The IP change script automatically updates these files:

### Network Configuration
- `/etc/netplan/00-installer-config.yaml` or `/etc/netplan/01-netcfg.yaml`

### BIND9 DNS Server
- `/etc/bind/named.conf.options`
- `/etc/bind/named.conf.local`
- `/etc/bind/zones/*.zone` (all zone files)
- `/etc/bind/zones/*.rev` (reverse zone files)

### Application Configuration
- `/opt/hybrid-dns-server/.env`
- `/opt/hybrid-dns-server/backend/.env` (if exists)
- `/opt/hybrid-dns-server/docker-compose.yml` (if exists)

### System Services
- `/etc/systemd/system/hybrid-dns-*.service`

### Firewall Rules
- UFW rules (if UFW is active)

## Backup Location

Backups are stored in:
```
/opt/hybrid-dns-server/backups/ip-change-YYYYMMDD-HHMMSS/
```

Each backup contains:
- Network configuration files
- Complete BIND9 configuration directory
- Application configuration files
- Systemd service files

## Troubleshooting

### Common Issues

1. **Network Configuration Fails**:
   - Check netplan syntax: `sudo netplan --debug apply`
   - Verify interface name: `ip link show`
   - Check for conflicting configurations

2. **BIND9 Fails to Start**:
   - Check configuration: `sudo named-checkconf`
   - Review logs: `sudo journalctl -u bind9 -n 50`
   - Verify file permissions: `ls -la /etc/bind/`

3. **Services Don't Start**:
   - Check systemd status: `sudo systemctl status service-name`
   - Review service logs: `sudo journalctl -u service-name -n 50`
   - Verify configuration files

4. **Web Interface Inaccessible**:
   - Check if services are running
   - Verify firewall rules: `sudo ufw status`
   - Test with curl: `curl -v http://[IP]:8000/health`

### Log Locations

- **BIND9 logs**: `/var/log/bind/bind.log`
- **System logs**: `journalctl -u bind9`, `journalctl -u hybrid-dns-backend`
- **Application logs**: `/opt/hybrid-dns-server/backend/logs/`
- **Network logs**: `journalctl -u systemd-networkd`

### Recovery Commands

```bash
# Check current IP
ip addr show

# Test DNS functionality
nslookup google.com
dig @localhost google.com

# Restart all services
sudo systemctl restart bind9
sudo systemctl restart hybrid-dns-backend
sudo systemctl restart hybrid-dns-monitoring

# Check service status
sudo systemctl status bind9 hybrid-dns-backend hybrid-dns-monitoring

# View recent logs
sudo journalctl -u bind9 -f
```

## Security Considerations

1. **Run scripts as root**: All scripts require root privileges for system configuration changes
2. **Backup verification**: Always verify backups are created before proceeding
3. **Network isolation**: Consider the impact on network connectivity during the change
4. **Service dependencies**: Understand which services depend on the IP address
5. **Client impact**: Plan for updating client DNS configurations

## Best Practices

1. **Schedule during maintenance window**: Plan IP changes during low-usage periods
2. **Test in development**: Test the process in a development environment first
3. **Document changes**: Keep records of IP changes and configurations
4. **Monitor after change**: Watch logs and metrics after the change
5. **Update documentation**: Update any documentation with the new IP address

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review the verification script output
3. Examine log files for error messages
4. Consider using the emergency rollback script
5. Consult the main project documentation in `/docs/`