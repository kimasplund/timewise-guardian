"""Auto-update functionality for TimeWise Guardian."""
import json
import logging
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple

import requests
from packaging import version

from .logging_config import log_error_with_context

logger = logging.getLogger(__name__)

class TWGUpdater:
    """Handles automatic updates for TimeWise Guardian."""

    def __init__(
        self,
        current_version: str,
        check_interval: int = 24,  # hours
        auto_update: bool = True,
        beta_channel: bool = False,
    ):
        """Initialize the updater.
        
        Args:
            current_version: Current version of TWG
            check_interval: Hours between update checks
            auto_update: Whether to automatically install updates
            beta_channel: Whether to use beta versions
        """
        self.current_version = version.parse(current_version)
        self.check_interval = timedelta(hours=check_interval)
        self.auto_update = auto_update
        self.beta_channel = beta_channel
        self._last_check = None
        self._update_info = None
        
        # Set up state file
        self.state_file = self._get_state_file_path()
        self._load_state()

    def _get_state_file_path(self) -> Path:
        """Get the path to the state file."""
        if sys.platform == "win32":
            base_dir = Path(os.environ.get("PROGRAMDATA", "")) / "TimeWiseGuardian"
        else:
            base_dir = Path("/var/lib/twg")
        
        base_dir.mkdir(parents=True, exist_ok=True)
        return base_dir / "updater_state.json"

    def _load_state(self) -> None:
        """Load updater state from file."""
        try:
            if self.state_file.exists():
                with open(self.state_file, "r") as f:
                    state = json.load(f)
                    self._last_check = datetime.fromisoformat(state.get("last_check", ""))
                    self._update_info = state.get("update_info")
        except Exception as e:
            log_error_with_context(logger, e, {"action": "load_state"})

    def _save_state(self) -> None:
        """Save updater state to file."""
        try:
            state = {
                "last_check": self._last_check.isoformat() if self._last_check else None,
                "update_info": self._update_info
            }
            with open(self.state_file, "w") as f:
                json.dump(state, f)
        except Exception as e:
            log_error_with_context(logger, e, {"action": "save_state"})

    def check_for_updates(self) -> Optional[Tuple[str, str]]:
        """Check for available updates.
        
        Returns:
            Tuple of (version, changelog) if update available, None otherwise
        """
        try:
            # Check if it's time to check for updates
            now = datetime.now()
            if (self._last_check and 
                now - self._last_check < self.check_interval):
                return None

            self._last_check = now
            
            # Check PyPI for latest version
            response = requests.get(
                "https://pypi.org/pypi/timewise-guardian-client/json"
            )
            response.raise_for_status()
            data = response.json()
            
            latest_version = version.parse(data["info"]["version"])
            if latest_version > self.current_version:
                changelog = data["info"].get("description", "No changelog available")
                self._update_info = {
                    "version": str(latest_version),
                    "changelog": changelog
                }
                self._save_state()
                return str(latest_version), changelog
                
            return None
            
        except Exception as e:
            log_error_with_context(
                logger, e, 
                {
                    "action": "check_updates",
                    "current_version": str(self.current_version)
                }
            )
            return None

    def update(self, version: Optional[str] = None) -> bool:
        """Perform the update.
        
        Args:
            version: Specific version to update to, or latest if None
        
        Returns:
            bool: Whether update was successful
        """
        try:
            logger.info("Starting update process...")
            
            # Create temporary directory for update
            with tempfile.TemporaryDirectory() as temp_dir:
                # Install new version
                cmd = [
                    sys.executable, "-m", "pip", "install", "--upgrade",
                    f"timewise-guardian-client{f'=={version}' if version else ''}"
                ]
                
                logger.debug(f"Running update command: {' '.join(cmd)}")
                subprocess.run(cmd, check=True, cwd=temp_dir)
                
                # Restart service if running as service
                if self._is_running_as_service():
                    self._restart_service()
                
                logger.info("Update completed successfully")
                return True
                
        except Exception as e:
            log_error_with_context(
                logger, e,
                {
                    "action": "update",
                    "target_version": version,
                    "current_version": str(self.current_version)
                }
            )
            return False

    def _is_running_as_service(self) -> bool:
        """Check if running as a service."""
        if sys.platform == "win32":
            import win32serviceutil
            try:
                return win32serviceutil.QueryServiceStatus("TimeWiseGuardian")[1] == 4
            except:
                return False
        else:
            try:
                return os.system("systemctl is-active --quiet twg") == 0
            except:
                return False

    def _restart_service(self) -> None:
        """Restart the service."""
        logger.info("Restarting service...")
        try:
            if sys.platform == "win32":
                subprocess.run(["net", "stop", "TimeWiseGuardian"], check=True)
                subprocess.run(["net", "start", "TimeWiseGuardian"], check=True)
            else:
                subprocess.run(["systemctl", "restart", "twg"], check=True)
        except Exception as e:
            log_error_with_context(logger, e, {"action": "restart_service"}) 