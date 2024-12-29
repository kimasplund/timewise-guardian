"""Tests for the client module."""
import asyncio
import pytest
from unittest.mock import MagicMock, patch
from timewise_guardian_client.common.client import BaseClient
from timewise_guardian_client.common.config import Config

@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    config = MagicMock(spec=Config)
    config.ha_url = "http://test.local:8123"
    config.ha_token = "test_token"
    config.sync_interval = 30
    config.ha_settings = {
        "categories": {
            "games": {
                "processes": ["game.exe"],
                "window_titles": ["Game"]
            }
        }
    }
    return config

class TestClient(BaseClient):
    """Test implementation of BaseClient."""
    
    async def update_active_windows(self):
        """Mock implementation."""
        self.active_windows = {1: "Test Window"}

    async def update_active_processes(self):
        """Mock implementation."""
        self.active_processes = {"test.exe"}

    async def update_browser_activity(self):
        """Mock implementation."""
        self.browser_urls = {"test": "http://test.com"}

@pytest.mark.asyncio
async def test_client_initialization(mock_config):
    """Test client initialization."""
    client = TestClient(mock_config)
    assert client.config == mock_config
    assert not client.running
    assert client.active_windows == {}
    assert client.active_processes == set()
    assert client.browser_urls == {}

@pytest.mark.asyncio
async def test_websocket_connection(mock_config):
    """Test WebSocket connection."""
    client = TestClient(mock_config)
    
    # Mock websockets.connect
    mock_ws = MagicMock()
    mock_ws.recv.side_effect = [
        {"type": "auth_required"},  # Initial message
        {"type": "auth_ok"}         # Auth response
    ]
    
    with patch("websockets.connect", return_value=mock_ws):
        await client.connect_websocket()
        assert client.ws == mock_ws
        assert mock_ws.send.call_count == 2  # Auth + subscribe

@pytest.mark.asyncio
async def test_state_update(mock_config):
    """Test state update functionality."""
    client = TestClient(mock_config)
    
    # Mock aiohttp.ClientSession
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status = 200
    mock_session.post.return_value.__aenter__.return_value = mock_response
    
    with patch("aiohttp.ClientSession", return_value=mock_session):
        await client.send_state_update({"state": "test"})
        assert mock_session.post.called

@pytest.mark.asyncio
async def test_config_subscription(mock_config):
    """Test configuration subscription."""
    client = TestClient(mock_config)
    mock_ws = MagicMock()
    
    with patch("websockets.connect", return_value=mock_ws):
        await client.connect_websocket()
        await client.subscribe_to_config()
        
        # Verify subscription message was sent
        subscription_call = mock_ws.send.call_args_list[-1]
        message = subscription_call[0][0]
        assert message["type"] == "subscribe_trigger"
        assert message["trigger"]["entity_id"] == "twg.config"

@pytest.mark.asyncio
async def test_memory_usage(mock_config):
    """Test memory usage reporting."""
    client = TestClient(mock_config)
    memory_info = client.get_memory_usage()
    
    assert "rss_mb" in memory_info
    assert "vms_mb" in memory_info
    assert "percent" in memory_info
    assert isinstance(memory_info["rss_mb"], float)
    assert isinstance(memory_info["percent"], float)

@pytest.mark.asyncio
async def test_category_detection(mock_config):
    """Test activity category detection."""
    client = TestClient(mock_config)
    
    # Set up test data
    client.active_windows = {1: "Game Window"}
    client.active_processes = {"game.exe"}
    
    category = client.get_active_category()
    assert category == "games"  # Should match the category from mock_config 