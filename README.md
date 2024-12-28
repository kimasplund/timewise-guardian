# TimeWise Guardian Client

A cross-platform client application for the TimeWise Guardian parental control system, designed to work with Home Assistant.

## Features

- Real-time monitoring of computer usage
- Process and window tracking
- Browser activity monitoring
- Integration with Home Assistant
- Cross-platform support (Windows and Linux)
- Configurable time limits and restrictions
- User activity categorization
- Notification system

## Installation

### Windows

You can install the TimeWise Guardian client using pip:

```bash
pip install timewise-guardian-client
```

Or download the latest Windows executable from the [releases page](https://github.com/kimasplund/timewise-guardian/releases).

### Linux

Install the package using pip:

```bash
pip install timewise-guardian-client
```

Or download the latest Linux executable from the [releases page](https://github.com/kimasplund/timewise-guardian/releases).

#### Linux Dependencies

On Ubuntu/Debian:

```bash
sudo apt-get install wmctrl python3-dbus
```

On Fedora:

```bash
sudo dnf install wmctrl python3-dbus
```

## Configuration

1. Create a configuration file at one of these locations:
   - Windows: `C:\ProgramData\TimeWise Guardian\config.yaml`
   - Linux: `/etc/timewise-guardian/config.yaml`
   - Or specify a custom location with the `-c` option

2. Example configuration:

```yaml
ha_url: "http://homeassistant.local:8123"
ha_token: "your_long_lived_access_token"

user_mapping:
  windows_username: "ha_username"
  linux_username: "ha_username"

categories:
  games:
    processes: ["*.exe"]
    window_titles: ["*game*"]
    browser_patterns:
      urls: ["*game*"]
      titles: ["*game*"]

time_limits:
  games: 120  # minutes

time_restrictions:
  games:
    weekday:
      start: "15:00"
      end: "20:00"
    weekend:
      start: "10:00"
      end: "22:00"

notifications:
  warning_threshold: 10  # minutes
  warning_intervals: [30, 15, 10, 5, 1]
  popup_duration: 10  # seconds
  sound_enabled: true
```

## Usage

### Running as a Service

#### Windows

Install as a service:

```bash
timewise-guardian-client --install
```

Uninstall the service:

```bash
timewise-guardian-client --uninstall
```

#### Linux

Install as a systemd service:

```bash
sudo timewise-guardian-client --install
```

Uninstall the service:

```bash
sudo timewise-guardian-client --uninstall
```

### Running Manually

Run the client with default configuration:

```bash
timewise-guardian-client
```

Specify a custom configuration file:

```bash
timewise-guardian-client -c /path/to/config.yaml
```

Enable debug logging:

```bash
timewise-guardian-client --debug
```

## Development

1. Clone the repository:

```bash
git clone https://github.com/kimasplund/timewise-guardian.git
cd timewise-guardian
```

2. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # Linux
venv\Scripts\activate     # Windows
```

3. Install development dependencies:

```bash
pip install -e ".[dev]"
```

4. Run tests:

```bash
pytest tests/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

Kim Asplund (kim.asplund@gmail.com)

## Links

- [Website](https://asplund.kim)
- [GitHub Repository](https://github.com/kimasplund/timewise-guardian)
- [Documentation](https://github.com/kimasplund/timewise-guardian/wiki) 