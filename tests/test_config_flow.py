"""Tests for TWG config flow."""
import pytest
from unittest.mock import Mock, patch
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry, OptionsFlow
from homeassistant.data_entry_flow import FlowResult
from custom_components.twg.config_flow import TWGOptionsFlow
from custom_components.twg.const import (
    CONF_USERS,
    CONF_BLOCKLIST_CATEGORIES,
    CONF_WHITELIST,
    CONF_BLACKLIST
)

@pytest.fixture
def mock_hass():
    """Create mock hass."""
    hass = Mock(spec=HomeAssistant)
    hass.data = {}
    return hass

@pytest.fixture
def mock_coordinator():
    """Create mock coordinator."""
    coordinator = Mock()
    coordinator.get_active_users.return_value = {
        "test_user": {
            "friendly_name": "Test User",
            "computer_id": "PC1",
            "system_user": "testuser"
        }
    }
    coordinator.get_available_categories.return_value = {
        "social": "Social Media",
        "gaming": "Gaming Sites"
    }
    return coordinator

class MockOptionsFlow(OptionsFlow):
    """Mock options flow."""
    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

async def test_options_flow_init(mock_hass, mock_coordinator):
    """Test options flow initialization."""
    config_entry = Mock(spec=ConfigEntry)
    config_entry.options = {}

    with patch("custom_components.twg.config_flow.OptionsFlow", MockOptionsFlow):
        flow = TWGOptionsFlow(config_entry)
        flow.hass = mock_hass
        flow.coordinator = mock_coordinator

        result = await flow.async_step_init()
        assert result["type"] == "form"
        assert result["step_id"] == "init"

async def test_options_flow_user_config(mock_hass, mock_coordinator):
    """Test user configuration in options flow."""
    config_entry = Mock(spec=ConfigEntry)
    config_entry.options = {
        CONF_USERS: {
            "test_user": {
                CONF_BLOCKLIST_CATEGORIES: ["social"],
                CONF_WHITELIST: ["allowed.com"],
                CONF_BLACKLIST: ["blocked.com"]
            }
        }
    }

    with patch("custom_components.twg.config_flow.OptionsFlow", MockOptionsFlow):
        flow = TWGOptionsFlow(config_entry)
        flow.hass = mock_hass
        flow.coordinator = mock_coordinator

        result = await flow.async_step_init()
        assert result["type"] == "form"
        assert result["step_id"] == "init"

        user_data = {
            "user_id": "test_user",
            CONF_BLOCKLIST_CATEGORIES: ["social", "gaming"],
            CONF_WHITELIST: ["example.com"],
            CONF_BLACKLIST: ["blocked.com"]
        }

        result = await flow.async_step_user(user_data)
        assert result["type"] == "create_entry"
        assert result["data"][CONF_USERS]["test_user"][CONF_BLOCKLIST_CATEGORIES] == ["social", "gaming"]
        assert result["data"][CONF_USERS]["test_user"][CONF_WHITELIST] == ["example.com"]
        assert result["data"][CONF_USERS]["test_user"][CONF_BLACKLIST] == ["blocked.com"] 