"""
Verification Result Cache Manager - File-Based Persistent Cache

This module provides a file-based cache system for VerificationResult instances.
It stores complete verification results with all method execution details,
solving the "TEMPS PAR MÉTHODE vide" problem.

Features:
- Persistent file cache (survives app restarts)
- Automatic cache invalidation on file modification
- Thread-safe operations
- Pickle serialization for complete data preservation

Usage:
    from src.plugins.duplicate_finder.processing.cache.verification_result_cache import VerificationResultCache
    from src.plugins.duplicate_finder.core.models import VerificationResult
    
    cache = VerificationResultCache()
    
    # Store result
    cache.store_result(
        file1='video1.mp4',
        file2='video2.mp4',
        result=verification_result  # VerificationResult instance
    )
    
    # Retrieve result
    cached = cache.get_result('video1.mp4', 'video2.mp4')
    if cached:
        print(f"Status: {cached.status}")
        print(f"Method stats: {cached.get_method_stats()}")
"""

import os
import pickle
import hashlib
import json
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from src.core.logger import Logger
from src.plugins.duplicate_finder.core.models import VerificationResult, VerificationStatus

logger = Logger.get_logger('DuplicateFinder.VerificationResultCache')


class VerificationResultCache:
    """
    File-based cache for verification results with automatic invalidation.
    
    Stores complete VerificationResult instances in pickle files, preserving
    all method execution details and statistics.
    """
    
    DEFAULT_CACHE_DIR = Path.home() / '.duplicate_finder' / 'cache' / 'verification_results'
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize verification result cache.
        
        Args:
            cache_dir: Optional custom cache directory (default: ~/.duplicate_finder/cache/verification_results)
        """
        self.cache_dir = cache_dir if cache_dir else self.DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"VerificationResultCache initialized: {self.cache_dir}")
    
    def _compute_cache_key(
        self,
        file1: str,
        file2: str,
        pipeline_config: Optional[str] = None
    ) -> str:
        """
        Compute unique cache key for a verification pair.
        
        Args:
            file1: Path to first video file
            file2: Path to second video file
            pipeline_config: Optional pipeline configuration hash
        
        Returns:
            Cache key (filename without extension)
        """
        # Use absolute paths for consistency
        file1_abs = str(Path(file1).resolve())
        file2_abs = str(Path(file2).resolve())
        
        # Create sorted tuple to ensure cache hits regardless of order
        file_tuple = tuple(sorted([file1_abs, file2_abs]))
        
        # Hash the file paths
        file_hash = hashlib.sha256(f"{file_tuple[0]}|{file_tuple[1]}".encode()).hexdigest()[:16]
        
        # Include pipeline config in key if provided
        if pipeline_config:
            config_hash = hashlib.sha1(pipeline_config.encode()).hexdigest()[:8]
            cache_key = f"verification_{file_hash}_{config_hash}"
        else:
            cache_key = f"verification_{file_hash}_default"
        
        return cache_key
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """Get full path to cache file."""
        return self.cache_dir / f"{cache_key}.pkl"
    
    def _get_file_metadata(self, file_path: str) -> Optional[Tuple[float, int]]:
        """
        Get file modification time and size for cache invalidation.
        
        Args:
            file_path: Path to file
        
        Returns:
            Tuple of (mtime, size) or None if file doesn't exist
        """
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                return None
            
            stat = file_path_obj.stat()
            return (stat.st_mtime, stat.st_size)
        except Exception as e:
            logger.warning(f"Error getting file metadata for {file_path}: {e}")
            return None
    
    def _is_cache_valid(
        self,
        cache_file: Path,
        file1: str,
        file2: str,
        stored_metadata: Dict[str, Any]
    ) -> bool:
        """
        Check if cached result is still valid.
        
        Args:
            cache_file: Path to cache file
            file1: Path to first video file
            file2: Path to second video file
            stored_metadata: Metadata stored with the cache
        
        Returns:
            True if cache is valid, False otherwise
        """
        # Check if cache file exists
        if not cache_file.exists():
            return False
        
        # Get current file metadata
        file1_meta = self._get_file_metadata(file1)
        file2_meta = self._get_file_metadata(file2)
        
        if not file1_meta or not file2_meta:
            logger.debug(f"Cache invalid: source files not found")
            return False
        
        # Compare with stored metadata
        file1_mtime, file1_size = file1_meta
        file2_mtime, file2_size = file2_meta
        
        # Check file1
        if (abs(file1_mtime - stored_metadata.get('file1_mtime', 0)) > 1.0 or
            file1_size != stored_metadata.get('file1_size', -1)):
            logger.debug(f"Cache invalid: {Path(file1).name} modified")
            return False
        
        # Check file2
        if (abs(file2_mtime - stored_metadata.get('file2_mtime', 0)) > 1.0 or
            file2_size != stored_metadata.get('file2_size', -1)):
            logger.debug(f"Cache invalid: {Path(file2).name} modified")
            return False
        
        return True
    
    def store_result(
        self,
        file1: str,
        file2: str,
        result: VerificationResult,
        pipeline_config: Optional[str] = None
    ) -> bool:
        """
        Store verification result in cache.
        
        Args:
            file1: Path to first video file
            file2: Path to second video file
            result: VerificationResult instance to cache
            pipeline_config: Optional pipeline configuration (for cache key)
        
        Returns:
            True if stored successfully, False otherwise
        """
        try:
            # Get file metadata for invalidation
            file1_meta = self._get_file_metadata(file1)
            file2_meta = self._get_file_metadata(file2)
            
            if not file1_meta or not file2_meta:
                logger.warning(f"Cannot cache: source files not found")
                return False
            
            # Create cache entry
            cache_entry = {
                'result': result,
                'file1_mtime': file1_meta[0],
                'file1_size': file1_meta[1],
                'file2_mtime': file2_meta[0],
                'file2_size': file2_meta[1],
                'cached_at': datetime.now().isoformat(),
                'pipeline_config': pipeline_config
            }
            
            # Compute cache key and path
            cache_key = self._compute_cache_key(file1, file2, pipeline_config)
            cache_path = self._get_cache_path(cache_key)
            
            # Write to cache file
            with open(cache_path, 'wb') as f:
                pickle.dump(cache_entry, f, protocol=pickle.HIGHEST_PROTOCOL)
            
            logger.debug(f"Verification result cached: {cache_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing verification result in cache: {e}")
            return False
    
    def get_result(
        self,
        file1: str,
        file2: str,
        pipeline_config: Optional[str] = None
    ) -> Optional[VerificationResult]:
        """
        Retrieve verification result from cache.
        
        Args:
            file1: Path to first video file
            file2: Path to second video file
            pipeline_config: Optional pipeline configuration (must match cached)
        
        Returns:
            VerificationResult instance or None if not cached/invalid
        """
        try:
            # Compute cache key
            cache_key = self._compute_cache_key(file1, file2, pipeline_config)
            cache_path = self._get_cache_path(cache_key)
            
            # Check if cache file exists
            if not cache_path.exists():
                return None
            
            # Load cache entry
            with open(cache_path, 'rb') as f:
                cache_entry = pickle.load(f)
            
            # Validate cache
            if not self._is_cache_valid(cache_path, file1, file2, cache_entry):
                # Cache invalidated - delete it
                cache_path.unlink()
                logger.debug(f"Cache invalidated and removed: {cache_key}")
                return None
            
            logger.debug(f"✓ Cache hit: {cache_key}")
            return cache_entry['result']
            
        except Exception as e:
            logger.warning(f"Error retrieving from cache: {e}")
            return None
    
    def clear_all(self) -> int:
        """
        Clear all cached verification results.
        
        Returns:
            Number of cache files deleted
        """
        try:
            count = 0
            for cache_file in self.cache_dir.glob("verification_*.pkl"):
                cache_file.unlink()
                count += 1
            
            logger.info(f"Cleared {count} verification result cache files")
            return count
            
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            cache_files = list(self.cache_dir.glob("verification_*.pkl"))
            total_size = sum(f.stat().st_size for f in cache_files)
            
            return {
                'cache_dir': str(self.cache_dir),
                'total_entries': len(cache_files),
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / 1024 / 1024, 2)
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}


# Convenience function for quick access
def get_verification_result_cache(cache_dir: Optional[Path] = None) -> VerificationResultCache:
    """
    Get verification result cache instance.
    
    Args:
        cache_dir: Optional custom cache directory
    
    Returns:
        VerificationResultCache instance
    """
    return VerificationResultCache(cache_dir)
