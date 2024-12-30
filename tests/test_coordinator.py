"""Tests for TWG coordinator."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from custom_components.twg.coordinator import TWGCoordinator

@pytest.fixture
def mock_hass():
    """Create mock hass."""
    hass = Mock()
    hass.async_create_task = AsyncMock()
    hass.async_add_executor_job = AsyncMock()
    hass.states = Mock()
    hass.states.async_set = AsyncMock()
    hass.bus = Mock()
    hass.bus.async_listen = Mock()
    hass.bus.async_listen_once = Mock()
    return hass

@pytest.fixture
def coordinator(mock_hass):
    """Create coordinator instance."""
    return TWGCoordinator(mock_hass)

async def test_coordinator_initialization(coordinator):
    """Test coordinator initialization."""
    assert coordinator.update_interval == timedelta(seconds=30)
    assert coordinator._active_users == {}
    assert coordinator._available_categories == {}
    assert coordinator._user_states == {}
    assert coordinator._blocked_domains == {}
    assert coordinator._time_limits == {}
    assert coordinator._restrictions == {}

async def test_coordinator_update(coordinator):
    """Test coordinator update method."""
    # Add test data
    coordinator._active_users = {
        "test_user": {
            "computer_id": "PC1",
            "friendly_name": "Test User",
            "system_user": "testuser"
        }
    }
    coordinator._user_states = {
        "test_user": {
            "state": "active",
            "windows": ["Test Window"],
            "processes": ["test.exe"]
        }
    }

    data = await coordinator._async_update_data()

    assert data["users"] == coordinator._active_users
    assert data["states"] == coordinator._user_states

async def test_handle_user_detected(coordinator):
    """Test handling of user detection event."""
    event = Mock()
    event.data = {
        "user_id": "test_user",
        "user_info": {
            "computer_id": "PC1",
            "friendly_name": "Test User",
            "system_user": "testuser"
        }
    }

    coordinator._handle_user_detected(event)

    assert "test_user" in coordinator._active_users
    assert coordinator._active_users["test_user"] == event.data["user_info"]
    assert coordinator._user_states["test_user"]["state"] == "active"

async def test_handle_user_activity(coordinator):
    """Test handling of user activity event."""
    # First add a user
    coordinator._active_users["test_user"] = {
        "computer_id": "PC1",
        "friendly_name": "Test User"
    }
    coordinator._user_states["test_user"] = {"state": "active"}

    event = Mock()
    event.data = {
        "user_id": "test_user",
        "activity": {
            "windows": ["New Window"],
            "processes": ["new.exe"]
        }
    }

    coordinator._handle_user_activity(event)

    assert coordinator._user_states["test_user"]["windows"] == ["New Window"]
    assert coordinator._user_states["test_user"]["processes"] == ["new.exe"]

async def test_handle_categories_updated(coordinator):
    """Test handling of categories update event."""
    event = Mock()
    event.data = {
        "categories": {
            "social": "Social Media",
            "gaming": "Gaming Sites"
        }
    }

    coordinator._handle_categories_updated(event)

    assert coordinator._available_categories == event.data["categories"]

async def test_update_user_state(coordinator):
    """Test updating user state."""
    user_id = "test_user"
    coordinator._user_states[user_id] = {"state": "active"}

    new_state = {
        "windows": ["New Window"],
        "processes": ["new.exe"]
    }

    await coordinator.async_update_user_state(user_id, new_state)

    assert coordinator._user_states[user_id]["windows"] == ["New Window"]
    assert coordinator._user_states[user_id]["processes"] == ["new.exe"]
    assert coordinator._user_states[user_id]["state"] == "active"

async def test_update_blocked_domains(coordinator):
    """Test updating blocked domains."""
    user_id = "test_user"
    coordinator._blocked_domains[user_id] = set()

    domains = {"facebook.com", "twitter.com"}
    await coordinator.async_update_blocked_domains(user_id, domains)

    assert coordinator._blocked_domains[user_id] == domains

async def test_update_time_limits(coordinator):
    """Test updating time limits."""
    user_id = "test_user"
    coordinator._time_limits[user_id] = {}

    limits = {
        "daily_limit": 7200,
        "time_used": 3600,
        "time_remaining": 3600,
        "reset_time": "00:00"
    }

    await coordinator.async_update_time_limits(user_id, limits)

    assert coordinator._time_limits[user_id] == limits

async def test_update_restrictions(coordinator):
    """Test updating restrictions."""
    user_id = "test_user"
    coordinator._restrictions[user_id] = {}

    restrictions = {
        "schedule": [
            {
                "days": [1, 2, 3, 4, 5],
                "start": "15:00",
                "end": "17:00"
            }
        ]
    }

    await coordinator.async_update_restrictions(user_id, restrictions)

    assert coordinator._restrictions[user_id] == restrictions

async def test_get_user_config(coordinator):
    """Test getting user configuration."""
    user_id = "test_user"
    coordinator._active_users[user_id] = {"friendly_name": "Test User"}
    coordinator._user_states[user_id] = {"state": "active"}
    coordinator._blocked_domains[user_id] = {"facebook.com"}
    coordinator._time_limits[user_id] = {"daily_limit": 7200}
    coordinator._restrictions[user_id] = {"schedule": []}

    config = coordinator.get_user_config(user_id)

    assert config["info"] == {"friendly_name": "Test User"}
    assert config["state"] == {"state": "active"}
    assert config["blocked_domains"] == ["facebook.com"]
    assert config["time_limits"] == {"daily_limit": 7200}
    assert config["restrictions"] == {"schedule": []}

async def test_is_user_active(coordinator):
    """Test checking if user is active."""
    user_id = "test_user"
    assert not coordinator.is_user_active(user_id)

    coordinator._active_users[user_id] = {"friendly_name": "Test User"}
    assert coordinator.is_user_active(user_id)

async def test_get_active_users(coordinator):
    """Test getting active users."""
    users = {
        "user1": {"friendly_name": "User 1"},
        "user2": {"friendly_name": "User 2"}
    }
    coordinator._active_users = users

    assert coordinator.get_active_users() == users

async def test_get_available_categories(coordinator):
    """Test getting available categories."""
    categories = {
        "gaming": "Gaming Sites",
        "social": "Social Media"
    }
    coordinator._available_categories = categories

    assert coordinator.get_available_categories() == categories 