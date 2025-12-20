"""
Pipeline storage for saving and loading custom pipeline configurations.

This module extends the existing preset system by allowing users to save
custom pipeline configurations (including validators) to a SQLite database.
"""

import sqlite3
import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime


class PipelineStore:
    """
    Persistent storage for custom pipeline configurations.

    Allows saving, loading, and managing custom pipelines including
    validators and analysis parameters. Complements the hard-coded
    presets in pipeline/presets.py.

    Example:
        >>> store = PipelineStore()
        >>>
        >>> # Save a custom pipeline
        >>> store.save(
        ...     name="my_fast_duplicate",
        ...     config={
        ...         'steps': [...],
        ...         'pre_validators': [...],
        ...         'analyze_duration': 60.0
        ...     },
        ...     description="My custom fast duplicate detector"
        ... )
        >>>
        >>> # Load it back
        >>> config = store.load("my_fast_duplicate")
        >>> pipeline = Pipeline(**config)
    """

    def __init__(self, db_path: str = "~/.duplicateflow/pipelines.db"):
        """
        Initialize pipeline store.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Pipelines table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pipelines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    category TEXT DEFAULT 'custom',

                    -- Full configuration as JSON
                    config_json TEXT NOT NULL,
                    config_hash TEXT NOT NULL,

                    -- Metadata
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used_at TIMESTAMP,
                    usage_count INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')

            # Indices
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_name
                ON pipelines(name)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_category
                ON pipelines(category)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_hash
                ON pipelines(config_hash)
            ''')

            conn.commit()

    def _compute_hash(self, config: Dict[str, Any]) -> str:
        """Compute hash of configuration for deduplication."""
        config_str = json.dumps(config, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]

    def save(
        self,
        name: str,
        config: Dict[str, Any],
        description: str = "",
        category: str = "custom",
        overwrite: bool = False
    ) -> int:
        """
        Save a pipeline configuration.

        Args:
            name: Unique pipeline name
            config: Full pipeline configuration (steps, validators, etc.)
            description: Human-readable description
            category: Category (custom, duplicates, scenes, etc.)
            overwrite: If True, update existing pipeline with same name

        Returns:
            Pipeline ID

        Raises:
            ValueError: If name exists and overwrite=False

        Example:
            >>> from duplicateflow.sdk import LengthValidator
            >>> config = {
            ...     'steps': [
            ...         {'algorithm': 'frame_hash', 'weight': 0.6, 'threshold': 80},
            ...         {'algorithm': 'color_histogram', 'weight': 0.4, 'threshold': 75}
            ...     ],
            ...     'global_threshold': 75.0,
            ...     'pre_validators': [
            ...         {
            ...             'type': 'LengthValidator',
            ...             'config': {
            ...                 'tolerance_percent': 5.0,
            ...                 'tolerance_seconds': 30.0,
            ...                 'require_both': False
            ...             }
            ...         }
            ...     ],
            ...     'analyze_duration': 60.0,
            ...     'analyze_from_start': True
            ... }
            >>> store.save("fast_duplicates", config, "Fast duplicate detection")
        """
        config_json = json.dumps(config)
        config_hash = self._compute_hash(config)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if overwrite:
                # Update existing
                cursor.execute('''
                    INSERT OR REPLACE INTO pipelines (
                        name, description, category, config_json, config_hash, updated_at
                    ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (name, description, category, config_json, config_hash))
            else:
                # Insert new (will fail if name exists)
                try:
                    cursor.execute('''
                        INSERT INTO pipelines (
                            name, description, category, config_json, config_hash
                        ) VALUES (?, ?, ?, ?, ?)
                    ''', (name, description, category, config_json, config_hash))
                except sqlite3.IntegrityError:
                    raise ValueError(f"Pipeline '{name}' already exists. Use overwrite=True to update.")

            conn.commit()

            # Get the ID
            cursor.execute('SELECT id FROM pipelines WHERE name = ?', (name,))
            return cursor.fetchone()[0]

    def load(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Load a pipeline configuration by name.

        Args:
            name: Pipeline name

        Returns:
            Configuration dictionary or None if not found

        Example:
            >>> config = store.load("fast_duplicates")
            >>> if config:
            ...     pipeline = Pipeline(**config)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT config_json FROM pipelines
                WHERE name = ? AND is_active = 1
            ''', (name,))

            row = cursor.fetchone()
            if not row:
                return None

            # Update usage stats
            cursor.execute('''
                UPDATE pipelines
                SET usage_count = usage_count + 1,
                    last_used_at = CURRENT_TIMESTAMP
                WHERE name = ?
            ''', (name,))

            conn.commit()

            return json.loads(row[0])

    def list(
        self,
        category: Optional[str] = None,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        List available pipelines.

        Args:
            category: Filter by category (None = all)
            active_only: Only return active pipelines

        Returns:
            List of pipeline info (without full config)

        Example:
            >>> pipelines = store.list(category="duplicates")
            >>> for p in pipelines:
            ...     print(f"{p['name']}: {p['description']}")
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = '''
                SELECT id, name, description, category,
                       created_at, updated_at, last_used_at, usage_count
                FROM pipelines
            '''

            conditions = []
            params = []

            if active_only:
                conditions.append('is_active = 1')

            if category:
                conditions.append('category = ?')
                params.append(category)

            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)

            query += ' ORDER BY usage_count DESC, name'

            cursor.execute(query, params)

            return [dict(row) for row in cursor.fetchall()]

    def delete(self, name: str, soft: bool = True):
        """
        Delete a pipeline.

        Args:
            name: Pipeline name
            soft: If True, mark as inactive. If False, permanently delete.

        Example:
            >>> store.delete("old_pipeline")  # Soft delete
            >>> store.delete("bad_pipeline", soft=False)  # Hard delete
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if soft:
                cursor.execute('''
                    UPDATE pipelines SET is_active = 0
                    WHERE name = ?
                ''', (name,))
            else:
                cursor.execute('''
                    DELETE FROM pipelines WHERE name = ?
                ''', (name,))

            conn.commit()

    def get_stats(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get usage statistics for a pipeline.

        Args:
            name: Pipeline name

        Returns:
            Statistics dictionary or None

        Example:
            >>> stats = store.get_stats("fast_duplicates")
            >>> print(f"Used {stats['usage_count']} times")
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT name, category, description,
                       usage_count, created_at, updated_at, last_used_at
                FROM pipelines
                WHERE name = ? AND is_active = 1
            ''', (name,))

            row = cursor.fetchone()
            if not row:
                return None

            return dict(row)

    def export_preset(self, name: str, output_path: str):
        """
        Export a pipeline as a preset file.

        Args:
            name: Pipeline name
            output_path: Path to save preset file

        Example:
            >>> store.export_preset("my_pipeline", "presets/my_preset.json")
        """
        config = self.load(name)
        if not config:
            raise ValueError(f"Pipeline '{name}' not found")

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        with open(output, 'w') as f:
            json.dump(config, f, indent=2)

    def import_preset(self, preset_path: str, name: Optional[str] = None):
        """
        Import a pipeline from a preset file.

        Args:
            preset_path: Path to preset JSON file
            name: Pipeline name (defaults to filename)

        Example:
            >>> store.import_preset("presets/custom.json")
        """
        with open(preset_path, 'r') as f:
            config = json.load(f)

        if name is None:
            name = Path(preset_path).stem

        self.save(name, config)
