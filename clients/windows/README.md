# Timewise Guardian Windows Client

A Windows client for monitoring computer usage and integrating with Home Assistant's Timewise Guardian component.

## Features

- Monitor active windows and applications
- Track browser history and categorize web content
- Support for time limits and restrictions
- Real-time notifications
- Integration with Home Assistant
- Runs as a Windows service with administrative privileges
- Automatic updates and monitoring

## Installation

### Standard Installation
```powershell
pip install timewise-guardian-client
```

### Service Installation
1. Open an Administrator PowerShell prompt
2. Install the package:
   ```powershell
   pip install timewise-guardian-client
   ```
3. Install the service:
   ```powershell
   timewise-guardian-client --install
   ```
4. Start the service:
   ```powershell
   Start-Service TimeWiseGuardian
   ```

### Automated Installation
Use the installation script for a complete setup:
```powershell
# Basic installation
.\install.ps1 -HAUrl "http://your-ha-instance:8123" -HAToken "your_token"

# With debug logging
.\install.ps1 -HAUrl "http://your-ha-instance:8123" -HAToken "your_token" -Debug
```

## Configuration

1. The configuration file is located at:
   ```
   C:\ProgramData\TimeWise Guardian\config.yaml
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
  "DESKTOP-ABC123\\JohnDoe": "john"

categories:
  games:
    processes:
      - minecraft.exe
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
- Real-time window and process monitoring
- Browser history tracking (Chrome, Firefox, Edge)
- YouTube content categorization
- Application usage statistics
- User session tracking

### Time Management
- Category-based time limits
- Time restriction schedules
- Warning notifications
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
- `C:\ProgramData\TimeWise Guardian\logs\client.log`
- Windows Event Viewer under "Applications and Services Logs"

### Commands
```powershell
# Start service
Start-Service TimeWiseGuardian

# Stop service
Stop-Service TimeWiseGuardian

# Restart service
Restart-Service TimeWiseGuardian

# Check status
Get-Service TimeWiseGuardian
```

## Manual Usage (without service)

Run the client directly:

```powershell
timewise-guardian-client
```

Or with a custom config path:

```powershell
timewise-guardian-client -c C:\path\to\config.yaml
```

Enable debug logging:

```powershell
timewise-guardian-client --debug
```

## Uninstallation

```powershell
# Uninstall service
timewise-guardian-client --uninstall

# Remove package
pip uninstall timewise-guardian-client
```

## Requirements

- Windows 10 or later
- Python 3.8 or later
- Administrative privileges for service installation
- Home Assistant with Timewise Guardian integration installed

## Development

1. Clone the repository
2. Create virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   ```
3. Install development dependencies:
   ```powershell
   pip install -e ".[dev]"
   ```
4. Run tests:
   ```powershell
   pytest
   ```

## Troubleshooting

### Common Issues
1. Service won't start:
   - Check service logs
   - Verify Python installation
   - Check configuration file permissions
   - Verify service configuration

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

### Debug Mode
Enable debug logging:
```powershell
timewise-guardian-client --debug
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 