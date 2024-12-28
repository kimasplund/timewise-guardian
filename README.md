# Timewise Guardian

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![My Home Assistant](https://img.shields.io/badge/My-Home%20Assistant-41BDF5.svg?style=for-the-badge)](https://my.home-assistant.io/redirect/integration_repository/?repository=timewise-guardian)

A Home Assistant integration for monitoring and managing computer usage time with granular control over applications and web content.

## Quick Install

1. Click the My Home Assistant button above, or
2. Add through HACS (search for "Timewise Guardian")

All required frontend dependencies (Mini Graph Card, ApexCharts Card, and Mushroom Cards) will be installed automatically.

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=twg)

## Features

- Monitor active users on Windows and Linux computers
- Track application usage and categorize activities
- Set time limits for different activity categories
- Granular control over web content categorization
- Real-time notifications for time limits
- Integration with Home Assistant for automation
- Beautiful dashboards and monitoring interfaces

## Installation

### HACS (Recommended)

1. Add this repository to HACS as a custom repository
2. Install the "Timewise Guardian" integration
3. Install required custom cards:
   - [Mini Graph Card](https://github.com/kalkih/mini-graph-card)
   - [ApexCharts Card](https://github.com/RomRider/apexcharts-card)
   - [Mushroom Cards](https://github.com/piitaya/lovelace-mushroom)
4. Restart Home Assistant
5. Add the integration through the Home Assistant UI

### Manual Installation

1. Copy the `custom_components/twg` directory to your Home Assistant `custom_components` directory
2. Install required custom cards (see above)
3. Restart Home Assistant
4. Add the integration through the Home Assistant UI

## Client Installation

### Windows Client

```powershell
# Basic installation
.\install.ps1 -HAUrl "http://your-ha-instance:8123" -HAToken "your_token"

# With debug logging
.\install.ps1 -HAUrl "http://your-ha-instance:8123" -HAToken "your_token" -Debug
```

### Linux Client

```bash
# Basic installation
sudo HA_URL="http://your-ha-instance:8123" HA_TOKEN="your_token" ./install.sh

# With debug logging
sudo HA_URL="http://your-ha-instance:8123" HA_TOKEN="your_token" DEBUG=true ./install.sh
```

## Configuration

1. Install the Home Assistant integration
2. Configure the client on your computer
3. Set up activity categories and time limits
4. Configure notification preferences

## Dashboards

TimeWise Guardian provides three dashboard options:

### 1. YAML Dashboard
A traditional Home Assistant dashboard with:
- User activity overview
- Time limit gauges
- Weekly statistics
- Notification history
- Usage trends

To enable:
```yaml
# configuration.yaml
lovelace:
  mode: yaml
  dashboards:
    twg:
      mode: yaml
      title: TimeWise Guardian
      icon: mdi:clock-time-eight
      show_in_sidebar: true
      filename: custom_components/twg/dashboards/twg_dashboard.yaml
```

### 2. Lovelace UI Dashboard
A modern Mushroom-style dashboard with:
- Overview tab with current status
- Statistics tab with detailed analytics
- Settings tab for configuration
- Interactive charts and system information

### 3. Custom Activity Card
A specialized card showing:
- Real-time activity monitoring
- Progress bars for time limits
- Color-coded status indicators
- Responsive grid layout

To use the custom card:
```yaml
# configuration.yaml
frontend:
  extra_module_url:
    - /local/twg-activity-card.js
```

Example card configuration:
```yaml
type: custom:twg-activity-card
activity_entity: sensor.twg_activity
time_entity: sensor.twg_time_remaining
```

## Monitoring Features

- Real-time activity tracking
- Time limit management
- Usage statistics and trends
- Category-based monitoring
- Web content classification
- Application tracking
- User session monitoring
- Notification system

## Uninstallation

### Windows
```powershell
# Keep logs and config
.\uninstall.ps1 -KeepLogs -KeepConfig

# Remove everything
.\uninstall.ps1 -Force
```

### Linux
```bash
# Keep logs and config
sudo KEEP_LOGS=true KEEP_CONFIG=true ./uninstall.sh

# Remove everything
sudo FORCE=true ./uninstall.sh
```

## Auto-Updates

The system automatically checks for updates daily and can be configured to:
- Auto-install updates
- Use beta channel
- Customize check interval
- Backup before updating

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

- Report issues on GitHub
- Join our Discord community
- Check the documentation for detailed setup guides 