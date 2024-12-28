"""Models for Timewise Guardian."""
from dataclasses import dataclass
from typing import Dict, List, Optional
from homeassistant.helpers.storage import Store

@dataclass
class TimeRestriction:
    """Time restriction model."""
    days: List[str]
    start_time: str
    end_time: str
    category: str

@dataclass
class Category:
    """Category model."""
    name: str
    processes: List[str]
    window_titles: List[str]
    urls: List[str]
    time_limit: int  # minutes per day
    restrictions: List[TimeRestriction]

@dataclass
class UserConfig:
    """User configuration model."""
    name: str
    categories: Dict[str, Category]
    notifications_enabled: bool
    warning_threshold: int  # percentage

class TWGStore:
    """Class to manage Timewise Guardian storage."""
    def __init__(self, hass, config_entry_id: str) -> None:
        """Initialize storage."""
        self.hass = hass
        self._store = Store(hass, 1, f"twg.{config_entry_id}")
        self._data = {}

    async def async_load(self) -> dict:
        """Load the data."""
        data = await self._store.async_load()
        if data is not None:
            self._data = data
        return self._data

    async def async_save(self) -> None:
        """Save data to storage."""
        await self._store.async_save(self._data)

    def get_user_config(self, user_id: str) -> Optional[UserConfig]:
        """Get user configuration."""
        if user_id in self._data:
            config_dict = self._data[user_id]
            return UserConfig(**config_dict)
        return None

    async def async_update_user_config(self, user_id: str, config: UserConfig) -> None:
        """Update user configuration."""
        self._data[user_id] = {
            "name": config.name,
            "categories": config.categories,
            "notifications_enabled": config.notifications_enabled,
            "warning_threshold": config.warning_threshold,
        }
        await self.async_save() 