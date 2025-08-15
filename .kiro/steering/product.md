# Product Overview

## Hybrid DNS Server

A production-ready hybrid DNS server solution based on BIND9 that provides enterprise-grade DNS services with advanced security, multi-source conditional forwarding, and modern web-based management.

### Core Features

- **Multi-source Conditional Forwarding**: Route different domain types (Active Directory, intranet, public) to appropriate DNS servers with automatic failover
- **Authoritative Zone Management**: Host and manage internal DNS zones with full record type support (A, AAAA, CNAME, MX, TXT, SRV, PTR)
- **DNS Security & Filtering (RPZ)**: Block malware, phishing, and unwanted content categories with Response Policy Zones
- **Modern Web Interface**: React-based dashboard with real-time monitoring, 2FA authentication, and role-based access
- **Enterprise Security**: Comprehensive audit logging, rate limiting, DNSSEC support, and network access controls

### Target Use Cases

- Organizations needing centralized DNS management with AD integration
- Companies requiring DNS-based security filtering and threat protection
- Enterprises with complex network topologies requiring conditional forwarding
- IT teams wanting modern web-based DNS administration tools
- Environments needing comprehensive DNS query logging and analytics

### Architecture

The solution combines BIND9 DNS server with a FastAPI backend, React frontend, PostgreSQL database, and monitoring services, all deployable via Docker or native installation on Ubuntu/Debian systems.