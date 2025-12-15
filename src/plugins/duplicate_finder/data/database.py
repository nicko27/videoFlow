"""
Main database manager facade for duplicate finder.

This module provides a unified interface to all database repositories,
coordinating access to different parts of the database schema.
"""

import os
from src.core.logger import Logger

from .connection_pool import ConnectionPool
from .schema.schema_manager import SchemaManager
from .repositories.video_repository import VideoRepository
from .repositories.hash_repository import HashRepository
from .repositories.comparison_repository import ComparisonRepository
from .repositories.duplicate_repository import DuplicateRepository
from .repositories.subsequence_repository import SubsequenceRepository
from .repositories.audio_repository import AudioRepository
from .repositories.advanced_pipeline_repository import AdvancedPipelineRepository
from .repositories.verification_repository import VerificationRepository
from .repositories.benchmark_repository import BenchmarkRepository
from .repositories.signature_repository import SignatureRepository

logger = Logger.get_logger('DuplicateFinder.DatabaseManager')


class DatabaseManager:
    """
    Main database manager facade.

    Coordinates access to all specialized repositories and provides
    a unified interface for database operations.

    Attributes:
        pool: ConnectionPool for database connections
        schema: SchemaManager for database schema management
        videos: VideoRepository for video file operations
        hashes: HashRepository for hash operations
        comparisons: ComparisonRepository for comparison operations
        duplicates: DuplicateRepository for duplicate operations
        subsequences: SubsequenceRepository for subsequence operations
        audio: AudioRepository for audio fingerprint operations
        advanced: AdvancedPipelineRepository for 3-level pipeline operations
        verification: VerificationRepository for verification operations
        benchmarks: BenchmarkRepository for benchmark operations
        signatures: SignatureRepository for signature operations
    """

    def __init__(self, db_path=None):
        """
        Initialize the database manager.

        Args:
            db_path: Path to the SQLite database file (default: auto-detect)
        """
        # Determine database path
        if db_path is None:
            # Place database at project root instead of plugin directory
            # Navigate from src/plugins/duplicate_finder/data/database.py to project root
            current_file = os.path.abspath(__file__)  # .../src/plugins/duplicate_finder/data/database.py
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file)))))
            db_path = os.path.join(project_root, 'video_duplicates.db')

        self.db_path = db_path

        # Create connection pool
        self.pool = ConnectionPool(db_path)

        # Initialize schema manager
        self.schema = SchemaManager(self.pool)

        # Initialize all repositories
        self.videos = VideoRepository(self.pool)
        self.hashes = HashRepository(self.pool)
        self.comparisons = ComparisonRepository(self.pool)
        self.duplicates = DuplicateRepository(self.pool)
        self.subsequences = SubsequenceRepository(self.pool)
        self.audio = AudioRepository(self.pool)
        self.advanced = AdvancedPipelineRepository(self.pool)
        self.verification = VerificationRepository(self.pool)
        self.benchmarks = BenchmarkRepository(self.pool)
        self.signatures = SignatureRepository(self.pool)

        # Initialize database structure
        self._ensure_database_exists()

        # Initialize schema (create tables if they don't exist)
        self.init_database()

        logger.info(f"DatabaseManager initialized with path: {db_path}")

    def _ensure_database_exists(self):
        """Ensure the database file and directory exist."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"Created database directory: {db_dir}")

    def init_database(self):
        """
        Initialize the complete database schema.

        Creates all tables, indexes, and performs necessary migrations.
        """
        self.schema.init_database()

    def close(self):
        """
        Close all database connections.

        Should be called when shutting down the application.
        """
        self.pool.close_all()
        logger.info("DatabaseManager closed")

    # Convenience methods that aggregate data from multiple repositories

    def get_statistics(self):
        """
        Get comprehensive statistics from all repositories.

        Returns:
            dict: Dictionary containing statistics from all repositories
        """
        return {
            'comparisons': self.comparisons.get_statistics(),
            'duplicates': self.duplicates.get_duplicate_statistics(),
            'subsequences': self.subsequences.get_subsequence_statistics(),
            'verification': self.verification.get_verification_statistics(),
            'advanced': self.advanced.get_advanced_mode_statistics()
        }

    def auto_cleanup_on_access(self):
        """
        Perform automatic cleanup of missing files.

        This is a convenience method that can be called periodically
        to clean up database entries for files that no longer exist.
        """
        self.videos.cleanup_missing_files()

    def clear_all_data(self):
        """
        Clear all data from the database.

        WARNING: This will delete all stored data including hashes,
        comparisons, duplicates, and ignored pairs.
        """
        logger.warning("Clearing all data from database")

        # Clear data from all repositories
        self.duplicates.clear_processed_duplicates()
        self.duplicates.clear_temporary_ignores()
        self.verification.clear_verification_cache()
        self.hashes.clear_hash_caches()
        self.hashes.clear_dense_hashes()
        self.signatures.clear_method_signatures()

        # Drop and recreate main tables
        tables_to_recreate = [
            'comparisons',
            'found_duplicates',
            'ignored_pairs',
            'video_subsequences',
            'verification_cache',
            'advanced_duplicates'
        ]

        for table_name in tables_to_recreate:
            try:
                self.schema.force_recreate_table(table_name)
            except Exception as e:
                logger.error(f"Error recreating table {table_name}: {e}")

        logger.info("All data cleared from database")

    def verify_database_integrity(self):
        """
        Verify the integrity of the database.

        Returns:
            dict: Dictionary with integrity check results
        """
        return self.schema.verify_database_integrity()

    def get_database_info(self):
        """
        Get information about the database.

        Returns:
            dict: Dictionary containing database information
        """
        return self.videos.get_database_info()

    def get_connection(self):
        """
        Get a database connection from the pool.

        This is provided for backward compatibility and special cases.
        Generally, you should use the specific repository methods instead.

        Returns:
            Context manager yielding a database connection
        """
        return self.pool.get_connection()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False

    def __del__(self):
        """Destructor to ensure connections are closed."""
        try:
            self.close()
        except Exception:
            pass
