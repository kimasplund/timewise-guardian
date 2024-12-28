"""Windows service implementation for Timewise Guardian."""
import logging
import os
import sys
import win32serviceutil
import win32service
import win32event
import servicemanager
from pathlib import Path

from ..common.config import Config
from .client import WindowsClient

logger = logging.getLogger(__name__)

class TimeWiseGuardianService(win32serviceutil.ServiceFramework):
    """Windows Service class for Timewise Guardian."""

    _svc_name_ = "TimeWiseGuardian"
    _svc_display_name_ = "TimeWise Guardian"
    _svc_description_ = "Monitors computer usage and enforces time limits"

    def __init__(self, args):
        """Initialize the service."""
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.client = None

    def SvcStop(self):
        """Stop the service."""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        if self.client:
            self.client.stop()

    def SvcDoRun(self):
        """Run the service."""
        try:
            # Set up logging
            from ..common.logger import setup_logging
            setup_logging()

            # Load configuration
            config_dir = Path(os.environ.get("PROGRAMDATA", "C:\\ProgramData")) / "TimeWise Guardian"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / "config.yaml"
            
            config = Config(config_file)
            self.client = WindowsClient(config)
            
            # Start the client
            logger.info("Starting TimeWise Guardian service")
            self.client.run()
            
        except Exception as e:
            logger.exception("Service error: %s", str(e))
            self.SvcStop()

def get_service_path() -> str:
    """Get the path to the service executable."""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return sys.executable
    else:
        # Running as script
        return sys.argv[0]

def install_service() -> None:
    """Install the Windows service."""
    try:
        if win32serviceutil.QueryService(TimeWiseGuardianService._svc_name_):
            logger.info("Service already installed")
            return
    except:
        pass

    try:
        # Prepare service installation
        service_path = get_service_path()
        logger.info("Installing service from: %s", service_path)
        
        # Install the service
        if getattr(sys, 'frozen', False):
            # If running as exe, use the exe path
            win32serviceutil.InstallService(
                None,
                TimeWiseGuardianService._svc_name_,
                TimeWiseGuardianService._svc_display_name_,
                startType=win32service.SERVICE_AUTO_START,
                exeName=service_path
            )
        else:
            # If running as script, use pythonservice.exe
            win32serviceutil.InstallService(
                TimeWiseGuardianService._svc_class_,
                TimeWiseGuardianService._svc_name_,
                TimeWiseGuardianService._svc_display_name_,
                startType=win32service.SERVICE_AUTO_START
            )
        
        # Start the service
        win32serviceutil.StartService(TimeWiseGuardianService._svc_name_)
        logger.info("Service installed and started successfully")
        
    except Exception as e:
        logger.error("Failed to install service: %s", str(e))
        raise

def uninstall_service() -> None:
    """Uninstall the Windows service."""
    try:
        # Stop the service if it's running
        try:
            win32serviceutil.StopService(TimeWiseGuardianService._svc_name_)
            logger.info("Service stopped")
        except:
            pass

        # Uninstall the service
        win32serviceutil.RemoveService(TimeWiseGuardianService._svc_name_)
        logger.info("Service uninstalled successfully")
        
    except Exception as e:
        logger.error("Failed to uninstall service: %s", str(e))
        raise

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(TimeWiseGuardianService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(TimeWiseGuardianService) 