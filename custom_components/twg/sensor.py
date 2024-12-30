"""Sensor platform for Timewise Guardian."""
from __future__ import annotations

import logging
from typing import Any, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN, NAME, VERSION

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Timewise Guardian sensors."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    # Create entities for existing users
    entities = []
    for user_id, user_info in coordinator.get_active_users().items():
        entities.extend([
            TWGUserSensor(coordinator, user_id),
            TWGActivitySensor(coordinator, user_id),
            TWGTimeLimitSensor(coordinator, user_id),
            TWGBlockedDomainsSensor(coordinator, user_id)
        ])

    async_add_entities(entities)

    # Set up dynamic entity creation
    @callback
    def async_add_new_user(user_id: str) -> None:
        """Add entities for a new user."""
        new_entities = [
            TWGUserSensor(coordinator, user_id),
            TWGActivitySensor(coordinator, user_id),
            TWGTimeLimitSensor(coordinator, user_id),
            TWGBlockedDomainsSensor(coordinator, user_id)
        ]
        async_add_entities(new_entities)

    # Register listener for new users
    coordinator.async_add_listener(
        lambda: hass.async_create_task(
            async_check_new_users(coordinator, async_add_new_user)
        )
    )

async def async_check_new_users(
    coordinator: DataUpdateCoordinator,
    add_callback: callable
) -> None:
    """Check for new users and add entities."""
    for user_id in coordinator.get_active_users():
        if not coordinator.hass.states.get(f"sensor.twg_{user_id}_status"):
            add_callback(user_id)

class TWGBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for TWG sensors."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        user_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.user_id = user_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, user_id)},
            name=f"TWG {coordinator.get_active_users()[user_id]['friendly_name']}",
            manufacturer="Timewise Guardian",
            model=VERSION,
            sw_version=VERSION,
        )

    @property
    def should_poll(self) -> bool:
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.is_user_active(self.user_id)

class TWGUserSensor(TWGBaseSensor):
    """Sensor for user status."""

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"twg_{self.user_id}_status"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"TWG {self.coordinator.get_active_users()[self.user_id]['friendly_name']} Status"

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        return self.coordinator.data["states"].get(self.user_id, {}).get("state", "unknown")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return self.coordinator.get_user_config(self.user_id)

class TWGActivitySensor(TWGBaseSensor):
    """Sensor for user activity."""

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"twg_{self.user_id}_activity"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"TWG {self.coordinator.get_active_users()[self.user_id]['friendly_name']} Activity"

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        state = self.coordinator.data["states"].get(self.user_id, {})
        return state.get("active_window", "unknown")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        state = self.coordinator.data["states"].get(self.user_id, {})
        return {
            "process": state.get("process"),
            "start_time": state.get("start_time"),
            "duration": state.get("duration")
        }

class TWGTimeLimitSensor(TWGBaseSensor):
    """Sensor for time limits."""

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"twg_{self.user_id}_time_limit"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"TWG {self.coordinator.get_active_users()[self.user_id]['friendly_name']} Time Limit"

    @property
    def native_value(self) -> Optional[int]:
        """Return the state of the sensor."""
        limits = self.coordinator.data["limits"].get(self.user_id, {})
        return limits.get("daily_limit")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        limits = self.coordinator.data["limits"].get(self.user_id, {})
        return {
            "time_used": limits.get("time_used", 0),
            "time_remaining": limits.get("time_remaining", 0),
            "reset_time": limits.get("reset_time")
        }

class TWGBlockedDomainsSensor(TWGBaseSensor):
    """Sensor for blocked domains."""

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"twg_{self.user_id}_blocked"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"TWG {self.coordinator.get_active_users()[self.user_id]['friendly_name']} Blocked"

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        blocked = self.coordinator.data["blocked"].get(self.user_id, set())
        return len(blocked)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {
            "blocked_domains": list(self.coordinator.data["blocked"].get(self.user_id, set())),
            "categories": self.coordinator.get_available_categories()
        } 