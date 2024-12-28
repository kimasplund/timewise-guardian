"""Config panel for Timewise Guardian."""
from typing import Any
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.components.http import HomeAssistantView
from homeassistant.components import websocket_api

from .const import DOMAIN
from .models import TWGStore, UserConfig, Category, TimeRestriction

async def async_setup_panel(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Set up the config panel."""
    store = TWGStore(hass, config_entry.entry_id)
    await store.async_load()

    hass.http.register_view(TWGConfigView(store))
    
    websocket_api.async_register_command(hass, websocket_get_config)
    websocket_api.async_register_command(hass, websocket_update_config)

class TWGConfigView(HomeAssistantView):
    """Config view for Timewise Guardian."""
    url = "/api/twg/config/{user_id}"
    name = "api:twg:config"

    def __init__(self, store: TWGStore) -> None:
        """Initialize."""
        self._store = store

    async def get(self, request, user_id):
        """Handle GET request."""
        config = self._store.get_user_config(user_id)
        if config:
            return self.json(config)
        return self.json_message("User not found", status_code=404)

    async def post(self, request, user_id):
        """Handle POST request."""
        data = await request.json()
        config = UserConfig(**data)
        await self._store.async_update_user_config(user_id, config)
        return self.json({"success": True})

@callback
@websocket_api.websocket_command({
    vol.Required("type"): "twg/config/get",
    vol.Required("user_id"): str,
})
async def websocket_get_config(hass, connection, msg):
    """Handle get config command."""
    store = TWGStore(hass, msg["entry_id"])
    config = store.get_user_config(msg["user_id"])
    connection.send_result(msg["id"], config)

@callback
@websocket_api.websocket_command({
    vol.Required("type"): "twg/config/update",
    vol.Required("user_id"): str,
    vol.Required("config"): dict,
})
async def websocket_update_config(hass, connection, msg):
    """Handle update config command."""
    store = TWGStore(hass, msg["entry_id"])
    config = UserConfig(**msg["config"])
    await store.async_update_user_config(msg["user_id"], config)
    connection.send_result(msg["id"], {"success": True}) 