"""
Automatic Cache Cleaner

Provides automatic cache management with:
- LRU eviction when cache exceeds size limit
- Removal of orphaned cache entries (video files deleted)
- Detection and removal of corrupted cache files
- Configurable size limits and cleanup policies
"""

import os
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta

from src.core.logger import Logger
from .hash_cache_manager import HashCacheManager
# from .verification_result_cache import VerificationResultCache  # Removed with core/models.py

logger = Logger.get_logger('DuplicateFinder.CacheCleaner')


class CacheCleaner:
    """
    Automatic cache cleaner with intelligent cleanup policies.

    Features:
    - LRU eviction when cache exceeds max size
    - Orphaned entry detection (video files deleted)
    - Corrupted cache file detection
    - Configurable policies
    - Statistics and reporting
    """

    def __init__(
        self,
        max_hash_cache_mb: int = 2048,  # 2 GB default
        max_verification_cache_mb: int = 100,  # 100 MB default
        max_age_days: int = 90,  # 90 days default
    ):
        """
        Initialize cache cleaner.

        Args:
            max_hash_cache_mb: Maximum hash cache size in MB (default: 2GB)
            max_verification_cache_mb: Maximum verification cache size in MB (default: 100MB)
            max_age_days: Maximum age for cached entries in days (default: 90)
        """
        self.max_hash_cache_mb = max_hash_cache_mb
        self.max_verification_cache_mb = max_verification_cache_mb
        self.max_age_days = max_age_days

        self.hash_cache_manager = HashCacheManager()
        self.verification_cache = VerificationResultCache()

        logger.info(f"CacheCleaner initialized: hash_max={max_hash_cache_mb}MB, "
                   f"verification_max={max_verification_cache_mb}MB, max_age={max_age_days}days")

    def clean_all(self, dry_run: bool = False) -> Dict[str, any]:
        """
        Clean all caches with all policies.

        Args:
            dry_run: If True, only report what would be cleaned

        Returns:
            Dict with cleanup statistics
        """
        results = {
            'hash_cache': self.clean_hash_cache(dry_run=dry_run),
            'verification_cache': self.clean_verification_cache(dry_run=dry_run),
            'dry_run': dry_run,
        }

        # Summary
        total_removed = (
            results['hash_cache']['orphaned_removed'] +
            results['hash_cache']['corrupted_removed'] +
            results['hash_cache']['lru_evicted'] +
            results['verification_cache']['orphaned_removed'] +
            results['verification_cache']['corrupted_removed'] +
            results['verification_cache']['lru_evicted']
        )

        total_space_freed_mb = (
            results['hash_cache']['space_freed_mb'] +
            results['verification_cache']['space_freed_mb']
        )

        results['summary'] = {
            'total_removed': total_removed,
            'total_space_freed_mb': total_space_freed_mb,
        }

        logger.info(f"Cache cleanup completed: {total_removed} files removed, "
                   f"{total_space_freed_mb:.2f}MB freed (dry_run={dry_run})")

        return results

    def clean_hash_cache(self, dry_run: bool = False) -> Dict[str, any]:
        """
        Clean hash cache.

        Args:
            dry_run: If True, only report what would be cleaned

        Returns:
            Dict with cleanup statistics
        """
        logger.info("Starting hash cache cleanup...")

        stats = {
            'orphaned_removed': 0,
            'corrupted_removed': 0,
            'lru_evicted': 0,
            'space_freed_mb': 0.0,
        }

        cache_files = list(self.hash_cache_manager.cache_dir.glob("*.pkl"))

        # 1. Remove orphaned entries (video files deleted)
        orphaned = self._find_orphaned_hash_entries(cache_files)
        for cache_file in orphaned:
            size_mb = cache_file.stat().st_size / 1024 / 1024
            logger.debug(f"Orphaned cache file: {cache_file.name} ({size_mb:.2f}MB)")

            if not dry_run:
                try:
                    cache_file.unlink()
                    stats['orphaned_removed'] += 1
                    stats['space_freed_mb'] += size_mb
                except Exception as e:
                    logger.error(f"Failed to remove orphaned cache file {cache_file}: {e}")

        # 2. Remove corrupted cache files
        corrupted = self._find_corrupted_cache_files(cache_files)
        for cache_file in corrupted:
            size_mb = cache_file.stat().st_size / 1024 / 1024
            logger.debug(f"Corrupted cache file: {cache_file.name} ({size_mb:.2f}MB)")

            if not dry_run:
                try:
                    cache_file.unlink()
                    stats['corrupted_removed'] += 1
                    stats['space_freed_mb'] += size_mb
                except Exception as e:
                    logger.error(f"Failed to remove corrupted cache file {cache_file}: {e}")

        # 3. LRU eviction if cache exceeds max size
        current_size_mb = self._get_cache_size_mb(self.hash_cache_manager.cache_dir)
        if current_size_mb > self.max_hash_cache_mb:
            logger.info(f"Hash cache exceeds max size ({current_size_mb:.2f}MB > {self.max_hash_cache_mb}MB)")

            # Get all cache files sorted by access time (LRU first)
            remaining_files = [f for f in cache_files if f.exists() and f not in orphaned and f not in corrupted]
            remaining_files.sort(key=lambda f: f.stat().st_atime)

            # Remove oldest files until under limit
            for cache_file in remaining_files:
                if current_size_mb <= self.max_hash_cache_mb:
                    break

                size_mb = cache_file.stat().st_size / 1024 / 1024
                logger.debug(f"LRU evicting: {cache_file.name} ({size_mb:.2f}MB)")

                if not dry_run:
                    try:
                        cache_file.unlink()
                        stats['lru_evicted'] += 1
                        stats['space_freed_mb'] += size_mb
                        current_size_mb -= size_mb
                    except Exception as e:
                        logger.error(f"Failed to evict cache file {cache_file}: {e}")

        logger.info(f"Hash cache cleanup: orphaned={stats['orphaned_removed']}, "
                   f"corrupted={stats['corrupted_removed']}, lru_evicted={stats['lru_evicted']}, "
                   f"space_freed={stats['space_freed_mb']:.2f}MB")

        return stats

    def clean_verification_cache(self, dry_run: bool = False) -> Dict[str, any]:
        """
        Clean verification cache.

        Args:
            dry_run: If True, only report what would be cleaned

        Returns:
            Dict with cleanup statistics
        """
        logger.info("Starting verification cache cleanup...")

        stats = {
            'orphaned_removed': 0,
            'corrupted_removed': 0,
            'lru_evicted': 0,
            'space_freed_mb': 0.0,
        }

        cache_files = list(self.verification_cache.cache_dir.glob("*.pkl"))

        # 1. Remove corrupted cache files
        corrupted = self._find_corrupted_cache_files(cache_files)
        for cache_file in corrupted:
            size_mb = cache_file.stat().st_size / 1024 / 1024
            logger.debug(f"Corrupted cache file: {cache_file.name} ({size_mb:.2f}MB)")

            if not dry_run:
                try:
                    cache_file.unlink()
                    stats['corrupted_removed'] += 1
                    stats['space_freed_mb'] += size_mb
                except Exception as e:
                    logger.error(f"Failed to remove corrupted cache file {cache_file}: {e}")

        # 2. LRU eviction if cache exceeds max size
        current_size_mb = self._get_cache_size_mb(self.verification_cache.cache_dir)
        if current_size_mb > self.max_verification_cache_mb:
            logger.info(f"Verification cache exceeds max size ({current_size_mb:.2f}MB > {self.max_verification_cache_mb}MB)")

            # Get all cache files sorted by access time (LRU first)
            remaining_files = [f for f in cache_files if f.exists() and f not in corrupted]
            remaining_files.sort(key=lambda f: f.stat().st_atime)

            # Remove oldest files until under limit
            for cache_file in remaining_files:
                if current_size_mb <= self.max_verification_cache_mb:
                    break

                size_mb = cache_file.stat().st_size / 1024 / 1024
                logger.debug(f"LRU evicting: {cache_file.name} ({size_mb:.2f}MB)")

                if not dry_run:
                    try:
                        cache_file.unlink()
                        stats['lru_evicted'] += 1
                        stats['space_freed_mb'] += size_mb
                        current_size_mb -= size_mb
                    except Exception as e:
                        logger.error(f"Failed to evict cache file {cache_file}: {e}")

        logger.info(f"Verification cache cleanup: corrupted={stats['corrupted_removed']}, "
                   f"lru_evicted={stats['lru_evicted']}, space_freed={stats['space_freed_mb']:.2f}MB")

        return stats

    def _find_orphaned_hash_entries(self, cache_files: List[Path]) -> List[Path]:
        """
        Find orphaned hash cache entries (video files deleted).

        Args:
            cache_files: List of cache files to check

        Returns:
            List of orphaned cache files
        """
        orphaned = []

        for cache_file in cache_files:
            try:
                # Load cache entry to get video path
                import pickle
                with open(cache_file, 'rb') as f:
                    cache_entry = pickle.load(f)

                video_path = cache_entry.get('video_path')
                if video_path and not Path(video_path).exists():
                    orphaned.append(cache_file)
            except Exception as e:
                logger.debug(f"Failed to check orphaned status for {cache_file}: {e}")
                # Will be caught by corrupted detection

        return orphaned

    def _find_corrupted_cache_files(self, cache_files: List[Path]) -> List[Path]:
        """
        Find corrupted cache files.

        Args:
            cache_files: List of cache files to check

        Returns:
            List of corrupted cache files
        """
        corrupted = []

        for cache_file in cache_files:
            try:
                # Try to load cache entry
                import pickle
                with open(cache_file, 'rb') as f:
                    cache_entry = pickle.load(f)

                # Validate required fields
                if 'hash' not in cache_entry or 'duration' not in cache_entry:
                    corrupted.append(cache_file)
            except Exception:
                # Failed to load = corrupted
                corrupted.append(cache_file)

        return corrupted

    def _get_cache_size_mb(self, cache_dir: Path) -> float:
        """
        Get total cache size in MB.

        Args:
            cache_dir: Cache directory

        Returns:
            Total size in MB
        """
        total_bytes = sum(f.stat().st_size for f in cache_dir.glob("*.pkl") if f.is_file())
        return total_bytes / 1024 / 1024

    def get_cleanup_report(self) -> Dict[str, any]:
        """
        Get cleanup report without actually cleaning.

        Returns:
            Dict with cleanup recommendations
        """
        report = {
            'hash_cache': self._analyze_hash_cache(),
            'verification_cache': self._analyze_verification_cache(),
        }

        return report

    def _analyze_hash_cache(self) -> Dict[str, any]:
        """Analyze hash cache and provide recommendations."""
        cache_files = list(self.hash_cache_manager.cache_dir.glob("*.pkl"))
        current_size_mb = self._get_cache_size_mb(self.hash_cache_manager.cache_dir)

        orphaned = self._find_orphaned_hash_entries(cache_files)
        corrupted = self._find_corrupted_cache_files(cache_files)

        return {
            'total_files': len(cache_files),
            'total_size_mb': current_size_mb,
            'max_size_mb': self.max_hash_cache_mb,
            'over_limit': current_size_mb > self.max_hash_cache_mb,
            'orphaned_count': len(orphaned),
            'corrupted_count': len(corrupted),
            'recommendations': self._get_recommendations(current_size_mb, self.max_hash_cache_mb, len(orphaned), len(corrupted)),
        }

    def _analyze_verification_cache(self) -> Dict[str, any]:
        """Analyze verification cache and provide recommendations."""
        cache_files = list(self.verification_cache.cache_dir.glob("*.pkl"))
        current_size_mb = self._get_cache_size_mb(self.verification_cache.cache_dir)

        corrupted = self._find_corrupted_cache_files(cache_files)

        return {
            'total_files': len(cache_files),
            'total_size_mb': current_size_mb,
            'max_size_mb': self.max_verification_cache_mb,
            'over_limit': current_size_mb > self.max_verification_cache_mb,
            'corrupted_count': len(corrupted),
            'recommendations': self._get_recommendations(current_size_mb, self.max_verification_cache_mb, 0, len(corrupted)),
        }

    def _get_recommendations(self, current_size: float, max_size: float, orphaned: int, corrupted: int) -> List[str]:
        """Get cleanup recommendations."""
        recommendations = []

        if corrupted > 0:
            recommendations.append(f"Remove {corrupted} corrupted cache files")

        if orphaned > 0:
            recommendations.append(f"Remove {orphaned} orphaned cache entries")

        if current_size > max_size:
            over_mb = current_size - max_size
            recommendations.append(f"Evict {over_mb:.2f}MB using LRU policy (cache over limit)")

        if not recommendations:
            recommendations.append("No cleanup needed - cache is healthy")

        return recommendations
