"""Windows service implementation for Timewise Guardian."""
import os
import sys
import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import logging
from pathlib import Path

from .monitor import WindowsMonitor

class TWGService(win32serviceutil.ServiceFramework):
    """Windows Service class for Timewise Guardian."""
    
    _svc_name_ = "TimeWiseGuardian"
    _svc_display_name_ = "TimeWise Guardian Monitor"
    _svc_description_ = "Monitors computer usage and enforces time limits"

    def __init__(self, args):
        """Initialize the service."""
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.monitor = None
        
        # Set up logging for the service
        log_dir = os.path.join(os.environ.get('PROGRAMDATA', ''), 'TimeWiseGuardian')
        os.makedirs(log_dir, exist_ok=True)
        
        logging.basicConfig(
            filename=os.path.join(log_dir, 'twg_service.log'),
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('TWGService')

    def SvcStop(self):
        """Stop the service."""
        self.logger.info('Stopping service...')
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)

    def SvcDoRun(self):
        """Run the service."""
        try:
            self.logger.info('Starting service...')
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PID_INFO,
                ('Service starting...', '')
            )
            
            # Get config path from registry or use default
            config_path = os.path.join(
                os.environ.get('PROGRAMDATA', ''),
                'TimeWiseGuardian',
                'config.yaml'
            )
            
            self.monitor = WindowsMonitor(config_path=config_path)
            self.monitor.run()
            
            win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)
            
        except Exception as e:
            self.logger.error(f'Service error: {e}', exc_info=True)
            servicemanager.LogErrorMsg(str(e))

def run_service():
    """Run the service."""
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(TWGService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(TWGService)

if __name__ == '__main__':
    run_service() 