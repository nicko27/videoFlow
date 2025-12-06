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
        - Configurable log levels (DEBUG, INFO, WARNING, ERROR)
        - Dynamic level changes without restart

    Attributes:
        _instance (Logger): Singleton instance of the Logger class.
        _initialized (bool): Whether the logger has been initialized.
        logger (logging.Logger): The main VideoFlow logger instance.
        _console_handler (logging.Handler): Console handler for level control.
        _file_handler (logging.Handler): File handler for level control.

    Example:
        Get a logger for a specific module::

            from src.core.logger import Logger

            # Configure logging level (before first use)
            Logger.configure(console_level=logging.INFO, file_level=logging.DEBUG)

            # Get logger instance
            logger = Logger.get_logger('MyModule')
            logger.info('Application started')
            logger.error('An error occurred', exc_info=True)

            # Change logging level dynamically
            Logger.set_console_level(logging.DEBUG)
            Logger.set_file_level(logging.WARNING)
    """
    _instance = None
    _initialized = False
    _console_handler = None
    _file_handler = None

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

    def _setup_logger(self, console_level=logging.INFO, file_level=logging.DEBUG):
        """Configure the logging system.

        Sets up both console and file handlers with appropriate formatting.
        Console handler outputs to stdout, while file handler writes to
        rotating log files in the logs/ directory.

        The log file naming includes a timestamp to differentiate between
        application runs. Files are rotated when they reach 100MB, keeping
        up to 5 backup files.

        Args:
            console_level: Logging level for console (default: INFO)
            file_level: Logging level for file (default: DEBUG)
        """
        # Main logger configuration
        self.logger = logging.getLogger('VideoFlow')
        self.logger.setLevel(logging.DEBUG)  # Allow all levels, handlers filter

        # Console handler
        Logger._console_handler = logging.StreamHandler(sys.stdout)
        Logger._console_handler.setLevel(console_level)

        # Console message format (more concise for console)
        console_formatter = logging.Formatter(
            '%(levelname)s - %(name)s - %(message)s'
        )
        Logger._console_handler.setFormatter(console_formatter)

        # Add console handler
        self.logger.addHandler(Logger._console_handler)

        try:
            # Create logs directory if it doesn't exist
            logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
            os.makedirs(logs_dir, exist_ok=True)

            # Log file name with date
            log_file = os.path.join(logs_dir, f'videoflow_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

            # File handler with rotation
            Logger._file_handler = RotatingFileHandler(
                log_file,
                maxBytes=100*1024*1024,  # 100MB
                backupCount=5,
                encoding='utf-8'
            )
            Logger._file_handler.setLevel(file_level)

            # File message format (detailed for file)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
            )
            Logger._file_handler.setFormatter(file_formatter)

            # Add file handler
            self.logger.addHandler(Logger._file_handler)
        except Exception as e:
            self.logger.error(f"Error during log file configuration: {str(e)}", exc_info=True)

        self.logger.info(f"Logger initialized (console={logging.getLevelName(console_level)}, file={logging.getLevelName(file_level)})")

    @classmethod
    def configure(cls, console_level=logging.INFO, file_level=logging.DEBUG):
        """Configure logging levels before first use.

        This method allows setting log levels before the logger is initialized.
        If the logger is already initialized, use set_console_level() and
        set_file_level() instead.

        Args:
            console_level: Logging level for console output (default: INFO)
            file_level: Logging level for file output (default: DEBUG)

        Example:
            # Configure before first logger creation
            Logger.configure(console_level=logging.WARNING, file_level=logging.DEBUG)
        """
        if not cls._initialized:
            instance = cls()
            instance._setup_logger(console_level, file_level)
        else:
            # If already initialized, update levels
            cls.set_console_level(console_level)
            cls.set_file_level(file_level)

    @classmethod
    def set_console_level(cls, level):
        """Dynamically change console logging level.

        Args:
            level: New logging level (logging.DEBUG, INFO, WARNING, ERROR, CRITICAL)

        Example:
            # Enable debug logging on console
            Logger.set_console_level(logging.DEBUG)

            # Reduce console verbosity
            Logger.set_console_level(logging.WARNING)
        """
        if cls._console_handler:
            cls._console_handler.setLevel(level)
            logger = logging.getLogger('VideoFlow')
            logger.info(f"Console log level changed to {logging.getLevelName(level)}")
        else:
            raise RuntimeError("Logger not initialized. Call Logger.get_logger() first.")

    @classmethod
    def set_file_level(cls, level):
        """Dynamically change file logging level.

        Args:
            level: New logging level (logging.DEBUG, INFO, WARNING, ERROR, CRITICAL)

        Example:
            # Log only errors to file
            Logger.set_file_level(logging.ERROR)

            # Log everything to file
            Logger.set_file_level(logging.DEBUG)
        """
        if cls._file_handler:
            cls._file_handler.setLevel(level)
            logger = logging.getLogger('VideoFlow')
            logger.info(f"File log level changed to {logging.getLevelName(level)}")
        else:
            raise RuntimeError("Logger not initialized. Call Logger.get_logger() first.")

    @classmethod
    def get_current_levels(cls):
        """Get current logging levels for console and file.

        Returns:
            dict: {'console': level_name, 'file': level_name}

        Example:
            levels = Logger.get_current_levels()
            print(f"Console: {levels['console']}, File: {levels['file']}")
        """
        if cls._console_handler and cls._file_handler:
            return {
                'console': logging.getLevelName(cls._console_handler.level),
                'file': logging.getLevelName(cls._file_handler.level)
            }
        return {'console': 'NOT_INITIALIZED', 'file': 'NOT_INITIALIZED'}

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
            # Get logger with default levels (INFO console, DEBUG file)
            logger = Logger.get_logger('PluginManager')

            # Or configure first
            Logger.configure(console_level=logging.WARNING)
            logger = Logger.get_logger('PluginManager')
        """
        instance = cls()
        if name:
            return logging.getLogger(f'VideoFlow.{name}')
        return instance.logger
