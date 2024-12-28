# Timewise Guardian

A Home Assistant integration for monitoring and managing computer usage time with granular control over applications and web content.

## Features

- Monitor active users on Windows and Linux computers
- Track application usage and categorize activities
- Set time limits for different activity categories
- Granular control over web content categorization
- Real-time notifications for time limits
- Integration with Home Assistant for automation

## Installation

### HACS (Recommended)

1. Add this repository to HACS as a custom repository
2. Install the "Timewise Guardian" integration
3. Restart Home Assistant
4. Add the integration through the Home Assistant UI

### Manual Installation

1. Copy the `custom_components/twg` directory to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Add the integration through the Home Assistant UI

## Client Installation

### Windows Client

```bash
pip install timewise-guardian-client
```

### Linux Client

```bash
pip install timewise-guardian-client
```

## Configuration

1. Install the Home Assistant integration
2. Configure the client on your computer
3. Set up activity categories and time limits
4. Configure notification preferences

## Usage

The integration provides several sensors:

- Current User: Shows the active user on the monitored computer
- Current Activity: Shows the current application or website being used
- Time Remaining: Shows the remaining time for the current activity category

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 