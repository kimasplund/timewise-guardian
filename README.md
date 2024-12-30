# Timewise Guardian

A computer usage monitoring and time management client for Home Assistant.

## Installation

```bash
pip install timewise-guardian
```

## Quick Start

The simplest way to start is to run:

```bash
timewise-guardian -c homeassistant.local:8123
```

This will:
1. Connect to your Home Assistant instance
2. Detect the current system user
3. Open a browser for authentication
4. Save the configuration automatically
5. Start monitoring

The client creates a unique computer user entity in Home Assistant that combines both the computer name and system username (e.g., `sensor.twg_desktop_john` for user "john" on computer "desktop").

## Command Line Options

```bash
timewise-guardian [OPTIONS]
  -c, --connect URL     Connect to Home Assistant instance (e.g., homeassistant.local:8123)
  -n, --name NAME      Set computer name (default: hostname)
  -u, --user USER      Override system username (default: current user)
  -i, --interval SECS  Set sync interval in seconds (default: 30)
  --config PATH        Use custom config file
  --debug             Enable debug logging
```

### Examples

Connect with custom computer name:
```bash
timewise-guardian -c homeassistant.local:8123 -n desktop-pc
```

Connect with different system user:
```bash
timewise-guardian -c homeassistant.local:8123 -u different-user
```

## User Management

The client creates unique computer user entities in Home Assistant that combine:
- Computer identifier (hostname or custom name)
- System username

This allows:
- Multiple computers with the same username (e.g., `twg_desktop_john`, `twg_laptop_john`)
- Different usernames on the same computer (e.g., `twg_desktop_john`, `twg_desktop_jane`)
- Alternative usernames for the same person (e.g., `twg_desktop_john`, `twg_shared_johnnyboy`)

Each computer user entity can be mapped to a Home Assistant user through the UI, enabling:
- One Home Assistant user to have multiple computer users
- Different permissions per computer user
- Tracking activity across multiple computers
- User-specific time limits and restrictions

### Example Scenarios

1. Same person, different computers:
   ```
   twg_desktop_john -> maps to -> HA user "John"
   twg_laptop_john -> maps to -> HA user "John"
   ```

2. Same person, different usernames:
   ```
   twg_desktop_john -> maps to -> HA user "John"
   twg_shared_johnnyboy -> maps to -> HA user "John"
   ```

3. Different people sharing a computer:
   ```
   twg_desktop_john -> maps to -> HA user "John"
   twg_desktop_jane -> maps to -> HA user "Jane"
   ```

## Manual Configuration

If you prefer manual configuration, create a YAML file at:
- Windows: `%APPDATA%/timewise-guardian/config.yaml`
- Linux: `~/.config/timewise-guardian/config.yaml`
- macOS: `~/Library/Application Support/timewise-guardian/config.yaml`

```yaml
ha_url: "http://your-home-assistant:8123"
ha_token: "your_long_lived_access_token"
sync_interval: 30  # Update interval in seconds
computer_id: "my-computer"  # Unique identifier for this computer
system_user: "username"  # System username to monitor
```

## Home Assistant Integration

The client creates the following entities:

- `sensor.twg_[computer]_[user]`: Computer user entity (e.g., `sensor.twg_desktop_john`)
- `sensor.twg_activity`: Current computer activity state
- `sensor.twg_blocked_urls`: Recently blocked URLs
- `sensor.twg_browser_history`: Recent browser history
- `sensor.twg_memory_usage`: Client memory usage

Each computer user entity includes:
- Computer ID
- System username
- Friendly name (e.g., "John on Desktop")
- Mapped Home Assistant user (if set)
- Current state (active/idle)

Use these entities in Home Assistant automations to:
- Get notifications about blocked content
- Track computer usage time
- Set up time-based restrictions
- Monitor user activity
- Handle user-specific rules

## Development

For development setup:

```bash
git clone https://github.com/kimasplund/timewise-guardian.git
cd timewise-guardian
pip install -e ".[dev]"
pytest tests/
``` 