# Configuration Templates

This directory contains Jinja2 templates for generating BIND9 configuration files.

## acl.j2

Generates Access Control Lists (ACL) configuration for BIND9 based on ACL data from the database.

### Template Variables

- `acls`: List of ACL objects from the database
- `generated_at`: Timestamp when the configuration was generated
- `config_version`: Version of the configuration format
- `include_predefined_acls`: Boolean to include predefined ACLs (default: true)
- `include_security_acls`: Boolean to include security ACLs (default: true)
- `include_dynamic_acls`: Boolean to include dynamic threat ACLs (default: false)
- `trusted_networks`: List of trusted network ranges
- `management_networks`: List of management network ranges
- `dns_servers`: List of DNS server IP addresses
- `monitoring_systems`: List of monitoring system IP addresses
- `blocked_networks`: List of blocked network ranges
- `rate_limited_networks`: List of rate-limited network ranges
- `dynamic_threats`: List of dynamic threat IP addresses
- `dynamic_allow`: List of dynamic allow IP addresses

### ACL Object Structure

Each ACL object should contain:

```python
{
    "id": int,                          # Unique ACL ID
    "name": str,                        # ACL name (used in BIND config)
    "acl_type": str,                    # Type: trusted, blocked, management, etc.
    "description": str,                 # Optional description
    "is_active": bool,                  # Whether ACL is active
    "entries": List[dict],              # List of ACL entries
    "created_at": datetime,             # Creation timestamp
    "updated_at": datetime              # Last update timestamp
}
```

### ACL Entry Structure

Each entry in the `entries` list should contain:

```python
{
    "address": str,         # IP address or network (e.g., "192.168.1.0/24")
    "is_active": bool,      # Whether entry is active
    "comment": str          # Optional comment for documentation
}
```

### Generated Configuration

The template generates BIND9 ACL configuration with:

- Header comments with generation info
- Custom ACLs from database
- Predefined ACLs for common network types
- Security ACLs for threat protection
- Dynamic ACLs for threat intelligence integration
- Comprehensive documentation and usage examples

### ACL Types

- **trusted**: Networks allowed for queries and recursion
- **management**: Networks allowed for administrative operations
- **dns-servers**: DNS servers allowed for zone transfers
- **monitoring**: Systems allowed for statistics access
- **blocked**: Networks explicitly denied access
- **rate-limited**: Networks subject to rate limiting
- **dynamic-threats**: Dynamically updated threat networks
- **dynamic-allow**: Dynamically updated allow networks

### Example Output

```bind
//
// ACCESS CONTROL LISTS (ACL) CONFIGURATION
// Generated automatically by Hybrid DNS Server
// Generated at: 2024-01-20 10:30:00
// Configuration version: 1.0
//

// ============================================================================
// CORPORATE-NETWORK ACL
// ============================================================================
// Description: Corporate office networks
// Type: TRUSTED
// Created: 2024-01-01 10:00:00
// Last Updated: 2024-01-15 14:30:00

acl "corporate-network" {
    192.168.1.0/24;     // Main office network
    192.168.2.0/24;     // Branch office network
    10.10.0.0/16;       // VPN network
};

// ============================================================================
// PREDEFINED ACLS FOR COMMON NETWORK CONFIGURATIONS
// ============================================================================

// Internal Networks ACL (RFC 1918 Private Networks)
acl "internal-networks" {
    127.0.0.0/8;        // Loopback
    10.0.0.0/8;         // Class A private
    172.16.0.0/12;      // Class B private  
    192.168.0.0/16;     // Class C private
    ::1;                // IPv6 loopback
    fc00::/7;           // IPv6 unique local addresses
};
```

### Usage in Code

```python
from jinja2 import Environment, FileSystemLoader

# Set up Jinja2 environment
env = Environment(loader=FileSystemLoader("templates"))
template = env.get_template("config/acl.j2")

# Render template
content = template.render(
    acls=acl_list,
    generated_at=datetime.now(),
    config_version="1.0",
    include_predefined_acls=True,
    include_security_acls=True,
    trusted_networks=["192.168.0.0/16", "10.0.0.0/8"],
    management_networks=["192.168.1.0/24"],
    dns_servers=["192.168.1.10", "192.168.1.11"]
)

# Write to BIND9 configuration file
with open("/etc/bind/acl.conf", "w") as f:
    f.write(content)
```

## forwarders.j2

Generates conditional forwarding configuration for BIND9 based on forwarder data from the database.

### Template Variables

- `forwarders`: List of forwarder objects from the database
- `generated_at`: Timestamp when the configuration was generated
- `config_version`: Version of the configuration format

### Forwarder Object Structure

Each forwarder object should contain:

```python
{
    "id": int,                          # Unique forwarder ID
    "name": str,                        # Human-readable name
    "forwarder_type": str,              # Type: active_directory, intranet, public
    "description": str,                 # Optional description
    "is_active": bool,                  # Whether forwarder is active
    "health_check_enabled": bool,       # Whether health checking is enabled
    "domains": List[str],               # List of domains to forward
    "servers": List[dict],              # List of DNS servers
    "created_at": datetime,             # Creation timestamp
    "updated_at": datetime              # Last update timestamp
}
```

### Server Object Structure

Each server in the `servers` list should contain:

```python
{
    "ip": str,          # IP address of the DNS server
    "port": int,        # Port number (default: 53)
    "priority": int     # Priority for ordering (lower = higher priority)
}
```

### Generated Configuration

The template generates BIND9 zone forwarding configuration with:

- Header comments with generation info
- Separate sections for each active forwarder
- Zone declarations for each domain
- Forwarder server lists with priorities
- Type-specific settings (AD, intranet, public)
- Proper BIND9 syntax and formatting

### Forwarder Types

- **active_directory**: Uses `forward first` and `check-names ignore` for AD compatibility
- **intranet**: Uses `forward only` for internal-only resolution
- **public**: Uses `forward first` to allow fallback to root servers

### Example Output

```bind
//
// CONDITIONAL FORWARDING CONFIGURATION
// Generated automatically by Hybrid DNS Server
// Generated at: 2024-01-20 10:30:00
// Configuration version: 1.0
//

// ============================================================================
// Active Directory (ACTIVE_DIRECTORY)
// ============================================================================
// Description: Forward AD queries to domain controllers
// Health Check: Enabled
// Created: 2024-01-01 10:00:00
// Last Updated: 2024-01-15 14:30:00

zone "company.local" {
    type forward;
    forward only;
    forwarders {
        192.168.1.10;
        192.168.1.11;  // Priority 2
    };
    // Active Directory specific settings
    forward first;
    check-names ignore;
};
```

### Usage in Code

```python
from jinja2 import Environment, FileSystemLoader

# Set up Jinja2 environment
env = Environment(loader=FileSystemLoader("templates"))
template = env.get_template("config/forwarders.j2")

# Render template
content = template.render(
    forwarders=forwarder_list,
    generated_at=datetime.now(),
    config_version="1.0"
)

# Write to BIND9 configuration file
with open("/etc/bind/forwarders.conf", "w") as f:
    f.write(content)
```
## 
statistics.j2

Generates BIND9 statistics configuration for monitoring and performance analysis.

### Template Variables

- `statistics_channels`: List of statistics channel objects from the database
- `generated_at`: Timestamp when the configuration was generated
- `config_version`: Version of the configuration format
- `enable_zone_statistics`: Boolean to enable per-zone statistics (default: true)
- `enable_server_statistics`: Boolean to enable server-wide statistics (default: true)
- `enable_mem_statistics`: Boolean to enable memory statistics (default: false)
- `enable_network_stats`: Boolean to enable network access to statistics (default: false)
- `enable_monitoring_stats`: Boolean to enable monitoring system access (default: false)
- `local_stats_port`: Port for localhost statistics access (default: 8053)
- `network_stats_port`: Port for network statistics access (default: 8053)
- `monitoring_stats_port`: Port for monitoring system access (default: 8053)
- `trusted_networks`: List of trusted network ranges for statistics access
- `management_networks`: List of management network configurations
- `monitoring_systems`: List of monitoring system configurations
- `monitoring_ips`: List of monitoring system IP addresses

### Statistics Channel Object Structure

Each statistics channel object should contain:

```python
{
    "id": int,                          # Unique channel ID
    "name": str,                        # Channel name for identification
    "description": str,                 # Optional description
    "address": str,                     # IP address to bind to (default: 127.0.0.1)
    "port": int,                        # Port number (default: 8053)
    "enabled": bool,                    # Whether channel is active
    "allowed_ips": List[str],           # List of allowed IP addresses/networks
    "created_at": datetime,             # Creation timestamp
    "updated_at": datetime              # Last update timestamp
}
```

### Management Network Object Structure

Each management network object should contain:

```python
{
    "interface": str,           # Network interface or IP (default: "*")
    "port": int,               # Port number (default: 8053)
    "allowed_networks": List[str]  # List of allowed networks
}
```

### Monitoring System Object Structure

Each monitoring system object should contain:

```python
{
    "ip": str,                 # IP address of monitoring system
    "interface": str,          # Network interface (default: "*")
    "port": int               # Port number (default: 8053)
}
```

### Generated Configuration

The template generates BIND9 statistics configuration with:

- Header comments with generation info
- Statistics channels for HTTP/XML access
- Access control lists for security
- Zone, server, and memory statistics options
- Comprehensive documentation and usage examples
- Security best practices and troubleshooting guides

### Statistics Types

- **Zone Statistics**: Per-zone query counts and response codes
- **Server Statistics**: Overall server performance metrics
- **Memory Statistics**: Detailed memory usage information
- **Resolver Statistics**: Recursive query performance
- **Cache Statistics**: Cache hit/miss ratios and efficiency

### Access Endpoints

- `/xml/v3/server` - Server-wide statistics and counters
- `/xml/v3/zones` - Per-zone statistics and query counts
- `/xml/v3/mem` - Memory usage and allocation statistics
- `/xml/v3/status` - Server status and configuration info
- `/json/v1/server` - JSON format server statistics (if supported)
- `/json/v1/zones` - JSON format zone statistics (if supported)

### Example Output

```bind
//
// STATISTICS CONFIGURATION
// Generated automatically by Hybrid DNS Server
// Generated at: 2024-01-20 10:30:00
// Configuration version: 1.0
//

// ============================================================================
// STATISTICS CHANNELS CONFIGURATION
// ============================================================================

statistics-channels {
    // Local statistics access (localhost only)
    inet 127.0.0.1 port 8053 allow { 
        127.0.0.1; 
        ::1; 
    };
    
    // Network statistics access (internal networks)
    inet * port 8053 allow { 
        127.0.0.1; 
        192.168.0.0/16; 
        10.0.0.0/8; 
        172.16.0.0/12; 
    };
};

// ============================================================================
// STATISTICS COLLECTION CONFIGURATION
// ============================================================================

// Zone statistics collection
zone-statistics yes;

// Server statistics collection  
server-statistics yes;

// Memory statistics collection
memstatistics no;
```

### Usage in Code

```python
from jinja2 import Environment, FileSystemLoader

# Set up Jinja2 environment
env = Environment(loader=FileSystemLoader("templates"))
template = env.get_template("config/statistics.j2")

# Render template
content = template.render(
    generated_at=datetime.now(),
    config_version="1.0",
    enable_zone_statistics=True,
    enable_server_statistics=True,
    enable_mem_statistics=False,
    enable_network_stats=True,
    trusted_networks=["127.0.0.1", "192.168.0.0/16", "10.0.0.0/8"],
    local_stats_port=8053,
    network_stats_port=8053
)

# Write to BIND9 configuration file
with open("/etc/bind/statistics.conf", "w") as f:
    f.write(content)
```

### Security Considerations

- Statistics reveal server configuration and usage patterns
- Restrict access to trusted networks only
- Monitor for unauthorized access attempts
- Consider firewall rules for statistics ports
- Use localhost access when possible for better security

### Integration Examples

- **Prometheus**: Use bind_exporter for metrics collection
- **Grafana**: Create dashboards from statistics data
- **Nagios/Icinga**: Monitor specific statistics thresholds
- **Custom Scripts**: Parse XML/JSON for automated monitoring