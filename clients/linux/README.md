# Timewise Guardian Linux Client

A Linux client for monitoring computer usage and integrating with Home Assistant's Timewise Guardian component.

## Features

- Monitor active windows and applications
- Track browser history and categorize web content
- Support for time limits and restrictions
- Real-time notifications
- Integration with Home Assistant
- Runs as a systemd service with root privileges
- Automatic updates and monitoring
- Multi-distribution support (Debian/Ubuntu, Fedora/RHEL, Arch)

## Installation

### Standard Installation
```bash
pip3 install timewise-guardian-client
```

### Service Installation
1. Open a terminal with root privileges
2. Install the package:
   ```bash
   sudo pip3 install timewise-guardian-client
   ```
3. Install the service:
   ```bash
   sudo systemctl enable twg
   ```
4. Start the service:
   ```bash
   sudo systemctl start twg
   ```

### Automated Installation
Use the installation script for a complete setup:
```bash
# Basic installation
sudo HA_URL="http://your-ha-instance:8123" HA_TOKEN="your_token" ./install.sh

# With debug logging
sudo HA_URL="http://your-ha-instance:8123" HA_TOKEN="your_token" DEBUG=true ./install.sh
```

## Configuration

1. The configuration file is located at:
   ```
   /etc/twg/config.yaml
   ```
2. Configure the following settings:
   - Home Assistant connection details
   - User mappings
   - Activity categories and patterns
   - Time limits and restrictions
   - Notification preferences

Example configuration:

```yaml
ha_url: "http://homeassistant.local:8123"
ha_token: "your_long_lived_access_token"

user_mapping:
  "username": "ha_user"

categories:
  games:
    processes:
      - minecraft
      - steam
    browser_patterns:
      urls:
        - "*minecraft.net*"
      youtube_channels:
        - "UCq6VFHwMzcMXbuKyG7SQYIg"  # Minecraft

time_limits:
  games: 120  # 2 hours per day
```

## Monitoring Features

### Activity Tracking
- Real-time window and process monitoring (X11 and Wayland support)
- Browser history tracking (Firefox, Chrome, Chromium)
- YouTube content categorization
- Application usage statistics
- User session tracking

### Time Management
- Category-based time limits
- Time restriction schedules
- Warning notifications (desktop notifications)
- Automatic enforcement

### Data Collection
- Application usage metrics
- Browser activity data
- Category statistics
- Time limit compliance

### Integration
- Real-time Home Assistant updates
- Custom sensor entities
- Dashboard integration
- Automation support

## Service Management

### Logs
Service logs are stored in:
- `/var/log/twg/monitor.log`
- `/var/log/twg/error.log`
- `/var/log/twg/twg_detailed_YYYYMMDD.log`
- System journal (`journalctl -u twg`)

### Commands
```bash
# Start service
sudo systemctl start twg

# Stop service
sudo systemctl stop twg

# Restart service
sudo systemctl restart twg

# Check status
sudo systemctl status twg

# View logs
sudo journalctl -u twg -f

# Check service configuration
sudo systemctl cat twg
```

## Auto-Updates

The client supports automatic updates:
```python
from twg.updater import TWGUpdater

updater = TWGUpdater(
    current_version="0.1.0",
    check_interval=24,  # Check every 24 hours
    auto_update=True,   # Automatically install updates
    beta_channel=False  # Use stable versions only
)
```

## Manual Usage (without service)

Run the monitor directly:

```bash
twg-monitor
```

Or with a custom config path:

```bash
twg-monitor --config /path/to/config.yaml
```

## Uninstallation

```bash
# Keep logs and config
sudo KEEP_LOGS=true KEEP_CONFIG=true ./uninstall.sh

# Remove everything
sudo FORCE=true ./uninstall.sh
```

## Requirements

- Linux distribution with systemd
- Python 3.8 or later
- Root privileges for service installation
- X11 or Wayland
- Home Assistant with Timewise Guardian integration installed

## Distribution-Specific Notes

### Debian/Ubuntu
```bash
# Install dependencies
sudo apt-get update
sudo apt-get install python3-pip python3-venv python3-dev
```

### Fedora/RHEL
```bash
# Install dependencies
sudo dnf install python3-pip python3-devel
```

### Arch Linux
```bash
# Install dependencies
sudo pacman -S python-pip
```

## Development

1. Clone the repository
2. Create virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```
4. Run tests:
   ```bash
   pytest
   ```

## Troubleshooting

### Common Issues
1. Service won't start:
   - Check service logs: `journalctl -u twg -n 50`
   - Verify Python installation
   - Check configuration file permissions
   - Verify systemd unit file

2. No data in Home Assistant:
   - Verify Home Assistant connection
   - Check API token
   - Review service logs
   - Check network connectivity

3. Browser tracking not working:
   - Ensure browser history access
   - Check browser support
   - Verify user permissions
   - Check browser profile paths

4. Desktop notifications not working:
   - Verify D-Bus configuration
   - Check notification daemon
   - Test with `notify-send`

### Debug Mode
Enable debug logging:
```bash
sudo DEBUG=true ./install.sh
```

Or edit `/etc/twg/config.yaml`:
```yaml
logging:
  level: DEBUG
```

### Security
The service runs with root privileges but implements several security measures:
- Protected system directories
- Read-only home directory access
- No new privileges
- Restricted namespaces
- Memory protections
- Real-time restrictions

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 