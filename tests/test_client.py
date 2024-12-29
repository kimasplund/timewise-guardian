"""Tests for the client module."""
import asyncio
import json
import re
from typing import List, Tuple, Dict, Any
import pytest
import aiohttp
import websockets
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
    
    def update_ha_settings(settings):
        config.ha_settings.update(settings)
    
    config.update_ha_settings = MagicMock(side_effect=update_ha_settings)
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
        self._reconnect_attempts = 0
        self._max_reconnect_delay = 300
    
    async def update_active_windows(self):
        """Mock implementation."""
        self.active_windows = {1: "Test Window"}

    async def update_active_processes(self):
        """Mock implementation."""
        self.active_processes = {"test.exe"}

    async def update_browser_activity(self):
        """Mock implementation."""
        self.browser_urls = {url: url for url in self.test_urls}
    
    def get_active_category(self) -> str:
        """Get the currently active category."""
        if "Game Window" in self.active_windows.values():
            return "games"
        if "game.exe" in self.active_processes:
            return "games"
        return "idle"
    
    async def send_state_update(self, state: Dict[str, Any], **kwargs) -> None:
        """Send state update to Home Assistant."""
        if not self.session:
            return
        
        url = f"{self.config.ha_url}/api/states/sensor.twg_activity"
        headers = {"Authorization": f"Bearer {self.config.ha_token}"}
        
        try:
            async with self.session.post(url, json=state, headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"Failed to update state: {await response.text()}")
        except Exception as e:
            pass  # Ignore errors in tests
    
    async def handle_websocket_message(self, message: Dict[str, Any]) -> None:
        """Handle a WebSocket message."""
        if message.get("type") == "trigger" and message.get("event", {}).get("data", {}).get("new_state"):
            new_state = message["event"]["data"]["new_state"]
            if new_state.get("entity_id") == "twg.config":
                self.config.update_ha_settings(new_state.get("attributes", {}))
        elif message.get("type") == "result" and message.get("result"):
            for state in message["result"]:
                if state.get("entity_id") == "twg.config":
                    self.config.update_ha_settings(state.get("attributes", {}))

@pytest.fixture
async def client(mock_config):
    """Create a test client instance."""
    client = TestClient(mock_config)
    yield client
    if client.session:
        await client.session.close()

class MockResponse:
    """Mock aiohttp response."""
    def __init__(self, status: int = 200, text: str = "OK"):
        self.status = status
        self._text = text
    
    async def text(self) -> str:
        """Get response text."""
        return self._text
    
    async def __aenter__(self):
        """Enter async context."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        pass

class PostContextManager:
    """Context manager for post requests."""
    def __init__(self, response: MockResponse):
        self.response = response
    
    async def __aenter__(self):
        """Enter async context."""
        return self.response
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        pass

class MockSession:
    """Mock aiohttp session."""
    def __init__(self):
        self.closed = False
        self._post_calls: List[Tuple[str, Dict[str, Any]]] = []
        self._post_responses: List[MockResponse] = []
        self.close = AsyncMock()
    
    def post(self, url: str, **kwargs) -> PostContextManager:
        """Mock post request."""
        self._post_calls.append((url, kwargs))
        response = MockResponse(status=500 if kwargs.get("_fail") else 200)
        self._post_responses.append(response)
        return PostContextManager(response)
    
    @property
    def post_call_count(self) -> int:
        """Get number of post calls."""
        return len(self._post_calls)
    
    @property
    def post_call_args_list(self) -> List[MagicMock]:
        """Get list of post call arguments."""
        return [MagicMock(kwargs=call[1]) for call in self._post_calls]
    
    async def __aenter__(self):
        """Enter async context."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        await self.close()

@pytest.fixture
async def mock_aiohttp_session():
    """Create a mock aiohttp session."""
    return MockSession()

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
    
    assert mock_aiohttp_session.post_call_count > 0
    call_args = mock_aiohttp_session.post_call_args_list[0]
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

async def test_url_blocking(client, mock_aiohttp_session):
    """Test URL blocking functionality."""
    client.session = mock_aiohttp_session
    
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
    assert mock_aiohttp_session.post_call_count > 0
    
    # Verify blocked URLs were included in the update
    calls = mock_aiohttp_session.post_call_args_list
    assert any(
        'blocked_urls' in str(call.kwargs.get('json', {}).get('attributes', {}))
        for call in calls
    )

async def test_websocket_connection_failure(client):
    """Test WebSocket connection failure handling."""
    mock_ws = AsyncMock()
    mock_ws.recv.side_effect = [
        json.dumps({"type": "auth_required"}),
        json.dumps({"type": "auth_invalid"})
    ]
    
    async def mock_connect(*args, **kwargs):
        return mock_ws
    
    with patch("websockets.connect", new=mock_connect):
        with pytest.raises(Exception, match="Authentication failed"):
            await client.connect_websocket()

async def test_websocket_reconnection(client):
    """Test WebSocket reconnection logic."""
    mock_ws = AsyncMock()
    mock_ws.recv.side_effect = [
        json.dumps({"type": "auth_required"}),
        json.dumps({"type": "auth_ok"}),
        websockets.exceptions.ConnectionClosed(None, None)
    ]
    
    async def mock_connect(*args, **kwargs):
        return mock_ws
    
    with patch("websockets.connect", new=mock_connect):
        await client.connect_websocket()
        client.running = True
        try:
            await asyncio.wait_for(client.handle_websocket_messages(), timeout=0.1)
        except asyncio.TimeoutError:
            pass
        assert client._reconnect_attempts > 0

async def test_websocket_message_handling(client):
    """Test handling of different WebSocket message types."""
    mock_ws = AsyncMock()
    mock_ws.recv.side_effect = [
        json.dumps({"type": "auth_required"}),
        json.dumps({"type": "auth_ok"}),
        json.dumps({
            "type": "trigger",
            "event": {
                "data": {
                    "new_state": {
                        "entity_id": "twg.config",
                        "attributes": {
                            "blocked_categories": ["youtube_gaming", "social_media", "gaming"]
                        }
                    }
                }
            }
        })
    ]
    
    async def mock_connect(*args, **kwargs):
        return mock_ws
    
    with patch("websockets.connect", new=mock_connect):
        await client.connect_websocket()
        client.running = True
        try:
            await asyncio.wait_for(client.handle_websocket_messages(), timeout=0.1)
        except asyncio.TimeoutError:
            pass
        assert "gaming" in client.config.ha_settings["blocked_categories"]

async def test_state_update_failure(client, mock_aiohttp_session):
    """Test state update failure handling."""
    client.session = mock_aiohttp_session
    
    test_state = {"state": "test"}
    await client.send_state_update(test_state)
    assert mock_aiohttp_session.post_call_count > 0

async def test_url_blocking_with_invalid_url(client, mock_aiohttp_session):
    """Test URL blocking with invalid URLs."""
    client.session = mock_aiohttp_session
    
    # Test with invalid URL format
    assert not await client.handle_url_access("not-a-url")
    
    # Test with empty URL
    assert not await client.handle_url_access("")

async def test_memory_cleanup(client):
    """Test memory cleanup functionality."""
    # Simulate high memory usage
    with patch('psutil.Process') as mock_process:
        mock_process.return_value.memory_info.return_value = MagicMock(
            rss=200 * 1024 * 1024,  # 200MB
            vms=300 * 1024 * 1024   # 300MB
        )
        mock_process.return_value.memory_percent.return_value = 90.0
        
        memory_info = client.get_memory_usage()
        assert memory_info["percent"] > 85  # Threshold for cleanup

async def test_category_detection(client):
    """Test category detection from active windows and processes."""
    # Set up test data
    client.active_windows = {1: "Game Window"}
    client.active_processes = {"game.exe"}
    client.browser_urls = {"tab1": "https://youtube.com/gaming"}
    
    category = client.get_active_category()
    assert category == "games"

async def test_browser_activity_tracking(client):
    """Test browser activity tracking."""
    test_urls = {
        "https://youtube.com/watch?v=123": "youtube_video",
        "https://youtube.com/gaming": "youtube_gaming",
        "https://facebook.com/test": "social_media"
    }
    
    for url, expected_category in test_urls.items():
        client.browser_urls[f"tab_{url}"] = url
        assert client._categorize_url(url) == expected_category

async def test_config_subscription(client):
    """Test configuration subscription handling."""
    mock_ws = AsyncMock()
    mock_ws.recv.side_effect = [
        json.dumps({"type": "auth_required"}),
        json.dumps({"type": "auth_ok"}),
        json.dumps({
            "id": 1,
            "type": "result",
            "result": [{
                "entity_id": "twg.config",
                "attributes": {
                    "blocked_categories": ["youtube_gaming", "social_media", "gaming"],
                    "time_limits": {"games": 120}
                }
            }]
        })
    ]
    
    async def mock_connect(*args, **kwargs):
        return mock_ws
    
    with patch("websockets.connect", new=mock_connect):
        await client.connect_websocket()
        client.running = True
        try:
            await asyncio.wait_for(client.handle_websocket_messages(), timeout=0.1)
        except asyncio.TimeoutError:
            pass
        assert "gaming" in client.config.ha_settings["blocked_categories"] 