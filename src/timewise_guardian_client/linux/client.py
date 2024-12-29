"""Linux client implementation for Timewise Guardian."""
import asyncio
import logging
import os
import psutil
import dbus
import sqlite3
from typing import Dict, Optional, Set
from pathlib import Path
import glob
import shutil
import time

from ..common.client import BaseClient
from ..common.config import Config

logger = logging.getLogger(__name__)

class LinuxClient(BaseClient):
    """Linux client implementation."""

    BROWSER_PROCESSES = {
        'chrome': {
            'history_path': '.config/google-chrome/*/History',
            'db_query': 'SELECT url FROM urls ORDER BY last_visit_time DESC LIMIT 5',
            'profiles': ['Default', 'Profile *']
        },
        'firefox': {
            'history_path': '.mozilla/firefox/*.default*/places.sqlite',
            'db_query': 'SELECT url FROM moz_places ORDER BY last_visit_date DESC LIMIT 5',
            'profiles': None  # Firefox uses profile discovery
        },
        'chromium': {
            'history_path': '.config/chromium/*/History',
            'db_query': 'SELECT url FROM urls ORDER BY last_visit_time DESC LIMIT 5',
            'profiles': ['Default', 'Profile *']
        },
        'brave': {
            'history_path': '.config/BraveSoftware/Brave-Browser/*/History',
            'db_query': 'SELECT url FROM urls ORDER BY last_visit_time DESC LIMIT 5',
            'profiles': ['Default', 'Profile *']
        },
        'opera': {
            'history_path': '.config/opera/History',
            'db_query': 'SELECT url FROM urls ORDER BY last_visit_time DESC LIMIT 5',
            'profiles': ['Default']
        },
        'vivaldi': {
            'history_path': '.config/vivaldi/*/History',
            'db_query': 'SELECT url FROM urls ORDER BY last_visit_time DESC LIMIT 5',
            'profiles': ['Default', 'Profile *']
        },
        'librewolf': {
            'history_path': '.librewolf/*.default*/places.sqlite',
            'db_query': 'SELECT url FROM moz_places ORDER BY last_visit_date DESC LIMIT 5',
            'profiles': None  # Firefox-based, uses profile discovery
        }
    }

    def __init__(self, config: Config):
        """Initialize Linux client."""
        super().__init__(config)
        self.browser_pids: Set[int] = set()
        self.session_bus = None
        self.wm_interface = None
        self._init_dbus()

    def _init_dbus(self) -> None:
        """Initialize D-Bus connections."""
        try:
            # Connect to session bus
            self.session_bus = dbus.SessionBus()
            
            # Try GNOME Shell first
            try:
                wm_proxy = self.session_bus.get_object(
                    'org.gnome.Shell',
                    '/org/gnome/Shell/WindowManager'
                )
                self.wm_interface = dbus.Interface(
                    wm_proxy,
                    'org.gnome.Shell.WindowManager'
                )
                logger.info("Connected to GNOME Shell window manager")
            except dbus.exceptions.DBusException:
                logger.debug("GNOME Shell not available, trying alternatives")
                
                # Try KDE Plasma
                try:
                    wm_proxy = self.session_bus.get_object(
                        'org.kde.KWin',
                        '/KWin'
                    )
                    self.wm_interface = dbus.Interface(
                        wm_proxy,
                        'org.kde.KWin'
                    )
                    logger.info("Connected to KDE Plasma window manager")
                except dbus.exceptions.DBusException:
                    logger.warning("No supported window manager found")
            
        except Exception as e:
            logger.error("Failed to initialize D-Bus: %s", str(e))

    async def update_active_windows(self) -> None:
        """Update list of active windows."""
        try:
            # Use wmctrl to get window information
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
                        if process.name() in self.BROWSER_PROCESSES:
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
                    time.sleep(1)  # Wait a second before retrying

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
                username = process.username()
                
                if process_name in self.BROWSER_PROCESSES:
                    urls = self._get_browser_history(process_name, username)
                    for url in urls:
                        self.browser_urls[f"{process_name}_{pid}"] = url
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            except Exception as e:
                logger.error("Error updating browser activity: %s", str(e)) 