"""Tests for the client module."""
import asyncio
import json
import re
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
        },
        "blocked_categories": ["youtube_gaming", "social_media"],
        "youtube_restrictions": {
            "blocked_categories": ["gaming", "entertainment"]
        },
        "blocked_patterns": [r"youtube\.com/watch\?v=.*&category=20"]
    }
    return config

class TestClient(BaseClient):
    """Test implementation of BaseClient."""
    def __init__(self, config):
        """Initialize without parent constructor."""
        super().__init__(config)
        self.test_urls = set()
    
    async def update_active_windows(self):
        """Mock implementation."""
        self.active_windows = {1: "Test Window"}

    async def update_active_processes(self):
        """Mock implementation."""
        self.active_processes = {"test.exe"}

    async def update_browser_activity(self):
        """Mock implementation."""
        self.browser_urls = {"test": url for url in self.test_urls}

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
    
    mock_ws = AsyncMock()
    mock_ws.recv.side_effect = [
        json.dumps({"type": "auth_required"}),
        json.dumps({"type": "auth_ok"})
    ]
    
    with patch("websockets.connect", return_value=mock_ws):
        await client.connect_websocket()
        assert client.ws is not None
        assert isinstance(client.ws, AsyncMock)

async def test_url_categorization(mock_config):
    """Test URL categorization."""
    client = TestClient(mock_config)
    
    # Test YouTube categorization
    assert client._categorize_url("https://youtube.com/watch?v=123") == "youtube_video"
    assert client._categorize_url("https://youtube.com/gaming") == "youtube_gaming"
    assert client._categorize_url("https://youtube.com/music") == "youtube_music"
    
    # Test social media
    assert client._categorize_url("https://facebook.com/test") == "social_media"
    assert client._categorize_url("https://twitter.com/user") == "social_media"
    
    # Test gaming sites
    assert client._categorize_url("https://twitch.tv/stream") == "gaming"
    assert client._categorize_url("https://steam.com/game") == "gaming"

async def test_url_blocking(mock_config):
    """Test URL blocking functionality."""
    client = TestClient(mock_config)
    
    # Test YouTube gaming block
    assert await client.handle_url_access("https://youtube.com/gaming")
    
    # Test social media block
    assert await client.handle_url_access("https://facebook.com/test")
    
    # Test pattern block
    assert await client.handle_url_access("https://youtube.com/watch?v=123&category=20")
    
    # Test allowed URL
    assert not await client.handle_url_access("https://youtube.com/education")

async def test_state_update(mock_config):
    """Test state update functionality."""
    client = TestClient(mock_config)
    client.session = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    
    client.session.post.return_value.__aenter__.return_value = mock_response
    
    await client.send_state_update({"state": "test"})
    assert client.session.post.called

async def test_memory_usage(mock_config):
    """Test memory usage reporting."""
    client = TestClient(mock_config)
    memory_info = client.get_memory_usage()
    
    assert "rss_mb" in memory_info
    assert "vms_mb" in memory_info
    assert "percent" in memory_info
    assert isinstance(memory_info["rss_mb"], float)
    assert isinstance(memory_info["percent"], float)

async def test_update_loop(mock_config):
    """Test the main update loop."""
    client = TestClient(mock_config)
    client.session = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    client.session.post.return_value.__aenter__.return_value = mock_response
    
    # Add a test URL that should be blocked
    client.test_urls.add("https://youtube.com/gaming")
    
    # Run one iteration
    client.running = True
    try:
        await asyncio.wait_for(client.update_loop(), timeout=0.1)
    except asyncio.TimeoutError:
        pass
    
    # Verify state update was called with blocked URL
    assert any(call.kwargs['json']['attributes'].get('blocked_urls') 
              for call in client.session.post.call_args_list) 