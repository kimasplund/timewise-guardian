"""Tests for TWG client."""
import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from aiohttp import ClientSession, WSMessage, WSMsgType
from timewise_guardian_client.common.client import TWGClient

@pytest.fixture
def mock_session():
    """Create mock aiohttp session."""
    session = Mock(spec=ClientSession)
    session.ws_connect = AsyncMock()
    session.post = AsyncMock()
    session.get = AsyncMock()
    return session

@pytest.fixture
def mock_ws():
    """Create mock WebSocket connection."""
    ws = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive = AsyncMock()
    ws.closed = False
    ws.close = AsyncMock()
    return ws

@pytest.fixture
def mock_config():
    """Create mock configuration."""
    return {
        "host": "localhost",
        "port": 8123,
        "token": "test_token",
        "user_id": "test_user",
        "computer_id": "test_pc"
    }

@pytest.fixture
async def client(mock_session, mock_ws, mock_config):
    """Create test client."""
    mock_session.ws_connect.return_value = mock_ws
    client = TWGClient(mock_config)
    client._session = mock_session
    client._ws = mock_ws
    client._subscription_id = 1
    return client

async def test_connect(client, mock_session, mock_ws):
    """Test client connection."""
    mock_ws.receive.return_value = WSMessage(
        type=WSMsgType.TEXT,
        data='{"type": "auth_ok", "ha_version": "2023.12.0"}',
        extra=None
    )
    
    await client.connect()
    mock_session.ws_connect.assert_called_once()
    mock_ws.send_json.assert_called_with({
        "type": "auth",
        "access_token": "test_token"
    })

async def test_send_state_update(client, mock_session):
    """Test sending state updates."""
    state = {
        "state": "active",
        "windows": ["Test Window"],
        "processes": ["test.exe"],
        "browser_urls": ["https://example.com"]
    }
    
    await client.send_state_update(state)
    mock_session.post.assert_called_once()
    assert mock_session.post.call_count == 1

async def test_update_loop(client, mock_session):
    """Test update loop."""
    client._update_count = 0
    client._max_updates = 1
    
    state = {
        "state": "active",
        "windows": ["Test Window"],
        "processes": ["test.exe"],
        "browser_urls": ["https://example.com"]
    }
    
    with patch.object(client, 'get_current_state', return_value=state):
        await client.update_loop()
        
    assert mock_session.post.call_count == 1

async def test_websocket_message_handling(client, mock_ws):
    """Test handling WebSocket messages."""
    # Auth OK message
    mock_ws.receive.return_value = WSMessage(
        type=WSMsgType.TEXT,
        data='{"type": "auth_ok", "ha_version": "2023.12.0"}',
        extra=None
    )
    await client.handle_websocket_message(mock_ws.receive())
    
    # Config update message
    mock_ws.receive.return_value = WSMessage(
        type=WSMsgType.TEXT,
        data='{"id": 1, "type": "result", "success": true, "result": {"blocked_categories": ["gaming"]}}',
        extra=None
    )
    await client.handle_websocket_message(mock_ws.receive())
    
    assert client._blocked_categories == {"gaming"}

async def test_config_subscription(client, mock_ws):
    """Test subscribing to configuration updates."""
    await client.subscribe_to_config()
    mock_ws.send_json.assert_called_with({
        "id": client._subscription_id,
        "type": "subscribe_trigger",
        "trigger": {
            "platform": "state",
            "entity_id": f"sensor.twg_test_user_config"
        }
    })

async def test_url_categorization(client):
    """Test URL categorization."""
    urls = {
        "https://www.youtube.com/watch?v=123": "video",
        "https://www.facebook.com": "social",
        "https://www.twitter.com": "social",
        "https://www.twitch.tv": "gaming",
        "https://www.reddit.com/r/gaming": "gaming"
    }
    
    for url, expected_category in urls.items():
        assert client._categorize_url(url) == expected_category

async def test_reconnection(client, mock_ws):
    """Test WebSocket reconnection."""
    client._reconnect_attempts = 0
    client._max_reconnect_delay = 1
    
    # Simulate connection error
    mock_ws.receive.side_effect = ConnectionError
    
    with pytest.raises(ConnectionError):
        await client.handle_websocket_message(mock_ws.receive())
    
    assert client._reconnect_attempts > 0

async def test_cleanup(client, mock_session, mock_ws):
    """Test client cleanup."""
    await client.cleanup()
    mock_ws.close.assert_called_once()
    mock_session.close.assert_called_once() 