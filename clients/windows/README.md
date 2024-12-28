# Timewise Guardian Windows Client

A Windows client for monitoring computer usage and integrating with Home Assistant's Timewise Guardian component.

## Features

- Monitor active windows and applications
- Track browser history and categorize web content
- Support for time limits and restrictions
- Real-time notifications
- Integration with Home Assistant
- Runs as a Windows service with administrative privileges

## Installation

### Standard Installation
```bash
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
   python -m twg.service install
   ```
4. Start the service:
   ```powershell
   Start-Service TimeWiseGuardian
   ```

To remove the service:
```powershell
python -m twg.service remove
```

## Configuration

1. The configuration file is located at:
   ```
   C:\ProgramData\TimeWiseGuardian\config.yaml
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

## Service Logs

Service logs are stored in:
- `C:\ProgramData\TimeWiseGuardian\twg_service.log`
- Windows Event Viewer under "Applications and Services Logs"

## Manual Usage (without service)

Run the monitor directly:

```bash
twg-monitor
```

Or with a custom config path:

```bash
twg-monitor --config /path/to/config.yaml
```

## Requirements

- Windows 10 or later
- Python 3.8 or later
- Administrative privileges for service installation
- Home Assistant with Timewise Guardian integration installed

## Development

1. Clone the repository
2. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```
3. Run tests:
   ```bash
   pytest
   ```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 