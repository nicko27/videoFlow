"""
Filter Manager for Duplicate Finder plugin.

Manages smart filters for duplicate results with multiple criteria.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any, Callable
from pathlib import Path
import re
import json

from src.core.logger import Logger

logger = Logger.get_logger(__name__)


@dataclass
class FilterCriteria:
    """Filter criteria for duplicate results."""

    # Similarity filters
    min_similarity: float = 0.0  # 0-100
    max_similarity: float = 100.0  # 0-100

    # Size filters
    min_size_diff: Optional[int] = None  # bytes
    max_size_diff: Optional[int] = None  # bytes
    size_diff_percent: Optional[float] = None  # percentage

    # Duration filters
    min_duration_diff: Optional[float] = None  # seconds
    max_duration_diff: Optional[float] = None  # seconds
    duration_diff_percent: Optional[float] = None  # percentage

    # Path filters
    path_pattern: Optional[str] = None  # regex pattern
    exclude_pattern: Optional[str] = None  # regex pattern
    case_sensitive: bool = False

    # General filters
    enabled: bool = True
    name: str = "Unnamed Filter"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FilterCriteria':
        """Create from dictionary."""
        return cls(**data)


class FilterManager:
    """
    Manages smart filters for duplicate results.

    Provides methods to:
    - Apply filters to duplicate pairs
    - Save/load filter presets
    - Validate filter criteria
    """

    def __init__(self):
        self.current_filter = FilterCriteria()
        self.presets: Dict[str, FilterCriteria] = {}
        self._load_presets()

        logger.info("FilterManager initialized")

    def apply_filter(
        self,
        duplicates: List[Dict[str, Any]],
        criteria: Optional[FilterCriteria] = None
    ) -> List[Dict[str, Any]]:
        """
        Apply filter criteria to duplicate pairs.

        Args:
            duplicates: List of duplicate pairs with metadata
            criteria: Filter criteria to apply (uses current_filter if None)

        Returns:
            Filtered list of duplicates
        """
        if criteria is None:
            criteria = self.current_filter

        if not criteria.enabled:
            return duplicates

        filtered = []
        for dup in duplicates:
            if self._matches_criteria(dup, criteria):
                filtered.append(dup)

        logger.debug(f"Filtered {len(duplicates)} duplicates -> {len(filtered)} matches")
        return filtered

    def _matches_criteria(self, duplicate: Dict[str, Any], criteria: FilterCriteria) -> bool:
        """
        Check if duplicate pair matches filter criteria.

        Args:
            duplicate: Duplicate pair dict with keys: similarity, file1_path, file2_path,
                      file1_size, file2_size, file1_duration, file2_duration
            criteria: Filter criteria

        Returns:
            True if matches all criteria
        """
        # Similarity filter
        similarity = duplicate.get('similarity', 0)
        if not (criteria.min_similarity <= similarity <= criteria.max_similarity):
            return False

        # Size difference filter
        if criteria.min_size_diff is not None or criteria.max_size_diff is not None:
            size1 = duplicate.get('file1_size', 0)
            size2 = duplicate.get('file2_size', 0)
            size_diff = abs(size1 - size2)

            if criteria.min_size_diff is not None and size_diff < criteria.min_size_diff:
                return False
            if criteria.max_size_diff is not None and size_diff > criteria.max_size_diff:
                return False

        # Size difference percentage filter
        if criteria.size_diff_percent is not None:
            size1 = duplicate.get('file1_size', 0)
            size2 = duplicate.get('file2_size', 0)
            if size1 > 0 and size2 > 0:
                max_size = max(size1, size2)
                diff_percent = (abs(size1 - size2) / max_size) * 100
                if diff_percent > criteria.size_diff_percent:
                    return False

        # Duration difference filter
        if criteria.min_duration_diff is not None or criteria.max_duration_diff is not None:
            dur1 = duplicate.get('file1_duration', 0)
            dur2 = duplicate.get('file2_duration', 0)
            dur_diff = abs(dur1 - dur2)

            if criteria.min_duration_diff is not None and dur_diff < criteria.min_duration_diff:
                return False
            if criteria.max_duration_diff is not None and dur_diff > criteria.max_duration_diff:
                return False

        # Duration difference percentage filter
        if criteria.duration_diff_percent is not None:
            dur1 = duplicate.get('file1_duration', 0)
            dur2 = duplicate.get('file2_duration', 0)
            if dur1 > 0 and dur2 > 0:
                max_dur = max(dur1, dur2)
                diff_percent = (abs(dur1 - dur2) / max_dur) * 100
                if diff_percent > criteria.duration_diff_percent:
                    return False

        # Path pattern filters
        path1 = duplicate.get('file1_path', '')
        path2 = duplicate.get('file2_path', '')

        if criteria.path_pattern:
            flags = 0 if criteria.case_sensitive else re.IGNORECASE
            try:
                pattern = re.compile(criteria.path_pattern, flags)
                if not (pattern.search(path1) or pattern.search(path2)):
                    return False
            except re.error as e:
                logger.warning(f"Invalid regex pattern '{criteria.path_pattern}': {e}")

        if criteria.exclude_pattern:
            flags = 0 if criteria.case_sensitive else re.IGNORECASE
            try:
                pattern = re.compile(criteria.exclude_pattern, flags)
                if pattern.search(path1) or pattern.search(path2):
                    return False
            except re.error as e:
                logger.warning(f"Invalid exclude pattern '{criteria.exclude_pattern}': {e}")

        return True

    def set_current_filter(self, criteria: FilterCriteria):
        """Set the current filter criteria."""
        self.current_filter = criteria
        logger.info(f"Current filter set: {criteria.name}")

    def reset_filter(self):
        """Reset to default (no filtering)."""
        self.current_filter = FilterCriteria()
        logger.info("Filter reset to default")

    def save_preset(self, name: str, criteria: Optional[FilterCriteria] = None):
        """
        Save filter preset.

        Args:
            name: Preset name
            criteria: Filter criteria (uses current_filter if None)
        """
        if criteria is None:
            criteria = self.current_filter

        criteria.name = name
        self.presets[name] = criteria
        self._save_presets()
        logger.info(f"Saved filter preset: {name}")

    def load_preset(self, name: str) -> Optional[FilterCriteria]:
        """
        Load filter preset.

        Args:
            name: Preset name

        Returns:
            Filter criteria or None if not found
        """
        if name in self.presets:
            criteria = self.presets[name]
            self.current_filter = criteria
            logger.info(f"Loaded filter preset: {name}")
            return criteria

        logger.warning(f"Preset not found: {name}")
        return None

    def delete_preset(self, name: str) -> bool:
        """
        Delete filter preset.

        Args:
            name: Preset name

        Returns:
            True if deleted, False if not found
        """
        if name in self.presets:
            del self.presets[name]
            self._save_presets()
            logger.info(f"Deleted filter preset: {name}")
            return True

        logger.warning(f"Cannot delete preset (not found): {name}")
        return False

    def get_preset_names(self) -> List[str]:
        """Get list of preset names."""
        return list(self.presets.keys())

    def _get_presets_path(self) -> Path:
        """Get path to presets file."""
        return Path(__file__).parent.parent / "filter_presets.json"

    def _save_presets(self):
        """Save presets to file."""
        try:
            presets_data = {
                name: criteria.to_dict()
                for name, criteria in self.presets.items()
            }

            path = self._get_presets_path()
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(presets_data, f, indent=2)

            logger.debug(f"Saved {len(self.presets)} filter presets to {path}")
        except Exception as e:
            logger.error(f"Failed to save filter presets: {e}")

    def _load_presets(self):
        """Load presets from file."""
        try:
            path = self._get_presets_path()
            if not path.exists():
                self._create_default_presets()
                return

            with open(path, 'r', encoding='utf-8') as f:
                presets_data = json.load(f)

            self.presets = {
                name: FilterCriteria.from_dict(data)
                for name, data in presets_data.items()
            }

            logger.debug(f"Loaded {len(self.presets)} filter presets from {path}")
        except Exception as e:
            logger.error(f"Failed to load filter presets: {e}")
            self._create_default_presets()

    def _create_default_presets(self):
        """Create default filter presets."""
        # High similarity only
        self.presets["High Similarity (>90%)"] = FilterCriteria(
            name="High Similarity (>90%)",
            min_similarity=90.0,
            max_similarity=100.0
        )

        # Exact duplicates
        self.presets["Exact Duplicates"] = FilterCriteria(
            name="Exact Duplicates",
            min_similarity=99.5,
            max_similarity=100.0,
            max_size_diff=0,
            max_duration_diff=0.1
        )

        # Similar size
        self.presets["Similar Size (<10% diff)"] = FilterCriteria(
            name="Similar Size (<10% diff)",
            min_similarity=80.0,
            size_diff_percent=10.0
        )

        # Different size (transcoded)
        self.presets["Different Size (>20% diff)"] = FilterCriteria(
            name="Different Size (>20% diff)",
            min_similarity=85.0,
            size_diff_percent=20.0
        )

        self._save_presets()
        logger.info(f"Created {len(self.presets)} default filter presets")


# Singleton instance
_filter_manager_instance = None


def get_filter_manager() -> FilterManager:
    """Get singleton FilterManager instance."""
    global _filter_manager_instance
    if _filter_manager_instance is None:
        _filter_manager_instance = FilterManager()
    return _filter_manager_instance
