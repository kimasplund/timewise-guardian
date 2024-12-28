"""Platform for sensor integration."""
from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from . import DOMAIN
from .models import TWGStore

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Timewise Guardian sensors."""
    name = config_entry.data[CONF_NAME]
    store = TWGStore(hass, config_entry.entry_id)
    await store.async_load()

    async_add_entities(
        [
            TWGUserSensor(name, config_entry.entry_id, store),
            TWGActivitySensor(name, config_entry.entry_id, store),
            TWGTimeLimitSensor(name, config_entry.entry_id, store),
        ]
    )

class TWGUserSensor(SensorEntity):
    """Sensor for tracking the current user."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, name: str, entry_id: str, store: TWGStore) -> None:
        """Initialize the sensor."""
        self._attr_unique_id = f"{entry_id}_user"
        self._attr_name = "Current User"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=name,
            manufacturer="Timewise Guardian",
        )
        self._store = store
        self._state: str | None = None

    @property
    def native_value(self) -> StateType:
        """Return the current user."""
        return self._state or "Unknown"

    async def async_update(self) -> None:
        """Update the sensor state."""
        # Get current active user from store
        active_user = await self._store.get_active_user()
        if active_user:
            self._state = active_user.name

class TWGActivitySensor(SensorEntity):
    """Sensor for tracking the current activity."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, name: str, entry_id: str, store: TWGStore) -> None:
        """Initialize the sensor."""
        self._attr_unique_id = f"{entry_id}_activity"
        self._attr_name = "Current Activity"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=name,
            manufacturer="Timewise Guardian",
        )
        self._store = store
        self._state: dict[str, Any] = {}

    @property
    def native_value(self) -> StateType:
        """Return the current activity."""
        return self._state.get("activity", "Idle")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        return {
            "category": self._state.get("category", "Unknown"),
            "window_title": self._state.get("window_title", ""),
            "process_name": self._state.get("process_name", ""),
            "start_time": self._state.get("start_time", datetime.now().isoformat()),
        }

    async def async_update(self) -> None:
        """Update the sensor state."""
        # Get current activity from store
        activity = await self._store.get_current_activity()
        if activity:
            self._state = activity

class TWGTimeLimitSensor(SensorEntity):
    """Sensor for tracking time limits."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "min"

    def __init__(self, name: str, entry_id: str, store: TWGStore) -> None:
        """Initialize the sensor."""
        self._attr_unique_id = f"{entry_id}_time_limit"
        self._attr_name = "Time Remaining"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=name,
            manufacturer="Timewise Guardian",
        )
        self._store = store
        self._state: dict[str, Any] = {}

    @property
    def native_value(self) -> StateType:
        """Return the remaining time."""
        return self._state.get("time_remaining", 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        return {
            "daily_limit": self._state.get("daily_limit", 0),
            "total_used_today": self._state.get("total_used_today", 0),
            "category": self._state.get("category", "Unknown"),
        }

    async def async_update(self) -> None:
        """Update the sensor state."""
        # Get time limits from store
        time_info = await self._store.get_time_limits()
        if time_info:
            self._state = time_info 