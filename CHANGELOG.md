# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-08-15

### Added
- Installation resume functionality with checkpoint support
- Comprehensive installation status checking
- Automatic BIND9 configuration fixes during installation
- Better error handling and logging during installation

### Fixed
- **Critical**: Fixed BIND9 configuration syntax errors that prevented startup on fresh installations
  - Removed problematic CIDR notation in statistics-channels configuration
  - Fixed duplicate zone definitions that conflicted with default-zones
  - Temporarily disabled logging configuration to avoid permission issues during initial setup
- Fixed zone files missing newline characters
- Fixed comprehensive file permissions for BIND9 configuration files
- Added proper ownership settings for all DNS-related directories and files

### Changed
- Installation script now validates BIND9 startup before proceeding
- Improved installation script with better error messages and recovery options
- Enhanced permission handling for BIND9 files and directories

### Security
- Improved file permission security for BIND9 configuration files
- Better isolation of service user permissions

## [1.0.0] - 2025-08-14

### Added
- Initial release with core DNS server functionality
- Multi-source conditional forwarding
- Authoritative zone management
- Response Policy Zones (RPZ) for security filtering
- Modern React-based web interface
- FastAPI backend with PostgreSQL database
- Automated installation script
- Docker deployment support
- Comprehensive documentation

### Security
- 2FA authentication support
- Role-based access control
- Firewall and fail2ban integration
- SSL/TLS encryption for web interface

### Performance
- Intelligent DNS caching
- Rate limiting protection
- Health monitoring and failover