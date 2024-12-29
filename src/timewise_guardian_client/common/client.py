"""Base client class for Timewise Guardian."""
import asyncio
import json
import logging
import platform
import re
from typing import Dict, List, Optional, Set, Any
import aiohttp
import websockets
import psutil
from aiohttp import ClientTimeout
from websockets.exceptions import WebSocketException
from urllib.parse import urlparse, parse_qs

from .config import Config

logger = logging.getLogger(__name__)

class BaseClient:
    """Base client class for platform-specific implementations."""

    # Common URL patterns for content categorization
    URL_PATTERNS = {
        'youtube': {
            'domains': ['youtube.com', 'youtu.be'],
            'categories': {
                'gaming': [r'/gaming', r'&category=20'],
                'music': [r'/music', r'&category=10'],
                'education': [r'/education', r'&category=27'],
                'entertainment': [r'/entertainment', r'&category=24']
            }
        },
        'social_media': {
            'domains': ['facebook.com', 'twitter.com', 'instagram.com', 'tiktok.com'],
            'patterns': [r'^https?://[^/]*(?:facebook\.com|twitter\.com|instagram\.com|tiktok\.com)']
        },
        'gaming': {
            'domains': ['twitch.tv', 'steam.com', 'epicgames.com'],
            'patterns': [r'^https?://[^/]*(?:twitch\.tv|steam\.com|epicgames\.com)']
        }
    }

    def __init__(self, config: Config):
        """Initialize client."""
        self.config = config
        self.active_windows: Dict[int, str] = {}
        self.active_processes: Set[str] = set()
        self.browser_urls: Dict[str, str] = {}
        self.running = False
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self._message_id = 0
        self._reconnect_attempts = 0
        self._max_reconnect_delay = 300  # 5 minutes
        self._blocked_urls: Set[str] = set()
        self._url_categories: Dict[str, List[str]] = {}

    def _categorize_url(self, url: str) -> Optional[str]:
        """Categorize a URL based on predefined patterns."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            path = parsed.path.lower()
            query = parse_qs(parsed.query)

            # Check YouTube specific categorization
            if any(yt_domain in domain for yt_domain in self.URL_PATTERNS['youtube']['domains']):
                # Check if it's a video
                if '/watch' in path:
                    video_id = query.get('v', [None])[0]
                    if video_id:
                        # Check category from config
                        for category, patterns in self.URL_PATTERNS['youtube']['categories'].items():
                            if any(re.search(pattern, path) for pattern in patterns):
                                return f'youtube_{category}'
                        return 'youtube_video'
                
                # Check YouTube section
                for category, patterns in self.URL_PATTERNS['youtube']['categories'].items():
                    if any(re.search(pattern, path) for pattern in patterns):
                        return f'youtube_{category}'
                
                return 'youtube'

            # Check social media
            if any(domain.endswith(social_domain) for social_domain in self.URL_PATTERNS['social_media']['domains']):
                return 'social_media'

            # Check gaming sites
            if any(domain.endswith(gaming_domain) for gaming_domain in self.URL_PATTERNS['gaming']['domains']):
                return 'gaming'

        except Exception as e:
            logger.error("Error categorizing URL %s: %s", url, str(e))

        return None

    def _should_block_url(self, url: str) -> bool:
        """Check if a URL should be blocked based on configuration."""
        try:
            # Get URL category
            category = self._categorize_url(url)
            if not category:
                return False

            # Check if category is blocked
            blocked_categories = self.config.ha_settings.get("blocked_categories", {})
            if category in blocked_categories:
                logger.info("Blocking URL %s (category: %s)", url, category)
                return True

            # Check for specific URL patterns
            blocked_patterns = self.config.ha_settings.get("blocked_patterns", [])
            if any(re.search(pattern, url) for pattern in blocked_patterns):
                logger.info("Blocking URL %s (matched pattern)", url)
                return True

            # Check YouTube specific restrictions
            if category.startswith('youtube_'):
                yt_restrictions = self.config.ha_settings.get("youtube_restrictions", {})
                subcategory = category.split('_')[1]
                if subcategory in yt_restrictions.get("blocked_categories", []):
                    logger.info("Blocking YouTube %s content: %s", subcategory, url)
                    return True

        except Exception as e:
            logger.error("Error checking URL block status %s: %s", url, str(e))

        return False

    async def handle_url_access(self, url: str) -> bool:
        """Handle URL access attempt and return whether it should be blocked."""
        if self._should_block_url(url):
            self._blocked_urls.add(url)
            # Notify Home Assistant about blocked attempt
            await self.send_state_update({
                "state": "blocked_attempt",
                "attributes": {
                    "url": url,
                    "category": self._categorize_url(url),
                    "timestamp": datetime.datetime.now().isoformat()
                }
            })
            return True
        return False

    async def _create_session(self) -> None:
        """Create aiohttp session with timeout."""
        if self.session is None or self.session.closed:
            timeout = ClientTimeout(total=30)  # 30 seconds timeout
            self.session = aiohttp.ClientSession(timeout=timeout)

    async def connect_websocket(self) -> None:
        """Connect to Home Assistant WebSocket API."""
        url = self.config.ha_url.replace('http', 'ws', 1) + "/api/websocket"
        
        try:
            self.ws = await websockets.connect(url)
            auth_msg = json.loads(await self.ws.recv())
            
            if auth_msg["type"] != "auth_required":
                raise Exception("Unexpected initial message")
                
            await self.ws.send(json.dumps({
                "type": "auth",
                "access_token": self.config.ha_token
            }))
            
            auth_result = json.loads(await self.ws.recv())
            if auth_result.get("type") == "auth_ok":
                logger.info("Connected to Home Assistant WebSocket API")
                self._reconnect_attempts = 0  # Reset counter on successful connection
                await self.subscribe_to_config()
            else:
                raise Exception("Authentication failed")
                
        except Exception as e:
            logger.error("WebSocket connection failed: %s", str(e))
            raise

    async def subscribe_to_config(self) -> None:
        """Subscribe to configuration updates from Home Assistant."""
        if not self.ws:
            return

        self._message_id += 1
        await self.ws.send({
            "id": self._message_id,
            "type": "subscribe_trigger",
            "trigger": {
                "platform": "state",
                "entity_id": "twg.config"
            }
        })

        # Get initial config
        self._message_id += 1
        await self.ws.send({
            "id": self._message_id,
            "type": "get_states",
            "entity_id": "twg.config"
        })

    async def handle_websocket_messages(self) -> None:
        """Handle incoming WebSocket messages."""
        if not self.ws:
            return

        try:
            while self.running:
                try:
                    message = json.loads(await self.ws.recv())
                    if message.get("type") == "trigger":
                        # Config update received
                        new_state = message["event"]["data"]["new_state"]
                        if new_state["entity_id"] == "twg.config":
                            self.config.update_ha_settings(new_state["attributes"])
                    elif message.get("type") == "result":
                        # Initial state received
                        if "result" in message:
                            for state in message["result"]:
                                if state["entity_id"] == "twg.config":
                                    self.config.update_ha_settings(state["attributes"])
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("WebSocket connection closed")
                    if self.running:
                        await self.reconnect()
                        break
                except json.JSONDecodeError as e:
                    logger.error("Invalid JSON message received: %s", str(e))
                    continue
                
        except Exception as e:
            logger.error("Error handling WebSocket messages: %s", str(e))
            if self.running:
                await self.reconnect()

    async def reconnect(self) -> None:
        """Reconnect to WebSocket API with exponential backoff."""
        try:
            await self.disconnect_websocket()
            
            # Calculate delay with exponential backoff
            delay = min(2 ** self._reconnect_attempts, self._max_reconnect_delay)
            self._reconnect_attempts += 1
            
            logger.info("Attempting reconnection in %d seconds (attempt %d)", 
                       delay, self._reconnect_attempts)
            await asyncio.sleep(delay)
            
            await self.connect_websocket()
            
        except Exception as e:
            logger.error("Reconnection failed: %s", str(e))

    async def disconnect_websocket(self) -> None:
        """Disconnect from Home Assistant WebSocket API."""
        if self.ws:
            await self.ws.close()
            self.ws = None

    async def send_state_update(self, data: dict) -> None:
        """Send state update to Home Assistant."""
        await self._create_session()

        headers = {
            "Authorization": f"Bearer {self.config.ha_token}",
            "Content-Type": "application/json",
        }

        try:
            async with self.session.post(
                f"{self.config.ha_url}/api/states/sensor.twg_activity",
                json=data,
                headers=headers
            ) as response:
                if response.status != 200:
                    logger.error("Failed to update state: %s", await response.text())
        except asyncio.TimeoutError:
            logger.error("Timeout while sending state update")
        except Exception as e:
            logger.error("Error sending state update: %s", str(e))

    def get_active_category(self) -> Optional[str]:
        """Get the currently active category based on active windows and processes."""
        # Check active windows
        for window_title in self.active_windows.values():
            for category in self.config.ha_settings.get("categories", {}):
                patterns = self.config.get_category_window_titles(category)
                if any(pattern.match(window_title) for pattern in patterns):
                    return category

        # Check active processes
        for process_name in self.active_processes:
            for category in self.config.ha_settings.get("categories", {}):
                patterns = self.config.get_category_processes(category)
                if any(pattern.match(process_name) for pattern in patterns):
                    return category

        # Check browser URLs
        for url in self.browser_urls.values():
            for category in self.config.ha_settings.get("categories", {}):
                patterns = self.config.get_category_browser_patterns(category)
                if any(pattern.match(url) for pattern in patterns.get("urls", [])):
                    return category

        return None

    async def update_loop(self) -> None:
        """Main update loop."""
        while self.running:
            try:
                # Update active windows and processes
                await self.update_active_windows()
                await self.update_active_processes()
                await self.update_browser_activity()

                # Get current category
                category = self.get_active_category()

                # Check for blocked URLs
                blocked_urls = set()
                for url in self.browser_urls.values():
                    if await self.handle_url_access(url):
                        blocked_urls.add(url)

                # Send state update
                await self.send_state_update({
                    "state": category or "idle",
                    "attributes": {
                        "windows": list(self.active_windows.values()),
                        "processes": list(self.active_processes),
                        "browser_urls": list(self.browser_urls.values()),
                        "blocked_urls": list(blocked_urls),
                        "platform": platform.system(),
                        "memory_usage": self.get_memory_usage()
                    }
                })

            except Exception as e:
                logger.error("Error in update loop: %s", str(e))

            await asyncio.sleep(self.config.sync_interval)

    def get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage information."""
        process = psutil.Process()
        memory_info = process.memory_info()
        return {
            "rss_mb": memory_info.rss / (1024 * 1024),
            "vms_mb": memory_info.vms / (1024 * 1024),
            "percent": process.memory_percent()
        }

    async def update_active_windows(self) -> None:
        """Update list of active windows. To be implemented by platform-specific classes."""
        raise NotImplementedError

    async def update_active_processes(self) -> None:
        """Update list of active processes. To be implemented by platform-specific classes."""
        raise NotImplementedError

    async def update_browser_activity(self) -> None:
        """Update browser activity. To be implemented by platform-specific classes."""
        raise NotImplementedError

    async def cleanup(self) -> None:
        """Clean up resources."""
        self.running = False
        if self.session and not self.session.closed:
            await self.session.close()
        if self.ws:
            await self.disconnect_websocket()

    def run(self) -> None:
        """Run the client."""
        self.running = True
        loop = asyncio.get_event_loop()
        
        try:
            # Create session
            loop.run_until_complete(self._create_session())
            # Connect WebSocket
            loop.run_until_complete(self.connect_websocket())
            # Start WebSocket message handler
            loop.create_task(self.handle_websocket_messages())
            # Start main update loop
            loop.run_until_complete(self.update_loop())
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            loop.run_until_complete(self.cleanup())
            loop.close()

    def stop(self) -> None:
        """Stop the client."""
        self.running = False 