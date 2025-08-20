# Product Overview

## Hybrid DNS Server

A production-ready hybrid DNS server solution based on BIND9 that provides enterprise-grade DNS services with advanced security, multi-source conditional forwarding, and modern web-based management.

### Core Features

- **Multi-source Conditional Forwarding**: Route different domain types (Active Directory, intranet, public) to appropriate DNS servers with automatic failover and health monitoring
- **Authoritative Zone Management**: Host and manage internal DNS zones with full record type support (A, AAAA, CNAME, MX, TXT, SRV, PTR) via web interface
- **DNS Security & Filtering (RPZ)**: Block malware, phishing, and unwanted content categories with Response Policy Zones and threat feed integration
- **Modern Web Interface**: React-based dashboard with real-time monitoring, 2FA authentication, role-based access, and WebSocket support
- **Enterprise Security**: Comprehensive audit logging, rate limiting, DNSSEC support, network access controls, and JWT authentication
- **Real-time Analytics**: Live DNS query monitoring, statistics, and reporting with WebSocket-based updates
- **Template System**: Jinja2-based configuration template system for BIND9 zone files and RPZ rules
- **Import/Export**: Bulk operations for DNS records with CSV, JSON, and BIND zone file format support
- **Backup & Recovery**: Automated backup system with configuration rollback capabilities
- **Health Monitoring**: Comprehensive system health checks and forwarder monitoring with automatic failover

### Target Use Cases

- Organizations needing centralized DNS management with AD integration
- Companies requiring DNS-based security filtering and threat protection
- Enterprises with complex network topologies requiring conditional forwarding
- IT teams wanting modern web-based DNS administration tools
- Environments needing comprehensive DNS query logging and analytics

### Architecture

The solution combines BIND9 DNS server with a FastAPI backend, React frontend, SQLite/PostgreSQL database, Redis caching, and monitoring services. It features WebSocket support for real-time updates, Jinja2 template system for configuration generation, and comprehensive API endpoints. Deployable via Docker Compose or native installation on Ubuntu/Debian systems with automated installation script.