"""Linux client implementation for Timewise Guardian."""
import asyncio
import logging
import os
import psutil
import dbus
from typing import Dict, Optional, Set
from pathlib import Path

from ..common.client import BaseClient
from ..common.config import Config

logger = logging.getLogger(__name__)

class LinuxClient(BaseClient):
    """Linux client implementation."""

    def __init__(self, config: Config):
        """Initialize Linux client."""
        super().__init__(config)
        self.session_bus = dbus.SessionBus()
        self.browser_pids: Set[int] = set()
        self._init_dbus()

    def _init_dbus(self) -> None:
        """Initialize D-Bus connections."""
        try:
            # Connect to window manager
            self.wm_proxy = self.session_bus.get_object(
                'org.gnome.Shell',
                '/org/gnome/Shell/WindowManager'
            )
            self.wm_interface = dbus.Interface(
                self.wm_proxy,
                'org.gnome.Shell.WindowManager'
            )
            
            # Connect to browser extensions (if available)
            self._init_browser_extensions()
            
        except Exception as e:
            logger.error("Failed to initialize D-Bus: %s", str(e))

    def _init_browser_extensions(self) -> None:
        """Initialize browser extension connections."""
        # This is a placeholder for browser extension integration
        # In a real implementation, you would:
        # 1. Connect to browser extension via native messaging
        # 2. Set up communication channels
        # 3. Register for URL change notifications
        pass

    async def update_active_windows(self) -> None:
        """Update list of active windows."""
        try:
            # Use xdotool or wmctrl to get window information
            proc = await asyncio.create_subprocess_exec(
                'wmctrl', '-l', '-p',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            
            windows = {}
            for line in stdout.decode().splitlines():
                parts = line.split(None, 4)
                if len(parts) >= 5:
                    window_id = int(parts[0], 16)
                    pid = int(parts[2])
                    title = parts[4]
                    windows[window_id] = title
                    
                    # Check if this is a browser window
                    try:
                        process = psutil.Process(pid)
                        if process.name() in ['chrome', 'firefox', 'chromium']:
                            self.browser_pids.add(pid)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            
            self.active_windows = windows
            
        except Exception as e:
            logger.error("Error updating active windows: %s", str(e))

    async def update_active_processes(self) -> None:
        """Update list of active processes."""
        try:
            self.active_processes = {
                proc.name() for proc in psutil.process_iter(['name'])
                if proc.info['name']
            }
        except Exception as e:
            logger.error("Error updating active processes: %s", str(e))

    async def update_browser_activity(self) -> None:
        """Update browser activity."""
        # This is a placeholder. In a real implementation, you would:
        # 1. Use browser extensions or native messaging to get active URLs
        # 2. Monitor browser history files
        # 3. Use browser automation tools
        # For now, we just check browser history files
        for pid in self.browser_pids:
            try:
                process = psutil.Process(pid)
                username = process.username()
                
                # Check Firefox history
                firefox_path = Path(f"/home/{username}/.mozilla/firefox")
                if firefox_path.exists():
                    for profile in firefox_path.glob("*.default*"):
                        history_file = profile / "places.sqlite"
                        if history_file.exists():
                            logger.debug("Found Firefox history at %s", history_file)
                
                # Check Chrome/Chromium history
                chrome_path = Path(f"/home/{username}/.config/google-chrome")
                if chrome_path.exists():
                    history_file = chrome_path / "Default/History"
                    if history_file.exists():
                        logger.debug("Found Chrome history at %s", history_file)
                
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            except Exception as e:
                logger.error("Error checking browser history: %s", str(e)) 