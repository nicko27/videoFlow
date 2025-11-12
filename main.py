#!/usr/bin/env python3
"""
VideoFlow - Professional Video Management Suite

Main entry point for the VideoFlow application.

This application provides a suite of tools for video file management including:
- Duplicate detection
- Batch conversion
- Video editing
- File organization
- And more...

Usage:
    python main.py
"""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from src.ui.main_window import MainWindow
from src.core.logger import Logger
from src.core.config import Config

# Add root directory to PYTHONPATH
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Initialize logger
logger = Logger.get_logger('VideoFlow.Main')


def setup_application(app: QApplication) -> None:
    """
    Configure the Qt application with proper settings.

    Args:
        app: QApplication instance to configure
    """
    # Set application metadata
    app.setApplicationName(Config.APP_NAME)
    app.setApplicationVersion(Config.APP_VERSION)
    app.setOrganizationName(Config.APP_AUTHOR)

    # Set modern Fusion style
    app.setStyle('Fusion')

    # Set application icon if available
    icon_path = Config.RESOURCES_DIR / 'icon.png'
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    logger.info(f"Application configured: {Config.APP_NAME} v{Config.APP_VERSION}")


def main() -> int:
    """
    Main entry point for VideoFlow application.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    logger.info("=" * 60)
    logger.info(f"Starting {Config.APP_NAME} v{Config.APP_VERSION}")
    logger.info("=" * 60)

    try:
        # Create Qt application
        app = QApplication(sys.argv)

        # Configure application
        setup_application(app)

        # Ensure necessary directories exist
        Config.ensure_directories()
        logger.info("Application directories initialized")

        # Create and show main window
        window = MainWindow()
        window.show()
        logger.info("Main window displayed successfully")

        # Start event loop
        exit_code = app.exec()
        logger.info(f"Application exiting with code: {exit_code}")

        return exit_code

    except KeyboardInterrupt:
        logger.info("Application interrupted by user (Ctrl+C)")
        return 0

    except Exception as e:
        logger.error(f"Fatal error occurred: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
