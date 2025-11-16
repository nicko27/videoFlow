import sqlite3
import os
import json
import pickle
import hashlib
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

    def __init__(self, db_path: str, pool_size: int = 5):
        """
        Initialize the connection pool.

        Args:
            db_path: Path to SQLite database
            pool_size: Maximum number of connections (default: 5)
        """
        self.db_path = db_path
        self.pool_size = pool_size
        self.pool = Queue(maxsize=pool_size)
        self.lock = Lock()
        self._closed = False

        # Create initial connections
        for _ in range(pool_size):
            conn = self._create_connection()
            self.pool.put(conn)

        logger.debug(f"Connection pool created with {pool_size} connections")

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
                    except:
                        pass
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
        self._ignore_type_exists = False  # Flag for ignore_type column (set after migration)

        # Create connection pool (5 connections)
        self.connection_pool = ConnectionPool(db_path, pool_size=5)

        self._ensure_database_exists()
        logger.info(f"Database initialized with connection pool: {self.db_path}")
    
    def _ensure_database_exists(self):
        """S'asone que la base de données et ses tables existent - UNE SEULE FOIS"""
        if self._initialized:
            return
            
        try:
            # Crée le répertoire parent si nécessaire
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
            
            # Initialise la structure
            self.init_database()
            self._initialized = True
            
            # Marque toutes les tables comme existantes
            self._tables_exist = {
                'video_files': True,
                'comparisons': True,
                'ignored_pairs': True,
                'corrupted_files': True,
                'found_duplicates': True,
                'video_subsequences': True
            }
                
        except Exception as e:
            logger.error(f"Error during l'initialization of the DB: {e}")
            raise
    
    def init_database(self):
        """Initialise la structure of the base de données - AVEC MIGRATION CORRIGÉE"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Active les optimisations SQLite
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA cache_size=10000")
                cursor.execute("PRAGMA temp_store=MEMORY")
                cursor.execute("PRAGMA foreign_keys=ON")
                
                # ÉTAPE 1: Crée les tables de base SANS ignore_type
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
                
                # ÉTAPE 2: Crée la table ignored_pairs SANS ignore_type d'abord
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

                # STEP 3: Check and add ignore_type column if necessary (migration)
                cursor.execute("PRAGMA table_info(ignored_pairs)")
                columns = [column[1] for column in cursor.fetchall()]

                if 'ignore_type' not in columns:
                    logger.info("Adding ignore_type column to ignored_pairs table")
                    cursor.execute("ALTER TABLE ignored_pairs ADD COLUMN ignore_type TEXT DEFAULT 'permanent'")

                    # Update existing entries
                    cursor.execute("UPDATE ignored_pairs SET ignore_type = 'permanent' WHERE ignore_type IS NULL")

                    logger.info("Database migration completed")

                # After migration, ignore_type column ALWAYS exists
                self._ignore_type_exists = True
                
                # ÉTAPE 4: Crée les index
                index_commands = [
                    "CREATE INDEX IF NOT EXISTS idx_file_path ON video_files(file_path)",
                    "CREATE INDEX IF NOT EXISTS idx_file_size ON video_files(file_size)",
                    "CREATE INDEX IF NOT EXISTS idx_duration ON video_files(duration)",
                    "CREATE INDEX IF NOT EXISTS idx_modification_time ON video_files(modification_time)",
                    "CREATE INDEX IF NOT EXISTS idx_comparison_files ON comparisons(file1_id, file2_id)",
                    "CREATE INDEX IF NOT EXISTS idx_similarity ON comparisons(similarity)",
                    "CREATE INDEX IF NOT EXISTS idx_corrupted_path ON corrupted_files(file_path)",
                    "CREATE INDEX IF NOT EXISTS idx_duplicates_status ON found_duplicates(status)",
                    "CREATE INDEX IF NOT EXISTS idx_duplicates_files ON found_duplicates(file1_id, file2_id)",
                    "CREATE INDEX IF NOT EXISTS idx_ignored_pairs ON ignored_pairs(file1_id, file2_id)",
                    "CREATE INDEX IF NOT EXISTS idx_ignored_type ON ignored_pairs(ignore_type)",
                    "CREATE INDEX IF NOT EXISTS idx_subsequences_status ON video_subsequences(status)",
                    "CREATE INDEX IF NOT EXISTS idx_subsequences_files ON video_subsequences(short_video_id, long_video_id)",
                    "CREATE INDEX IF NOT EXISTS idx_subsequences_confidence ON video_subsequences(confidence)"
                ]
                
                for cmd in index_commands:
                    cursor.execute(cmd)
                
                conn.commit()
                logger.debug("Structure de base de données créée/vérifiée with migration")
                
        except Exception as e:
            logger.error(f"Error during l'initialization of the base de données: {e}")
            raise
    
    def _table_exists(self, table_name):
        """Checks si une table existe - AVEC CACHE"""
        # Utilise le cache en first
        if table_name in self._tables_exist:
            return self._tables_exist[table_name]
            
        # Sinon vérifie une seule fois
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
        """Checks si un file a été modifié - OPTIMISÉ"""
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
                    return True  # File pas en base
                
                stored_mtime, stored_size = result
                
                # Checks si modifié (tolérance de 1 seconde pour les systèmes de files)
                return (abs(current_mtime - stored_mtime) > 1.0 or 
                       current_size != stored_size)
                
        except Exception as e:
            logger.error(f"Error vérification modification {file_path}: {e}")
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
    
    def get_cached_comparison(self, file1_path, file2_path):
        """Récupère un résultat de comparison - OPTIMISÉ"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Requête optimisée with index
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
            logger.error(f"Error récupération comparison: {e}")
            
        return None
    
    def store_comparison(self, file1_path, file2_path, similarity, 
                        comparison_method="optimized", is_early_exit=False, computation_time=0.0):
        """Stocke un résultat de comparison - OPTIMISÉ with batch"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Récupère les IDs en une seule requête
                cursor.execute('''
                    SELECT 
                        (SELECT id FROM video_files WHERE file_path = ?) as id1,
                        (SELECT id FROM video_files WHERE file_path = ?) as id2
                ''', (file1_path, file2_path))
                
                result = cursor.fetchone()
                if not result or not result[0] or not result[1]:
                    return False
                
                file1_id, file2_id = result
                
                # Asone l'ordre pour éviter les doublons
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
            logger.error(f"Error stockage comparison: {e}")
            return False
    
    def is_pair_ignored(self, file1_path, file2_path):
        """Checks si une paire est ignorée - CORRIGÉ with ignore_type"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # CORRECTION: Checks seulement les paires ignorées DÉFINITIVEMENT
                # Utilise COALESCE pour gérer les anciennes entrées sans ignore_type
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
            logger.error(f"Error vérification paire ignorée: {e}")
            
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
                
                # Size of the base
                db_size = os.path.getsize(self.db_path) / 1024 if os.path.exists(self.db_path) else 0
                
                # Calcul du time économisé (estimé à 2s par comparison)
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
            logger.error(f"Error récupération statistics: {e}")
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
        """Nettoie la base des files qui n'existent plus"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Récupère tous les files
                cursor.execute('SELECT id, file_path FROM video_files')
                files = cursor.fetchall()
                
                missing_ids = []
                for file_id, file_path in files:
                    if not os.path.exists(file_path):
                        missing_ids.append(file_id)
                
                if missing_ids:
                    # Removes en une seule transaction
                    placeholders = ','.join('?' * len(missing_ids))
                    
                    # Removes les comparaisons
                    cursor.execute(f'''
                        DELETE FROM comparisons 
                        WHERE file1_id IN ({placeholders}) OR file2_id IN ({placeholders})
                    ''', missing_ids + missing_ids)
                    
                    # Removes les paires ignorées
                    cursor.execute(f'''
                        DELETE FROM ignored_pairs 
                        WHERE file1_id IN ({placeholders}) OR file2_id IN ({placeholders})
                    ''', missing_ids + missing_ids)
                    
                    # Removes les doublons found
                    cursor.execute(f'''
                        DELETE FROM found_duplicates 
                        WHERE file1_id IN ({placeholders}) OR file2_id IN ({placeholders})
                    ''', missing_ids + missing_ids)
                    
                    # Removes les files
                    cursor.execute(f'DELETE FROM video_files WHERE id IN ({placeholders})', missing_ids)
                    
                    conn.commit()
                    logger.info(f"Nettoyage base: {len(missing_ids)} files supprimés")
                    
                return len(missing_ids)
                
        except Exception as e:
            logger.error(f"Error nettoyage base: {e}")
            return 0
    
    def auto_cleanup_on_access(self):
        """Nettoie automatiquement lors des accès si nécessaire"""
        # Nettoie seulement une fois par session
        if not hasattr(self, '_cleaned_this_session'):
            self._cleaned_this_session = True
            removed = self.cleanup_missing_files()
            if removed > 0:
                logger.info(f"Nettoyage automatique: {removed} files manquants supprimés")
    
    def clear_all_data(self):
        """Vide complètement la base de données"""
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
                logger.info("Base de données vidée et compactée")
                return True

        except Exception as e:
            logger.error(f"Error vidage base: {e}")
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
            logger.error(f"Error marquage file corrompu: {e}")

    def get_files_needing_analysis(self, file_paths):
        """Returns les files qui ont besoin d'être analysés - OPTIMISÉ"""
        if not file_paths:
            return []
            
        files_to_analyze = []
        
        # Batch check pour performance
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Récupère tous les files existants en une requête
            placeholders = ','.join('?' * len(file_paths))
            cursor.execute(f'''
                SELECT file_path, modification_time, file_size 
                FROM video_files 
                WHERE file_path IN ({placeholders})
            ''', file_paths)
            
            existing_files = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}
        
        # Checks chaque file
        for file_path in file_paths:
            if not os.path.exists(file_path):
                continue
                
            if file_path not in existing_files:
                files_to_analyze.append(file_path)
            else:
                # Checks si modifié
                current_mtime = os.path.getmtime(file_path)
                current_size = os.path.getsize(file_path)
                stored_mtime, stored_size = existing_files[file_path]
                
                if abs(current_mtime - stored_mtime) > 1.0 or current_size != stored_size:
                    files_to_analyze.append(file_path)
        
        return files_to_analyze
    
    def store_found_duplicate(self, file1_path, file2_path, similarity):
        """Stocke un doublon found pour récupération ultérieure"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Récupère les IDs
                cursor.execute('''
                    SELECT 
                        (SELECT id FROM video_files WHERE file_path = ?) as id1,
                        (SELECT id FROM video_files WHERE file_path = ?) as id2
                ''', (file1_path, file2_path))
                
                result = cursor.fetchone()
                if not result or not result[0] or not result[1]:
                    return False
                
                file1_id, file2_id = result
                
                # Asone l'ordre
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
            logger.error(f"Error stockage doublon found: {e}")
            return False
    
    def get_pending_duplicates(self):
        """Récupère les doublons pending de processing"""
        try:
            duplicates = []
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT v1.file_path, v2.file_path, d.similarity, d.id
                    FROM found_duplicates d
                    JOIN video_files v1 ON d.file1_id = v1.id
                    JOIN video_files v2 ON d.file2_id = v2.id
                    WHERE d.status = 'pending'
                    ORDER BY d.similarity DESC, d.detected_at DESC
                ''')
                
                for row in cursor.fetchall():
                    file1, file2, similarity, dup_id = row
                    # Checks si les files existent encore
                    if os.path.exists(file1) and os.path.exists(file2):
                        duplicates.append((file1, file2, similarity, dup_id))
                
                return duplicates
                
        except Exception as e:
            logger.error(f"Error récupération doublons pending: {e}")
            return []
    
    def update_duplicate_status(self, dup_id, status, action=None):
        """Met à jour le statut d'un doublon"""
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
            logger.error(f"Error mise à jour statut doublon: {e}")
            return False
    
    def clear_processed_duplicates(self):
        """Removes les doublons déjà traités"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    DELETE FROM found_duplicates 
                    WHERE status != 'pending'
                ''')
                
                deleted = cursor.rowcount
                conn.commit()
                
                logger.info(f"Suppression de {deleted} doublons traités")
                return deleted
                
        except Exception as e:
            logger.error(f"Error suppression doublons traités: {e}")
            return 0
    
    def get_duplicate_statistics(self):
        """Récupère les statistics des doublons"""
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
            logger.error(f"Error récupération stats doublons: {e}")
            
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
        """Efface toutes les paires ignorées temporairement"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Checks si ignore_type existe
                cursor.execute("PRAGMA table_info(ignored_pairs)")
                columns = [column[1] for column in cursor.fetchall()]
                
                if 'ignore_type' in columns:
                    cursor.execute('''
                        DELETE FROM ignored_pairs 
                        WHERE ignore_type = 'temporary'
                    ''')
                else:
                    # Si pas de colonne ignore_type, ne fait rien (toutes sont permanentes)
                    return 0
                
                deleted = cursor.rowcount
                conn.commit()
                
                if deleted > 0:
                    logger.info(f"Suppression de {deleted} paires ignorées temporairement")
                
                return deleted
                
        except Exception as e:
            logger.error(f"Error suppression ignores temporaires: {e}")
            return 0
    
    def get_ignored_pairs_details(self):
        """Récupère les details des paires ignorées"""
        try:
            ignored_pairs = []
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Checks si ignore_type existe
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
            logger.error(f"Error récupération details paires ignorées: {e}")
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
                    logger.info(f"Table {table_name} recréée with success")
                    return True
                    
        except Exception as e:
            logger.error(f"Error recréation table {table_name}: {e}")
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
                    logger.warning(f"Problème d'intégrité détecté: {integrity_result[0]}")
                    return False
                
                # Checks que toutes les tables existent
                required_tables = ['video_files', 'comparisons', 'ignored_pairs', 'corrupted_files', 'found_duplicates', 'video_subsequences']
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                existing_tables = [row[0] for row in cursor.fetchall()]
                
                missing_tables = [table for table in required_tables if table not in existing_tables]
                if missing_tables:
                    logger.warning(f"Tables manquantes: {missing_tables}")
                    return False
                
                # Checks la structure de ignored_pairs
                cursor.execute("PRAGMA table_info(ignored_pairs)")
                columns = [column[1] for column in cursor.fetchall()]
                
                if 'ignore_type' not in columns:
                    logger.info("Colonne ignore_type manquante - migration nécessaire")
                    return False
                
                logger.info("Intégrité of the base de données vérifiée with success")
                return True
                
        except Exception as e:
            logger.error(f"Error vérification intégrité: {e}")
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
                        except:
                            info['pragma_settings'][pragma] = 'error'

            return info

        except Exception as e:
            logger.error(f"Error récupération infos DB: {e}")
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

    def get_pending_subsequences(self):
        """Get all pending subsequence detections.

        Returns:
            List of tuples: (short_path, long_path, match_ratio, start_frame, confidence, id)
        """
        try:
            subsequences = []

            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT v1.file_path, v2.file_path, s.match_ratio,
                           s.start_frame_idx, s.confidence, s.id
                    FROM video_subsequences s
                    JOIN video_files v1 ON s.short_video_id = v1.id
                    JOIN video_files v2 ON s.long_video_id = v2.id
                    WHERE s.status = 'pending'
                    ORDER BY s.confidence DESC, s.detected_at DESC
                ''')

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

    def update_subsequence_status(self, subseq_id, status, action=None):
        """Update the status of a subsequence detection.

        Args:
            subseq_id: Subsequence detection ID
            status: New status
            action: Action taken (optional)

        Returns:
            bool: True if successful
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

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