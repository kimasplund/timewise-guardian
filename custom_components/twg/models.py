"""Models for Timewise Guardian."""
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from datetime import datetime
from homeassistant.helpers.storage import Store

@dataclass
class TimeRestriction:
    """Time restriction model."""
    days: List[str]
    start_time: str
    end_time: str
    category: str

    @classmethod
    def from_dict(cls, data: dict) -> "TimeRestriction":
        """Create instance from dictionary."""
        return cls(
            days=data["days"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            category=data["category"]
        )

@dataclass
class Category:
    """Category model."""
    name: str
    processes: List[str]
    window_titles: List[str]
    urls: List[str]
    time_limit: int  # minutes per day
    restrictions: List[TimeRestriction]

    @classmethod
    def from_dict(cls, data: dict) -> "Category":
        """Create instance from dictionary."""
        return cls(
            name=data["name"],
            processes=data["processes"],
            window_titles=data["window_titles"],
            urls=data["urls"],
            time_limit=data["time_limit"],
            restrictions=[TimeRestriction.from_dict(r) for r in data["restrictions"]]
        )

@dataclass
class UserConfig:
    """User configuration model."""
    name: str
    categories: Dict[str, Category]
    notifications_enabled: bool
    warning_threshold: int  # percentage

    @classmethod
    def from_dict(cls, data: dict) -> "UserConfig":
        """Create instance from dictionary."""
        return cls(
            name=data["name"],
            categories={
                name: Category.from_dict(cat_data)
                for name, cat_data in data["categories"].items()
            },
            notifications_enabled=data["notifications_enabled"],
            warning_threshold=data["warning_threshold"]
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "categories": {
                name: asdict(category)
                for name, category in self.categories.items()
            },
            "notifications_enabled": self.notifications_enabled,
            "warning_threshold": self.warning_threshold
        }

@dataclass
class ActiveUser:
    """Active user model."""
    name: str
    computer_id: str
    session_start: datetime

class TWGStore:
    """Class to manage Timewise Guardian storage."""
    def __init__(self, hass, config_entry_id: str) -> None:
        """Initialize storage."""
        self.hass = hass
        self._store = Store(hass, 1, f"twg.{config_entry_id}")
        self._data = {}
        self._active_users = {}
        self._current_activities = {}
        self._time_limits = {}

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
            return UserConfig.from_dict(self._data[user_id])
        return None

    async def async_update_user_config(self, user_id: str, config: UserConfig) -> None:
        """Update user configuration."""
        self._data[user_id] = config.to_dict()
        await self.async_save()

    async def get_active_user(self) -> Optional[ActiveUser]:
        """Get the currently active user."""
        # This would typically be updated by your Windows client
        # For now, return the first active user if any exist
        return next(iter(self._active_users.values())) if self._active_users else None

    async def get_current_activity(self) -> Optional[dict]:
        """Get the current activity."""
        # This would typically be updated by your Windows client
        # For now, return the first activity if any exist
        return next(iter(self._current_activities.values())) if self._current_activities else None

    async def get_time_limits(self) -> Optional[dict]:
        """Get the current time limits."""
        # This would typically be calculated based on usage data from your Windows client
        # For now, return the first time limit if any exist
        return next(iter(self._time_limits.values())) if self._time_limits else None

    async def update_active_user(self, user_id: str, computer_id: str) -> None:
        """Update the active user."""
        config = self.get_user_config(user_id)
        if config:
            self._active_users[computer_id] = ActiveUser(
                name=config.name,
                computer_id=computer_id,
                session_start=datetime.now()
            )

    async def update_activity(self, computer_id: str, activity: dict) -> None:
        """Update the current activity."""
        self._current_activities[computer_id] = activity

    async def update_time_limits(self, computer_id: str, limits: dict) -> None:
        """Update time limits."""
        self._time_limits[computer_id] = limits 