# BIND9 Dockerfile - Custom DNS Server
FROM ubuntu:22.04

# Install BIND9 and dependencies
RUN apt-get update && apt-get install -y \
    bind9 \
    bind9utils \
    bind9-doc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create bind user and directories
RUN mkdir -p /etc/bind/zones /etc/bind/rpz /var/log/bind /var/cache/bind && \
    chown -R bind:bind /etc/bind /var/log/bind /var/cache/bind

# Copy BIND configuration files
COPY named.conf.options /etc/bind/
COPY named.conf.local /etc/bind/
COPY zones/ /etc/bind/zones/
COPY rpz/ /etc/bind/rpz/

# Set proper permissions
RUN chown -R bind:bind /etc/bind && \
    chmod 644 /etc/bind/named.conf.* && \
    chmod 644 /etc/bind/zones/* && \
    chmod 644 /etc/bind/rpz/*

# Create log files with proper permissions
RUN touch /var/log/bind/queries.log \
           /var/log/bind/security.log \
           /var/log/bind/general.log && \
    chown bind:bind /var/log/bind/*.log

# Expose DNS ports
EXPOSE 53/udp 53/tcp 953/tcp

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD dig @localhost google.com +short || exit 1

# Switch to bind user
USER bind

# Start BIND9
CMD ["/usr/sbin/named", "-g", "-c", "/etc/bind/named.conf", "-u", "bind"]