"""The Timewise Guardian integration."""
import asyncio
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .coordinator import TWGCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.SWITCH, Platform.BINARY_SENSOR]

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Timewise Guardian component."""
    hass.data[DOMAIN] = {}
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Timewise Guardian from a config entry."""
    coordinator = TWGCoordinator(hass)
    await coordinator.async_config_entry_first_refresh()
    
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "listeners": []
    }

    # Set up all platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register update listener for config entry updates
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # Register service handlers
    async def handle_update_categories(call):
        """Handle the update_categories service call."""
        categories = call.data.get("categories", {})
        coordinator.update_categories(categories)

    async def handle_update_time_limits(call):
        """Handle the update_time_limits service call."""
        user_id = call.data.get("user_id")
        limits = call.data.get("limits", {})
        if user_id:
            await coordinator.async_update_time_limits(user_id, limits)

    async def handle_update_restrictions(call):
        """Handle the update_restrictions service call."""
        user_id = call.data.get("user_id")
        restrictions = call.data.get("restrictions", {})
        if user_id:
            await coordinator.async_update_restrictions(user_id, restrictions)

    # Register services
    hass.services.async_register(
        DOMAIN, "update_categories", handle_update_categories
    )
    hass.services.async_register(
        DOMAIN, "update_time_limits", handle_update_time_limits
    )
    hass.services.async_register(
        DOMAIN, "update_restrictions", handle_update_restrictions
    )

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        # Clean up
        for unsub in hass.data[DOMAIN][entry.entry_id]["listeners"]:
            unsub()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry) 