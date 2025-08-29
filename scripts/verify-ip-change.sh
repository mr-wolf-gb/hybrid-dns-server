#!/bin/bash

# IP Change Verification Script
# Comprehensive verification of DNS server functionality after IP change

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}✓${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_WARNING=0

test_result() {
    if [[ $1 -eq 0 ]]; then
        log "$2"
        ((TESTS_PASSED++))
    else
        error "$2"
        ((TESTS_FAILED++))
    fi
}

test_warning() {
    warn "$1"
    ((TESTS_WARNING++))
}

echo "=============================================="
echo "    DNS Server IP Change Verification"
echo "=============================================="
echo

# Get current IP
CURRENT_IP=$(ip route get 8.8.8.8 | awk '{print $7; exit}' 2>/dev/null || echo "Unknown")
info "Current server IP: $CURRENT_IP"
echo

# Test 1: Network connectivity
echo "1. Testing Network Connectivity"
echo "--------------------------------"

ping -c 3 8.8.8.8 >/dev/null 2>&1
test_result $? "Internet connectivity (ping 8.8.8.8)"

ping -c 3 1.1.1.1 >/dev/null 2>&1
test_result $? "Alternative connectivity (ping 1.1.1.1)"

# Test 2: DNS Resolution
echo
echo "2. Testing DNS Resolution"
echo "-------------------------"

nslookup google.com >/dev/null 2>&1
test_result $? "External DNS resolution (google.com)"

nslookup localhost >/dev/null 2>&1
test_result $? "Local DNS resolution (localhost)"

# Test 3: BIND9 Service
echo
echo "3. Testing BIND9 Service"
echo "------------------------"

systemctl is-active --quiet bind9
test_result $? "BIND9 service is running"

systemctl is-enabled --quiet bind9
test_result $? "BIND9 service is enabled"

named-checkconf >/dev/null 2>&1
test_result $? "BIND9 configuration syntax is valid"

# Test 4: DNS Server Functionality
echo
echo "4. Testing DNS Server Functionality"
echo "------------------------------------"

if [[ "$CURRENT_IP" != "Unknown" ]]; then
    nslookup google.com $CURRENT_IP >/dev/null 2>&1
    test_result $? "DNS queries to local server ($CURRENT_IP)"
    
    dig @$CURRENT_IP google.com >/dev/null 2>&1
    test_result $? "DNS queries via dig to local server"
else
    test_warning "Cannot test local DNS server - IP unknown"
fi

# Test 5: Application Services
echo
echo "5. Testing Application Services"
echo "-------------------------------"

if systemctl list-units --type=service | grep -q hybrid-dns-backend; then
    systemctl is-active --quiet hybrid-dns-backend
    test_result $? "Backend service is running"
else
    test_warning "Backend service not installed or not found"
fi

if systemctl list-units --type=service | grep -q hybrid-dns-monitoring; then
    systemctl is-active --quiet hybrid-dns-monitoring
    test_result $? "Monitoring service is running"
else
    test_warning "Monitoring service not installed or not found"
fi

# Test 6: Web Interface Connectivity
echo
echo "6. Testing Web Interface"
echo "-------------------------"

if [[ "$CURRENT_IP" != "Unknown" ]]; then
    # Test backend API
    if curl -s --connect-timeout 5 "http://$CURRENT_IP:8000/health" >/dev/null 2>&1; then
        log "Backend API is accessible (port 8000)"
        ((TESTS_PASSED++))
    else
        error "Backend API is not accessible (port 8000)"
        ((TESTS_FAILED++))
    fi
    
    # Test frontend
    if curl -s --connect-timeout 5 "http://$CURRENT_IP:3000" >/dev/null 2>&1; then
        log "Frontend is accessible (port 3000)"
        ((TESTS_PASSED++))
    else
        error "Frontend is not accessible (port 3000)"
        ((TESTS_FAILED++))
    fi
else
    test_warning "Cannot test web interfaces - IP unknown"
fi

# Test 7: Configuration Files
echo
echo "7. Testing Configuration Files"
echo "------------------------------"

if [[ -f /etc/bind/named.conf.options ]]; then
    if grep -q "$CURRENT_IP" /etc/bind/named.conf.options 2>/dev/null; then
        log "BIND options contains current IP"
        ((TESTS_PASSED++))
    else
        test_warning "BIND options may not contain current IP"
    fi
else
    test_warning "BIND options file not found"
fi

if [[ -f /opt/hybrid-dns-server/.env ]]; then
    log "Application environment file exists"
    ((TESTS_PASSED++))
else
    test_warning "Application environment file not found"
fi

# Test 8: Log Files
echo
echo "8. Testing Log Files"
echo "--------------------"

if [[ -f /var/log/bind/bind.log ]]; then
    if tail -n 10 /var/log/bind/bind.log | grep -q "$(date +%d-%b-%Y)" 2>/dev/null; then
        log "BIND logs are being written"
        ((TESTS_PASSED++))
    else
        test_warning "BIND logs may not be current"
    fi
else
    test_warning "BIND log file not found"
fi

# Test 9: Firewall Status
echo
echo "9. Testing Firewall Configuration"
echo "---------------------------------"

if command -v ufw >/dev/null 2>&1; then
    if ufw status | grep -q "Status: active"; then
        if ufw status | grep -q "53"; then
            log "UFW firewall allows DNS traffic"
            ((TESTS_PASSED++))
        else
            test_warning "UFW may not allow DNS traffic on port 53"
        fi
    else
        info "UFW firewall is inactive"
    fi
else
    info "UFW not installed"
fi

# Test 10: Performance Check
echo
echo "10. Testing Performance"
echo "-----------------------"

if [[ "$CURRENT_IP" != "Unknown" ]]; then
    # Test DNS query response time
    RESPONSE_TIME=$(dig @$CURRENT_IP google.com | grep "Query time:" | awk '{print $4}' 2>/dev/null || echo "0")
    if [[ "$RESPONSE_TIME" -gt 0 ]] && [[ "$RESPONSE_TIME" -lt 1000 ]]; then
        log "DNS query response time: ${RESPONSE_TIME}ms"
        ((TESTS_PASSED++))
    else
        test_warning "DNS query response time may be slow or unavailable"
    fi
else
    test_warning "Cannot test DNS performance - IP unknown"
fi

# Summary
echo
echo "=============================================="
echo "              Verification Summary"
echo "=============================================="
echo
echo -e "Tests Passed:  ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests Failed:  ${RED}$TESTS_FAILED${NC}"
echo -e "Warnings:      ${YELLOW}$TESTS_WARNING${NC}"
echo

if [[ $TESTS_FAILED -eq 0 ]]; then
    log "All critical tests passed! DNS server is functioning correctly."
    echo
    info "Next steps:"
    echo "  - Update client DNS settings to point to $CURRENT_IP"
    echo "  - Update any hardcoded IP references in applications"
    echo "  - Monitor logs for any issues: journalctl -u bind9 -f"
    echo "  - Test from client machines: nslookup google.com $CURRENT_IP"
    exit 0
else
    error "Some tests failed. Please review the issues above."
    echo
    info "Troubleshooting steps:"
    echo "  - Check service status: systemctl status bind9"
    echo "  - Review logs: journalctl -u bind9 -n 50"
    echo "  - Verify configuration: named-checkconf"
    echo "  - Check network: ip addr show"
    echo "  - Consider rollback: sudo ./emergency-ip-rollback.sh"
    exit 1
fi