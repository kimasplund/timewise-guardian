"""Windows client for Timewise Guardian."""
import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, Optional

import psutil
import requests
import win32gui
import win32process
from browser_history.browsers import Chrome, Firefox, Safari
from win32com.client import GetObject

_LOGGER = logging.getLogger(__name__)

class WindowsMonitor:
    """Monitor Windows system for user activity."""

    def __init__(self, config_path: str = "config.yaml") -> None:
        """Initialize the monitor."""
        self.config_path = config_path
        self.config = self._load_config()
        self.current_user = None
        self.current_window = None
        self.current_process = None
        self.browser_history = {}
        self.category_times = {}
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Set up logging."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler("twg_monitor.log"),
                logging.StreamHandler(),
            ],
        )

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except Exception as e:
            _LOGGER.error("Failed to load config: %s", e)
            return {}

    def get_active_window_info(self) -> Dict[str, str]:
        """Get information about the active window."""
        try:
            window = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(window)
            process = psutil.Process(pid)
            
            return {
                "window_title": win32gui.GetWindowText(window),
                "process_name": process.name(),
                "exe_path": process.exe(),
            }
        except Exception as e:
            _LOGGER.error("Failed to get window info: %s", e)
            return {
                "window_title": "Unknown",
                "process_name": "Unknown",
                "exe_path": "Unknown",
            }

    def get_current_user(self) -> str:
        """Get the currently logged in user."""
        try:
            wmi = GetObject("winmgmts://./root/cimv2")
            sessions = wmi.ExecQuery("SELECT * FROM Win32_ComputerSystem")
            for session in sessions:
                return session.UserName
        except Exception as e:
            _LOGGER.error("Failed to get current user: %s", e)
            return "Unknown"

    def get_browser_history(self) -> Dict[str, Any]:
        """Get recent browser history."""
        history = {}
        browsers = [Chrome(), Firefox(), Safari()]
        
        for browser in browsers:
            try:
                outputs = browser.fetch_history()
                if outputs.histories:
                    history[browser.__class__.__name__] = outputs.histories[-1]
            except Exception as e:
                _LOGGER.error("Failed to get %s history: %s", browser.__class__.__name__, e)
        
        return history

    def categorize_activity(self, window_info: Dict[str, str], browser_history: Dict[str, Any]) -> str:
        """Categorize the current activity based on window info and browser history."""
        # TODO: Implement categorization logic based on config rules
        return "Unknown"

    def update_category_time(self, category: str, duration: float) -> None:
        """Update time spent in a category."""
        if category not in self.category_times:
            self.category_times[category] = 0
        self.category_times[category] += duration

    def check_time_limits(self) -> Dict[str, Any]:
        """Check if any time limits have been exceeded."""
        warnings = {}
        for category, time_spent in self.category_times.items():
            if category in self.config.get("time_limits", {}):
                limit = self.config["time_limits"][category]
                remaining = limit - time_spent
                if remaining <= 0:
                    warnings[category] = {
                        "status": "exceeded",
                        "time_spent": time_spent,
                        "limit": limit,
                    }
                elif remaining <= self.config.get("warning_threshold", 10):
                    warnings[category] = {
                        "status": "warning",
                        "time_spent": time_spent,
                        "limit": limit,
                        "remaining": remaining,
                    }
        return warnings

    def send_state_update(self) -> None:
        """Send state update to Home Assistant."""
        try:
            data = {
                "user": self.current_user,
                "window": self.current_window,
                "process": self.current_process,
                "category_times": self.category_times,
                "timestamp": datetime.now().isoformat(),
            }
            
            response = requests.post(
                f"{self.config['ha_url']}/api/twg/update",
                json=data,
                headers={"Authorization": f"Bearer {self.config['ha_token']}"},
            )
            response.raise_for_status()
        except Exception as e:
            _LOGGER.error("Failed to send state update: %s", e)

    def run(self) -> None:
        """Run the monitor."""
        _LOGGER.info("Starting Windows monitor...")
        
        while True:
            try:
                # Get current state
                self.current_user = self.get_current_user()
                window_info = self.get_active_window_info()
                self.current_window = window_info["window_title"]
                self.current_process = window_info["process_name"]
                
                # Update browser history periodically
                if not hasattr(self, "_last_history_check") or \
                   time.time() - self._last_history_check > 60:
                    self.browser_history = self.get_browser_history()
                    self._last_history_check = time.time()
                
                # Categorize activity and update times
                category = self.categorize_activity(window_info, self.browser_history)
                self.update_category_time(category, 1)  # 1 second increment
                
                # Check time limits
                warnings = self.check_time_limits()
                if warnings:
                    _LOGGER.warning("Time limit warnings: %s", warnings)
                
                # Send state update
                self.send_state_update()
                
                # Sleep for 1 second
                time.sleep(1)
                
            except Exception as e:
                _LOGGER.error("Monitor error: %s", e)
                time.sleep(5)  # Wait before retrying

if __name__ == "__main__":
    monitor = WindowsMonitor()
    monitor.run() 