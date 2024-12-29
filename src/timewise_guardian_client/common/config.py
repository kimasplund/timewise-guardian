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
        self.ha_settings: Dict[str, Any] = {}  # Dynamic settings from HA
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
            "homeassistant": {
                "url": "http://homeassistant.local:8123",
                "token": ""
            },
            "client": {
                "auto_register": True,
                "sync_interval": 60,
                "memory_management": {
                    "max_client_memory_mb": 100,
                    "cleanup_interval_minutes": 5,
                    "memory_threshold": 90
                }
            }
        }

    def update_ha_settings(self, settings: Dict[str, Any]) -> None:
        """Update settings received from Home Assistant."""
        self.ha_settings = settings
        logger.debug("Updated Home Assistant settings: %s", settings)

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value, checking HA settings first."""
        # Check HA settings first for dynamic config
        if key in ["categories", "time_limits", "time_restrictions", "notifications"]:
            return self.ha_settings.get(key, default)
        # Fall back to local config for client settings
        return self.config.get("client", {}).get(key) or self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        if key in ["categories", "time_limits", "time_restrictions", "notifications"]:
            logger.warning("Cannot set %s locally, it is managed by Home Assistant", key)
            return
        self.config[key] = value
        self.save()

    @property
    def ha_url(self) -> str:
        """Get Home Assistant URL."""
        return self.config.get("homeassistant", {}).get("url", "http://homeassistant.local:8123")

    @property
    def ha_token(self) -> str:
        """Get Home Assistant token."""
        return self.config.get("homeassistant", {}).get("token", "")

    @property
    def memory_settings(self) -> Dict[str, Any]:
        """Get memory management settings."""
        return self.config.get("client", {}).get("memory_management", {})

    @property
    def sync_interval(self) -> int:
        """Get sync interval in seconds."""
        return self.config.get("client", {}).get("sync_interval", 60)

    def get_category_processes(self, category: str) -> list:
        """Get process patterns for category from HA settings."""
        return self.ha_settings.get("categories", {}).get(category, {}).get("processes", [])

    def get_category_window_titles(self, category: str) -> list:
        """Get window title patterns for category from HA settings."""
        return self.ha_settings.get("categories", {}).get(category, {}).get("window_titles", [])

    def get_category_browser_patterns(self, category: str) -> Dict[str, list]:
        """Get browser patterns for category from HA settings."""
        return self.ha_settings.get("categories", {}).get(category, {}).get("browser_patterns", {})

    def get_time_limit(self, category: str) -> Optional[int]:
        """Get time limit for category in minutes from HA settings."""
        return self.ha_settings.get("time_limits", {}).get(category)

    def get_time_restrictions(self, category: str) -> Dict[str, Dict[str, str]]:
        """Get time restrictions for category from HA settings."""
        return self.ha_settings.get("time_restrictions", {}).get(category, {}) 