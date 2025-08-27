# DNS Diagnostic Tools

A comprehensive set of diagnostic and testing tools for DNS resolution, network connectivity, zone validation, forwarder testing, and threat detection.

## Features

### 🔍 DNS Lookup Tool
- **Purpose**: Resolve DNS records for any domain with detailed information
- **Features**:
  - Support for all major DNS record types (A, AAAA, CNAME, MX, TXT, NS, SOA, PTR, SRV, CAA)
  - Custom nameserver specification
  - Configurable timeout settings
  - Response time measurement
  - TTL and canonical name information
  - Query history tracking

### 🌐 Ping Test Tool
- **Purpose**: Test network connectivity and latency to any host
- **Features**:
  - Configurable packet count and timeout
  - Packet loss calculation
  - Response time statistics (min/max/avg)
  - Cross-platform support (Windows/Linux)
  - Raw output display
  - Test history tracking

### 🏗️ Zone Testing Tool
- **Purpose**: Validate DNS zone configuration and health
- **Features**:
  - SOA record validation and detailed information
  - NS record enumeration
  - Zone transfer (AXFR) security check
  - DNSSEC validation
  - Zone health assessment
  - Security feature analysis

### ☁️ Forwarder Test Tool
- **Purpose**: Test DNS forwarder configuration and functionality
- **Features**:
  - Forwarder connectivity testing
  - Resolution verification
  - Expected result validation
  - Response time measurement
  - Troubleshooting guidance
  - Test history tracking

### 🛡️ Threat & URL Test Tool
- **Purpose**: Check domains and URLs for threats and RPZ blocking
- **Features**:
  - RPZ rule matching detection
  - DNS-based threat detection
  - Threat categorization
  - Reputation scoring
  - Security assessment
  - URL analysis support

### 📊 Network Information Tool
- **Purpose**: Display system network configuration and DNS settings
- **Features**:
  - System DNS server detection
  - Network interface enumeration
  - IPv4/IPv6 address listing
  - Private/public IP classification
  - Network configuration summary
  - Real-time refresh capability

## API Endpoints

All diagnostic tools are accessible via REST API endpoints under `/api/diagnostics/`:

- `POST /api/diagnostics/dns-lookup` - DNS resolution testing
- `POST /api/diagnostics/ping` - Network connectivity testing
- `POST /api/diagnostics/zone-test` - DNS zone validation
- `POST /api/diagnostics/forwarder-test` - Forwarder functionality testing
- `POST /api/diagnostics/threat-test` - Threat and security testing
- `GET /api/diagnostics/network-info` - Network configuration information

## Usage

### Accessing Diagnostic Tools

1. Navigate to the **Diagnostic Tools** page in the web interface
2. Select the desired diagnostic tool from the available options
3. Configure the test parameters
4. Execute the test and review results
5. View historical test results for comparison

### DNS Lookup Example

```json
{
  "hostname": "example.com",
  "record_type": "A",
  "nameserver": "8.8.8.8",
  "timeout": 5
}
```

### Ping Test Example

```json
{
  "target": "google.com",
  "count": 4,
  "timeout": 5
}
```

### Zone Test Example

```json
{
  "zone_name": "example.com",
  "nameserver": "ns1.example.com"
}
```

## Security Considerations

- **Input Validation**: All inputs are validated for proper format and security
- **Rate Limiting**: API endpoints are protected against abuse
- **Authentication**: All diagnostic tools require valid authentication
- **Network Safety**: Tests are designed to be non-intrusive and safe
- **Privacy**: No sensitive information is logged or stored

## Troubleshooting

### Common Issues

1. **DNS Resolution Failures**
   - Check network connectivity
   - Verify nameserver accessibility
   - Confirm domain name spelling
   - Test with known working DNS servers

2. **Ping Test Failures**
   - Verify target host is reachable
   - Check firewall rules
   - Confirm network routing
   - Test with IP addresses directly

3. **Zone Test Issues**
   - Ensure zone exists and is properly configured
   - Verify nameserver authority
   - Check DNS propagation
   - Validate zone file syntax

4. **Forwarder Problems**
   - Confirm forwarder IP is correct
   - Test forwarder accessibility
   - Check DNS forwarding configuration
   - Verify network connectivity

5. **Threat Detection Issues**
   - Ensure RPZ rules are properly configured
   - Check threat feed updates
   - Verify DNS blocking mechanisms
   - Test with known malicious domains

### Performance Tips

- Use specific nameservers for faster resolution
- Adjust timeout values based on network conditions
- Monitor test history for patterns
- Regular zone validation for proactive maintenance
- Periodic forwarder testing for reliability

## Integration

The diagnostic tools integrate seamlessly with the existing DNS server management system:

- **Real-time Updates**: Results can be viewed in real-time dashboards
- **Event Logging**: All diagnostic activities are logged for audit purposes
- **Health Monitoring**: Results contribute to overall system health assessment
- **Reporting**: Diagnostic data can be included in system reports
- **Automation**: API endpoints enable automated testing and monitoring

## Technical Implementation

### Backend Components

- **FastAPI Endpoints**: RESTful API for all diagnostic functions
- **DNS Resolution**: Uses `dnspython` library for DNS operations
- **Network Testing**: Cross-platform ping implementation
- **System Information**: Uses `psutil` for network interface data
- **Input Validation**: Comprehensive validation using Pydantic models
- **Error Handling**: Robust error handling and user-friendly messages

### Frontend Components

- **React Components**: Modern, responsive UI components
- **Real-time Updates**: Live result display and history tracking
- **Form Validation**: Client-side validation with helpful error messages
- **Responsive Design**: Works on desktop and mobile devices
- **Accessibility**: WCAG compliant interface design

### Dependencies

**Backend:**
- `dnspython` - DNS resolution and query operations
- `psutil` - System and network information
- `requests` - HTTP client for URL testing
- `asyncio` - Asynchronous operations
- `ipaddress` - IP address validation and manipulation

**Frontend:**
- `react-hook-form` - Form handling and validation
- `@heroicons/react` - Icon components
- `react-toastify` - User notifications
- `axios` - HTTP client for API communication

## Future Enhancements

- **Batch Testing**: Support for testing multiple targets simultaneously
- **Scheduled Tests**: Automated periodic testing with alerting
- **Advanced Analytics**: Trend analysis and performance insights
- **Export Functionality**: Export test results in various formats
- **Custom Test Suites**: User-defined test combinations
- **Integration APIs**: Webhooks and external system integration
- **Mobile App**: Native mobile application for on-the-go diagnostics