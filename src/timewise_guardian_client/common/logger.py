"""Logging configuration for Timewise Guardian Client."""
import logging
import logging.handlers
import os
from pathlib import Path
import platform
import sys

def get_log_directory() -> Path:
    """Get the appropriate log directory based on the platform."""
    if platform.system() == "Windows":
        base_dir = os.environ.get("PROGRAMDATA", "C:\\ProgramData")
        return Path(base_dir) / "TimeWise Guardian" / "logs"
    else:
        return Path("/var/log/timewise-guardian")

def setup_logging(level: int = logging.INFO) -> None:
    """Set up logging configuration."""
    # Create log directory if it doesn't exist
    log_dir = get_log_directory()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "client.log"

    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )

    # Set up file handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(level)

    # Set up console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(level)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Set levels for some chatty libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)

    # Log initial message
    logger = logging.getLogger(__name__)
    logger.info("Logging initialized at %s", log_file)
    logger.debug("Log level set to %s", logging.getLevelName(level)) 