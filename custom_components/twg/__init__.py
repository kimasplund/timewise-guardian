"""The Timewise Guardian integration."""
import logging
import sys
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .models import TWGStore
from .config_panel import async_setup_panel
from .websocket_api import async_setup_websocket_api
from .statistics import websocket_get_stats

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR]

# Verify Python version
if sys.version_info < (3, 8):
    _LOGGER.critical(
        "Python 3.8 or higher is required for Timewise Guardian. Current version: %s",
        sys.version
    )
    raise RuntimeError("Python 3.8 or higher is required")

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Timewise Guardian from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Initialize storage
    store = TWGStore(hass, entry.entry_id)
    await store.async_load()
    hass.data[DOMAIN][entry.entry_id] = store

    # Set up config panel
    await async_setup_panel(hass, entry)

    # Set up websocket API
    await async_setup_websocket_api(hass)

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok 