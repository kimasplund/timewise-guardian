"""Configuration handling for Timewise Guardian Client."""
import logging
from pathlib import Path
from typing import Any, Dict, Optional
import yaml

logger = logging.getLogger(__name__)

class Config:
    """Configuration handler class."""

    def __init__(self, config_path: Path):
        """Initialize configuration."""
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Load configuration from file."""
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            logger.info("Configuration loaded from %s", self.config_path)
        except FileNotFoundError:
            logger.warning("Configuration file not found at %s, using defaults", self.config_path)
            self.config = self.get_default_config()
            self.save()
        except Exception as e:
            logger.error("Error loading configuration: %s", str(e))
            raise

    def save(self) -> None:
        """Save configuration to file."""
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
            logger.info("Configuration saved to %s", self.config_path)
        except Exception as e:
            logger.error("Error saving configuration: %s", str(e))
            raise

    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "ha_url": "http://homeassistant.local:8123",
            "ha_token": "",
            "user_mapping": {},
            "categories": {
                "games": {
                    "processes": ["*.exe"],
                    "window_titles": ["*game*"],
                    "browser_patterns": {
                        "urls": ["*game*"],
                        "titles": ["*game*"]
                    }
                }
            },
            "time_limits": {
                "games": 120  # minutes
            },
            "time_restrictions": {
                "games": {
                    "weekday": {
                        "start": "15:00",
                        "end": "20:00"
                    },
                    "weekend": {
                        "start": "10:00",
                        "end": "22:00"
                    }
                }
            },
            "notifications": {
                "warning_threshold": 10,  # minutes
                "warning_intervals": [30, 15, 10, 5, 1],  # minutes
                "popup_duration": 10,  # seconds
                "sound_enabled": True
            }
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self.config[key] = value
        self.save()

    @property
    def ha_url(self) -> str:
        """Get Home Assistant URL."""
        return self.get("ha_url", "http://homeassistant.local:8123")

    @property
    def ha_token(self) -> str:
        """Get Home Assistant token."""
        return self.get("ha_token", "")

    def get_user_mapping(self, username: str) -> Optional[str]:
        """Get Home Assistant username for system username."""
        return self.get("user_mapping", {}).get(username)

    def get_category_processes(self, category: str) -> list:
        """Get process patterns for category."""
        return self.get("categories", {}).get(category, {}).get("processes", [])

    def get_category_window_titles(self, category: str) -> list:
        """Get window title patterns for category."""
        return self.get("categories", {}).get(category, {}).get("window_titles", [])

    def get_category_browser_patterns(self, category: str) -> Dict[str, list]:
        """Get browser patterns for category."""
        return self.get("categories", {}).get(category, {}).get("browser_patterns", {})

    def get_time_limit(self, category: str) -> Optional[int]:
        """Get time limit for category in minutes."""
        return self.get("time_limits", {}).get(category)

    def get_time_restrictions(self, category: str) -> Dict[str, Dict[str, str]]:
        """Get time restrictions for category."""
        return self.get("time_restrictions", {}).get(category, {}) 