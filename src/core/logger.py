"""Centralized logging system for the VideoFlow application.

This module provides a singleton Logger class that manages logging configuration
for the entire application, including console and file handlers with rotation.

Classes:
    Logger: Singleton logger manager with dual console and file output.
"""

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
import sys

class Logger:
    """Singleton logger manager for VideoFlow.

    Provides centralized logging with both console and file output. The logger
    uses a singleton pattern to ensure consistent logging configuration across
    the entire application.

    Features:
        - Console output with detailed formatting
        - File output with rotation (100MB max, 5 backups)
        - Timestamped log files in the logs/ directory
        - UTF-8 encoding support
        - DEBUG level logging by default

    Attributes:
        _instance (Logger): Singleton instance of the Logger class.
        _initialized (bool): Whether the logger has been initialized.
        logger (logging.Logger): The main VideoFlow logger instance.

    Example:
        Get a logger for a specific module::

            from src.core.logger import Logger

            logger = Logger.get_logger('MyModule')
            logger.info('Application started')
            logger.error('An error occurred', exc_info=True)
    """
    _instance = None
    _initialized = False

    def __new__(cls):
        """Create or return the singleton Logger instance.

        Returns:
            Logger: The singleton Logger instance.
        """
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the logger (only runs once due to singleton pattern)."""
        if not Logger._initialized:
            Logger._initialized = True
            self._setup_logger()

    def _setup_logger(self):
        """Configure the logging system.

        Sets up both console and file handlers with appropriate formatting.
        Console handler outputs to stdout with DEBUG level, while file handler
        writes to rotating log files in the logs/ directory.

        The log file naming includes a timestamp to differentiate between
        application runs. Files are rotated when they reach 100MB, keeping
        up to 5 backup files.
        """
        # Main logger configuration
        self.logger = logging.getLogger('VideoFlow')
        self.logger.setLevel(logging.DEBUG)

        # Console handler with more details
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)  # Changed to DEBUG to see all messages

        # Console message format
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        console_handler.setFormatter(console_formatter)

        # Add console handler
        self.logger.addHandler(console_handler)

        try:
            # Create logs directory if it doesn't exist
            logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
            os.makedirs(logs_dir, exist_ok=True)

            # Log file name with date
            log_file = os.path.join(logs_dir, f'videoflow_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

            # File handler with rotation
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=100*1024*1024,  # 100MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)

            # File message format
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
            )
            file_handler.setFormatter(file_formatter)

            # Add file handler
            self.logger.addHandler(file_handler)
        except Exception as e:
            self.logger.error(f"Error during log file configuration: {str(e)}", exc_info=True)

        self.logger.info("Logger initialized")

    @classmethod
    def get_logger(cls, name: str = None) -> logging.Logger:
        """Get a configured logger instance.

        Creates or retrieves a logger with the VideoFlow namespace. If a name
        is provided, it creates a child logger under VideoFlow.<name>.

        Args:
            name (str, optional): Name for the logger (creates VideoFlow.<name>).
                If None, returns the root VideoFlow logger. Defaults to None.

        Returns:
            logging.Logger: Configured logger instance ready for use.

        Example:
            logger = Logger.get_logger('PluginManager')
            # Creates logger 'VideoFlow.PluginManager'
        """
        instance = cls()
        if name:
            return logging.getLogger(f'VideoFlow.{name}')
        return instance.logger
