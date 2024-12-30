"""Tests for TWG sensors."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from custom_components.twg.sensor import (
    TWGUserSensor,
    TWGActivitySensor,
    TWGTimeLimitSensor,
    TWGBlockedDomainsSensor
)

@pytest.fixture
def mock_hass():
    """Create mock hass."""
    hass = Mock(spec=HomeAssistant)
    hass.states = Mock()
    hass.states.async_set = AsyncMock()
    hass.states.async_all = Mock(return_value=[])
    return hass

@pytest.fixture
def mock_coordinator(mock_hass):
    """Create mock coordinator."""
    coordinator = Mock(spec=DataUpdateCoordinator)
    coordinator.hass = mock_hass
    coordinator.data = {
        "states": {},
        "users": {},
        "blocked": {},
        "limits": {}
    }
    coordinator.async_request_refresh = AsyncMock()
    coordinator.get_active_users = Mock(return_value={})
    coordinator.async_get_active_users = AsyncMock(return_value={})
    coordinator.get_user_config = Mock(return_value={})
    coordinator.get_available_categories = Mock(return_value={})
    return coordinator

@pytest.fixture
def user_data():
    """Create test user data."""
    return {
        "user_id": "test_user",
        "info": {
            "computer_id": "PC1",
            "friendly_name": "Test User",
            "system_user": "testuser",
            "ha_user": None,
            "icon": "mdi:account",
            "device_class": "computer_user"
        },
        "activity": {
            "state": "active",
            "windows": ["Test Window"],
            "processes": ["test.exe"],
            "browser_urls": ["https://example.com"]
        },
        "time_limits": {
            "daily_limit": 7200,
            "time_used": 3600,
            "time_remaining": 3600,
            "reset_time": "00:00"
        },
        "blocked_domains": {
            "facebook.com",
            "twitter.com"
        }
    }

async def test_user_sensor(mock_coordinator, user_data):
    """Test user status sensor."""
    user_id = user_data["user_id"]
    mock_coordinator.data = {
        "users": {
            user_id: user_data["info"]
        },
        "states": {
            user_id: {"state": "active"}
        }
    }
    mock_coordinator.get_active_users.return_value = {user_id: user_data["info"]}
    mock_coordinator.async_get_active_users.return_value = {user_id: user_data["info"]}
    mock_coordinator.get_user_config.return_value = user_data["info"]

    sensor = TWGUserSensor(mock_coordinator, user_id)
    assert sensor.unique_id == f"twg_{user_id}_status"
    assert sensor.name == f"TWG {user_data['info']['friendly_name']} Status"
    assert sensor.native_value == "active"
    assert sensor.extra_state_attributes == user_data["info"]

async def test_activity_sensor(mock_coordinator, user_data):
    """Test activity sensor."""
    user_id = user_data["user_id"]
    mock_coordinator.data = {
        "users": {
            user_id: user_data["info"]
        },
        "states": {
            user_id: user_data["activity"]
        }
    }
    mock_coordinator.get_active_users.return_value = {user_id: user_data["info"]}
    mock_coordinator.async_get_active_users.return_value = {user_id: user_data["info"]}
    mock_coordinator.get_user_config.return_value = user_data["info"]

    sensor = TWGActivitySensor(mock_coordinator, user_id)
    assert sensor.unique_id == f"twg_{user_id}_activity"
    assert sensor.name == f"TWG {user_data['info']['friendly_name']} Activity"
    assert sensor.native_value == user_data["activity"]["state"]
    assert sensor.extra_state_attributes == user_data["activity"]

async def test_time_limit_sensor(mock_coordinator, user_data):
    """Test time limit sensor."""
    user_id = user_data["user_id"]
    mock_coordinator.data = {
        "users": {
            user_id: user_data["info"]
        },
        "limits": {
            user_id: user_data["time_limits"]
        }
    }
    mock_coordinator.get_active_users.return_value = {user_id: user_data["info"]}
    mock_coordinator.async_get_active_users.return_value = {user_id: user_data["info"]}
    mock_coordinator.get_user_config.return_value = user_data["info"]

    sensor = TWGTimeLimitSensor(mock_coordinator, user_id)
    assert sensor.unique_id == f"twg_{user_id}_time_limit"
    assert sensor.name == f"TWG {user_data['info']['friendly_name']} Time Limit"
    assert sensor.native_value == user_data["time_limits"]["time_remaining"]
    assert sensor.extra_state_attributes == user_data["time_limits"]

async def test_blocked_domains_sensor(mock_coordinator, user_data):
    """Test blocked domains sensor."""
    user_id = user_data["user_id"]
    mock_coordinator.data = {
        "users": {
            user_id: user_data["info"]
        },
        "blocked": {
            user_id: user_data["blocked_domains"]
        }
    }
    mock_coordinator.get_active_users.return_value = {user_id: user_data["info"]}
    mock_coordinator.async_get_active_users.return_value = {user_id: user_data["info"]}
    mock_coordinator.get_user_config.return_value = user_data["info"]
    mock_coordinator.get_available_categories.return_value = {"social": "Social Media"}

    sensor = TWGBlockedDomainsSensor(mock_coordinator, user_id)
    assert sensor.unique_id == f"twg_{user_id}_blocked"
    assert sensor.name == f"TWG {user_data['info']['friendly_name']} Blocked"
    assert sensor.native_value == len(user_data["blocked_domains"])
    assert sensor.extra_state_attributes == {"domains": list(user_data["blocked_domains"])}

async def test_sensor_unavailable(mock_coordinator, user_data):
    """Test sensor availability."""
    user_id = user_data["user_id"]
    mock_coordinator.data = {
        "users": {
            user_id: None
        },
        "states": {
            user_id: None
        }
    }
    mock_coordinator.get_active_users.return_value = {}
    mock_coordinator.async_get_active_users.return_value = {}
    mock_coordinator.get_user_config.return_value = None

    sensor = TWGUserSensor(mock_coordinator, user_id)
    assert not sensor.available

async def test_dynamic_entity_creation(mock_hass, mock_coordinator, user_data):
    """Test dynamic entity creation."""
    user_id = user_data["user_id"]
    mock_coordinator.data = {
        "users": {
            user_id: user_data["info"]
        },
        "states": {
            user_id: {"state": "active"}
        }
    }
    mock_coordinator.get_active_users.return_value = {user_id: user_data["info"]}
    mock_coordinator.async_get_active_users.return_value = {user_id: user_data["info"]}
    mock_coordinator.get_user_config.return_value = user_data["info"]

    # Create sensors
    sensors = [
        TWGUserSensor(mock_coordinator, user_id),
        TWGActivitySensor(mock_coordinator, user_id),
        TWGTimeLimitSensor(mock_coordinator, user_id),
        TWGBlockedDomainsSensor(mock_coordinator, user_id)
    ]

    # Add entities to hass
    for sensor in sensors:
        await sensor.async_added_to_hass()
        await sensor.async_update()  # Force an update to trigger state changes

    # Verify entities were created
    assert mock_hass.states.async_set.call_count == len(sensors)

async def test_sensor_update_on_coordinator_update(mock_coordinator, user_data):
    """Test sensors update when coordinator data changes."""
    user_id = user_data["user_id"]
    mock_coordinator.data = {
        "users": {
            user_id: user_data["info"]
        },
        "states": {
            user_id: {"state": "active"}
        }
    }
    mock_coordinator.get_active_users.return_value = {user_id: user_data["info"]}
    mock_coordinator.async_get_active_users.return_value = {user_id: user_data["info"]}
    mock_coordinator.get_user_config.return_value = user_data["info"]

    sensor = TWGUserSensor(mock_coordinator, user_id)
    assert sensor.native_value == "active"

    # Update coordinator data
    mock_coordinator.data["states"][user_id]["state"] = "idle"
    await mock_coordinator.async_request_refresh()

    assert sensor.native_value == "idle" 