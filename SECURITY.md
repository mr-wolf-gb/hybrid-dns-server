# Security Policy

## Supported Versions

We actively maintain and provide security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of the Hybrid DNS Server seriously. If you discover a security vulnerability, please follow these guidelines:

### How to Report

1. **DO NOT** create a public GitHub issue for security vulnerabilities
2. Send an email to the project maintainers with details about the vulnerability
3. Include the following information:
   - Description of the vulnerability
   - Steps to reproduce the issue
   - Potential impact assessment
   - Suggested fix (if available)

### What to Expect

- **Acknowledgment**: We will acknowledge receipt of your vulnerability report within 48 hours
- **Initial Assessment**: We will provide an initial assessment within 5 business days
- **Updates**: We will keep you informed of our progress throughout the investigation
- **Resolution**: We aim to resolve critical vulnerabilities within 30 days

### Security Best Practices

When deploying the Hybrid DNS Server, please follow these security recommendations:

#### Network Security
- Deploy behind a firewall with restricted access
- Use VPN or private networks for administrative access
- Implement network segmentation
- Monitor DNS traffic for anomalies

#### Authentication & Access Control
- Enable 2FA for all administrative accounts
- Use strong, unique passwords
- Regularly rotate authentication credentials
- Implement role-based access control
- Review user permissions regularly

#### System Security
- Keep the system and all dependencies updated
- Use HTTPS/TLS for all web interfaces
- Configure proper SSL/TLS certificates
- Enable audit logging
- Regularly backup configurations

#### DNS Security
- Enable DNSSEC where appropriate
- Configure proper ACLs for zone transfers
- Implement rate limiting
- Monitor for DNS tunneling attempts
- Use Response Policy Zones (RPZ) for threat blocking

#### Container Security (if using Docker)
- Use official base images
- Regularly update container images
- Scan images for vulnerabilities
- Run containers with minimal privileges
- Use secrets management for sensitive data

### Security Features

The Hybrid DNS Server includes several built-in security features:

- **JWT Authentication**: Secure token-based authentication
- **Rate Limiting**: Protection against brute force attacks
- **Input Validation**: Comprehensive validation of all inputs
- **Audit Logging**: Complete audit trail of all actions
- **RBAC**: Role-based access control system
- **RPZ Support**: DNS-based threat blocking
- **Security Headers**: Proper HTTP security headers
- **Session Management**: Secure session handling

### Known Security Considerations

- This software is designed for internal/private network use
- Ensure proper network isolation when deployed
- Regular security assessments are recommended
- Monitor logs for suspicious activities
- Keep threat intelligence feeds updated

### Vulnerability Disclosure Timeline

1. **Day 0**: Vulnerability reported
2. **Day 1-2**: Acknowledgment sent
3. **Day 3-7**: Initial assessment and triage
4. **Day 8-30**: Investigation and fix development
5. **Day 31+**: Public disclosure (after fix is available)

### Security Updates

Security updates will be:
- Released as soon as possible after verification
- Clearly marked in release notes
- Accompanied by upgrade instructions
- Communicated through project channels

### Scope

This security policy covers:
- The core Hybrid DNS Server application
- Official Docker images
- Installation scripts and documentation
- Default configurations

This policy does not cover:
- Third-party dependencies (report to respective projects)
- User-modified configurations
- Custom deployments or integrations

### Contact Information

For security-related inquiries:
- Create a private security advisory on GitHub
- Contact project maintainers through the repository
- Use encrypted communication when possible

Thank you for helping keep the Hybrid DNS Server secure!