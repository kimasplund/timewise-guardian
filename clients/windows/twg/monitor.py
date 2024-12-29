"""Windows client for Timewise Guardian."""
import json
import logging
import os
import time
import weakref
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List
from collections import deque

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
        # Use deque with maxlen for fixed-size circular buffers
        self.memory_history = deque(maxlen=86400)  # 24 hours of history
        self.memory_threshold = 90  # Alert when RAM usage is above 90%
        # Use weak references for browser history to allow garbage collection
        self.browser_history = weakref.WeakValueDictionary()
        # Use fixed-size dict for category times
        self.category_times = {}
        self._setup_logging()
        # Track our own memory usage
        self.last_cleanup = datetime.now()
        self.cleanup_interval = timedelta(minutes=5)
        self.max_client_memory_mb = 100  # Maximum memory for the client itself

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

    def _cleanup(self) -> None:
        """Perform memory cleanup if needed."""
        try:
            current_process = psutil.Process(os.getpid())
            memory_mb = current_process.memory_info().rss / (1024 * 1024)

            if memory_mb > self.max_client_memory_mb or datetime.now() - self.last_cleanup > self.cleanup_interval:
                # Clear any unnecessary caches
                self.browser_history.clear()
                
                # Force garbage collection
                import gc
                gc.collect()

                # Log memory usage
                new_memory_mb = current_process.memory_info().rss / (1024 * 1024)
                _LOGGER.debug(
                    "Memory cleanup performed. Usage before: %.2f MB, after: %.2f MB",
                    memory_mb, new_memory_mb
                )
                
                self.last_cleanup = datetime.now()

        except Exception as e:
            _LOGGER.error("Failed to perform memory cleanup: %s", e)

    def get_memory_info(self) -> Dict[str, Any]:
        """Get detailed memory information."""
        try:
            # Check and cleanup our own memory usage first
            self._cleanup()

            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Get per-process memory usage more efficiently
            process_memory = []
            for proc in psutil.process_iter(['name', 'memory_percent']):
                try:
                    # Only get detailed memory info for significant processes (using > 0.1% memory)
                    if proc.info['memory_percent'] > 0.1:
                        process_memory.append({
                            'name': proc.info['name'],
                            'memory_percent': proc.info['memory_percent'],
                            'memory_mb': proc.memory_info().rss / (1024 * 1024)
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Sort and limit top processes efficiently
            process_memory.sort(key=lambda x: x['memory_percent'], reverse=True)
            top_processes = process_memory[:10]

            memory_info = {
                'total': memory.total / (1024 * 1024 * 1024),  # GB
                'available': memory.available / (1024 * 1024 * 1024),  # GB
                'used': memory.used / (1024 * 1024 * 1024),  # GB
                'percent': memory.percent,
                'swap_total': swap.total / (1024 * 1024 * 1024),  # GB
                'swap_used': swap.used / (1024 * 1024 * 1024),  # GB
                'swap_percent': swap.percent,
                'top_processes': top_processes,
                'timestamp': datetime.now().isoformat(),
                'client_memory_mb': psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
            }

            # Store historical data efficiently using deque
            self.memory_history.append({
                'timestamp': memory_info['timestamp'],
                'percent': memory_info['percent'],
                'swap_percent': memory_info['swap_percent']
            })

            # Check for memory alerts
            if memory_info['percent'] > self.memory_threshold:
                self._handle_memory_alert(memory_info)

            return memory_info

        except Exception as e:
            _LOGGER.error("Failed to get memory info: %s", e)
            return {}

    def _handle_memory_alert(self, memory_info: Dict[str, Any]) -> None:
        """Handle high memory usage alerts."""
        try:
            alert_data = {
                'type': 'memory_alert',
                'severity': 'warning' if memory_info['percent'] < 95 else 'critical',
                'message': f"High memory usage: {memory_info['percent']:.1f}%",
                'details': {
                    'available_gb': memory_info['available'],
                    'top_processes': memory_info['top_processes'][:5]  # Top 5 memory consumers
                },
                'timestamp': datetime.now().isoformat()
            }

            # Send alert to Home Assistant
            self.send_alert(alert_data)

            # Log the alert
            _LOGGER.warning("Memory alert: %s", alert_data['message'])

        except Exception as e:
            _LOGGER.error("Failed to handle memory alert: %s", e)

    def send_alert(self, alert_data: Dict[str, Any]) -> None:
        """Send alert to Home Assistant."""
        try:
            response = requests.post(
                f"{self.config['ha_url']}/api/twg/alert",
                json=alert_data,
                headers={"Authorization": f"Bearer {self.config['ha_token']}"},
            )
            response.raise_for_status()
        except Exception as e:
            _LOGGER.error("Failed to send alert: %s", e)

    def get_memory_trends(self) -> Dict[str, Any]:
        """Calculate memory usage trends efficiently."""
        try:
            if not self.memory_history:
                return {}

            # Convert deque to list only for the needed samples
            hour_samples = min(3600, len(self.memory_history))
            last_hour = list(self.memory_history)[-hour_samples:]
            
            # Calculate statistics in a single pass
            hour_stats = {
                'sum': 0,
                'max': float('-inf'),
                'min': float('inf'),
                'swap_sum': 0,
                'swap_max': float('-inf')
            }

            for sample in last_hour:
                percent = sample['percent']
                swap_percent = sample['swap_percent']
                
                hour_stats['sum'] += percent
                hour_stats['max'] = max(hour_stats['max'], percent)
                hour_stats['min'] = min(hour_stats['min'], percent)
                hour_stats['swap_sum'] += swap_percent
                hour_stats['swap_max'] = max(hour_stats['swap_max'], swap_percent)

            hour_avg = hour_stats['sum'] / len(last_hour)
            swap_avg = hour_stats['swap_sum'] / len(last_hour)

            # Determine trend by comparing with the oldest sample
            trend = 'increasing' if hour_avg > last_hour[0]['percent'] else 'decreasing'

            return {
                'last_hour': {
                    'average': hour_avg,
                    'maximum': hour_stats['max'],
                    'minimum': hour_stats['min'],
                    'trend': trend
                },
                'swap_usage': {
                    'average': swap_avg,
                    'maximum': hour_stats['swap_max']
                }
            }

        except Exception as e:
            _LOGGER.error("Failed to calculate memory trends: %s", e)
            return {}

    def send_state_update(self) -> None:
        """Send state update to Home Assistant."""
        try:
            # Get memory info and trends efficiently
            memory_info = self.get_memory_info()
            memory_trends = self.get_memory_trends()
            
            # Create update data with minimal memory allocation
            data = {
                "user": self.current_user,
                "window": self.current_window,
                "process": self.current_process,
                "category_times": self.category_times,
                "memory_info": memory_info,
                "memory_trends": memory_trends,
                "timestamp": datetime.now().isoformat(),
            }
            
            # Send update
            response = requests.post(
                f"{self.config['ha_url']}/api/twg/update",
                json=data,
                headers={"Authorization": f"Bearer {self.config['ha_token']}"},
            )
            response.raise_for_status()

            # Cleanup after sending update
            self._cleanup()

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