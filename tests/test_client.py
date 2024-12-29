"""Tests for the client module."""
import asyncio
import json
import re
import pytest
import aiohttp
from unittest.mock import MagicMock, patch, AsyncMock, create_autospec
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
        """Initialize test client."""
        self.config = config
        self.running = False
        self.active_windows = {}
        self.active_processes = set()
        self.browser_urls = {}
        self.test_urls = set()
        self.ws = None
        self.session = None
        self._message_id = 0
        self._blocked_urls = set()
        self._computer_id = "test_computer"
        self._user_id = "test_user"
        self._state = {}
    
    async def update_active_windows(self):
        """Mock implementation."""
        self.active_windows = {1: "Test Window"}

    async def update_active_processes(self):
        """Mock implementation."""
        self.active_processes = {"test.exe"}

    async def update_browser_activity(self):
        """Mock implementation."""
        self.browser_urls = {url: url for url in self.test_urls}

@pytest.fixture
async def client(mock_config):
    """Create a test client instance."""
    client = TestClient(mock_config)
    yield client
    if client.session:
        await client.session.close()

@pytest.fixture
async def mock_aiohttp_session():
    """Create a mock aiohttp session."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value="OK")
    
    async def mock_aenter():
        return mock_response
    
    async def mock_aexit(*args):
        pass
    
    mock_response.__aenter__ = mock_aenter
    mock_response.__aexit__ = mock_aexit
    
    mock_session = AsyncMock()
    mock_session.post = AsyncMock(return_value=mock_response)
    mock_session.closed = False
    mock_session.close = AsyncMock()
    
    return mock_session

async def test_websocket_connection(client):
    """Test WebSocket connection."""
    mock_ws = AsyncMock()
    mock_ws.recv.side_effect = [
        json.dumps({"type": "auth_required"}),
        json.dumps({"type": "auth_ok"})
    ]
    
    async def mock_connect(*args, **kwargs):
        return mock_ws
    
    with patch("websockets.connect", new=mock_connect):
        await client.connect_websocket()
        assert client.ws is not None

async def test_state_update(client, mock_aiohttp_session):
    """Test state update functionality."""
    client.session = mock_aiohttp_session
    
    test_state = {"state": "test", "attributes": {"test_attr": "value"}}
    await client.send_state_update(test_state)
    
    assert mock_aiohttp_session.post.call_count > 0
    call_args = mock_aiohttp_session.post.call_args
    assert call_args is not None
    assert call_args.kwargs["json"] == test_state

async def test_url_categorization(client):
    """Test URL categorization."""
    assert client._categorize_url("https://youtube.com/watch?v=123") == "youtube_video"
    assert client._categorize_url("https://youtube.com/gaming") == "youtube_gaming"
    assert client._categorize_url("https://youtube.com/music") == "youtube_music"
    assert client._categorize_url("https://facebook.com/test") == "social_media"
    assert client._categorize_url("https://twitter.com/user") == "social_media"
    assert client._categorize_url("https://twitch.tv/stream") == "gaming"
    assert client._categorize_url("https://steam.com/game") == "gaming"

async def test_url_blocking(client):
    """Test URL blocking functionality."""
    assert await client.handle_url_access("https://youtube.com/gaming")
    assert await client.handle_url_access("https://facebook.com/test")
    assert await client.handle_url_access("https://youtube.com/watch?v=123&category=20")
    assert not await client.handle_url_access("https://youtube.com/education")

async def test_memory_usage(client):
    """Test memory usage reporting."""
    memory_info = client.get_memory_usage()
    assert "rss_mb" in memory_info
    assert "vms_mb" in memory_info
    assert "percent" in memory_info
    assert isinstance(memory_info["rss_mb"], float)
    assert isinstance(memory_info["percent"], float)

async def test_update_loop(client, mock_aiohttp_session):
    """Test the main update loop."""
    client.session = mock_aiohttp_session
    
    # Add a test URL that should be blocked
    client.test_urls.add("https://youtube.com/gaming")
    
    # Run one iteration
    client.running = True
    try:
        await asyncio.wait_for(client.update_loop(), timeout=0.1)
    except asyncio.TimeoutError:
        pass
    
    # Verify state update was called
    assert mock_aiohttp_session.post.call_count > 0
    
    # Verify blocked URLs were included in the update
    calls = mock_aiohttp_session.post.call_args_list
    assert any(
        'blocked_urls' in str(call.kwargs.get('json', {}).get('attributes', {}))
        for call in calls
    ) 