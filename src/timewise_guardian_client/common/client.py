"""Base client implementation."""
import asyncio
import json
import logging
from typing import Dict, Any, Optional
from urllib.parse import urlparse
from .blocklists import BlocklistManager

logger = logging.getLogger(__name__)

class BaseClient:
    """Base client implementation."""
    
    def __init__(self, config):
        """Initialize the client."""
        self.config = config
        self.running = False
        self.ws = None
        self.session = None
        self.blocklist_manager = BlocklistManager(config.config_dir)
        self._update_task = None
        self._subscription_id = None
        self._registered = False
    
    def get_unique_user_id(self) -> str:
        """Generate a unique user identifier that includes both computer and user."""
        computer_id = self.config.computer_id.lower()
        system_user = self.config.system_user.lower()
        return f"twg_{computer_id}_{system_user}"
    
    def get_user_entity_id(self) -> str:
        """Get the entity ID for this computer user."""
        return f"sensor.{self.get_unique_user_id()}"
    
    def get_user_friendly_name(self) -> str:
        """Get a user-friendly name for display in Home Assistant."""
        return f"{self.config.system_user} on {self.config.computer_id}"
    
    def get_state_attributes(self) -> Dict[str, Any]:
        """Get the state attributes for the user entity."""
        return {
            "computer_id": self.config.computer_id,
            "system_user": self.config.system_user,
            "friendly_name": self.get_user_friendly_name(),
            "icon": "mdi:account-multiple",
            "device_class": "computer_user",
            "ha_user": None,  # Will be set through UI when mapped
        }
    
    async def update_user_state(self) -> None:
        """Update the user entity state in Home Assistant."""
        if not self.session:
            return
        
        entity_id = self.get_user_entity_id()
        state = "active"  # Could be expanded to include "idle", "away", etc.
        
        await self.send_state_update({
            "state": state,
            "attributes": self.get_state_attributes()
        }, entity_id=entity_id)
    
    async def send_state_update(self, state: Dict[str, Any], entity_id: str = None) -> None:
        """Send state update to Home Assistant."""
        if not self.session:
            return
        
        if entity_id is None:
            entity_id = "sensor.twg_activity"
        
        url = f"{self.config.ha_url}/api/states/{entity_id}"
        headers = {"Authorization": f"Bearer {self.config.ha_token}"}
        
        try:
            async with self.session.post(url, json=state, headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"Failed to update state: {await response.text()}")
        except Exception as e:
            logger.error(f"Error sending state update: {e}")
    
    def is_url_blocked(self, url: str) -> bool:
        """Check if a URL should be blocked."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            return self.blocklist_manager.is_domain_blocked(domain)
        except Exception as e:
            logger.error(f"Error checking URL block status: {e}")
            return False
    
    async def handle_config_update(self, config: Dict[str, Any]) -> None:
        """Handle configuration update from Home Assistant."""
        logger.info("Received configuration update")
        
        # Handle user-specific settings
        user_id = self.get_unique_user_id()
        user_config = config.get("users", {}).get(user_id, {})
        
        # Update blocklist categories for this user
        if "blocklist_categories" in user_config:
            logger.info(f"Updating blocklist categories for user {user_id}")
            self.blocklist_manager.update_enabled_categories(user_config["blocklist_categories"])
        
        # Update user-specific whitelist
        if "whitelist" in user_config:
            logger.info(f"Updating whitelist for user {user_id}")
            # Clear existing whitelist for this user
            self.blocklist_manager.whitelist.clear()
            for domain in user_config["whitelist"]:
                self.blocklist_manager.add_to_whitelist(domain)
        
        # Update user-specific blacklist
        if "blacklist" in user_config:
            logger.info(f"Updating blacklist for user {user_id}")
            # Clear existing blacklist for this user
            self.blocklist_manager.blacklist.clear()
            for domain in user_config["blacklist"]:
                self.blocklist_manager.add_to_blacklist(domain)
        
        # Save configuration
        self.blocklist_manager.save_config()
    
    async def subscribe_to_config(self) -> None:
        """Subscribe to configuration updates via WebSocket."""
        if not self.ws:
            return
        
        # Subscribe to configuration updates
        msg = {
            "type": "subscribe_trigger",
            "trigger": {
                "platform": "event",
                "event_type": "twg_config_update"
            }
        }
        
        try:
            await self.ws.send_json(msg)
            response = await self.ws.receive_json()
            if response.get("success"):
                self._subscription_id = response.get("id")
                logger.info("Subscribed to configuration updates")
        except Exception as e:
            logger.error(f"Error subscribing to config updates: {e}")
    
    async def handle_websocket_message(self, msg: Dict[str, Any]) -> None:
        """Handle incoming WebSocket message."""
        try:
            if msg.get("type") == "event" and msg.get("event", {}).get("event_type") == "twg_config_update":
                # Extract configuration from event data
                config = msg["event"]["data"]
                await self.handle_config_update(config)
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
    
    async def register_user(self) -> None:
        """Register this user with Home Assistant."""
        if self._registered:
            return
        
        # Create user entity
        entity_id = self.get_user_entity_id()
        state = "active"
        attributes = self.get_state_attributes()
        
        await self.send_state_update({
            "state": state,
            "attributes": attributes
        }, entity_id=entity_id)
        
        # Notify about new user
        if self.ws:
            try:
                await self.ws.send_json({
                    "type": "fire_event",
                    "event_type": "twg_user_detected",
                    "event_data": {
                        "user_id": self.get_unique_user_id(),
                        "user_info": {
                            "friendly_name": self.get_user_friendly_name(),
                            "computer_id": self.config.computer_id,
                            "system_user": self.config.system_user
                        }
                    }
                })
                self._registered = True
                logger.info(f"Registered user {self.get_unique_user_id()}")
            except Exception as e:
                logger.error(f"Error registering user: {e}")
    
    async def update_categories(self) -> None:
        """Update available blocklist categories."""
        categories = self.blocklist_manager.get_available_categories()
        if self.ws:
            try:
                await self.ws.send_json({
                    "type": "fire_event",
                    "event_type": "twg_categories_updated",
                    "event_data": {
                        "categories": categories
                    }
                })
                logger.info("Updated available categories")
            except Exception as e:
                logger.error(f"Error updating categories: {e}")
    
    async def start(self) -> None:
        """Start the client."""
        # Start blocklist update task
        self._update_task = asyncio.create_task(
            self.blocklist_manager.schedule_updates(interval_hours=24)
        )
        
        # Initial blocklist update
        await self.blocklist_manager.update_blocklists()
        
        # Register user and update categories
        await self.register_user()
        await self.update_categories()
        
        # Subscribe to configuration updates
        await self.subscribe_to_config()
        
        self.running = True
        await self.update_loop()
    
    async def update_loop(self) -> None:
        """Main update loop."""
        while self.running:
            try:
                if self.ws:
                    msg = await self.ws.receive_json()
                    await self.handle_websocket_message(msg)
            except Exception as e:
                logger.error(f"Error in update loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def stop(self) -> None:
        """Stop the client."""
        self.running = False
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
        if self.ws:
            await self.ws.close()
        if self.session:
            await self.session.close() 