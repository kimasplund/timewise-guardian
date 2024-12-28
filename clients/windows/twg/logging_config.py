"""Logging configuration for Timewise Guardian."""
import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

def setup_logging(
    service_mode: bool = False,
    log_level: str = "INFO",
    max_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> logging.Logger:
    """Set up logging configuration.
    
    Args:
        service_mode: Whether running as a service
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        max_size: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
    """
    logger = logging.getLogger("TimeWiseGuardian")
    logger.setLevel(getattr(logging, log_level.upper()))

    # Determine log directory
    if service_mode:
        if sys.platform == "win32":
            log_dir = Path(os.environ.get("PROGRAMDATA", "")) / "TimeWiseGuardian" / "logs"
        else:
            log_dir = Path("/var/log/twg")
    else:
        log_dir = Path.home() / ".twg" / "logs"

    log_dir.mkdir(parents=True, exist_ok=True)

    # Create formatters
    detailed_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - [%(levelname)s] - "
        "%(pathname)s:%(lineno)d - %(funcName)s - %(message)s"
    )
    
    simple_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    )

    # File handler for detailed logging
    detailed_log = log_dir / f"twg_detailed_{datetime.now():%Y%m%d}.log"
    detailed_handler = logging.handlers.RotatingFileHandler(
        detailed_log,
        maxBytes=max_size,
        backupCount=backup_count,
        encoding="utf-8",
    )
    detailed_handler.setFormatter(detailed_formatter)
    detailed_handler.setLevel(logging.DEBUG)

    # File handler for general logging
    general_log = log_dir / "twg.log"
    general_handler = logging.handlers.RotatingFileHandler(
        general_log,
        maxBytes=max_size,
        backupCount=backup_count,
        encoding="utf-8",
    )
    general_handler.setFormatter(simple_formatter)
    general_handler.setLevel(getattr(logging, log_level.upper()))

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(simple_formatter)
    console_handler.setLevel(getattr(logging, log_level.upper()))

    # Add handlers to logger
    logger.addHandler(detailed_handler)
    logger.addHandler(general_handler)
    logger.addHandler(console_handler)

    # Log startup information
    logger.info("Logging initialized")
    logger.debug(f"Log directory: {log_dir}")
    logger.debug(f"Python version: {sys.version}")
    logger.debug(f"Platform: {sys.platform}")
    logger.debug(f"Service mode: {service_mode}")

    return logger

def log_system_info(logger: logging.Logger) -> None:
    """Log detailed system information."""
    import platform
    import psutil
    
    logger.info("=== System Information ===")
    
    # Platform info
    logger.info(f"OS: {platform.platform()}")
    logger.info(f"Python: {platform.python_version()}")
    logger.info(f"Machine: {platform.machine()}")
    logger.info(f"Processor: {platform.processor()}")
    
    # Memory info
    memory = psutil.virtual_memory()
    logger.info(f"Memory Total: {memory.total / (1024**3):.2f} GB")
    logger.info(f"Memory Available: {memory.available / (1024**3):.2f} GB")
    
    # Disk info
    disk = psutil.disk_usage('/')
    logger.info(f"Disk Total: {disk.total / (1024**3):.2f} GB")
    logger.info(f"Disk Free: {disk.free / (1024**3):.2f} GB")
    
    # Network info
    try:
        import socket
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        logger.info(f"Hostname: {hostname}")
        logger.info(f"IP Address: {ip_address}")
    except Exception as e:
        logger.error(f"Failed to get network info: {e}")

def log_error_with_context(
    logger: logging.Logger,
    error: Exception,
    context: Optional[dict] = None
) -> None:
    """Log an error with additional context information."""
    import traceback
    
    logger.error("=== Error Details ===")
    logger.error(f"Error Type: {type(error).__name__}")
    logger.error(f"Error Message: {str(error)}")
    
    if context:
        logger.error("=== Context ===")
        for key, value in context.items():
            logger.error(f"{key}: {value}")
    
    logger.error("=== Traceback ===")
    logger.error(traceback.format_exc()) 