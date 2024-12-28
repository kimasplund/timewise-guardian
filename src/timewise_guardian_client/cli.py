"""Command-line interface for Timewise Guardian Client."""
import argparse
import logging
import platform
import sys
from pathlib import Path

from . import __version__
from .common.config import Config
from .common.logger import setup_logging

def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Timewise Guardian Client - Home Assistant based parental control system"
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "-c", "--config",
        type=Path,
        help="Path to configuration file",
        default=Path("config.yaml")
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="Install the client as a system service"
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Uninstall the client service"
    )
    return parser

def main() -> int:
    """Main entry point for the client."""
    parser = create_parser()
    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(log_level)
    logger = logging.getLogger(__name__)

    try:
        # Load configuration
        config = Config(args.config)
        
        # Handle service installation/uninstallation
        if args.install:
            if platform.system() == "Windows":
                from .windows.service import install_service
                install_service()
            else:
                from .linux.service import install_service
                install_service()
            return 0
        
        if args.uninstall:
            if platform.system() == "Windows":
                from .windows.service import uninstall_service
                uninstall_service()
            else:
                from .linux.service import uninstall_service
                uninstall_service()
            return 0

        # Start the client based on platform
        if platform.system() == "Windows":
            from .windows.client import WindowsClient
            client = WindowsClient(config)
        else:
            from .linux.client import LinuxClient
            client = LinuxClient(config)

        client.run()
        return 0

    except KeyboardInterrupt:
        logger.info("Client stopped by user")
        return 0
    except Exception as e:
        logger.exception("Error running client: %s", str(e))
        return 1

if __name__ == "__main__":
    sys.exit(main()) 