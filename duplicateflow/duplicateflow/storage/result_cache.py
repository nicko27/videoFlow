"""
Result caching for algorithm comparisons.

This module provides persistent caching of algorithm results using SQLite.
Results are keyed by (file1_hash, file2_hash, algorithm, params_hash).
"""

import sqlite3
import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime


class ResultCache:
    """
    Persistent cache for algorithm comparison results.

    Stores results in SQLite database to avoid recomputing expensive
    algorithm comparisons. Results are keyed by file hashes, algorithm
    name, and parameter hash.

    Example:
        >>> cache = ResultCache("~/.duplicateflow/results.db")
        >>>
        >>> # Store result
        >>> cache.store(
        ...     file1_hash="abc123",
        ...     file2_hash="def456",
        ...     algorithm="color_histogram",
        ...     params={'threshold': 70.0},
        ...     result={'similarity': 0.85, 'accepted': True}
        ... )
        >>>
        >>> # Retrieve result
        >>> result = cache.get(
        ...     file1_hash="abc123",
        ...     file2_hash="def456",
        ...     algorithm="color_histogram",
        ...     params={'threshold': 70.0}
        ... )
        >>> print(result['similarity'])
        0.85
    """

    def __init__(self, db_path: str = "~/.duplicateflow/results.db"):
        """
        Initialize result cache.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

        # In-memory cache for hot results
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._max_memory_items = 500

    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Create results table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file1_hash TEXT NOT NULL,
                    file2_hash TEXT NOT NULL,
                    algorithm TEXT NOT NULL,
                    params_hash TEXT NOT NULL,
                    similarity REAL NOT NULL,
                    accepted BOOLEAN NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(file1_hash, file2_hash, algorithm, params_hash)
                )
            ''')

            # Create indices for performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_files
                ON results(file1_hash, file2_hash)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_algorithm
                ON results(algorithm)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_created
                ON results(created_at)
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
        file1_hash: str,
        file2_hash: str,
        algorithm: str,
        params_hash: str
    ) -> str:
        """Create memory cache key."""
        # Ensure consistent ordering
        if file1_hash > file2_hash:
            file1_hash, file2_hash = file2_hash, file1_hash

        return f"{file1_hash}:{file2_hash}:{algorithm}:{params_hash}"

    def store(
        self,
        file1_hash: str,
        file2_hash: str,
        algorithm: str,
        params: Dict[str, Any],
        result: Dict[str, Any]
    ) -> None:
        """
        Store algorithm result in cache.

        Args:
            file1_hash: MD5 hash of first file
            file2_hash: MD5 hash of second file
            algorithm: Algorithm name
            params: Algorithm parameters
            result: Result dictionary with 'similarity', 'accepted', 'metadata'
        """
        # Ensure consistent ordering (file1 < file2)
        if file1_hash > file2_hash:
            file1_hash, file2_hash = file2_hash, file1_hash

        params_hash = self._compute_params_hash(params)

        # Extract result fields
        similarity = result.get('similarity', 0.0)
        accepted = result.get('accepted', False)

        # Convert metadata to JSON-serializable format (handle numpy types)
        metadata_dict = result.get('metadata', {})
        metadata = json.dumps(metadata_dict, default=lambda x: float(x) if hasattr(x, 'item') else str(x))

        # Store in database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO results
                (file1_hash, file2_hash, algorithm, params_hash,
                 similarity, accepted, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                file1_hash, file2_hash, algorithm, params_hash,
                similarity, accepted, metadata
            ))

            conn.commit()

        # Update memory cache
        cache_key = self._make_cache_key(
            file1_hash, file2_hash, algorithm, params_hash
        )
        self._memory_cache[cache_key] = result

        # Evict old entries if cache too large
        if len(self._memory_cache) > self._max_memory_items:
            # Remove oldest 20%
            num_to_remove = self._max_memory_items // 5
            keys_to_remove = list(self._memory_cache.keys())[:num_to_remove]
            for key in keys_to_remove:
                del self._memory_cache[key]

    def get(
        self,
        file1_hash: str,
        file2_hash: str,
        algorithm: str,
        params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached result.

        Args:
            file1_hash: MD5 hash of first file
            file2_hash: MD5 hash of second file
            algorithm: Algorithm name
            params: Algorithm parameters

        Returns:
            Result dictionary or None if not cached
        """
        # Ensure consistent ordering
        if file1_hash > file2_hash:
            file1_hash, file2_hash = file2_hash, file1_hash

        params_hash = self._compute_params_hash(params)

        # Check memory cache first
        cache_key = self._make_cache_key(
            file1_hash, file2_hash, algorithm, params_hash
        )

        if cache_key in self._memory_cache:
            return self._memory_cache[cache_key]

        # Query database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT similarity, accepted, metadata
                FROM results
                WHERE file1_hash = ? AND file2_hash = ?
                  AND algorithm = ? AND params_hash = ?
            ''', (file1_hash, file2_hash, algorithm, params_hash))

            row = cursor.fetchone()

        if row is None:
            return None

        # Reconstruct result
        similarity, accepted, metadata_json = row
        metadata = json.loads(metadata_json) if metadata_json else {}

        # Convert accepted to proper boolean (SQLite may return int or bytes)
        if isinstance(accepted, bytes):
            accepted = bool(int.from_bytes(accepted, byteorder='big'))
        elif isinstance(accepted, int):
            accepted = bool(accepted)

        result = {
            'similarity': float(similarity),
            'accepted': bool(accepted),
            'metadata': metadata
        }

        # Cache in memory
        self._memory_cache[cache_key] = result

        return result

    def clear_algorithm(self, algorithm: str) -> int:
        """
        Clear all results for a specific algorithm.

        Args:
            algorithm: Algorithm name

        Returns:
            Number of entries deleted
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                'DELETE FROM results WHERE algorithm = ?',
                (algorithm,)
            )

            deleted = cursor.rowcount
            conn.commit()

        # Clear from memory cache
        keys_to_remove = [
            k for k in self._memory_cache.keys()
            if f":{algorithm}:" in k
        ]
        for key in keys_to_remove:
            del self._memory_cache[key]

        return deleted

    def clear_older_than(self, days: int) -> int:
        """
        Clear results older than specified days.

        Args:
            days: Number of days

        Returns:
            Number of entries deleted
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                DELETE FROM results
                WHERE created_at < datetime('now', ?)
            ''', (f'-{days} days',))

            deleted = cursor.rowcount
            conn.commit()

        # Clear memory cache entirely (simpler than selective removal)
        self._memory_cache.clear()

        return deleted

    def clear_all(self) -> None:
        """Clear all cached results."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM results')
            conn.commit()

        self._memory_cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Total entries
            cursor.execute('SELECT COUNT(*) FROM results')
            total_entries = cursor.fetchone()[0]

            # By algorithm
            cursor.execute('''
                SELECT algorithm, COUNT(*) as count
                FROM results
                GROUP BY algorithm
                ORDER BY count DESC
            ''')
            by_algorithm = dict(cursor.fetchall())

            # Database size
            db_size_mb = self.db_path.stat().st_size / (1024 * 1024)

        return {
            'total_entries': total_entries,
            'by_algorithm': by_algorithm,
            'memory_cache_size': len(self._memory_cache),
            'database_size_mb': round(db_size_mb, 2)
        }

    def vacuum(self) -> None:
        """Optimize database (reclaim space after deletions)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('VACUUM')
