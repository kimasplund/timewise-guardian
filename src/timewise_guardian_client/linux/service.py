"""Linux service implementation for Timewise Guardian."""
import logging
import os
import sys
from pathlib import Path

from ..common.config import Config
from .client import LinuxClient

logger = logging.getLogger(__name__)

SYSTEMD_SERVICE_TEMPLATE = """[Unit]
Description=TimeWise Guardian - Computer Usage Monitor
After=network.target

[Service]
Type=simple
User={user}
Group={group}
ExecStart={exec_path}
Restart=always
RestartSec=5
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/{user}/.Xauthority

[Install]
WantedBy=multi-user.target
"""

def get_service_path() -> str:
    """Get the path to the service executable."""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return sys.executable
    else:
        # Running as script
        return f"{sys.executable} {sys.argv[0]}"

def install_service() -> None:
    """Install the Linux systemd service."""
    try:
        # Get current user
        user = os.environ.get('SUDO_USER', os.getenv('USER'))
        if not user:
            raise RuntimeError("Could not determine user")

        # Get user's group
        import grp
        import pwd
        pw_record = pwd.getpwnam(user)
        group = grp.getgrgid(pw_record.pw_gid).gr_name

        # Create service file
        service_content = SYSTEMD_SERVICE_TEMPLATE.format(
            user=user,
            group=group,
            exec_path=get_service_path()
        )

        # Write service file
        service_path = Path("/etc/systemd/system/timewise-guardian.service")
        if not os.geteuid() == 0:
            logger.error("Service installation requires root privileges")
            raise RuntimeError("Must run as root")

        with open(service_path, 'w') as f:
            f.write(service_content)

        # Set permissions
        os.chmod(service_path, 0o644)

        # Create configuration directory
        config_dir = Path("/etc/timewise-guardian")
        config_dir.mkdir(parents=True, exist_ok=True)
        os.chown(config_dir, pw_record.pw_uid, pw_record.pw_gid)

        # Create log directory
        log_dir = Path("/var/log/timewise-guardian")
        log_dir.mkdir(parents=True, exist_ok=True)
        os.chown(log_dir, pw_record.pw_uid, pw_record.pw_gid)

        # Reload systemd and enable service
        os.system("systemctl daemon-reload")
        os.system("systemctl enable timewise-guardian")
        os.system("systemctl start timewise-guardian")

        logger.info("Service installed and started successfully")

    except Exception as e:
        logger.error("Failed to install service: %s", str(e))
        raise

def uninstall_service() -> None:
    """Uninstall the Linux systemd service."""
    try:
        if not os.geteuid() == 0:
            logger.error("Service uninstallation requires root privileges")
            raise RuntimeError("Must run as root")

        # Stop and disable service
        os.system("systemctl stop timewise-guardian")
        os.system("systemctl disable timewise-guardian")

        # Remove service file
        service_path = Path("/etc/systemd/system/timewise-guardian.service")
        if service_path.exists():
            service_path.unlink()

        # Reload systemd
        os.system("systemctl daemon-reload")

        logger.info("Service uninstalled successfully")

    except Exception as e:
        logger.error("Failed to uninstall service: %s", str(e))
        raise

def run_service() -> None:
    """Run the service directly."""
    try:
        # Set up logging
        from ..common.logger import setup_logging
        setup_logging()

        # Load configuration
        config_file = Path("/etc/timewise-guardian/config.yaml")
        if not config_file.exists():
            config_file = Path("config.yaml")

        config = Config(config_file)
        client = LinuxClient(config)

        # Start the client
        logger.info("Starting TimeWise Guardian service")
        client.run()

    except Exception as e:
        logger.exception("Service error: %s", str(e))
        sys.exit(1)

if __name__ == '__main__':
    run_service() 