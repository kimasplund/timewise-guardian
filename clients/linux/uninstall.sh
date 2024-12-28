#!/bin/bash

# TimeWise Guardian Uninstallation Script
set -e

# Default values
KEEP_LOGS=${KEEP_LOGS:-false}
KEEP_CONFIG=${KEEP_CONFIG:-false}
FORCE=${FORCE:-false}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Log function
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a /var/log/twg/uninstall.log
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

# Function to backup files
backup_files() {
    local backup_dir="/root/twg_backup_$(date +%Y%m%d)"
    mkdir -p "$backup_dir"
    
    if [ "$KEEP_CONFIG" = true ] && [ -f "/etc/twg/config.yaml" ]; then
        log "Backing up configuration..."
        cp -p "/etc/twg/config.yaml" "$backup_dir/"
    fi
    
    if [ "$KEEP_LOGS" = true ] && [ -d "/var/log/twg" ]; then
        log "Backing up logs..."
        cp -rp "/var/log/twg" "$backup_dir/"
    fi
    
    if [ -d "$backup_dir" ] && [ "$(ls -A $backup_dir)" ]; then
        log "Backup created at $backup_dir"
        return 0
    fi
    return 1
}

# Main uninstallation process
log "Starting TimeWise Guardian uninstallation..."

# Stop and disable service
if systemctl is-active --quiet twg; then
    log "Stopping TWG service..."
    systemctl stop twg
fi

if systemctl is-enabled --quiet twg; then
    log "Disabling TWG service..."
    systemctl disable twg
fi

# Backup files if requested
if [ "$KEEP_LOGS" = true ] || [ "$KEEP_CONFIG" = true ]; then
    backup_files
fi

# Remove service file
if [ -f "/etc/systemd/system/twg.service" ]; then
    log "Removing systemd service..."
    rm -f "/etc/systemd/system/twg.service"
    systemctl daemon-reload
fi

# Remove virtual environment
if [ -d "/opt/twg" ]; then
    log "Removing virtual environment..."
    rm -rf "/opt/twg"
fi

# Remove configuration and logs
if [ "$KEEP_CONFIG" = false ]; then
    log "Removing configuration directory..."
    rm -rf "/etc/twg"
fi

if [ "$KEEP_LOGS" = false ]; then
    log "Removing log directory..."
    rm -rf "/var/log/twg"
fi

# Clean up system-wide Python package if installed
if command -v pip3 &> /dev/null; then
    log "Removing Python package..."
    pip3 uninstall -y timewise-guardian-client
fi

# Remove cron jobs
if [ -f "/etc/cron.d/twg" ]; then
    log "Removing cron jobs..."
    rm -f "/etc/cron.d/twg"
fi

# Clean up temporary files
log "Cleaning up temporary files..."
find /tmp -name "twg_*" -exec rm -rf {} +

# Final cleanup based on package manager
if command -v apt-get &> /dev/null; then
    log "Cleaning up Debian/Ubuntu packages..."
    apt-get autoremove -y python3-pip python3-venv
elif command -v dnf &> /dev/null; then
    log "Cleaning up Fedora/RHEL packages..."
    dnf autoremove -y python3-pip
elif command -v pacman &> /dev/null; then
    log "Cleaning up Arch Linux packages..."
    pacman -Rns --noconfirm python-pip
fi

log "${GREEN}TimeWise Guardian has been successfully uninstalled!${NC}"
if [ "$KEEP_CONFIG" = true ] || [ "$KEEP_LOGS" = true ]; then
    echo -e "\nBackups can be found in /root/twg_backup_$(date +%Y%m%d)"
fi 