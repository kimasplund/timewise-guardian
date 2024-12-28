#!/bin/bash

# TimeWise Guardian Installation Script
set -e

# Default values
HA_URL=${HA_URL:-"http://homeassistant.local:8123"}
HA_TOKEN=${HA_TOKEN:-""}
FORCE=${FORCE:-false}
DEBUG=${DEBUG:-false}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Log function
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a /var/log/twg/install.log
}

# Error handler
error() {
    log "${RED}Error: $1${NC}"
    exit 1
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    error "Please run as root"
fi

# Create necessary directories
mkdir -p /var/log/twg
mkdir -p /etc/twg

# Install Python and dependencies
log "Installing system dependencies..."
if command -v apt-get &> /dev/null; then
    # Debian/Ubuntu
    apt-get update
    apt-get install -y python3 python3-pip python3-venv python3-dev
elif command -v dnf &> /dev/null; then
    # Fedora/RHEL
    dnf install -y python3 python3-pip python3-devel
elif command -v pacman &> /dev/null; then
    # Arch Linux
    pacman -Sy --noconfirm python python-pip
else
    error "Unsupported package manager"
fi

# Create virtual environment
log "Creating virtual environment..."
python3 -m venv /opt/twg
source /opt/twg/bin/activate

# Install/upgrade pip
log "Upgrading pip..."
pip install --upgrade pip

# Install TimeWise Guardian
log "Installing TimeWise Guardian..."
pip install --upgrade timewise-guardian-client

# Create configuration
if [ ! -f "/etc/twg/config.yaml" ] || [ "$FORCE" = true ]; then
    log "Creating configuration file..."
    cat > /etc/twg/config.yaml << EOF
ha_url: "${HA_URL}"
ha_token: "${HA_TOKEN}"

user_mapping:
  "$(whoami)": "$(whoami)"

categories:
  games:
    processes:
      - minecraft
      - steam
    browser_patterns:
      urls:
        - "*minecraft.net*"
        - "*steampowered.com*"

time_limits:
  games: 120  # 2 hours per day

notifications:
  warning_threshold: 10
  warning_intervals: [30, 15, 10, 5, 1]
  popup_duration: 10
  sound_enabled: true
EOF

    if [ "$DEBUG" = true ]; then
        echo -e "\nlogging:\n  level: DEBUG" >> /etc/twg/config.yaml
    fi
fi

# Create systemd service
log "Installing systemd service..."
cat > /etc/systemd/system/twg.service << EOF
[Unit]
Description=TimeWise Guardian Monitor
After=network.target

[Service]
Type=simple
User=root
Group=root
Environment=PYTHONUNBUFFERED=1
ExecStart=/opt/twg/bin/twg-monitor --config /etc/twg/config.yaml
Restart=always
RestartSec=5
StandardOutput=append:/var/log/twg/monitor.log
StandardError=append:/var/log/twg/error.log

# Security hardening
ProtectSystem=strict
ProtectHome=read-only
PrivateTmp=true
NoNewPrivileges=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictNamespaces=true
MemoryDenyWriteExecute=true
RestrictRealtime=true

[Install]
WantedBy=multi-user.target
EOF

# Set permissions
log "Setting permissions..."
chmod 600 /etc/twg/config.yaml
chmod 644 /etc/systemd/system/twg.service
chown -R root:root /etc/twg
chown -R root:root /var/log/twg

# Start service
log "Starting service..."
systemctl daemon-reload
systemctl enable twg
systemctl start twg

# Check service status
if systemctl is-active --quiet twg; then
    log "${GREEN}TimeWise Guardian has been installed and started successfully!${NC}"
    echo -e "\nConfiguration file: /etc/twg/config.yaml"
    echo "Logs directory: /var/log/twg"
    echo "Service status: $(systemctl status twg | grep Active)"
else
    error "Service failed to start. Check logs at /var/log/twg/error.log"
fi

# Cleanup
deactivate 