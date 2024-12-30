"""Main entry point for the Timewise Guardian client."""
import os
import sys
import asyncio
import logging
import socket
import argparse
from typing import Optional
from .auth import HomeAssistantAuth, AuthenticationError
from .common.config import Config
from .common.client import BaseClient
from .windows.client import WindowsClient
from .linux.client import LinuxClient

logger = logging.getLogger(__name__)

def get_default_computer_id() -> str:
    """Get default computer identifier."""
    return socket.gethostname()

def get_system_user() -> str:
    """Get current system user."""
    return os.getlogin()

async def main(args: Optional[argparse.Namespace] = None) -> None:
    """Main entry point."""
    if args is None:
        parser = argparse.ArgumentParser(description="Timewise Guardian - Home Assistant computer monitoring client")
        parser.add_argument("-c", "--connect", help="Connect to Home Assistant instance (e.g., homeassistant.local:8123)")
        parser.add_argument("-n", "--name", help="Set computer name (default: hostname)")
        parser.add_argument("-u", "--user", help="Override system username (default: current user)")
        parser.add_argument("-i", "--interval", type=int, help="Set sync interval in seconds (default: 30)")
        parser.add_argument("--config", help="Use custom config file")
        parser.add_argument("--debug", action="store_true", help="Enable debug logging")
        args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    try:
        # Handle initial connection
        if args.connect:
            auth = HomeAssistantAuth(args.connect)
            computer_id = args.name or get_default_computer_id()
            system_user = args.user or get_system_user()
            
            config_data = await auth.authenticate(
                computer_id=computer_id,
                system_user=system_user
            )
            if args.interval:
                config_data['sync_interval'] = args.interval
            config = Config(config_data)
        else:
            config = Config.load(args.config)

        # Create and run client
        if os.name == 'nt':
            client = WindowsClient(config)
        elif os.name == 'posix':
            client = LinuxClient(config)
        else:
            raise RuntimeError(f"Unsupported platform: {os.name}")

        print(f"\nConnected to Home Assistant at {config.ha_url}")
        print(f"Computer ID: {config.computer_id}")
        print(f"System User: {config.system_user}")
        print(f"Sync interval: {config.sync_interval} seconds")
        print("\nNote: You can map this system user to a Home Assistant user in the UI")
        print("\nPress Ctrl+C to stop monitoring...")

        await client.start()

    except AuthenticationError as e:
        logger.error(f"Authentication failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nStopping monitoring...")
    except Exception as e:
        logger.exception("Unexpected error")
        sys.exit(1)

def run() -> None:
    """Entry point for the console script."""
    asyncio.run(main()) 