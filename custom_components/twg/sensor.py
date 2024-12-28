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

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Timewise Guardian sensors."""
    name = config_entry.data[CONF_NAME]

    async_add_entities(
        [
            TWGUserSensor(name, config_entry.entry_id),
            TWGActivitySensor(name, config_entry.entry_id),
            TWGTimeLimitSensor(name, config_entry.entry_id),
        ]
    )

class TWGUserSensor(SensorEntity):
    """Sensor for tracking the current user."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, name: str, entry_id: str) -> None:
        """Initialize the sensor."""
        self._attr_unique_id = f"{entry_id}_user"
        self._attr_name = "Current User"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=name,
            manufacturer="Timewise Guardian",
        )

    @property
    def native_value(self) -> StateType:
        """Return the current user."""
        return "Not Implemented"

class TWGActivitySensor(SensorEntity):
    """Sensor for tracking the current activity."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, name: str, entry_id: str) -> None:
        """Initialize the sensor."""
        self._attr_unique_id = f"{entry_id}_activity"
        self._attr_name = "Current Activity"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=name,
            manufacturer="Timewise Guardian",
        )

    @property
    def native_value(self) -> StateType:
        """Return the current activity."""
        return "Not Implemented"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        return {
            "category": "Not Implemented",
            "window_title": "Not Implemented",
            "process_name": "Not Implemented",
            "start_time": datetime.now().isoformat(),
        }

class TWGTimeLimitSensor(SensorEntity):
    """Sensor for tracking time limits."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "min"

    def __init__(self, name: str, entry_id: str) -> None:
        """Initialize the sensor."""
        self._attr_unique_id = f"{entry_id}_time_limit"
        self._attr_name = "Time Remaining"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=name,
            manufacturer="Timewise Guardian",
        )

    @property
    def native_value(self) -> StateType:
        """Return the remaining time."""
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        return {
            "daily_limit": 0,
            "total_used_today": 0,
            "category": "Not Implemented",
        } 