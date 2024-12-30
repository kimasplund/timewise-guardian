"""Data coordinator for Timewise Guardian."""
import asyncio
import logging
from datetime import timedelta
from typing import Dict, Any, Optional, Set
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.helpers.entity_registry import async_get as get_entity_registry

from .const import (
    DOMAIN, EVENT_USER_DETECTED, EVENT_USER_ACTIVITY,
    EVENT_CATEGORIES_UPDATED, EVENT_TIME_LIMIT_WARNING,
    EVENT_TIME_LIMIT_REACHED, EVENT_RESTRICTION_ACTIVE
)

_LOGGER = logging.getLogger(__name__)

class TWGCoordinator(DataUpdateCoordinator):
    """Class to manage fetching TWG data."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )
        self.hass = hass
        self._active_users: Dict[str, Dict[str, Any]] = {}
        self._available_categories: Dict[str, str] = {}
        self._user_states: Dict[str, Dict[str, Any]] = {}
        self._blocked_domains: Dict[str, Set[str]] = {}
        self._time_limits: Dict[str, Dict[str, Any]] = {}
        self._restrictions: Dict[str, Dict[str, Any]] = {}
        
        # Register event handlers
        hass.bus.async_listen(EVENT_USER_DETECTED, self._handle_user_detected)
        hass.bus.async_listen(EVENT_USER_ACTIVITY, self._handle_user_activity)
        hass.bus.async_listen(EVENT_CATEGORIES_UPDATED, self._handle_categories_updated)
        
        # Register startup handler
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, self._handle_startup)

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from API endpoint."""
        return {
            "users": self._active_users,
            "categories": self._available_categories,
            "states": self._user_states,
            "blocked": self._blocked_domains,
            "limits": self._time_limits,
            "restrictions": self._restrictions
        }

    @callback
    def _handle_user_detected(self, event) -> None:
        """Handle user detection event."""
        user_id = event.data.get("user_id")
        user_info = event.data.get("user_info", {})
        
        if user_id and user_info:
            self._active_users[user_id] = user_info
            # Initialize user data structures
            if user_id not in self._user_states:
                self._user_states[user_id] = {"state": "active"}
            if user_id not in self._blocked_domains:
                self._blocked_domains[user_id] = set()
            if user_id not in self._time_limits:
                self._time_limits[user_id] = {}
            if user_id not in self._restrictions:
                self._restrictions[user_id] = {}
            
            self.async_set_updated_data(self._async_update_data())

    @callback
    def _handle_user_activity(self, event) -> None:
        """Handle user activity event."""
        user_id = event.data.get("user_id")
        activity = event.data.get("activity", {})
        
        if user_id and activity:
            if user_id not in self._user_states:
                self._user_states[user_id] = {}
            
            self._user_states[user_id].update(activity)
            self.async_set_updated_data(self._async_update_data())

    @callback
    def _handle_categories_updated(self, event) -> None:
        """Handle categories update event."""
        categories = event.data.get("categories", {})
        if categories:
            self._available_categories = categories
            self.async_set_updated_data(self._async_update_data())

    async def _handle_startup(self, _) -> None:
        """Handle Home Assistant startup."""
        # Load existing entities
        registry = get_entity_registry(self.hass)
        entities = registry.entities
        
        # Initialize from existing entities
        for entity_id, entry in entities.items():
            if entry.platform == DOMAIN:
                user_id = entry.unique_id
                if user_id not in self._active_users:
                    self._active_users[user_id] = {
                        "friendly_name": entry.original_name,
                        "entity_id": entity_id
                    }
        
        await self.async_refresh()

    async def async_update_user_state(self, user_id: str, state: Dict[str, Any]) -> None:
        """Update user state."""
        if user_id in self._user_states:
            self._user_states[user_id].update(state)
            self.async_set_updated_data(self._async_update_data())

    async def async_update_blocked_domains(self, user_id: str, domains: Set[str]) -> None:
        """Update blocked domains for user."""
        if user_id in self._blocked_domains:
            self._blocked_domains[user_id] = domains
            self.async_set_updated_data(self._async_update_data())

    async def async_update_time_limits(self, user_id: str, limits: Dict[str, Any]) -> None:
        """Update time limits for user."""
        if user_id in self._time_limits:
            self._time_limits[user_id].update(limits)
            self.async_set_updated_data(self._async_update_data())

    async def async_update_restrictions(self, user_id: str, restrictions: Dict[str, Any]) -> None:
        """Update restrictions for user."""
        if user_id in self._restrictions:
            self._restrictions[user_id].update(restrictions)
            self.async_set_updated_data(self._async_update_data())

    def get_user_config(self, user_id: str) -> Dict[str, Any]:
        """Get complete configuration for a user."""
        return {
            "info": self._active_users.get(user_id, {}),
            "state": self._user_states.get(user_id, {}),
            "blocked_domains": list(self._blocked_domains.get(user_id, set())),
            "time_limits": self._time_limits.get(user_id, {}),
            "restrictions": self._restrictions.get(user_id, {})
        }

    def is_user_active(self, user_id: str) -> bool:
        """Check if a user is currently active."""
        return user_id in self._active_users

    def get_active_users(self) -> Dict[str, Dict[str, Any]]:
        """Get all active users."""
        return self._active_users

    def get_available_categories(self) -> Dict[str, str]:
        """Get available blocklist categories."""
        return self._available_categories 