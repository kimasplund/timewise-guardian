"""Base client class for Timewise Guardian."""
import asyncio
import logging
import platform
from typing import Dict, List, Optional, Set
import aiohttp
import websockets

from .config import Config

logger = logging.getLogger(__name__)

class BaseClient:
    """Base client class for platform-specific implementations."""

    def __init__(self, config: Config):
        """Initialize client."""
        self.config = config
        self.active_windows: Dict[int, str] = {}
        self.active_processes: Set[str] = set()
        self.browser_urls: Dict[str, str] = {}
        self.running = False
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.session: Optional[aiohttp.ClientSession] = None

    async def connect_websocket(self) -> None:
        """Connect to Home Assistant WebSocket API."""
        url = self.config.ha_url.replace('http', 'ws', 1) + "/api/websocket"
        
        try:
            self.ws = await websockets.connect(url)
            auth_msg = await self.ws.recv()
            await self.ws.send({
                "type": "auth",
                "access_token": self.config.ha_token
            })
            auth_result = await self.ws.recv()
            
            if auth_result.get("type") == "auth_ok":
                logger.info("Connected to Home Assistant WebSocket API")
            else:
                raise Exception("Authentication failed")
                
        except Exception as e:
            logger.error("WebSocket connection failed: %s", str(e))
            raise

    async def disconnect_websocket(self) -> None:
        """Disconnect from Home Assistant WebSocket API."""
        if self.ws:
            await self.ws.close()
            self.ws = None

    async def send_state_update(self, data: dict) -> None:
        """Send state update to Home Assistant."""
        if not self.session:
            self.session = aiohttp.ClientSession()

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
        except Exception as e:
            logger.error("Error sending state update: %s", str(e))

    def get_active_category(self) -> Optional[str]:
        """Get the currently active category based on active windows and processes."""
        # Check active windows
        for window_title in self.active_windows.values():
            for category in self.config.get("categories", {}):
                patterns = self.config.get_category_window_titles(category)
                if any(pattern.match(window_title) for pattern in patterns):
                    return category

        # Check active processes
        for process_name in self.active_processes:
            for category in self.config.get("categories", {}):
                patterns = self.config.get_category_processes(category)
                if any(pattern.match(process_name) for pattern in patterns):
                    return category

        # Check browser URLs
        for url in self.browser_urls.values():
            for category in self.config.get("categories", {}):
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

                # Send state update
                await self.send_state_update({
                    "state": category or "idle",
                    "attributes": {
                        "windows": list(self.active_windows.values()),
                        "processes": list(self.active_processes),
                        "browser_urls": list(self.browser_urls.values()),
                        "platform": platform.system()
                    }
                })

            except Exception as e:
                logger.error("Error in update loop: %s", str(e))

            await asyncio.sleep(1)

    async def update_active_windows(self) -> None:
        """Update list of active windows. To be implemented by platform-specific classes."""
        raise NotImplementedError

    async def update_active_processes(self) -> None:
        """Update list of active processes. To be implemented by platform-specific classes."""
        raise NotImplementedError

    async def update_browser_activity(self) -> None:
        """Update browser activity. To be implemented by platform-specific classes."""
        raise NotImplementedError

    def run(self) -> None:
        """Run the client."""
        self.running = True
        loop = asyncio.get_event_loop()
        
        try:
            loop.run_until_complete(self.connect_websocket())
            loop.run_until_complete(self.update_loop())
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            self.running = False
            if self.session:
                loop.run_until_complete(self.session.close())
            loop.run_until_complete(self.disconnect_websocket())
            loop.close()

    def stop(self) -> None:
        """Stop the client."""
        self.running = False 