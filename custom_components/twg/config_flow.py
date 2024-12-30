"""Config flow for Timewise Guardian."""
from typing import Any, Dict, Optional
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN, CONF_USERS, CONF_BLOCKLIST_CATEGORIES, 
    CONF_WHITELIST, CONF_BLACKLIST,
    EVENT_USER_DETECTED
)

class TWGConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Timewise Guardian."""

    VERSION = 1

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(title="Timewise Guardian", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({})
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return TWGOptionsFlow(config_entry)


class TWGOptionsFlow(config_entries.OptionsFlow):
    """Handle TWG options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        super().__init__(config_entry)
        self._config = dict(config_entry.options)

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_USERS,
                    default=self._config.get(CONF_USERS, {})
                ): {
                    str: {
                        vol.Optional(CONF_BLOCKLIST_CATEGORIES): [str],
                        vol.Optional(CONF_WHITELIST): [str],
                        vol.Optional(CONF_BLACKLIST): [str]
                    }
                }
            })
        )

    async def _get_available_categories(self):
        """Get available categories from coordinator."""
        coordinator = self.hass.data[DOMAIN].get("coordinator")
        if coordinator:
            self._categories = await coordinator.async_get_categories()
        return self._categories or {}

    async def _get_active_users(self):
        """Get list of active computer users."""
        # Get from entity registry
        registry = self.hass.helpers.entity_registry.async_get(self.hass)
        users = {
            entity_id: entry.original_name
            for entity_id, entry in registry.entities.items()
            if entry.platform == "twg" and entry.domain == "sensor"
        }
        
        # Get from coordinator for real-time users
        coordinator = self.hass.data[DOMAIN].get("coordinator")
        if coordinator:
            active_users = await coordinator.async_get_active_users()
            for user_id, user_info in active_users.items():
                if user_id not in users:
                    users[user_id] = user_info["friendly_name"]
        
        return users

    async def async_step_user_config(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Configure settings for selected user."""
        if user_input is not None:
            # Update options for this user
            if CONF_USERS not in self.options:
                self.options[CONF_USERS] = {}
            
            self.options[CONF_USERS][self._current_user] = {
                CONF_BLOCKLIST_CATEGORIES: user_input[CONF_BLOCKLIST_CATEGORIES],
                CONF_WHITELIST: user_input.get(CONF_WHITELIST, "").split(),
                CONF_BLACKLIST: user_input.get(CONF_BLACKLIST, "").split()
            }

            # Fire event to notify clients
            self.hass.bus.async_fire("twg_config_update", self.options)

            return self.async_create_entry(title="", data=self.options)

        # Get current settings for user
        user_config = self.options.get(CONF_USERS, {}).get(self._current_user, {})
        
        # Get available categories
        categories = await self._get_available_categories()
        
        return self.async_show_form(
            step_id="user_config",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_BLOCKLIST_CATEGORIES,
                    default=user_config.get(CONF_BLOCKLIST_CATEGORIES, [])
                ): cv.multi_select(categories),
                vol.Optional(
                    CONF_WHITELIST,
                    default=" ".join(user_config.get(CONF_WHITELIST, []))
                ): cv.string,
                vol.Optional(
                    CONF_BLACKLIST,
                    default=" ".join(user_config.get(CONF_BLACKLIST, []))
                ): cv.string
            }),
            description_placeholders={
                "name": self._users[self._current_user]
            }
        ) 