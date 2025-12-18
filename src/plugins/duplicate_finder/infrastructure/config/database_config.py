"""
Database Configuration Module - Single Source of Truth for Database Path

This module provides centralized database path management to prevent
multiple database locations and ensure consistency across the application.

CRITICAL: All database access MUST use get_database_path() to ensure
the same database is used throughout the application.
"""

import os
from pathlib import Path
from typing import Optional
from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.DatabaseConfig')


class DatabaseConfig:
    """
    Centralized database configuration.

    Provides a single source of truth for database location,
    preventing the proliferation of database files across the project.
    """

    # Default database location: project root
    _DEFAULT_DB_NAME = 'video_duplicates.db'
    _project_root: Optional[Path] = None
    _db_path: Optional[Path] = None

    @classmethod
    def _get_project_root(cls) -> Path:
        """
        Get the project root directory.

        Returns:
            Path to project root (where main.py is located)
        """
        if cls._project_root is None:
            # Navigate from this file to project root
            # Current: src/plugins/duplicate_finder/infrastructure/config/database_config.py
            current_file = Path(__file__).resolve()
            # Go up: config -> infrastructure -> duplicate_finder -> plugins -> src -> root
            cls._project_root = current_file.parent.parent.parent.parent.parent.parent

        return cls._project_root

    @classmethod
    def get_database_path(cls, custom_path: Optional[str] = None) -> str:
        """
        Get the database path (single source of truth).

        This method ensures that all parts of the application use the same
        database file. Custom paths should only be used for testing.

        Args:
            custom_path: Optional custom database path (for testing only)

        Returns:
            Absolute path to the database file

        Usage:
            >>> from src.plugins.duplicate_finder.infrastructure.config.database_config import DatabaseConfig
            >>> db_path = DatabaseConfig.get_database_path()
            >>> db = DatabaseManager(db_path)
        """
        if custom_path is not None:
            # Custom path for testing
            path = Path(custom_path).resolve()
            logger.debug(f"Using custom database path: {path}")
            return str(path)

        if cls._db_path is None:
            # Default: project root
            project_root = cls._get_project_root()
            cls._db_path = project_root / cls._DEFAULT_DB_NAME
            logger.info(f"Database path initialized: {cls._db_path}")

        return str(cls._db_path)

    @classmethod
    def set_database_path(cls, path: str):
        """
        Override the default database path (use with caution).

        This should only be used in tests or when explicitly migrating
        the database location.

        Args:
            path: New database path
        """
        cls._db_path = Path(path).resolve()
        logger.warning(f"Database path manually overridden to: {cls._db_path}")

    @classmethod
    def reset(cls):
        """Reset to default configuration (for testing)."""
        cls._db_path = None
        cls._project_root = None

    @classmethod
    def get_info(cls) -> dict:
        """
        Get database configuration information.

        Returns:
            Dict with database configuration details
        """
        db_path = cls.get_database_path()
        path_obj = Path(db_path)

        return {
            'db_path': db_path,
            'exists': path_obj.exists(),
            'size_bytes': path_obj.stat().st_size if path_obj.exists() else 0,
            'size_mb': round(path_obj.stat().st_size / 1024 / 1024, 2) if path_obj.exists() else 0,
            'parent_dir': str(path_obj.parent),
            'project_root': str(cls._get_project_root()),
        }


# Convenience function for quick access
def get_database_path(custom_path: Optional[str] = None) -> str:
    """
    Get the database path (convenience function).

    Args:
        custom_path: Optional custom database path (for testing only)

    Returns:
        Absolute path to the database file

    Example:
        >>> from src.plugins.duplicate_finder.infrastructure.config.database_config import get_database_path
        >>> db_path = get_database_path()
    """
    return DatabaseConfig.get_database_path(custom_path)


if __name__ == '__main__':
    # Self-test: print database configuration
    print("=== Database Configuration ===")
    info = DatabaseConfig.get_info()
    for key, value in info.items():
        print(f"{key:15s}: {value}")
