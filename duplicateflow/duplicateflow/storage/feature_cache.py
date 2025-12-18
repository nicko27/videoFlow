"""
Feature caching for algorithm extraction.

This module provides persistent caching of extracted features (fingerprints, histograms, etc.)
using SQLite. Features are keyed by (file_hash, algorithm, params_hash).
"""

import sqlite3
import json
import pickle
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime


class FeatureCache:
    """
    Persistent cache for algorithm feature extraction.

    Stores extracted features in SQLite database to avoid recomputing expensive
    extractions. Features are keyed by file hash, algorithm name, and parameter hash.

    Example:
        >>> cache = FeatureCache("~/.duplicateflow/features.db")
        >>>
        >>> # Store features
        >>> cache.store(
        ...     file_hash="abc123",
        ...     algorithm="audio_fingerprint",
        ...     params={'sr': 11025, 'n_fft': 4096},
        ...     features={'hashes': {123: [1, 2, 3]}, 'num_hashes': 150}
        ... )
        >>>
        >>> # Retrieve features
        >>> features = cache.get(
        ...     file_hash="abc123",
        ...     algorithm="audio_fingerprint",
        ...     params={'sr': 11025, 'n_fft': 4096}
        ... )
        >>> print(features['num_hashes'])
        150
    """

    def __init__(self, db_path: str = "~/.duplicateflow/features.db"):
        """
        Initialize feature cache.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

        # In-memory cache for hot features
        self._memory_cache: Dict[str, Any] = {}
        self._max_memory_items = 100  # Features are larger than results

    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Create features table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS features (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_hash TEXT NOT NULL,
                    algorithm TEXT NOT NULL,
                    params_hash TEXT NOT NULL,
                    features BLOB NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(file_hash, algorithm, params_hash)
                )
            ''')

            # Create indices for performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_file_hash
                ON features(file_hash)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_algorithm
                ON features(algorithm)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_file_algo
                ON features(file_hash, algorithm)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_created
                ON features(created_at)
            ''')

            conn.commit()

    def _compute_params_hash(self, params: Dict[str, Any]) -> str:
        """
        Compute hash of parameters for cache key.

        Args:
            params: Algorithm parameters

        Returns:
            MD5 hash of sorted parameters
        """
        # Sort keys for consistent hashing
        params_str = json.dumps(params, sort_keys=True)
        return hashlib.md5(params_str.encode()).hexdigest()

    def _make_cache_key(
        self,
        file_hash: str,
        algorithm: str,
        params_hash: str
    ) -> str:
        """Create memory cache key."""
        return f"{file_hash}:{algorithm}:{params_hash}"

    def store(
        self,
        file_hash: str,
        algorithm: str,
        params: Dict[str, Any],
        features: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Store extracted features in cache.

        Args:
            file_hash: MD5 hash of file
            algorithm: Algorithm name
            params: Algorithm parameters used for extraction
            features: Extracted features (will be pickled)
            metadata: Optional metadata (e.g., extraction time, num features)
        """
        params_hash = self._compute_params_hash(params)
        cache_key = self._make_cache_key(file_hash, algorithm, params_hash)

        # Serialize features
        features_blob = pickle.dumps(features)

        # Serialize metadata
        metadata_json = json.dumps(metadata) if metadata else None

        # Store in database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO features
                (file_hash, algorithm, params_hash, features, metadata)
                VALUES (?, ?, ?, ?, ?)
            ''', (file_hash, algorithm, params_hash, features_blob, metadata_json))

            conn.commit()

        # Update memory cache
        if len(self._memory_cache) < self._max_memory_items:
            self._memory_cache[cache_key] = features

    def get(
        self,
        file_hash: str,
        algorithm: str,
        params: Dict[str, Any]
    ) -> Optional[Any]:
        """
        Retrieve features from cache.

        Args:
            file_hash: MD5 hash of file
            algorithm: Algorithm name
            params: Algorithm parameters

        Returns:
            Cached features or None if not found
        """
        params_hash = self._compute_params_hash(params)
        cache_key = self._make_cache_key(file_hash, algorithm, params_hash)

        # Check memory cache first
        if cache_key in self._memory_cache:
            return self._memory_cache[cache_key]

        # Check database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT features FROM features
                WHERE file_hash = ? AND algorithm = ? AND params_hash = ?
            ''', (file_hash, algorithm, params_hash))

            row = cursor.fetchone()

            if row:
                features_blob = row[0]
                features = pickle.loads(features_blob)

                # Update memory cache
                if len(self._memory_cache) < self._max_memory_items:
                    self._memory_cache[cache_key] = features

                return features

        return None

    def has(
        self,
        file_hash: str,
        algorithm: str,
        params: Dict[str, Any]
    ) -> bool:
        """
        Check if features are cached.

        Args:
            file_hash: MD5 hash of file
            algorithm: Algorithm name
            params: Algorithm parameters

        Returns:
            True if cached, False otherwise
        """
        params_hash = self._compute_params_hash(params)
        cache_key = self._make_cache_key(file_hash, algorithm, params_hash)

        # Check memory cache
        if cache_key in self._memory_cache:
            return True

        # Check database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT 1 FROM features
                WHERE file_hash = ? AND algorithm = ? AND params_hash = ?
            ''', (file_hash, algorithm, params_hash))

            return cursor.fetchone() is not None

    def delete_for_file(self, file_hash: str) -> int:
        """
        Delete all cached features for a file.

        Args:
            file_hash: MD5 hash of file

        Returns:
            Number of entries deleted
        """
        # Clear from memory cache
        keys_to_remove = [k for k in self._memory_cache.keys() if k.startswith(file_hash + ":")]
        for key in keys_to_remove:
            del self._memory_cache[key]

        # Delete from database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('DELETE FROM features WHERE file_hash = ?', (file_hash,))
            deleted = cursor.rowcount

            conn.commit()

        return deleted

    def clear(self) -> int:
        """
        Clear entire cache.

        Returns:
            Number of entries deleted
        """
        self._memory_cache.clear()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('SELECT COUNT(*) FROM features')
            count = cursor.fetchone()[0]

            cursor.execute('DELETE FROM features')
            conn.commit()

        return count

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Total entries
            cursor.execute('SELECT COUNT(*) FROM features')
            total = cursor.fetchone()[0]

            # Entries by algorithm
            cursor.execute('''
                SELECT algorithm, COUNT(*) FROM features
                GROUP BY algorithm
            ''')
            by_algorithm = dict(cursor.fetchall())

            # Database size
            cursor.execute('SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()')
            db_size = cursor.fetchone()[0]

        return {
            'total_entries': total,
            'by_algorithm': by_algorithm,
            'memory_cache_size': len(self._memory_cache),
            'db_size_bytes': db_size,
            'db_size_mb': db_size / (1024 * 1024)
        }
