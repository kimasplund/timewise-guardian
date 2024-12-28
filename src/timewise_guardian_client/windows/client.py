"""Windows client implementation for Timewise Guardian."""
import asyncio
import logging
import win32gui
import win32process
import psutil
from typing import Dict, Optional, Tuple

from ..common.client import BaseClient
from ..common.config import Config

logger = logging.getLogger(__name__)

def get_window_info() -> Dict[int, Tuple[str, int]]:
    """Get information about all visible windows."""
    def callback(hwnd: int, windows: dict) -> bool:
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    windows[hwnd] = (title, pid)
                except Exception:
                    pass
        return True

    windows = {}
    win32gui.EnumWindows(callback, windows)
    return windows

def get_process_name(pid: int) -> Optional[str]:
    """Get process name from PID."""
    try:
        process = psutil.Process(pid)
        return process.name()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None

class WindowsClient(BaseClient):
    """Windows client implementation."""

    def __init__(self, config: Config):
        """Initialize Windows client."""
        super().__init__(config)
        self.browser_pids = set()

    async def update_active_windows(self) -> None:
        """Update list of active windows."""
        try:
            windows = get_window_info()
            self.active_windows = {
                hwnd: title for hwnd, (title, _) in windows.items()
            }
            
            # Update browser PIDs
            self.browser_pids = {
                pid for _, (_, pid) in windows.items()
                if get_process_name(pid) in ['chrome.exe', 'firefox.exe', 'msedge.exe']
            }
            
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
        # For now, we just log the browser PIDs
        if self.browser_pids:
            logger.debug("Active browser PIDs: %s", self.browser_pids) 