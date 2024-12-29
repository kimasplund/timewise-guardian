"""Windows client implementation for Timewise Guardian."""
import asyncio
import logging
import platform
import socket
import win32gui
import win32process
import psutil
import sqlite3
from typing import Dict, Optional, Tuple, Set
from pathlib import Path
import os
import glob
import shutil

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

    BROWSER_PROCESSES = {
        'chrome.exe': {
            'history_path': r'AppData\Local\Google\Chrome\User Data\*\History',
            'db_query': 'SELECT url FROM urls ORDER BY last_visit_time DESC LIMIT 5',
            'profiles': ['Default', 'Profile *']
        },
        'firefox.exe': {
            'history_path': r'AppData\Roaming\Mozilla\Firefox\Profiles\*.default*\places.sqlite',
            'db_query': 'SELECT url FROM moz_places ORDER BY last_visit_date DESC LIMIT 5',
            'profiles': None  # Firefox uses profile discovery
        },
        'msedge.exe': {
            'history_path': r'AppData\Local\Microsoft\Edge\User Data\*\History',
            'db_query': 'SELECT url FROM urls ORDER BY last_visit_time DESC LIMIT 5',
            'profiles': ['Default', 'Profile *']
        },
        'brave.exe': {
            'history_path': r'AppData\Local\BraveSoftware\Brave-Browser\User Data\*\History',
            'db_query': 'SELECT url FROM urls ORDER BY last_visit_time DESC LIMIT 5',
            'profiles': ['Default', 'Profile *']
        },
        'opera.exe': {
            'history_path': r'AppData\Roaming\Opera Software\Opera Stable\History',
            'db_query': 'SELECT url FROM urls ORDER BY last_visit_time DESC LIMIT 5',
            'profiles': ['Default']
        },
        'vivaldi.exe': {
            'history_path': r'AppData\Local\Vivaldi\User Data\*\History',
            'db_query': 'SELECT url FROM urls ORDER BY last_visit_time DESC LIMIT 5',
            'profiles': ['Default', 'Profile *']
        }
    }

    def __init__(self, config: Config):
        """Initialize Windows client."""
        super().__init__(config)
        self.browser_pids: Set[int] = set()
        self.computer_id = self._generate_computer_id()
        self.computer_info = self._get_computer_info()

    def _generate_computer_id(self) -> str:
        """Generate a unique computer ID."""
        return f"{socket.gethostname().lower()}"

    def _get_computer_info(self) -> dict:
        """Get computer information."""
        return {
            "id": self.computer_id,
            "name": socket.gethostname(),
            "os": f"Windows {platform.win32_ver()[0]}",
            "version": platform.win32_ver()[1]
        }

    async def connect(self) -> None:
        """Connect to Home Assistant and register computer."""
        await super().connect_websocket()
        
        # Register computer
        try:
            await self.ws.send_json({
                "type": "twg/register_computer",
                "computer_info": self.computer_info
            })
            response = await self.ws.recv_json()
            if response.get("success"):
                logger.info("Successfully registered computer with ID: %s", self.computer_id)
            else:
                logger.error("Failed to register computer: %s", response.get("error", "Unknown error"))
        except Exception as e:
            logger.error("Error registering computer: %s", str(e))
            raise

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
                if get_process_name(pid) in self.BROWSER_PROCESSES.keys()
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

    def _get_browser_history(self, process_name: str, username: str) -> Set[str]:
        """Get browser history for a specific browser."""
        urls = set()
        browser_info = self.BROWSER_PROCESSES.get(process_name)
        if not browser_info:
            return urls

        try:
            base_path = os.path.expanduser(f'~{username}')
            
            # Handle profile-based browsers
            if browser_info['profiles']:
                for profile in browser_info['profiles']:
                    # Replace * with actual profile pattern
                    profile_path = browser_info['history_path'].replace('*', profile)
                    full_path = os.path.join(base_path, profile_path)
                    
                    # Handle wildcards in profile names
                    if '*' in full_path:
                        matching_paths = glob.glob(full_path)
                        for history_path in matching_paths:
                            urls.update(self._read_history_db(history_path, browser_info['db_query']))
                    else:
                        urls.update(self._read_history_db(full_path, browser_info['db_query']))
            else:
                # Handle Firefox-style profile discovery
                full_path = os.path.join(base_path, browser_info['history_path'])
                matching_paths = glob.glob(full_path)
                for history_path in matching_paths:
                    urls.update(self._read_history_db(history_path, browser_info['db_query']))

        except Exception as e:
            logger.error("Error reading browser history for %s: %s", process_name, str(e))

        return urls

    def _read_history_db(self, history_path: str, query: str) -> Set[str]:
        """Read URLs from a browser history database."""
        urls = set()
        if not os.path.exists(history_path):
            return urls

        # Create a copy of the database file to avoid lock issues
        temp_db = f"{history_path}.tmp"
        try:
            # Wait for file to be unlocked
            max_retries = 3
            retry_count = 0
            while retry_count < max_retries:
                try:
                    shutil.copy2(history_path, temp_db)
                    break
                except (PermissionError, FileNotFoundError):
                    retry_count += 1
                    if retry_count == max_retries:
                        return urls
                    asyncio.sleep(1)  # Wait a second before retrying

            try:
                with sqlite3.connect(temp_db) as conn:
                    conn.row_factory = sqlite3.Row  # Enable column access by name
                    cursor = conn.cursor()
                    cursor.execute(query)
                    urls.update(row[0] for row in cursor.fetchall())
            finally:
                try:
                    os.remove(temp_db)
                except OSError:
                    pass

        except Exception as e:
            logger.error("Error reading history database %s: %s", history_path, str(e))

        return urls

    async def update_browser_activity(self) -> None:
        """Update browser activity."""
        self.browser_urls.clear()
        
        for pid in self.browser_pids:
            try:
                process = psutil.Process(pid)
                process_name = process.name()
                username = process.username().split('\\')[-1]  # Remove domain prefix
                
                if process_name in self.BROWSER_PROCESSES:
                    urls = self._get_browser_history(process_name, username)
                    for url in urls:
                        self.browser_urls[f"{process_name}_{pid}"] = url
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            except Exception as e:
                logger.error("Error updating browser activity: %s", str(e)) 