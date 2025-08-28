#!/bin/bash

# Test script to verify BIND9 reload functionality

echo "Testing BIND9 reload functionality..."

# Test 1: Check if rndc works directly
echo "Test 1: Direct rndc reload test"
if /usr/sbin/rndc reload 2>/dev/null; then
    echo "✓ Direct rndc reload works"
else
    echo "✗ Direct rndc reload failed"
fi

# Test 2: Check if systemd reload service works
echo "Test 2: Systemd reload service test"
if systemctl start bind9-reload.service 2>/dev/null; then
    echo "✓ Systemd reload service works"
else
    echo "✗ Systemd reload service failed"
fi

# Test 3: Check if systemd restart service works
echo "Test 3: Systemd restart service test"
if systemctl start bind9-restart.service 2>/dev/null; then
    echo "✓ Systemd restart service works"
else
    echo "✗ Systemd restart service failed"
fi

# Test 4: Check service status
echo "Test 4: Service status check"
echo "Backend service status:"
systemctl is-active hybrid-dns-backend.service || echo "Backend service not running"

echo "BIND9 service status:"
systemctl is-active bind9.service 2>/dev/null || systemctl is-active named.service 2>/dev/null || echo "BIND9 service not running"

echo "Test completed."