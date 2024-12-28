"""Config panel for Timewise Guardian."""
from typing import Any
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.components.http import HomeAssistantView
from homeassistant.components.websocket_api import (
    async_register_command,
    websocket_command,
    require_admin,
    ActiveConnection,
    ERR_INVALID_FORMAT,
)
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .models import TWGStore, UserConfig, Category, TimeRestriction

CONFIG_SCHEMA = vol.Schema({
    vol.Required("name"): str,
    vol.Required("categories"): {
        str: vol.Schema({
            vol.Required("name"): str,
            vol.Required("processes"): [str],
            vol.Required("window_titles"): [str],
            vol.Required("urls"): [str],
            vol.Required("time_limit"): int,
            vol.Required("restrictions"): [vol.Schema({
                vol.Required("days"): [str],
                vol.Required("start_time"): str,
                vol.Required("end_time"): str,
                vol.Required("category"): str,
            })],
        }),
    },
    vol.Required("notifications_enabled"): bool,
    vol.Required("warning_threshold"): int,
})

class ConfigError(HomeAssistantError):
    """Config error."""

async def async_setup_panel(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Set up the config panel."""
    store = TWGStore(hass, config_entry.entry_id)
    await store.async_load()

    hass.http.register_view(TWGConfigView(store))
    
    async_register_command(hass, websocket_get_config)
    async_register_command(hass, websocket_update_config)

class TWGConfigView(HomeAssistantView):
    """Config view for Timewise Guardian."""
    url = "/api/twg/config/{user_id}"
    name = "api:twg:config"
    requires_auth = True

    def __init__(self, store: TWGStore) -> None:
        """Initialize."""
        self._store = store

    async def get(self, request, user_id):
        """Handle GET request."""
        try:
            config = self._store.get_user_config(user_id)
            if config:
                return self.json(config.to_dict())
            return self.json_message("User not found", status_code=404)
        except Exception as err:
            return self.json_message(f"Error retrieving config: {err}", status_code=500)

    async def post(self, request, user_id):
        """Handle POST request."""
        try:
            data = await request.json()
            # Validate config data
            CONFIG_SCHEMA(data)
            
            # Convert to UserConfig object
            config = UserConfig.from_dict(data)
            
            # Save config
            await self._store.async_update_user_config(user_id, config)
            return self.json({"success": True})
        except vol.Invalid as err:
            return self.json_message(f"Invalid config: {err}", status_code=400)
        except Exception as err:
            return self.json_message(f"Error updating config: {err}", status_code=500)

@callback
@websocket_command({
    vol.Required("type"): "twg/config/get",
    vol.Required("user_id"): str,
})
async def websocket_get_config(hass: HomeAssistant, connection: ActiveConnection, msg: dict):
    """Handle get config command."""
    try:
        store = TWGStore(hass, msg["entry_id"])
        config = store.get_user_config(msg["user_id"])
        if config:
            connection.send_result(msg["id"], config.to_dict())
        else:
            connection.send_error(msg["id"], "not_found", "User not found")
    except Exception as err:
        connection.send_error(msg["id"], "get_failed", str(err))

@callback
@websocket_command({
    vol.Required("type"): "twg/config/update",
    vol.Required("user_id"): str,
    vol.Required("config"): CONFIG_SCHEMA,
})
@require_admin
async def websocket_update_config(hass: HomeAssistant, connection: ActiveConnection, msg: dict):
    """Handle update config command."""
    try:
        store = TWGStore(hass, msg["entry_id"])
        config = UserConfig.from_dict(msg["config"])
        await store.async_update_user_config(msg["user_id"], config)
        connection.send_result(msg["id"], {"success": True})
    except vol.Invalid as err:
        connection.send_error(msg["id"], ERR_INVALID_FORMAT, str(err))
    except Exception as err:
        connection.send_error(msg["id"], "update_failed", str(err)) 