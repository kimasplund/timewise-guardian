# Timewise Guardian Linux Client

A Linux client for monitoring computer usage and integrating with Home Assistant's Timewise Guardian component.

## Features

- Monitor active windows and applications
- Track browser history and categorize web content
- Support for time limits and restrictions
- Real-time notifications
- Integration with Home Assistant
- Runs as a systemd service
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
   sudo timewise-guardian-client --install
   ```
4. Start the service:
   ```bash
   sudo systemctl start timewise-guardian
   ```

### Dependencies

#### Debian/Ubuntu
```bash
sudo apt-get update
sudo apt-get install python3-pip python3-venv python3-dev wmctrl python3-dbus
```

#### Fedora/RHEL
```bash
sudo dnf install python3-pip python3-devel wmctrl python3-dbus
```

#### Arch Linux
```bash
sudo pacman -S python-pip wmctrl python-dbus
```

## Configuration

1. The configuration file is located at:
   ```
   /etc/timewise-guardian/config.yaml
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
- `/var/log/timewise-guardian/client.log`
- System journal (`journalctl -u timewise-guardian`)

### Commands
```bash
# Start service
sudo systemctl start timewise-guardian

# Stop service
sudo systemctl stop timewise-guardian

# Restart service
sudo systemctl restart timewise-guardian

# Check status
sudo systemctl status timewise-guardian

# View logs
sudo journalctl -u timewise-guardian -f
```

## Manual Usage (without service)

Run the client directly:

```bash
timewise-guardian-client
```

Or with a custom config path:

```bash
timewise-guardian-client -c /path/to/config.yaml
```

Enable debug logging:

```bash
timewise-guardian-client --debug
```

## Uninstallation

```bash
# Uninstall service
sudo timewise-guardian-client --uninstall

# Remove package
sudo pip3 uninstall timewise-guardian-client
```

## Requirements

- Linux distribution with systemd
- Python 3.8 or later
- Root privileges for service installation
- X11 or Wayland
- Home Assistant with Timewise Guardian integration installed

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
   - Check service logs: `journalctl -u timewise-guardian -n 50`
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
timewise-guardian-client --debug
```

### Security
The service implements several security measures:
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