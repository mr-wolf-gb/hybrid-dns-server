#!/bin/bash
# Helper script to restart BIND9 service
# This script should be installed with proper permissions

set -e

# Log the restart attempt
echo "$(date): BIND9 restart requested by hybrid-dns-server" >> /var/log/hybrid-dns/bind-restart.log

# Try rndc reload first
if command -v rndc >/dev/null 2>&1; then
    if rndc reload 2>/dev/null; then
        echo "$(date): BIND9 reloaded successfully via rndc" >> /var/log/hybrid-dns/bind-restart.log
        exit 0
    fi
fi

# Fallback to systemctl restart
if command -v systemctl >/dev/null 2>&1; then
    if systemctl restart bind9 2>/dev/null; then
        echo "$(date): BIND9 restarted successfully via systemctl" >> /var/log/hybrid-dns/bind-restart.log
        exit 0
    fi
fi

# If both fail, log error
echo "$(date): BIND9 restart failed - both rndc and systemctl failed" >> /var/log/hybrid-dns/bind-restart.log
exit 1