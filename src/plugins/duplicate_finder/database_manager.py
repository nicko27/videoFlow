import sqlite3
import os
import json
import pickle
import multiprocessing
from datetime import datetime
from contextlib import contextmanager
from queue import Queue, Empty
from threading import Lock
import numpy as np
from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.DatabaseManager')


class ConnectionPool:
    """Thread-safe SQLite connection pool.

    Manages a pool of SQLite connections to avoid the overhead of creating
    new connections for each operation. Designed for SQLite's single-writer
    limitation with a small pool size.

    Attributes:
        db_path: Path to the SQLite database file
        pool_size: Maximum number of connections (default: 5)
        pool: Queue containing available connections
        lock: Thread lock for pool operations
    """

    def __init__(self, db_path: str, pool_size: int = None):
        """
        Initialize the connection pool with auto-detected optimal size.

        Args:
            db_path: Path to SQLite database
            pool_size: Maximum number of connections (default: auto-detect based on CPU)
        """
        self.db_path = db_path

        # AUTO-DETECT optimal pool size based on CPU count
        if pool_size is None:
            cpu_count = multiprocessing.cpu_count()
            # Formula: min(CPU_count + 2, 10) for balanced concurrency
            # SQLite handles writes sequentially, so too many connections don't help
            self.pool_size = min(cpu_count + 2, 10)
            logger.info(
                f"Auto-detected pool_size={self.pool_size} based on {cpu_count} CPUs"
            )
        else:
            self.pool_size = max(1, min(pool_size, 20))  # Clamp between 1-20
            logger.debug(f"Using configured pool_size={self.pool_size}")

        self.pool = Queue(maxsize=self.pool_size)
        self.lock = Lock()
        self._closed = False

        # Create initial connections
        for _ in range(self.pool_size):
            conn = self._create_connection()
            self.pool.put(conn)

        logger.debug(f"Connection pool created with {self.pool_size} connections")

    def _create_connection(self) -> sqlite3.Connection:
        """
        Create a new optimized SQLite connection.

        Returns:
            Configured SQLite connection
        """
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        # Apply optimizations
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA temp_store=MEMORY")
        return conn

    @contextmanager
    def get_connection(self):
        """
        Get a connection from the pool (context manager).

        Yields:
            SQLite connection from the pool

        Example:
            with pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT ...")
        """
        if self._closed:
            raise RuntimeError("Connection pool is closed")

        conn = None
        try:
            # Get connection from pool (timeout 30 seconds)
            conn = self.pool.get(timeout=30)
            yield conn
        except Empty:
            # Pool exhausted - create temporary connection
            logger.warning("Connection pool exhausted, creating temporary connection")
            temp_conn = self._create_connection()
            try:
                yield temp_conn
            finally:
                temp_conn.close()
        finally:
            # Return connection to pool
            if conn is not None:
                try:
                    # Rollback any uncommitted transaction
                    conn.rollback()
                    self.pool.put(conn, block=False)
                except Exception as e:
                    logger.error(f"Error returning connection to pool: {e}")
                    # Connection might be broken, create a new one
                    try:
                        conn.close()
                    except Exception as close_error:
                        logger.debug(f"Error closing broken connection: {close_error}")
                    new_conn = self._create_connection()
                    self.pool.put(new_conn, block=False)

    def close_all(self):
        """
        Close all connections in the pool.

        Should be called when shutting down the application.
        """
        with self.lock:
            if self._closed:
                return

            self._closed = True
            closed_count = 0

            # Close all connections in pool
            while not self.pool.empty():
                try:
                    conn = self.pool.get(block=False)
                    conn.close()
                    closed_count += 1
                except Empty:
                    break
                except Exception as e:
                    logger.error(f"Error closing connection: {e}")

            logger.info(f"Connection pool closed ({closed_count} connections)")

    def __del__(self):
        """Destructor to ensure connections are closed."""
        self.close_all()


class VideoDatabase:
    """Optimized database manager for video hashes and comparisons - With proper migration"""

    def __init__(self, db_path=None):
        if db_path is None:
            # Place DB in the same folder as the plugin
            plugin_dir = os.path.dirname(__file__)
            db_path = os.path.join(plugin_dir, 'video_duplicates.db')

        self.db_path = db_path
        self._initialized = False  # Flag to avoid repeated checks
        self._tables_exist = {}  # Cache for table existence

        # Create connection pool with auto-detected optimal size
        self.connection_pool = ConnectionPool(db_path, pool_size=None)

        self._ensure_database_exists()
        logger.info(f"Database initialized with connection pool: {self.db_path}")
    
    def _ensure_database_exists(self):
        """Ensure database and its tables exist - ONLY ONCE"""
        if self._initialized:
            return

        try:
            # Create parent directory if necessary
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)

            # Initialize structure
            self.init_database()
            self._initialized = True

            # Mark all tables as existing
            self._tables_exist = {
                'video_files': True,
                'comparisons': True,
                'ignored_pairs': True,
                'corrupted_files': True,
                'found_duplicates': True,
                'video_subsequences': True,
                'lsh_fingerprints': True,
                'level2_long_audio': True,
                'level3_phash': True,
                'advanced_duplicates': True
            }
                
        except Exception as e:
            logger.error(f"Error during database initialization: {e}")
            raise
    
    def init_database(self):
        """Initialize database structure - WITH CORRECTED MIGRATION"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Enable SQLite optimizations
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA cache_size=10000")
                cursor.execute("PRAGMA temp_store=MEMORY")
                cursor.execute("PRAGMA foreign_keys=ON")

                # STEP 1: Create base tables WITHOUT ignore_type
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS video_files (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_path TEXT UNIQUE NOT NULL,
                        file_name TEXT NOT NULL,
                        file_size INTEGER,
                        modification_time REAL,
                        duration REAL,
                        width INTEGER,
                        height INTEGER,
                        hash_method TEXT,
                        hash_data BLOB,
                        frames_indices TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS comparisons (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file1_id INTEGER,
                        file2_id INTEGER,
                        similarity REAL,
                        comparison_method TEXT,
                        is_early_exit BOOLEAN DEFAULT 0,
                        computation_time REAL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (file1_id) REFERENCES video_files (id) ON DELETE CASCADE,
                        FOREIGN KEY (file2_id) REFERENCES video_files (id) ON DELETE CASCADE,
                        UNIQUE(file1_id, file2_id)
                    )
                ''')

                # STEP 2: Create ignored_pairs table WITHOUT ignore_type first
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS ignored_pairs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file1_id INTEGER,
                        file2_id INTEGER,
                        reason TEXT DEFAULT 'user_choice',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (file1_id) REFERENCES video_files (id) ON DELETE CASCADE,
                        FOREIGN KEY (file2_id) REFERENCES video_files (id) ON DELETE CASCADE,
                        UNIQUE(file1_id, file2_id)
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS corrupted_files (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_path TEXT UNIQUE NOT NULL,
                        error_message TEXT,
                        detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS found_duplicates (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file1_id INTEGER,
                        file2_id INTEGER,
                        similarity REAL,
                        status TEXT DEFAULT 'pending',
                        action_taken TEXT,
                        detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        processed_at TIMESTAMP,
                        FOREIGN KEY (file1_id) REFERENCES video_files (id) ON DELETE CASCADE,
                        FOREIGN KEY (file2_id) REFERENCES video_files (id) ON DELETE CASCADE,
                        UNIQUE(file1_id, file2_id)
                    )
                ''')

                # Table for subsequence detections
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS video_subsequences (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        short_video_id INTEGER,
                        long_video_id INTEGER,
                        match_ratio REAL,
                        start_frame_idx INTEGER,
                        confidence REAL,
                        status TEXT DEFAULT 'pending',
                        action_taken TEXT,
                        detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        processed_at TIMESTAMP,
                        FOREIGN KEY (short_video_id) REFERENCES video_files (id) ON DELETE CASCADE,
                        FOREIGN KEY (long_video_id) REFERENCES video_files (id) ON DELETE CASCADE,
                        UNIQUE(short_video_id, long_video_id)
                    )
                ''')

                # Table for dense hashes (frame-by-frame hashes for subsequence detection)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS dense_hashes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        video_id INTEGER UNIQUE,
                        dense_hash BLOB NOT NULL,
                        sample_interval REAL NOT NULL,
                        duration REAL NOT NULL,
                        num_frames INTEGER NOT NULL,
                        modification_time REAL NOT NULL,
                        file_size INTEGER NOT NULL,
                        params_hash TEXT,
                        params_json TEXT,
                        computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (video_id) REFERENCES video_files (id) ON DELETE CASCADE
                    )
                ''')

                # ═══════════════════════════════════════════════════════════
                # ADVANCED 3-LEVEL MODE TABLES
                # ═══════════════════════════════════════════════════════════

                # Table for LSH fingerprints (Level 1)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS lsh_fingerprints (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        video_id INTEGER UNIQUE,
                        fingerprint BLOB NOT NULL,
                        signature_bands TEXT,
                        n_bands INTEGER,
                        n_rows INTEGER,
                        params_hash TEXT,
                        params_json TEXT,
                        computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        fingerprint_version INTEGER DEFAULT 1,
                        FOREIGN KEY (video_id) REFERENCES video_files (id) ON DELETE CASCADE
                    )
                ''')

                # Table for Level 2 long-period audio comparisons
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS level2_long_audio (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        pair_id TEXT UNIQUE NOT NULL,
                        file1_id INTEGER,
                        file2_id INTEGER,
                        similarity_score REAL,
                        window_duration INTEGER,
                        window_start REAL,
                        params_hash TEXT,
                        params_json TEXT,
                        compared_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (file1_id) REFERENCES video_files (id) ON DELETE CASCADE,
                        FOREIGN KEY (file2_id) REFERENCES video_files (id) ON DELETE CASCADE
                    )
                ''')

                # Table for Level 3 pHash visual comparisons
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS level3_phash (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        pair_id TEXT UNIQUE NOT NULL,
                        file1_id INTEGER,
                        file2_id INTEGER,
                        phash_distance INTEGER,
                        frames_compared INTEGER,
                        frames_similar INTEGER,
                        similarity_rate REAL,
                        frame_indices TEXT,
                        params_hash TEXT,
                        params_json TEXT,
                        compared_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (file1_id) REFERENCES video_files (id) ON DELETE CASCADE,
                        FOREIGN KEY (file2_id) REFERENCES video_files (id) ON DELETE CASCADE
                    )
                ''')

                # ═══════════════════════════════════════════════════════════
                # SUBSEQUENCE VERIFICATION CACHE (Strategy 3)
                # ═══════════════════════════════════════════════════════════

                # Table for caching verification results
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS verification_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        short_video_id INTEGER NOT NULL,
                        long_video_id INTEGER NOT NULL,
                        short_mtime REAL NOT NULL,
                        long_mtime REAL NOT NULL,
                        short_size INTEGER NOT NULL,
                        long_size INTEGER NOT NULL,
                        start_time REAL NOT NULL,
                        duration REAL NOT NULL,
                        sequence_score REAL NOT NULL,
                        config_hash TEXT,
                        num_samples INTEGER,
                        warmup_seconds REAL,
                        execution_time REAL,
                        -- Verification results
                        accepted BOOLEAN NOT NULL,
                        scene_cuts_score REAL NOT NULL,
                        dct_score REAL NOT NULL,
                        rejection_reason TEXT,
                        verification_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (short_video_id) REFERENCES video_files (id) ON DELETE CASCADE,
                        FOREIGN KEY (long_video_id) REFERENCES video_files (id) ON DELETE CASCADE,
                        UNIQUE(short_video_id, long_video_id, start_time)
                    )
                ''')

                # Table for validated duplicates from 3-level analysis
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS advanced_duplicates (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        pair_id TEXT UNIQUE NOT NULL,
                        file1_id INTEGER,
                        file2_id INTEGER,
                        level1_score REAL,
                        level2_score REAL,
                        level3_score REAL,
                        confidence TEXT DEFAULT 'high',
                        status TEXT DEFAULT 'pending',
                        action_taken TEXT,
                        validated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        processed_at TIMESTAMP,
                        FOREIGN KEY (file1_id) REFERENCES video_files (id) ON DELETE CASCADE,
                        FOREIGN KEY (file2_id) REFERENCES video_files (id) ON DELETE CASCADE
                    )
                ''')

                # ═══════════════════════════════════════════════════════════
                # PIPELINE/METHOD CONFIGS & RUNS (for benchmarks/debug)
                # ═══════════════════════════════════════════════════════════

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS pipeline_configs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        config_hash TEXT UNIQUE NOT NULL,
                        mode TEXT,
                        config_json TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS method_configs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        method_name TEXT NOT NULL,
                        params_hash TEXT NOT NULL,
                        params_json TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(method_name, params_hash)
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS verification_runs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        pipeline_config_id INTEGER,
                        short_video_id INTEGER NOT NULL,
                        long_video_id INTEGER NOT NULL,
                        start_time REAL NOT NULL,
                        duration REAL NOT NULL,
                        sequence_score REAL,
                        accepted BOOLEAN,
                        total_time REAL,
                        run_label TEXT,
                        debug_flag BOOLEAN DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (pipeline_config_id) REFERENCES pipeline_configs(id) ON DELETE SET NULL,
                        FOREIGN KEY (short_video_id) REFERENCES video_files(id) ON DELETE CASCADE,
                        FOREIGN KEY (long_video_id) REFERENCES video_files(id) ON DELETE CASCADE
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS verification_method_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        run_id INTEGER NOT NULL,
                        method_config_id INTEGER,
                        method_name TEXT NOT NULL,
                        accepted BOOLEAN,
                        primary_score REAL,
                        threshold REAL,
                        execution_time REAL,
                        extra_json TEXT,
                        FOREIGN KEY (run_id) REFERENCES verification_runs(id) ON DELETE CASCADE,
                        FOREIGN KEY (method_config_id) REFERENCES method_configs(id) ON DELETE SET NULL
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS debug_labels (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        short_video_id INTEGER NOT NULL,
                        long_video_id INTEGER NOT NULL,
                        label TEXT NOT NULL,
                        notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(short_video_id, long_video_id, label),
                        FOREIGN KEY (short_video_id) REFERENCES video_files(id) ON DELETE CASCADE,
                        FOREIGN KEY (long_video_id) REFERENCES video_files(id) ON DELETE CASCADE
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS video_hashes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        video_id INTEGER NOT NULL,
                        method_name TEXT NOT NULL,
                        params_hash TEXT NOT NULL,
                        params_json TEXT NOT NULL,
                        hash_blob BLOB NOT NULL,
                        modification_time REAL NOT NULL,
                        file_size INTEGER NOT NULL,
                        computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (video_id) REFERENCES video_files(id) ON DELETE CASCADE,
                        UNIQUE(video_id, method_name, params_hash)
                    )
                ''')

                # STEP 3: Check and add ignore_type column if necessary (migration)
                cursor.execute("PRAGMA table_info(ignored_pairs)")
                columns = [column[1] for column in cursor.fetchall()]

                if 'ignore_type' not in columns:
                    logger.info("Adding ignore_type column to ignored_pairs table")
                    cursor.execute("ALTER TABLE ignored_pairs ADD COLUMN ignore_type TEXT DEFAULT 'permanent'")

                    # Update existing entries
                    cursor.execute("UPDATE ignored_pairs SET ignore_type = 'permanent' WHERE ignore_type IS NULL")

                    logger.info("Database migration completed")

                # STEP 4: Check and add audio_fingerprint column if necessary (migration)
                cursor.execute("PRAGMA table_info(video_files)")
                video_columns = [column[1] for column in cursor.fetchall()]

                if 'audio_fingerprint' not in video_columns:
                    logger.info("Adding audio_fingerprint column to video_files table")
                    cursor.execute("ALTER TABLE video_files ADD COLUMN audio_fingerprint BLOB")
                    logger.info("Audio fingerprint column added")

                # STEP 5: verification_cache migrations (new columns)
                cursor.execute("PRAGMA table_info(verification_cache)")
                verification_cols = [column[1] for column in cursor.fetchall()]

                if 'config_hash' not in verification_cols:
                    cursor.execute("ALTER TABLE verification_cache ADD COLUMN config_hash TEXT")
                if 'num_samples' not in verification_cols:
                    cursor.execute("ALTER TABLE verification_cache ADD COLUMN num_samples INTEGER")
                if 'warmup_seconds' not in verification_cols:
                    cursor.execute("ALTER TABLE verification_cache ADD COLUMN warmup_seconds REAL")
                if 'execution_time' not in verification_cols:
                    cursor.execute("ALTER TABLE verification_cache ADD COLUMN execution_time REAL")

                # STEP 6: add params_hash/params_json to caches if missing
                cursor.execute("PRAGMA table_info(lsh_fingerprints)")
                lsh_cols = [column[1] for column in cursor.fetchall()]
                if 'params_hash' not in lsh_cols:
                    cursor.execute("ALTER TABLE lsh_fingerprints ADD COLUMN params_hash TEXT")
                if 'params_json' not in lsh_cols:
                    cursor.execute("ALTER TABLE lsh_fingerprints ADD COLUMN params_json TEXT")

                cursor.execute("PRAGMA table_info(dense_hashes)")
                dense_cols = [column[1] for column in cursor.fetchall()]
                if 'params_hash' not in dense_cols:
                    cursor.execute("ALTER TABLE dense_hashes ADD COLUMN params_hash TEXT")
                if 'params_json' not in dense_cols:
                    cursor.execute("ALTER TABLE dense_hashes ADD COLUMN params_json TEXT")

                cursor.execute("PRAGMA table_info(level2_long_audio)")
                l2_cols = [column[1] for column in cursor.fetchall()]
                if 'params_hash' not in l2_cols:
                    cursor.execute("ALTER TABLE level2_long_audio ADD COLUMN params_hash TEXT")
                if 'params_json' not in l2_cols:
                    cursor.execute("ALTER TABLE level2_long_audio ADD COLUMN params_json TEXT")

                cursor.execute("PRAGMA table_info(level3_phash)")
                l3_cols = [column[1] for column in cursor.fetchall()]
                if 'params_hash' not in l3_cols:
                    cursor.execute("ALTER TABLE level3_phash ADD COLUMN params_hash TEXT")
                if 'params_json' not in l3_cols:
                    cursor.execute("ALTER TABLE level3_phash ADD COLUMN params_json TEXT")

                # STEP 4: Benchmark system tables
                # ═══════════════════════════════════════════════════════════
                # BENCHMARK SYSTEM TABLES
                # ═══════════════════════════════════════════════════════════

                # Table for saved user pipelines
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS saved_pipelines (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        description TEXT,
                        mode TEXT NOT NULL,
                        methods_json TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_used_at TIMESTAMP,
                        use_count INTEGER DEFAULT 0
                    )
                ''')

                # Table for test pairs (ground truth for benchmarking)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS test_pairs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        video1_path TEXT NOT NULL,
                        video2_path TEXT NOT NULL,
                        expected TEXT NOT NULL CHECK(expected IN ('positive', 'negative', 'unknown')),
                        start_time REAL DEFAULT 0.0,
                        duration REAL,
                        sequence_score REAL DEFAULT 100.0,
                        notes TEXT,
                        test_set_name TEXT DEFAULT 'default',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(video1_path, video2_path, test_set_name)
                    )
                ''')

                # Table for benchmark runs (batch benchmarks)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS benchmark_runs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        run_label TEXT NOT NULL,
                        test_set_name TEXT NOT NULL,
                        total_pairs INTEGER NOT NULL,
                        pipelines_count INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP,
                        status TEXT DEFAULT 'running'
                    )
                ''')

                # Table for benchmark results (per pipeline in a run)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS benchmark_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        benchmark_run_id INTEGER NOT NULL,
                        pipeline_name TEXT NOT NULL,
                        pipeline_config_json TEXT NOT NULL,
                        tp INTEGER DEFAULT 0,
                        fp INTEGER DEFAULT 0,
                        tn INTEGER DEFAULT 0,
                        fn INTEGER DEFAULT 0,
                        precision REAL,
                        recall REAL,
                        f1_score REAL,
                        total_time REAL,
                        per_pair_results_json TEXT,
                        FOREIGN KEY (benchmark_run_id) REFERENCES benchmark_runs(id) ON DELETE CASCADE
                    )
                ''')

                # STEP 5: Create indexes
                index_commands = [
                    "CREATE INDEX IF NOT EXISTS idx_file_path ON video_files(file_path)",
                    "CREATE INDEX IF NOT EXISTS idx_file_size ON video_files(file_size)",
                    "CREATE INDEX IF NOT EXISTS idx_duration ON video_files(duration)",
                    "CREATE INDEX IF NOT EXISTS idx_modification_time ON video_files(modification_time)",
                    "CREATE INDEX IF NOT EXISTS idx_comparison_files ON comparisons(file1_id, file2_id)",
                    "CREATE INDEX IF NOT EXISTS idx_similarity ON comparisons(similarity)",
                    "CREATE INDEX IF NOT EXISTS idx_early_exit ON comparisons(is_early_exit)",
                    "CREATE INDEX IF NOT EXISTS idx_corrupted_path ON corrupted_files(file_path)",
                    "CREATE INDEX IF NOT EXISTS idx_duplicates_status ON found_duplicates(status)",
                    "CREATE INDEX IF NOT EXISTS idx_duplicates_files ON found_duplicates(file1_id, file2_id)",
                    "CREATE INDEX IF NOT EXISTS idx_ignored_pairs ON ignored_pairs(file1_id, file2_id)",
                    "CREATE INDEX IF NOT EXISTS idx_ignored_type ON ignored_pairs(ignore_type)",
                    "CREATE INDEX IF NOT EXISTS idx_subsequences_status ON video_subsequences(status)",
                    "CREATE INDEX IF NOT EXISTS idx_subsequences_files ON video_subsequences(short_video_id, long_video_id)",
                    "CREATE INDEX IF NOT EXISTS idx_subsequences_confidence ON video_subsequences(confidence)",
                    # Verification cache indexes
                    "CREATE INDEX IF NOT EXISTS idx_verification_videos ON verification_cache(short_video_id, long_video_id, start_time)",
                    "CREATE INDEX IF NOT EXISTS idx_verification_accepted ON verification_cache(accepted)",
                    "CREATE INDEX IF NOT EXISTS idx_verification_date ON verification_cache(verification_date)",
                    # Advanced 3-level mode indexes
                    "CREATE INDEX IF NOT EXISTS idx_lsh_video ON lsh_fingerprints(video_id)",
                    "CREATE INDEX IF NOT EXISTS idx_lsh_computed_at ON lsh_fingerprints(computed_at)",
                    "CREATE INDEX IF NOT EXISTS idx_lsh_params ON lsh_fingerprints(params_hash)",
                    "CREATE INDEX IF NOT EXISTS idx_level2_pair ON level2_long_audio(pair_id)",
                    "CREATE INDEX IF NOT EXISTS idx_level2_files ON level2_long_audio(file1_id, file2_id)",
                    "CREATE INDEX IF NOT EXISTS idx_level2_similarity ON level2_long_audio(similarity_score)",
                    "CREATE INDEX IF NOT EXISTS idx_level2_params ON level2_long_audio(params_hash)",
                    "CREATE INDEX IF NOT EXISTS idx_level3_pair ON level3_phash(pair_id)",
                    "CREATE INDEX IF NOT EXISTS idx_level3_files ON level3_phash(file1_id, file2_id)",
                    "CREATE INDEX IF NOT EXISTS idx_level3_similarity ON level3_phash(similarity_rate)",
                    "CREATE INDEX IF NOT EXISTS idx_level3_params ON level3_phash(params_hash)",
                    "CREATE INDEX IF NOT EXISTS idx_advanced_dup_status ON advanced_duplicates(status)",
                    "CREATE INDEX IF NOT EXISTS idx_advanced_dup_pair ON advanced_duplicates(pair_id)",
                    "CREATE INDEX IF NOT EXISTS idx_advanced_dup_confidence ON advanced_duplicates(confidence)",
                    "CREATE INDEX IF NOT EXISTS idx_pipeline_config_hash ON pipeline_configs(config_hash)",
                    "CREATE INDEX IF NOT EXISTS idx_method_config ON method_configs(method_name, params_hash)",
                    "CREATE INDEX IF NOT EXISTS idx_verification_runs_videos ON verification_runs(short_video_id, long_video_id)",
                    "CREATE INDEX IF NOT EXISTS idx_verification_runs_pipeline ON verification_runs(pipeline_config_id)",
                    "CREATE INDEX IF NOT EXISTS idx_video_hashes ON video_hashes(video_id, method_name, params_hash)",
                    # Benchmark system indexes
                    "CREATE INDEX IF NOT EXISTS idx_saved_pipelines_name ON saved_pipelines(name)",
                    "CREATE INDEX IF NOT EXISTS idx_test_pairs_set ON test_pairs(test_set_name)",
                    "CREATE INDEX IF NOT EXISTS idx_test_pairs_expected ON test_pairs(expected)",
                    "CREATE INDEX IF NOT EXISTS idx_benchmark_runs_label ON benchmark_runs(run_label)",
                    "CREATE INDEX IF NOT EXISTS idx_benchmark_runs_status ON benchmark_runs(status)",
                    "CREATE INDEX IF NOT EXISTS idx_benchmark_results_run ON benchmark_results(benchmark_run_id)",
                    "CREATE INDEX IF NOT EXISTS idx_benchmark_results_pipeline ON benchmark_results(pipeline_name)"
                ]

                for cmd in index_commands:
                    cursor.execute(cmd)

                conn.commit()
                logger.debug("Database structure created/verified with migration")
                
        except Exception as e:
            logger.error(f"Error during database initialization: {e}")
            raise
    
    def _table_exists(self, table_name):
        """Check if a table exists - WITH CACHE"""
        # Use cache first
        if table_name in self._tables_exist:
            return self._tables_exist[table_name]

        # Otherwise check only once
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name=?
                ''', (table_name,))
                exists = cursor.fetchone() is not None
                self._tables_exist[table_name] = exists
                return exists
        except Exception:
            return False
    
    @contextmanager
    def get_connection(self):
        """
        Get an optimized database connection from the pool (context manager).

        Yields:
            SQLite connection from the connection pool

        Example:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT ...")
        """
        with self.connection_pool.get_connection() as conn:
            yield conn

    def close(self):
        """
        Close all database connections.

        Should be called when shutting down.
        """
        self.connection_pool.close_all()
        logger.info("Database connections closed")
    
    def file_needs_reanalysis(self, file_path):
        """Check if a file has been modified - OPTIMIZED"""
        if not os.path.exists(file_path):
            return True

        try:
            current_mtime = os.path.getmtime(file_path)
            current_size = os.path.getsize(file_path)

            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT modification_time, file_size FROM video_files
                    WHERE file_path = ?
                ''', (file_path,))

                result = cursor.fetchone()
                if not result:
                    return True  # File not in database

                stored_mtime, stored_size = result

                # Check if modified (1 second tolerance for file systems)
                return (abs(current_mtime - stored_mtime) > 1.0 or
                       current_size != stored_size)
                
        except Exception as e:
            logger.error(f"Error checking modification {file_path}: {e}")
            return True
    
    def store_video_hash(self, file_path, hash_data, duration, width=None, height=None,
                        hash_method="pHash", frames_indices=None, sampling_method=None):
        """
        Store video hash in database.

        **OPTIMIZED**: Uses JSON serialization instead of pickle for security and speed.

        Args:
            file_path (str): Path to the video file.
            hash_data (np.ndarray): Video hash data.
            duration (float): Video duration in seconds.
            width (int, optional): Video width.
            height (int, optional): Video height.
            hash_method (str): Hash method used ('pHash', 'dHash', 'aHash').
            frames_indices (list, optional): Frame indices used for hashing.
            sampling_method (str, optional): Sampling method used.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            from src.core.serialization import serialize_numpy_to_json

            file_stats = os.stat(file_path)

            with self.get_connection() as conn:
                cursor = conn.cursor()

                # OPTIMIZED: Use JSON instead of pickle (secure + faster)
                hash_json = serialize_numpy_to_json(hash_data)
                hash_blob = hash_json.encode('utf-8')
                frames_json = json.dumps(frames_indices) if frames_indices else None

                # Combine hash method and sampling method if provided
                full_method = hash_method
                if sampling_method:
                    full_method += f"_{sampling_method}"

                cursor.execute('''
                    INSERT OR REPLACE INTO video_files
                    (file_path, file_name, file_size, modification_time, duration,
                     width, height, hash_method, hash_data, frames_indices, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    file_path,
                    os.path.basename(file_path),
                    file_stats.st_size,
                    file_stats.st_mtime,
                    duration,
                    width,
                    height,
                    full_method,
                    hash_blob,
                    frames_json
                ))

                conn.commit()
                return True

        except Exception as e:
            logger.error(f"Error storing hash {file_path}: {e}")
            return False
    
    def has_video(self, file_path):
        """
        Check if a video exists in the database.

        Args:
            file_path (str): Path to the video file.

        Returns:
            bool: True if video exists in database, False otherwise.
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 1 FROM video_files WHERE file_path = ? LIMIT 1
                ''', (file_path,))
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking if video exists {file_path}: {e}")
            return False

    def get_video_hash(self, file_path):
        """
        Retrieve video hash from database.

        **OPTIMIZED**: Supports both JSON (new) and pickle (legacy) formats.

        Args:
            file_path (str): Path to the video file.

        Returns:
            dict: Dictionary with 'hash', 'duration', and 'frames' keys, or None if not found.
        """
        try:
            from src.core.serialization import deserialize_numpy_from_json

            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT hash_data, duration, frames_indices FROM video_files
                    WHERE file_path = ?
                ''', (file_path,))

                result = cursor.fetchone()
                if result:
                    hash_blob, duration, frames_json = result

                    # OPTIMIZED: Try JSON first (new format), fallback to pickle (legacy)
                    try:
                        hash_data = deserialize_numpy_from_json(hash_blob.decode('utf-8'))
                    except (UnicodeDecodeError, AttributeError):
                        # Legacy pickle format
                        hash_data = pickle.loads(hash_blob)

                    frames_indices = json.loads(frames_json) if frames_json else None

                    return {
                        'hash': hash_data,
                        'duration': duration,
                        'frames': frames_indices
                    }

        except Exception as e:
            logger.error(f"Error retrieving hash {file_path}: {e}")

        return None

    def store_audio_fingerprint(self, file_path, audio_fingerprint):
        """
        Store audio fingerprint in database.

        Args:
            file_path (str): Path to the video file.
            audio_fingerprint (np.ndarray): Audio fingerprint data.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            from src.core.serialization import serialize_numpy_to_json

            file_stats = os.stat(file_path)

            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Serialize audio fingerprint to JSON
                audio_json = serialize_numpy_to_json(audio_fingerprint)
                audio_blob = audio_json.encode('utf-8')

                # First, ensure the video file exists in the database
                cursor.execute('''
                    INSERT OR IGNORE INTO video_files
                    (file_path, file_name, file_size, modification_time)
                    VALUES (?, ?, ?, ?)
                ''', (
                    file_path,
                    os.path.basename(file_path),
                    file_stats.st_size,
                    file_stats.st_mtime
                ))

                # Then update the audio fingerprint
                cursor.execute('''
                    UPDATE video_files
                    SET audio_fingerprint = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE file_path = ?
                ''', (audio_blob, file_path))

                conn.commit()
                return True

        except Exception as e:
            logger.error(f"Error storing audio fingerprint for {file_path}: {e}")
            return False

    def get_audio_fingerprint(self, file_path):
        """
        Retrieve audio fingerprint from database.

        Args:
            file_path (str): Path to the video file.

        Returns:
            np.ndarray: Audio fingerprint, or None if not found.
        """
        try:
            from src.core.serialization import deserialize_numpy_from_json

            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT audio_fingerprint, modification_time FROM video_files
                    WHERE file_path = ?
                ''', (file_path,))

                result = cursor.fetchone()
                if result and result[0] is not None:
                    audio_blob, db_mtime = result

                    # Check if file has been modified since fingerprint was stored
                    try:
                        current_mtime = os.path.getmtime(file_path)
                        if abs(current_mtime - db_mtime) >= 1:
                            # File was modified, fingerprint is stale
                            return None
                    except Exception as e:
                        # File doesn't exist anymore or permission error
                        logger.debug(f"Cannot access file {file_path}: {e}")
                        return None

                    # Deserialize audio fingerprint
                    try:
                        audio_data = deserialize_numpy_from_json(audio_blob.decode('utf-8'))
                        return audio_data
                    except (UnicodeDecodeError, AttributeError):
                        # Legacy pickle format (if any)
                        return pickle.loads(audio_blob)

        except Exception as e:
            logger.error(f"Error retrieving audio fingerprint for {file_path}: {e}")

        return None

    def get_cached_comparison(self, file1_path, file2_path):
        """Retrieve a comparison result - OPTIMIZED"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Optimized query with index
                cursor.execute('''
                    SELECT c.similarity
                    FROM comparisons c
                    JOIN video_files v1 ON c.file1_id = v1.id
                    JOIN video_files v2 ON c.file2_id = v2.id
                    WHERE (v1.file_path = ? AND v2.file_path = ?)
                       OR (v1.file_path = ? AND v2.file_path = ?)
                ''', (file1_path, file2_path, file2_path, file1_path))
                
                result = cursor.fetchone()
                if result:
                    return result[0]
                    
        except Exception as e:
            logger.error(f"Error retrieving comparison: {e}")
            
        return None
    
    def store_comparison(self, file1_path, file2_path, similarity,
                        comparison_method="optimized", is_early_exit=False, computation_time=0.0):
        """Store a comparison result - OPTIMIZED with batch"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Retrieve IDs in a single query
                cursor.execute('''
                    SELECT
                        (SELECT id FROM video_files WHERE file_path = ?) as id1,
                        (SELECT id FROM video_files WHERE file_path = ?) as id2
                ''', (file1_path, file2_path))

                result = cursor.fetchone()
                if not result or not result[0] or not result[1]:
                    return False

                file1_id, file2_id = result

                # Ensure order to avoid duplicates
                if file1_id > file2_id:
                    file1_id, file2_id = file2_id, file1_id
                
                cursor.execute('''
                    INSERT OR REPLACE INTO comparisons 
                    (file1_id, file2_id, similarity, comparison_method, is_early_exit, computation_time)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (file1_id, file2_id, similarity, comparison_method, is_early_exit, computation_time))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error storing comparison: {e}")
            return False
    
    def is_pair_ignored(self, file1_path, file2_path):
        """Check if a pair is ignored - CORRECTED with ignore_type"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # CORRECTION: Check only PERMANENTLY ignored pairs
                # Use COALESCE to handle old entries without ignore_type
                cursor.execute('''
                    SELECT 1 FROM ignored_pairs ip
                    JOIN video_files v1 ON ip.file1_id = v1.id
                    JOIN video_files v2 ON ip.file2_id = v2.id
                    WHERE (v1.file_path = ? AND v2.file_path = ?)
                       OR (v1.file_path = ? AND v2.file_path = ?)
                    AND COALESCE(ip.ignore_type, 'permanent') = 'permanent'
                    LIMIT 1
                ''', (file1_path, file2_path, file2_path, file1_path))
                
                return cursor.fetchone() is not None
                
        except Exception as e:
            logger.error(f"Error checking ignored pair: {e}")
            
        return False

    def get_all_ignored_pairs(self):
        """
        Get all permanently ignored pairs.

        Returns:
            List[Tuple[str, str]]: List of tuples (file1_path, file2_path) for all ignored pairs.
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Get all permanently ignored pairs in one batch query
                cursor.execute('''
                    SELECT v1.file_path, v2.file_path
                    FROM ignored_pairs ip
                    JOIN video_files v1 ON ip.file1_id = v1.id
                    JOIN video_files v2 ON ip.file2_id = v2.id
                    WHERE COALESCE(ip.ignore_type, 'permanent') = 'permanent'
                ''')

                return cursor.fetchall()

        except Exception as e:
            logger.error(f"Error fetching all ignored pairs: {e}")
            return []

    def add_ignored_pair(self, file1_path, file2_path, reason="user_choice", ignore_type="permanent"):
        """Add a pair to ignore list with specified type (permanent/temporary)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Get IDs in a single query
                cursor.execute('''
                    SELECT
                        (SELECT id FROM video_files WHERE file_path = ?) as id1,
                        (SELECT id FROM video_files WHERE file_path = ?) as id2
                ''', (file1_path, file2_path))

                result = cursor.fetchone()
                if not result or not result[0] or not result[1]:
                    logger.warning(f"Files not found in database: {file1_path}, {file2_path}")
                    return False

                file1_id, file2_id = result

                # Ensure order
                if file1_id > file2_id:
                    file1_id, file2_id = file2_id, file1_id

                # After migration, ignore_type column ALWAYS exists
                # No need to check - just use it
                cursor.execute('''
                    INSERT OR REPLACE INTO ignored_pairs (file1_id, file2_id, reason, ignore_type)
                    VALUES (?, ?, ?, ?)
                ''', (file1_id, file2_id, reason, ignore_type))

                conn.commit()
                logger.info(f"Pair ignored ({ignore_type}): {os.path.basename(file1_path)} <-> {os.path.basename(file2_path)}")
                return True

        except Exception as e:
            logger.error(f"Error adding ignored pair: {e}")
            return False
    
    def get_statistics(self):
        """Get database statistics - Optimized with a single query"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Query all statistics in a single optimized query
                cursor.execute('''
                    SELECT
                        (SELECT COUNT(*) FROM video_files) as files_count,
                        (SELECT COUNT(*) FROM comparisons) as comparisons_count,
                        (SELECT COUNT(*) FROM comparisons WHERE is_early_exit = 1) as early_exits,
                        (SELECT COUNT(*) FROM ignored_pairs WHERE COALESCE(ignore_type, 'permanent') = 'permanent') as ignored_permanent,
                        (SELECT COUNT(*) FROM ignored_pairs WHERE ignore_type = 'temporary') as ignored_temporary,
                        (SELECT COUNT(*) FROM ignored_pairs) as ignored_total
                ''')

                result = cursor.fetchone()
                files_count, comparisons_count, early_exits, ignored_perm, ignored_temp, ignored_total = result

                # Database size
                db_size = os.path.getsize(self.db_path) / 1024 if os.path.exists(self.db_path) else 0

                # Calculate time saved (estimated at 2s per comparison)
                time_saved = comparisons_count * 2
                
                return {
                    'files_count': files_count or 0,
                    'comparisons_count': comparisons_count or 0,
                    'early_exits': early_exits or 0,
                    'ignored_count': ignored_total or 0,
                    'ignored_permanent': ignored_perm or 0,
                    'ignored_temporary': ignored_temp or 0,
                    'db_size_kb': db_size,
                    'time_saved_seconds': time_saved,
                    'early_exit_percentage': (early_exits / comparisons_count * 100) if comparisons_count > 0 else 0
                }
                
        except Exception as e:
            logger.error(f"Error retrieving statistics: {e}")
            return {
                'files_count': 0,
                'comparisons_count': 0,
                'early_exits': 0,
                'ignored_count': 0,
                'ignored_permanent': 0,
                'ignored_temporary': 0,
                'db_size_kb': 0,
                'time_saved_seconds': 0,
                'early_exit_percentage': 0
            }
    
    def cleanup_missing_files(self):
        """Clean up database from files that no longer exist"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Get all files
                cursor.execute('SELECT id, file_path FROM video_files')
                files = cursor.fetchall()

                missing_ids = []
                for file_id, file_path in files:
                    if not os.path.exists(file_path):
                        missing_ids.append(file_id)

                if missing_ids:
                    # Remove in a single transaction
                    placeholders = ','.join('?' * len(missing_ids))

                    # Remove comparisons
                    cursor.execute(f'''
                        DELETE FROM comparisons
                        WHERE file1_id IN ({placeholders}) OR file2_id IN ({placeholders})
                    ''', missing_ids + missing_ids)

                    # Remove ignored pairs
                    cursor.execute(f'''
                        DELETE FROM ignored_pairs
                        WHERE file1_id IN ({placeholders}) OR file2_id IN ({placeholders})
                    ''', missing_ids + missing_ids)

                    # Remove found duplicates
                    cursor.execute(f'''
                        DELETE FROM found_duplicates
                        WHERE file1_id IN ({placeholders}) OR file2_id IN ({placeholders})
                    ''', missing_ids + missing_ids)

                    # Remove files
                    cursor.execute(f'DELETE FROM video_files WHERE id IN ({placeholders})', missing_ids)
                    
                    conn.commit()
                    logger.info(f"Database cleanup: {len(missing_ids)} files removed")
                    
                return len(missing_ids)
                
        except Exception as e:
            logger.error(f"Error cleaning database: {e}")
            return 0
    
    def auto_cleanup_on_access(self):
        """Automatically clean up on access if necessary"""
        # Clean up only once per session
        if not hasattr(self, '_cleaned_this_session'):
            self._cleaned_this_session = True
            removed = self.cleanup_missing_files()
            if removed > 0:
                logger.info(f"Automatic cleanup: {removed} missing files removed")

    def clear_all_data(self):
        """Completely empty the database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Transaction unique pour tout remove
                cursor.executescript('''
                    DELETE FROM comparisons;
                    DELETE FROM ignored_pairs;
                    DELETE FROM corrupted_files;
                    DELETE FROM found_duplicates;
                    DELETE FROM video_subsequences;
                    DELETE FROM video_files;
                    VACUUM;
                ''')

                conn.commit()
                logger.info("Database cleared and compacted")
                return True

        except Exception as e:
            logger.error(f"Error clearing database: {e}")
            return False
    
    def mark_file_as_corrupted(self, file_path, error_message):
        """Marque un file comme corrompu"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO corrupted_files (file_path, error_message)
                    VALUES (?, ?)
                ''', (file_path, error_message))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error marking corrupted file: {e}")

    def get_files_needing_analysis(self, file_paths):
        """Returns les files qui ont besoin d'être analysés - OPTIMISÉ"""
        if not file_paths:
            return []
            
        files_to_analyze = []
        
        # Batch check pour performance
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Retrieve all existing files in one query
            placeholders = ','.join('?' * len(file_paths))
            cursor.execute(f'''
                SELECT file_path, modification_time, file_size
                FROM video_files
                WHERE file_path IN ({placeholders})
            ''', file_paths)

            existing_files = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}

        # Check each file
        for file_path in file_paths:
            if not os.path.exists(file_path):
                continue

            if file_path not in existing_files:
                files_to_analyze.append(file_path)
            else:
                # Check if modified
                current_mtime = os.path.getmtime(file_path)
                current_size = os.path.getsize(file_path)
                stored_mtime, stored_size = existing_files[file_path]
                
                if abs(current_mtime - stored_mtime) > 1.0 or current_size != stored_size:
                    files_to_analyze.append(file_path)
        
        return files_to_analyze
    
    def store_found_duplicate(self, file1_path, file2_path, similarity):
        """Store a found duplicate for later retrieval"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Retrieve IDs
                cursor.execute('''
                    SELECT
                        (SELECT id FROM video_files WHERE file_path = ?) as id1,
                        (SELECT id FROM video_files WHERE file_path = ?) as id2
                ''', (file1_path, file2_path))

                result = cursor.fetchone()
                if not result or not result[0] or not result[1]:
                    return False

                file1_id, file2_id = result

                # Ensure order
                if file1_id > file2_id:
                    file1_id, file2_id = file2_id, file1_id
                
                cursor.execute('''
                    INSERT OR REPLACE INTO found_duplicates 
                    (file1_id, file2_id, similarity, status, detected_at)
                    VALUES (?, ?, ?, 'pending', CURRENT_TIMESTAMP)
                ''', (file1_id, file2_id, similarity))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error storing found duplicate: {e}")
            return False
    
    def get_pending_duplicates(self, limit: int = 1000, offset: int = 0):
        """
        Get pending duplicates with pagination support.

        Args:
            limit: Maximum number of duplicates to retrieve (default: 1000)
            offset: Number of duplicates to skip (default: 0)

        Returns:
            List of tuples (file1_path, file2_path, similarity, dup_id)
        """
        try:
            duplicates = []

            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Paginated query to prevent loading all results at once
                cursor.execute('''
                    SELECT v1.file_path, v2.file_path, d.similarity, d.id
                    FROM found_duplicates d
                    JOIN video_files v1 ON d.file1_id = v1.id
                    JOIN video_files v2 ON d.file2_id = v2.id
                    WHERE d.status = 'pending'
                    ORDER BY d.similarity DESC, d.detected_at DESC
                    LIMIT ? OFFSET ?
                ''', (limit, offset))

                for row in cursor.fetchall():
                    file1, file2, similarity, dup_id = row
                    # Check if files still exist
                    if os.path.exists(file1) and os.path.exists(file2):
                        duplicates.append((file1, file2, similarity, dup_id))

                return duplicates

        except Exception as e:
            logger.error(f"Error retrieving pending duplicates: {e}")
            return []
    
    def update_duplicate_status(self, dup_id, status, action=None):
        """Update duplicate status"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE found_duplicates 
                    SET status = ?, action_taken = ?, processed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, action, dup_id))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error updating duplicate status: {e}")
            return False
    
    def clear_processed_duplicates(self):
        """Remove already processed duplicates"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    DELETE FROM found_duplicates 
                    WHERE status != 'pending'
                ''')
                
                deleted = cursor.rowcount
                conn.commit()
                
                logger.info(f"Removed {deleted} processed duplicates")
                return deleted
                
        except Exception as e:
            logger.error(f"Error removing processed duplicates: {e}")
            return 0
    
    def get_duplicate_statistics(self):
        """Retrieve duplicate statistics"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                        SUM(CASE WHEN status = 'processed' THEN 1 ELSE 0 END) as processed,
                        SUM(CASE WHEN action_taken = 'kept_left' THEN 1 ELSE 0 END) as kept_left,
                        SUM(CASE WHEN action_taken = 'kept_right' THEN 1 ELSE 0 END) as kept_right,
                        SUM(CASE WHEN action_taken = 'ignored_permanently' THEN 1 ELSE 0 END) as ignored,
                        SUM(CASE WHEN action_taken = 'ignored_temporarily' THEN 1 ELSE 0 END) as skipped
                    FROM found_duplicates
                ''')
                
                result = cursor.fetchone()
                if result:
                    return {
                        'total': result[0] or 0,
                        'pending': result[1] or 0,
                        'processed': result[2] or 0,
                        'kept_left': result[3] or 0,
                        'kept_right': result[4] or 0,
                        'ignored': result[5] or 0,
                        'skipped': result[6] or 0
                    }
                    
        except Exception as e:
            logger.error(f"Error retrieving duplicate stats: {e}")
            
        return {
            'total': 0,
            'pending': 0,
            'processed': 0,
            'kept_left': 0,
            'kept_right': 0,
            'ignored': 0,
            'skipped': 0
        }
    
    def clear_temporary_ignores(self):
        """Clear all temporarily ignored pairs"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Check if ignore_type exists
                cursor.execute("PRAGMA table_info(ignored_pairs)")
                columns = [column[1] for column in cursor.fetchall()]

                if 'ignore_type' in columns:
                    cursor.execute('''
                        DELETE FROM ignored_pairs
                        WHERE ignore_type = 'temporary'
                    ''')
                else:
                    # If no ignore_type column, do nothing (all are permanent)
                    return 0
                
                deleted = cursor.rowcount
                conn.commit()
                
                if deleted > 0:
                    logger.info(f"Removed {deleted} temporarily ignored pairs")
                
                return deleted
                
        except Exception as e:
            logger.error(f"Error removing temporary ignores: {e}")
            return 0
    
    def get_ignored_pairs_details(self):
        """Retrieve details of ignored pairs"""
        try:
            ignored_pairs = []

            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Check if ignore_type exists
                cursor.execute("PRAGMA table_info(ignored_pairs)")
                columns = [column[1] for column in cursor.fetchall()]
                has_ignore_type = 'ignore_type' in columns
                
                if has_ignore_type:
                    cursor.execute('''
                        SELECT v1.file_path, v2.file_path, ip.reason, 
                               COALESCE(ip.ignore_type, 'permanent') as ignore_type, ip.created_at
                        FROM ignored_pairs ip
                        JOIN video_files v1 ON ip.file1_id = v1.id
                        JOIN video_files v2 ON ip.file2_id = v2.id
                        ORDER BY ip.created_at DESC
                    ''')
                else:
                    cursor.execute('''
                        SELECT v1.file_path, v2.file_path, ip.reason, 
                               'permanent' as ignore_type, ip.created_at
                        FROM ignored_pairs ip
                        JOIN video_files v1 ON ip.file1_id = v1.id
                        JOIN video_files v2 ON ip.file2_id = v2.id
                        ORDER BY ip.created_at DESC
                    ''')
                
                for row in cursor.fetchall():
                    file1, file2, reason, ignore_type, created_at = row
                    ignored_pairs.append({
                        'file1': file1,
                        'file2': file2,
                        'reason': reason,
                        'type': ignore_type,
                        'created_at': created_at
                    })
                
                return ignored_pairs
                
        except Exception as e:
            logger.error(f"Error retrieving ignored pairs details: {e}")
            return []
    
    def force_recreate_table(self, table_name):
        """Force la recréation d'une table (pour migration manuelle)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if table_name == "ignored_pairs":
                    # Saves les données existantes
                    cursor.execute('''
                        CREATE TEMPORARY TABLE ignored_pairs_backup AS 
                        SELECT * FROM ignored_pairs
                    ''')
                    
                    # Removes l'ancienne table
                    cursor.execute("DROP TABLE ignored_pairs")
                    
                    # Recrée la nouvelle table
                    cursor.execute('''
                        CREATE TABLE ignored_pairs (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            file1_id INTEGER,
                            file2_id INTEGER,
                            reason TEXT DEFAULT 'user_choice',
                            ignore_type TEXT DEFAULT 'permanent',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (file1_id) REFERENCES video_files (id) ON DELETE CASCADE,
                            FOREIGN KEY (file2_id) REFERENCES video_files (id) ON DELETE CASCADE,
                            UNIQUE(file1_id, file2_id)
                        )
                    ''')
                    
                    # Restaure les données
                    cursor.execute('''
                        INSERT INTO ignored_pairs (id, file1_id, file2_id, reason, ignore_type, created_at)
                        SELECT id, file1_id, file2_id, reason, 'permanent', created_at 
                        FROM ignored_pairs_backup
                    ''')
                    
                    # Removes la table temporaire
                    cursor.execute("DROP TABLE ignored_pairs_backup")
                    
                    # Recrée les index
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ignored_pairs ON ignored_pairs(file1_id, file2_id)")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ignored_type ON ignored_pairs(ignore_type)")
                    
                    conn.commit()
                    logger.info(f"Table {table_name} recreated successfully")
                    return True
                    
        except Exception as e:
            logger.error(f"Error recreating table {table_name}: {e}")
            return False
    
    def verify_database_integrity(self):
        """Checks l'intégrité of the base de données"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Checks l'intégrité SQLite
                cursor.execute("PRAGMA integrity_check")
                integrity_result = cursor.fetchone()
                
                if integrity_result[0] != "ok":
                    logger.warning(f"Integrity problem detected: {integrity_result[0]}")
                    return False
                
                # Checks que toutes les tables existent
                required_tables = ['video_files', 'comparisons', 'ignored_pairs', 'corrupted_files', 'found_duplicates', 'video_subsequences']
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                existing_tables = [row[0] for row in cursor.fetchall()]
                
                missing_tables = [table for table in required_tables if table not in existing_tables]
                if missing_tables:
                    logger.warning(f"Missing tables: {missing_tables}")
                    return False
                
                # Checks la structure de ignored_pairs
                cursor.execute("PRAGMA table_info(ignored_pairs)")
                columns = [column[1] for column in cursor.fetchall()]
                
                if 'ignore_type' not in columns:
                    logger.info("Missing ignore_type column - migration required")
                    return False

                logger.info("Database integrity verified successfully")
                return True
                
        except Exception as e:
            logger.error(f"Error checking integrity: {e}")
            return False
    
    def get_database_info(self):
        """Récupère des information détaillées on la base"""
        try:
            info = {
                'path': self.db_path,
                'exists': os.path.exists(self.db_path),
                'size_bytes': 0,
                'tables': [],
                'version': None,
                'pragma_settings': {}
            }

            if info['exists']:
                info['size_bytes'] = os.path.getsize(self.db_path)

                with self.get_connection() as conn:
                    cursor = conn.cursor()

                    # Tables
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    info['tables'] = [row[0] for row in cursor.fetchall()]

                    # Version SQLite
                    cursor.execute("SELECT sqlite_version()")
                    info['version'] = cursor.fetchone()[0]

                    # Settings PRAGMA
                    pragmas = ['journal_mode', 'synchronous', 'cache_size', 'temp_store', 'foreign_keys']
                    for pragma in pragmas:
                        try:
                            cursor.execute(f"PRAGMA {pragma}")
                            result = cursor.fetchone()
                            info['pragma_settings'][pragma] = result[0] if result else None
                        except Exception as e:
                            logger.debug(f"Error reading PRAGMA {pragma}: {e}")
                            info['pragma_settings'][pragma] = 'error'

            return info

        except Exception as e:
            logger.error(f"Error retrieving DB info: {e}")
            return {'error': str(e)}

    # Subsequence detection methods
    def store_subsequence_detection(self, short_video_path, long_video_path,
                                    match_ratio, start_frame_idx, confidence):
        """Store a subsequence detection result.

        Args:
            short_video_path: Path to the shorter video
            long_video_path: Path to the longer video
            match_ratio: Match ratio (0.0-1.0)
            start_frame_idx: Starting frame index in long video
            confidence: Detection confidence (0.0-1.0)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Get IDs
                cursor.execute('''
                    SELECT
                        (SELECT id FROM video_files WHERE file_path = ?) as id1,
                        (SELECT id FROM video_files WHERE file_path = ?) as id2
                ''', (short_video_path, long_video_path))

                result = cursor.fetchone()
                if not result or not result[0] or not result[1]:
                    logger.warning(f"Files not found in DB: {short_video_path}, {long_video_path}")
                    return False

                short_id, long_id = result

                cursor.execute('''
                    INSERT OR REPLACE INTO video_subsequences
                    (short_video_id, long_video_id, match_ratio, start_frame_idx,
                     confidence, status, detected_at)
                    VALUES (?, ?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP)
                ''', (short_id, long_id, match_ratio, start_frame_idx, confidence))

                conn.commit()
                logger.info(f"Subsequence stored: {os.path.basename(short_video_path)} "
                          f"in {os.path.basename(long_video_path)} ({match_ratio*100:.1f}%)")
                return True

        except Exception as e:
            logger.error(f"Error storing subsequence: {e}")
            return False

    def get_pending_subsequences(self, limit: int = 1000, offset: int = 0):
        """
        Get pending subsequence detections with pagination support.

        Args:
            limit: Maximum number of subsequences to retrieve (default: 1000)
            offset: Number of subsequences to skip (default: 0)

        Returns:
            List of tuples: (short_path, long_path, match_ratio, start_frame, confidence, id)
        """
        try:
            subsequences = []

            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Paginated query to prevent loading all results at once
                cursor.execute('''
                    SELECT v1.file_path, v2.file_path, s.match_ratio,
                           s.start_frame_idx, s.confidence, s.id
                    FROM video_subsequences s
                    JOIN video_files v1 ON s.short_video_id = v1.id
                    JOIN video_files v2 ON s.long_video_id = v2.id
                    WHERE s.status = 'pending'
                    ORDER BY s.confidence DESC, s.detected_at DESC
                    LIMIT ? OFFSET ?
                ''', (limit, offset))

                for row in cursor.fetchall():
                    short_path, long_path, match_ratio, start_frame, confidence, subseq_id = row
                    # Check if files still exist
                    if os.path.exists(short_path) and os.path.exists(long_path):
                        subsequences.append((short_path, long_path, match_ratio,
                                           start_frame, confidence, subseq_id))

                return subsequences

        except Exception as e:
            logger.error(f"Error retrieving pending subsequences: {e}")
            return []

    def update_subsequence_status(self, short_video_path=None, long_video_path=None, status=None, action=None, subseq_id=None):
        """Update the status of a subsequence detection.

        Args:
            short_video_path: Path to short video (used to find ID if subseq_id not provided)
            long_video_path: Path to long video (used to find ID if subseq_id not provided)
            status: New status
            action: Action taken (optional)
            subseq_id: Subsequence detection ID (if known, overrides path lookup)

        Returns:
            bool: True if successful
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # If ID not provided, find it using video paths
                if subseq_id is None:
                    if short_video_path is None or long_video_path is None:
                        logger.error("Must provide either subseq_id or both video paths")
                        return False

                    # OPTIMIZED: Get both file IDs in a single query (ISSUE #26 fix)
                    cursor.execute('''
                        SELECT
                            (SELECT id FROM video_files WHERE file_path = ?) as short_id,
                            (SELECT id FROM video_files WHERE file_path = ?) as long_id
                    ''', (short_video_path, long_video_path))
                    result = cursor.fetchone()
                    if not result or not result[0] or not result[1]:
                        if not result or not result[0]:
                            logger.error(f"Short video not found in database: {short_video_path}")
                        if not result or not result[1]:
                            logger.error(f"Long video not found in database: {long_video_path}")
                        return False
                    short_id, long_id = result

                    # Find subsequence ID
                    cursor.execute('''
                        SELECT id FROM video_subsequences
                        WHERE short_video_id = ? AND long_video_id = ?
                        ORDER BY detected_at DESC LIMIT 1
                    ''', (short_id, long_id))
                    result = cursor.fetchone()
                    if not result:
                        logger.error(f"Subsequence not found: {os.path.basename(short_video_path)} in {os.path.basename(long_video_path)}")
                        return False
                    subseq_id = result[0]

                # Update status
                cursor.execute('''
                    UPDATE video_subsequences
                    SET status = ?, action_taken = ?, processed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, action, subseq_id))

                conn.commit()
                return True

        except Exception as e:
            logger.error(f"Error updating subsequence status: {e}")
            return False

    def get_subsequence_statistics(self):
        """Get statistics about subsequence detections.

        Returns:
            dict: Statistics about detected subsequences
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                        SUM(CASE WHEN status = 'processed' THEN 1 ELSE 0 END) as processed,
                        AVG(match_ratio) as avg_match_ratio,
                        AVG(confidence) as avg_confidence
                    FROM video_subsequences
                ''')

                result = cursor.fetchone()
                if result:
                    return {
                        'total': result[0] or 0,
                        'pending': result[1] or 0,
                        'processed': result[2] or 0,
                        'avg_match_ratio': result[3] or 0.0,
                        'avg_confidence': result[4] or 0.0
                    }

        except Exception as e:
            logger.error(f"Error retrieving subsequence stats: {e}")

        return {
            'total': 0,
            'pending': 0,
            'processed': 0,
            'avg_match_ratio': 0.0,
            'avg_confidence': 0.0
        }

    # ═══════════════════════════════════════════════════════════
    # VERIFICATION CACHE METHODS (Strategy 3)
    # ═══════════════════════════════════════════════════════════

    def store_verification_result(self, short_video_path, long_video_path, start_time,
                                  duration, sequence_score, verification_result):
        """
        Store verification result in cache with file metadata.

        Args:
            short_video_path: Path to short video
            long_video_path: Path to long video
            start_time: Start time in long video (seconds)
            duration: Duration of match (seconds)
            sequence_score: Sequence match score (0-100)
            verification_result: Dict with verification results
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Get video IDs and metadata
                short_id = self._get_or_create_video_id(short_video_path, cursor)
                long_id = self._get_or_create_video_id(long_video_path, cursor)

                # Get file metadata for cache invalidation
                short_stat = os.stat(short_video_path)
                long_stat = os.stat(long_video_path)

                # Store verification result
                cursor.execute('''
                    INSERT OR REPLACE INTO verification_cache (
                        short_video_id, long_video_id,
                        short_mtime, long_mtime,
                        short_size, long_size,
                        start_time, duration, sequence_score,
                        config_hash, num_samples, warmup_seconds, execution_time,
                        accepted, scene_cuts_score, dct_score, rejection_reason
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    short_id, long_id,
                    short_stat.st_mtime, long_stat.st_mtime,
                    short_stat.st_size, long_stat.st_size,
                    start_time, duration, sequence_score,
                    verification_result.get('config_hash'),
                    verification_result.get('num_samples'),
                    verification_result.get('warmup_seconds'),
                    verification_result.get('execution_time'),
                    verification_result['accepted'],
                    verification_result['scene_cuts_score'],
                    verification_result['dct_score'],
                    verification_result.get('rejection_reason')
                ))

                conn.commit()
                logger.debug(f"Verification result cached: {os.path.basename(short_video_path)} @ {start_time:.1f}s")

        except Exception as e:
            logger.error(f"Error storing verification result: {e}")

    def get_cached_verification(self, short_video_path, long_video_path, start_time, tolerance=0.5, config_hash: str = None):
        """
        Get cached verification result if files haven't changed.

        Args:
            short_video_path: Path to short video
            long_video_path: Path to long video
            start_time: Start time in long video (seconds)
            tolerance: Time tolerance for matching (default: 0.5s)

        Returns:
            Dict with verification result or None if not cached/invalidated
        """
        try:
            # Check if files still exist
            if not os.path.exists(short_video_path) or not os.path.exists(long_video_path):
                return None

            # Get current file metadata
            short_stat = os.stat(short_video_path)
            long_stat = os.stat(long_video_path)

            with self.get_connection() as conn:
                cursor = conn.cursor()

                # OPTIMIZED: Get both video IDs in a single query (ISSUE #26 fix)
                cursor.execute('''
                    SELECT
                        (SELECT id FROM video_files WHERE file_path = ?) as short_id,
                        (SELECT id FROM video_files WHERE file_path = ?) as long_id
                ''', (short_video_path, long_video_path))
                result = cursor.fetchone()
                if not result or not result[0] or not result[1]:
                    return None
                short_id, long_id = result

                # Get cached result with time tolerance
                cursor.execute('''
                    SELECT
                        short_mtime, long_mtime,
                        short_size, long_size,
                        accepted, scene_cuts_score, dct_score,
                        rejection_reason, sequence_score,
                        config_hash, num_samples, warmup_seconds, execution_time
                    FROM verification_cache
                    WHERE short_video_id = ?
                      AND long_video_id = ?
                      AND ABS(start_time - ?) < ?
                    ORDER BY verification_date DESC
                    LIMIT 1
                ''', (short_id, long_id, start_time, tolerance))

                result = cursor.fetchone()
                if not result:
                    return None

                # Verify file hasn't changed (mtime + size)
                cached_short_mtime, cached_long_mtime = result[0], result[1]
                cached_short_size, cached_long_size = result[2], result[3]

                # Check if files modified (1 second tolerance for mtime)
                if (abs(short_stat.st_mtime - cached_short_mtime) > 1.0 or
                    short_stat.st_size != cached_short_size or
                    abs(long_stat.st_mtime - cached_long_mtime) > 1.0 or
                    long_stat.st_size != cached_long_size):
                    logger.debug(f"Cache invalidated: files modified")
                    return None

                # Invalidate if config hash provided and mismatching
                cached_config_hash = result[9]
                if config_hash and cached_config_hash and cached_config_hash != config_hash:
                    logger.debug("Cache invalidated: config hash changed")
                    return None

                # Return cached result
                return {
                    'accepted': bool(result[4]),
                    'scene_cuts_score': result[5],
                    'dct_score': result[6],
                    'rejection_reason': result[7],
                    'sequence_score': result[8],
                    'config_hash': cached_config_hash,
                    'num_samples': result[10],
                    'warmup_seconds': result[11],
                    'execution_time': result[12],
                    'from_cache': True
                }

        except Exception as e:
            logger.error(f"Error retrieving cached verification: {e}")
            return None

    def get_verification_statistics(self):
        """Get statistics about verification cache.

        Returns:
            dict: Statistics about cached verifications
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN accepted = 1 THEN 1 ELSE 0 END) as accepted,
                        SUM(CASE WHEN accepted = 0 THEN 1 ELSE 0 END) as rejected,
                        AVG(scene_cuts_score) as avg_scene_cuts,
                        AVG(dct_score) as avg_dct,
                        AVG(sequence_score) as avg_sequence
                    FROM verification_cache
                ''')

                result = cursor.fetchone()
                if result:
                    return {
                        'total': result[0] or 0,
                        'accepted': result[1] or 0,
                        'rejected': result[2] or 0,
                        'avg_scene_cuts': result[3] or 0.0,
                        'avg_dct': result[4] or 0.0,
                        'avg_sequence': result[5] or 0.0
                    }

        except Exception as e:
            logger.error(f"Error retrieving verification stats: {e}")

        return {
            'total': 0,
            'accepted': 0,
            'rejected': 0,
            'avg_scene_cuts': 0.0,
            'avg_dct': 0.0,
            'avg_sequence': 0.0
        }

    # ═══════════════════════════════════════════════════════════
    # PIPELINE/METHOD CONFIGS & RUNS (for benchmarks/debug)
    # ═══════════════════════════════════════════════════════════

    def upsert_pipeline_config(self, config_hash: str, mode: str, config_json: str) -> int:
        """Insert or get pipeline_config id."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM pipeline_configs WHERE config_hash = ?",
                (config_hash,)
            )
            row = cursor.fetchone()
            if row:
                return row[0]

            cursor.execute(
                "INSERT INTO pipeline_configs (config_hash, mode, config_json) VALUES (?, ?, ?)",
                (config_hash, mode, config_json)
            )
            conn.commit()
            return cursor.lastrowid

    def upsert_method_config(self, method_name: str, params_hash: str, params_json: str) -> int:
        """Insert or get method_config id."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM method_configs WHERE method_name = ? AND params_hash = ?",
                (method_name, params_hash)
            )
            row = cursor.fetchone()
            if row:
                return row[0]

            cursor.execute(
                "INSERT INTO method_configs (method_name, params_hash, params_json) VALUES (?, ?, ?)",
                (method_name, params_hash, params_json)
            )
            conn.commit()
            return cursor.lastrowid

    def store_verification_run(self, pipeline_config_id: int, short_video_path: str, long_video_path: str,
                               start_time: float, duration: float, sequence_score: float,
                               accepted: bool, total_time: float, run_label: str = None,
                               debug_flag: bool = False) -> int:
        """Store a verification run (for benchmarks/debug)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            short_id = self._get_or_create_video_id(short_video_path, cursor)
            long_id = self._get_or_create_video_id(long_video_path, cursor)

            cursor.execute(
                '''INSERT INTO verification_runs (
                    pipeline_config_id, short_video_id, long_video_id,
                    start_time, duration, sequence_score,
                    accepted, total_time, run_label, debug_flag
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (
                    pipeline_config_id, short_id, long_id,
                    start_time, duration, sequence_score,
                    accepted, total_time, run_label, int(debug_flag)
                )
            )
            conn.commit()
            return cursor.lastrowid

    def store_verification_method_result(self, run_id: int, method_name: str, accepted: bool,
                                         primary_score: float, threshold: float,
                                         execution_time: float = None, extra_json: str = None,
                                         method_config_id: int = None):
        """Store a per-method result for a run."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO verification_method_results (
                    run_id, method_config_id, method_name, accepted,
                    primary_score, threshold, execution_time, extra_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                (
                    run_id, method_config_id, method_name, int(accepted),
                    primary_score, threshold, execution_time, extra_json
                )
            )
            conn.commit()

    def upsert_debug_label(self, short_video_path: str, long_video_path: str, label: str, notes: str = None):
        """Store or update a debug label (oracle)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            short_id = self._get_or_create_video_id(short_video_path, cursor)
            long_id = self._get_or_create_video_id(long_video_path, cursor)
            cursor.execute(
                '''INSERT OR REPLACE INTO debug_labels (short_video_id, long_video_id, label, notes)
                   VALUES (?, ?, ?, ?)''',
                (short_id, long_id, label, notes)
            )
            conn.commit()

    def upsert_video_hash(self, video_path: str, method_name: str, params_hash: str,
                          params_json: str, hash_blob: bytes):
        """Store reusable video hash for a given algo/param combo."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            video_id = self._get_or_create_video_id(video_path, cursor)
            stat = os.stat(video_path)
            cursor.execute(
                '''INSERT OR REPLACE INTO video_hashes (
                    video_id, method_name, params_hash, params_json, hash_blob,
                    modification_time, file_size
                ) VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (
                    video_id, method_name, params_hash, params_json, hash_blob,
                    stat.st_mtime, stat.st_size
                )
            )
            conn.commit()

    def get_video_hash(self, video_path: str, method_name: str, params_hash: str):
        """Retrieve cached hash if file unchanged."""
        if not os.path.exists(video_path):
            return None
        stat = os.stat(video_path)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT hash_blob, modification_time, file_size
                   FROM video_hashes
                   WHERE method_name = ? AND params_hash = ?
                     AND video_id = (SELECT id FROM video_files WHERE file_path = ?)''',
                (method_name, params_hash, video_path)
            )
            row = cursor.fetchone()
            if not row:
                return None
            if abs(row[1] - stat.st_mtime) > 1.0 or row[2] != stat.st_size:
                return None
            return row[0]

    def clear_verification_cache(self):
        """Clear all verification cache entries."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM verification_cache')
                conn.commit()
                logger.info("Verification cache cleared")
        except Exception as e:
            logger.error(f"Error clearing verification cache: {e}")

    # ═══════════════════════════════════════════════════════════
    # ADVANCED 3-LEVEL MODE METHODS
    # ═══════════════════════════════════════════════════════════

    def store_lsh_fingerprint(self, file_path, fingerprint, signature_bands, n_bands, n_rows):
        """
        Store LSH fingerprint for a video (Level 1).

        Args:
            file_path: Path to the video file
            fingerprint: LSH fingerprint (numpy array or serialized)
            signature_bands: JSON string of LSH bands
            n_bands: Number of bands used
            n_rows: Number of rows per band

        Returns:
            bool: True if successful
        """
        try:
            from src.core.serialization import serialize_numpy_to_json

            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Get video ID
                cursor.execute('SELECT id FROM video_files WHERE file_path = ?', (file_path,))
                result = cursor.fetchone()
                if not result:
                    logger.warning(f"Video not found in database: {file_path}")
                    return False

                video_id = result[0]

                # Serialize fingerprint
                fingerprint_json = serialize_numpy_to_json(fingerprint)
                fingerprint_blob = fingerprint_json.encode('utf-8')

                cursor.execute('''
                    INSERT OR REPLACE INTO lsh_fingerprints
                    (video_id, fingerprint, signature_bands, n_bands, n_rows, computed_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (video_id, fingerprint_blob, signature_bands, n_bands, n_rows))

                conn.commit()
                logger.debug(f"LSH fingerprint stored for {os.path.basename(file_path)}")
                return True

        except Exception as e:
            logger.error(f"Error storing LSH fingerprint: {e}")
            return False

    def get_lsh_fingerprint(self, file_path):
        """
        Retrieve LSH fingerprint for a video.

        Args:
            file_path: Path to the video file

        Returns:
            dict: {'fingerprint', 'bands', 'n_bands', 'n_rows'} or None
        """
        try:
            from src.core.serialization import deserialize_numpy_from_json

            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT lsh.fingerprint, lsh.signature_bands, lsh.n_bands, lsh.n_rows
                    FROM lsh_fingerprints lsh
                    JOIN video_files v ON lsh.video_id = v.id
                    WHERE v.file_path = ?
                ''', (file_path,))

                result = cursor.fetchone()
                if result:
                    fp_blob, bands_json, n_bands, n_rows = result
                    fingerprint = deserialize_numpy_from_json(fp_blob.decode('utf-8'))

                    return {
                        'fingerprint': fingerprint,
                        'bands': bands_json,
                        'n_bands': n_bands,
                        'n_rows': n_rows
                    }

        except Exception as e:
            logger.error(f"Error retrieving LSH fingerprint: {e}")

        return None

    def store_level2_result(self, file1_path, file2_path, similarity_score, window_duration, window_start=0.0):
        """
        Store Level 2 long-period audio comparison result.

        Args:
            file1_path: First video path
            file2_path: Second video path
            similarity_score: Similarity score (0.0-1.0)
            window_duration: Duration of analyzed window (seconds)
            window_start: Start time of window (seconds)

        Returns:
            bool: True if successful
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Get IDs
                cursor.execute('''
                    SELECT
                        (SELECT id FROM video_files WHERE file_path = ?) as id1,
                        (SELECT id FROM video_files WHERE file_path = ?) as id2
                ''', (file1_path, file2_path))

                result = cursor.fetchone()
                if not result or not result[0] or not result[1]:
                    return False

                file1_id, file2_id = result

                # Ensure order
                if file1_id > file2_id:
                    file1_id, file2_id = file2_id, file1_id

                # Create pair ID
                pair_id = f"{file1_id}_{file2_id}"

                cursor.execute('''
                    INSERT OR REPLACE INTO level2_long_audio
                    (pair_id, file1_id, file2_id, similarity_score, window_duration,
                     window_start, compared_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (pair_id, file1_id, file2_id, similarity_score, window_duration, window_start))

                conn.commit()
                logger.debug(f"Level 2 result stored: {similarity_score:.3f}")
                return True

        except Exception as e:
            logger.error(f"Error storing Level 2 result: {e}")
            return False

    def store_level3_result(self, file1_path, file2_path, phash_distance,
                           frames_compared, frames_similar, frame_indices=None):
        """
        Store Level 3 pHash visual comparison result.

        Args:
            file1_path: First video path
            file2_path: Second video path
            phash_distance: Average Hamming distance
            frames_compared: Number of frames compared
            frames_similar: Number of similar frames
            frame_indices: List of frame indices used (optional)

        Returns:
            bool: True if successful
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Get IDs
                cursor.execute('''
                    SELECT
                        (SELECT id FROM video_files WHERE file_path = ?) as id1,
                        (SELECT id FROM video_files WHERE file_path = ?) as id2
                ''', (file1_path, file2_path))

                result = cursor.fetchone()
                if not result or not result[0] or not result[1]:
                    return False

                file1_id, file2_id = result

                # Ensure order
                if file1_id > file2_id:
                    file1_id, file2_id = file2_id, file1_id

                # Create pair ID
                pair_id = f"{file1_id}_{file2_id}"

                # Calculate similarity rate
                similarity_rate = frames_similar / frames_compared if frames_compared > 0 else 0.0

                # Serialize frame indices
                frame_indices_json = json.dumps(frame_indices) if frame_indices else None

                cursor.execute('''
                    INSERT OR REPLACE INTO level3_phash
                    (pair_id, file1_id, file2_id, phash_distance, frames_compared,
                     frames_similar, similarity_rate, frame_indices, compared_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (pair_id, file1_id, file2_id, phash_distance, frames_compared,
                      frames_similar, similarity_rate, frame_indices_json))

                conn.commit()
                logger.debug(f"Level 3 result stored: {frames_similar}/{frames_compared} similar frames")
                return True

        except Exception as e:
            logger.error(f"Error storing Level 3 result: {e}")
            return False

    def store_advanced_duplicate(self, file1_path, file2_path, level1_score,
                                 level2_score, level3_score, confidence='high'):
        """
        Store a validated duplicate from 3-level analysis.

        Args:
            file1_path: First video path
            file2_path: Second video path
            level1_score: LSH similarity score
            level2_score: Long audio similarity score
            level3_score: pHash similarity rate
            confidence: Confidence level ('high', 'medium', 'low')

        Returns:
            bool: True if successful
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Get IDs
                cursor.execute('''
                    SELECT
                        (SELECT id FROM video_files WHERE file_path = ?) as id1,
                        (SELECT id FROM video_files WHERE file_path = ?) as id2
                ''', (file1_path, file2_path))

                result = cursor.fetchone()
                if not result or not result[0] or not result[1]:
                    return False

                file1_id, file2_id = result

                # Ensure order
                if file1_id > file2_id:
                    file1_id, file2_id = file2_id, file1_id

                # Create pair ID
                pair_id = f"{file1_id}_{file2_id}"

                cursor.execute('''
                    INSERT OR REPLACE INTO advanced_duplicates
                    (pair_id, file1_id, file2_id, level1_score, level2_score,
                     level3_score, confidence, status, validated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP)
                ''', (pair_id, file1_id, file2_id, level1_score, level2_score,
                      level3_score, confidence))

                conn.commit()
                logger.info(f"Advanced duplicate stored: {os.path.basename(file1_path)} <-> "
                           f"{os.path.basename(file2_path)} ({confidence})")
                return True

        except Exception as e:
            logger.error(f"Error storing advanced duplicate: {e}")
            return False

    def get_pending_advanced_duplicates(self, limit=1000, offset=0):
        """
        Get pending duplicates from advanced 3-level analysis.

        Args:
            limit: Maximum number to retrieve
            offset: Number to skip

        Returns:
            List of tuples: (file1_path, file2_path, l1_score, l2_score, l3_score, confidence, id)
        """
        try:
            duplicates = []

            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT v1.file_path, v2.file_path, ad.level1_score, ad.level2_score,
                           ad.level3_score, ad.confidence, ad.id
                    FROM advanced_duplicates ad
                    JOIN video_files v1 ON ad.file1_id = v1.id
                    JOIN video_files v2 ON ad.file2_id = v2.id
                    WHERE ad.status = 'pending'
                    ORDER BY ad.confidence DESC, ad.level3_score DESC, ad.validated_at DESC
                    LIMIT ? OFFSET ?
                ''', (limit, offset))

                for row in cursor.fetchall():
                    file1, file2, l1, l2, l3, conf, dup_id = row
                    if os.path.exists(file1) and os.path.exists(file2):
                        duplicates.append((file1, file2, l1, l2, l3, conf, dup_id))

                return duplicates

        except Exception as e:
            logger.error(f"Error retrieving advanced duplicates: {e}")
            return []

    def get_advanced_mode_statistics(self):
        """
        Get statistics about advanced 3-level mode analysis.

        Returns:
            dict: Statistics for each level and overall
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Level 1: LSH fingerprints
                cursor.execute('SELECT COUNT(*) FROM lsh_fingerprints')
                lsh_count = cursor.fetchone()[0]

                # Level 2: Long audio comparisons
                cursor.execute('SELECT COUNT(*), AVG(similarity_score) FROM level2_long_audio')
                result = cursor.fetchone()
                level2_count, level2_avg = result[0] or 0, result[1] or 0.0

                # Level 3: pHash comparisons
                cursor.execute('SELECT COUNT(*), AVG(similarity_rate) FROM level3_phash')
                result = cursor.fetchone()
                level3_count, level3_avg = result[0] or 0, result[1] or 0.0

                # Advanced duplicates
                cursor.execute('''
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                        SUM(CASE WHEN confidence = 'high' THEN 1 ELSE 0 END) as high_conf,
                        SUM(CASE WHEN confidence = 'medium' THEN 1 ELSE 0 END) as med_conf,
                        SUM(CASE WHEN confidence = 'low' THEN 1 ELSE 0 END) as low_conf
                    FROM advanced_duplicates
                ''')

                result = cursor.fetchone()
                total, pending, high, medium, low = result

                return {
                    'lsh_fingerprints': lsh_count or 0,
                    'level2_comparisons': level2_count,
                    'level2_avg_similarity': level2_avg,
                    'level3_comparisons': level3_count,
                    'level3_avg_similarity': level3_avg,
                    'total_duplicates': total or 0,
                    'pending_duplicates': pending or 0,
                    'high_confidence': high or 0,
                    'medium_confidence': medium or 0,
                    'low_confidence': low or 0
                }

        except Exception as e:
            logger.error(f"Error retrieving advanced mode stats: {e}")
            return {
                'lsh_fingerprints': 0,
                'level2_comparisons': 0,
                'level2_avg_similarity': 0.0,
                'level3_comparisons': 0,
                'level3_avg_similarity': 0.0,
                'total_duplicates': 0,
                'pending_duplicates': 0,
                'high_confidence': 0,
                'medium_confidence': 0,
                'low_confidence': 0
            }

    # ═══════════════════════════════════════════════════════════
    # DENSE HASH METHODS (for subsequence detection)
    # ═══════════════════════════════════════════════════════════

    def get_dense_hash(self, video_path: str, sample_interval: float):
        """
        Retrieve cached dense hash from database.

        Args:
            video_path: Path to video file
            sample_interval: Sample interval used (e.g., 0.75)

        Returns:
            Tuple (dense_hash_array, duration) if found and valid, else (None, None)
        """
        try:
            # Get current file metadata
            if not os.path.exists(video_path):
                return None, None

            current_mtime = os.path.getmtime(video_path)
            current_size = os.path.getsize(video_path)

            with self.connection_pool.get_connection() as conn:
                cursor = conn.cursor()

                # Get video_id
                cursor.execute('SELECT id FROM video_files WHERE file_path = ?', (video_path,))
                row = cursor.fetchone()

                if not row:
                    return None, None

                video_id = row[0]

                # Get dense hash with metadata check
                cursor.execute('''
                    SELECT dense_hash, duration, modification_time, file_size, sample_interval
                    FROM dense_hashes
                    WHERE video_id = ?
                ''', (video_id,))

                row = cursor.fetchone()

                if not row:
                    return None, None

                stored_hash_blob, duration, stored_mtime, stored_size, stored_interval = row

                # Validate: file not modified and same sample interval
                if (abs(stored_mtime - current_mtime) < 0.1 and
                    stored_size == current_size and
                    abs(stored_interval - sample_interval) < 0.01):

                    # Deserialize numpy array
                    dense_hash = pickle.loads(stored_hash_blob)
                    logger.debug(f"Dense hash cache HIT: {os.path.basename(video_path)}")
                    return dense_hash, duration
                else:
                    logger.debug(f"Dense hash cache INVALID (file modified or different interval): {os.path.basename(video_path)}")
                    return None, None

        except Exception as e:
            logger.error(f"Error retrieving dense hash: {e}")
            return None, None

    def store_dense_hash(self, video_path: str, dense_hash: np.ndarray, duration: float, sample_interval: float):
        """
        Store dense hash in database.

        Args:
            video_path: Path to video file
            dense_hash: Numpy array of frame hashes
            duration: Video duration in seconds
            sample_interval: Sample interval used (e.g., 0.75)
        """
        try:
            if not os.path.exists(video_path):
                logger.warning(f"Cannot store dense hash: file not found: {video_path}")
                return

            current_mtime = os.path.getmtime(video_path)
            current_size = os.path.getsize(video_path)
            num_frames = len(dense_hash)

            # Serialize numpy array
            hash_blob = pickle.dumps(dense_hash, protocol=pickle.HIGHEST_PROTOCOL)

            with self.connection_pool.get_connection() as conn:
                cursor = conn.cursor()

                # Ensure video_files entry exists
                cursor.execute('SELECT id FROM video_files WHERE file_path = ?', (video_path,))
                row = cursor.fetchone()

                if not row:
                    # Create video_files entry
                    cursor.execute('''
                        INSERT INTO video_files (file_path, file_name, file_size, modification_time, duration)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (video_path, os.path.basename(video_path), current_size, current_mtime, duration))
                    video_id = cursor.lastrowid
                else:
                    video_id = row[0]

                # Insert or replace dense hash
                cursor.execute('''
                    INSERT OR REPLACE INTO dense_hashes
                    (video_id, dense_hash, sample_interval, duration, num_frames, modification_time, file_size)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (video_id, hash_blob, sample_interval, duration, num_frames, current_mtime, current_size))

                conn.commit()
                logger.debug(f"Dense hash stored: {os.path.basename(video_path)} ({num_frames} frames)")

        except Exception as e:
            logger.error(f"Error storing dense hash: {e}")

    def clear_dense_hashes(self):
        """Clear all cached dense hashes from database."""
        try:
            with self.connection_pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM dense_hashes')
                conn.commit()
                count = cursor.rowcount
                logger.info(f"Cleared {count} dense hash(es) from database")
        except Exception as e:
            logger.error(f"Error clearing dense hashes: {e}")
