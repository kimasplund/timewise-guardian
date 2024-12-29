#!/bin/bash

# TimeWise Guardian Linux Installation Script

# Default values
INSTALL_DIR="/opt/timewise-guardian"
CONFIG_DIR="/etc/timewise-guardian"
LOG_DIR="/var/log/timewise-guardian"
SYSTEMD_DIR="/etc/systemd/system"
MAX_MEMORY=100
CLEANUP_INTERVAL=5
DEBUG=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --max-memory)
            MAX_MEMORY="$2"
            shift 2
            ;;
        --cleanup-interval)
            CLEANUP_INTERVAL="$2"
            shift 2
            ;;
        --debug)
            DEBUG=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root"
    exit 1
fi

# Create directories
mkdir -p "$INSTALL_DIR" "$CONFIG_DIR" "$LOG_DIR"

# Install dependencies
if command -v apt-get &> /dev/null; then
    apt-get update
    apt-get install -y python3 python3-pip libnotify-bin
elif command -v dnf &> /dev/null; then
    dnf install -y python3 python3-pip libnotify
elif command -v pacman &> /dev/null; then
    pacman -Sy python python-pip libnotify --noconfirm
else
    echo "Unsupported package manager"
    exit 1
fi

# Install Python package
pip3 install --upgrade timewise-guardian-client

# Create systemd service
cat > "$SYSTEMD_DIR/timewise-guardian.service" << EOL
[Unit]
Description=TimeWise Guardian
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/twg-service
Restart=always
RestartSec=60
User=root
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOL

# Create config file if it doesn't exist
if [ ! -f "$CONFIG_DIR/config.yaml" ]; then
    cat > "$CONFIG_DIR/config.yaml" << EOL
---
# Home Assistant connection settings
homeassistant:
  url: "http://homeassistant.local:8123"
  token: ""

# Client settings
client:
  auto_register: true
  sync_interval: 60
  memory_management:
    max_client_memory_mb: $MAX_MEMORY
    cleanup_interval_minutes: $CLEANUP_INTERVAL
    memory_threshold: 90
  notification_backend: "notify-send"
  process_monitor: "psutil"
  window_manager: "auto"

# All other settings are managed through Home Assistant
EOL

    if [ "$DEBUG" = true ]; then
        echo "logging:" >> "$CONFIG_DIR/config.yaml"
        echo "  level: DEBUG" >> "$CONFIG_DIR/config.yaml"
    fi
fi

# Set permissions
chown -R root:root "$INSTALL_DIR" "$CONFIG_DIR" "$LOG_DIR"
chmod 755 "$INSTALL_DIR" "$CONFIG_DIR" "$LOG_DIR"
chmod 644 "$CONFIG_DIR/config.yaml"

# Enable and start service
systemctl daemon-reload
systemctl enable timewise-guardian
systemctl start timewise-guardian

echo "TimeWise Guardian has been installed successfully!"
echo "Configuration file: $CONFIG_DIR/config.yaml"
echo "Log directory: $LOG_DIR"
echo "Memory limit: $MAX_MEMORY MB"
echo "Cleanup interval: $CLEANUP_INTERVAL minutes"
echo "Service status: $(systemctl is-active timewise-guardian)" 