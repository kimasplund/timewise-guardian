"""Tests for the client module."""
import asyncio
import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from timewise_guardian_client.common.client import BaseClient
from timewise_guardian_client.common.config import Config

pytestmark = pytest.mark.asyncio  # Mark all tests in this module as async

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
                "window_titles": ["Game Window"]
            }
        }
    }
    config.get_category_processes.return_value = ["game.exe"]
    config.get_category_window_titles.return_value = ["Game Window"]
    return config

class TestClient(BaseClient):
    """Test implementation of BaseClient."""
    def __init__(self, config):
        """Initialize without parent constructor."""
        self.config = config
        self.running = False
        self.active_windows = {}
        self.active_processes = set()
        self.browser_urls = {}
        self.ws = None
    
    async def update_active_windows(self):
        """Mock implementation."""
        self.active_windows = {1: "Test Window"}

    async def update_active_processes(self):
        """Mock implementation."""
        self.active_processes = {"test.exe"}

    async def update_browser_activity(self):
        """Mock implementation."""
        self.browser_urls = {"test": "http://test.com"}

    @staticmethod
    def _setup_window_tracking():
        """Mock window tracking setup."""
        pass

async def test_client_initialization(mock_config):
    """Test client initialization."""
    client = TestClient(mock_config)
    assert client.config == mock_config
    assert not client.running
    assert client.active_windows == {}
    assert client.active_processes == set()
    assert client.browser_urls == {}

async def test_websocket_connection(mock_config):
    """Test WebSocket connection."""
    client = TestClient(mock_config)
    
    async def mock_connect(*args, **kwargs):
        mock_ws = AsyncMock()
        mock_ws.recv.side_effect = [
            json.dumps({"type": "auth_required"}),
            json.dumps({"type": "auth_ok"})
        ]
        return mock_ws
    
    with patch("websockets.connect", new=mock_connect):
        await client.connect_websocket()
        assert client.ws is not None
        assert isinstance(client.ws, AsyncMock)

async def test_state_update(mock_config):
    """Test state update functionality."""
    client = TestClient(mock_config)
    
    async def mock_post(*args, **kwargs):
        return AsyncMock(status=200)
    
    mock_session = AsyncMock()
    mock_session.post.return_value.__aenter__.return_value = AsyncMock(status=200)
    
    with patch("aiohttp.ClientSession", return_value=mock_session):
        await client.send_state_update({"state": "test"})
        assert mock_session.post.called

async def test_config_subscription(mock_config):
    """Test configuration subscription."""
    client = TestClient(mock_config)
    
    async def mock_connect(*args, **kwargs):
        mock_ws = AsyncMock()
        mock_ws.recv.side_effect = [
            json.dumps({"type": "auth_required"}),
            json.dumps({"type": "auth_ok"})
        ]
        return mock_ws
    
    with patch("websockets.connect", new=mock_connect):
        await client.connect_websocket()
        assert client.ws is not None
        assert isinstance(client.ws, AsyncMock)

async def test_memory_usage(mock_config):
    """Test memory usage reporting."""
    client = TestClient(mock_config)
    memory_info = client.get_memory_usage()
    
    assert "rss_mb" in memory_info
    assert "vms_mb" in memory_info
    assert "percent" in memory_info
    assert isinstance(memory_info["rss_mb"], float)
    assert isinstance(memory_info["percent"], float)

async def test_category_detection(mock_config):
    """Test activity category detection."""
    client = TestClient(mock_config)
    
    # Set up test data
    client.active_windows = {1: "Game Window"}
    client.active_processes = {"game.exe"}
    
    category = client.get_active_category()
    assert category == "games" 