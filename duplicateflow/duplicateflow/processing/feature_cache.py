"""
Segment-based feature cache for optimized window search.

Pre-computes and caches features for video segments to avoid redundant
computation when searching with overlapping windows.
"""

import logging
import pickle
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np
import cv2
from tqdm import tqdm

logger = logging.getLogger('duplicateflow.processing.feature_cache')


class SegmentFeatureCache:
    """
    Cache video features by segments for fast window-based search.

    Instead of recomputing features for every overlapping window,
    divide video into segments and reuse cached features.

    Example:
        >>> cache = SegmentFeatureCache(segment_duration=60.0)
        >>> features = cache.get_or_compute(video_path, 'frame_hash')
        >>> window_features = cache.get_window_features(features, start=120, duration=300)
    """

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        segment_duration: float = 60.0,
        max_memory_segments: int = 100
    ):
        """
        Initialize feature cache.

        Args:
            cache_dir: Directory for cache storage
            segment_duration: Duration of each segment in seconds
            max_memory_segments: Maximum segments to keep in memory
        """
        if cache_dir is None:
            cache_dir = Path.home() / '.duplicateflow' / 'feature_cache'

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.segment_duration = segment_duration
        self.max_memory_segments = max_memory_segments

        # In-memory cache
        self._memory_cache: Dict[str, Dict[float, Any]] = {}

    def _get_cache_key(self, video_path: str, algorithm: str, params: Dict) -> str:
        """Generate cache key from video and algorithm config."""
        from duplicateflow.storage.hash_cache import HashCache

        hash_cache = HashCache()
        video_hash = hash_cache.get_file_hash(video_path, method='fast')

        # Include segment duration in key
        params_str = f"{algorithm}_{self.segment_duration}"
        for k, v in sorted(params.items()):
            params_str += f"_{k}_{v}"

        return f"{video_hash}_{params_str}"

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get file path for cached features."""
        return self.cache_dir / f"{cache_key}.pkl"

    def has_cache(self, video_path: str, algorithm: str, params: Dict = None) -> bool:
        """Check if features are cached."""
        params = params or {}
        cache_key = self._get_cache_key(video_path, algorithm, params)

        # Check memory cache
        if cache_key in self._memory_cache:
            return True

        # Check disk cache
        return self._get_cache_path(cache_key).exists()

    def load_cache(
        self,
        video_path: str,
        algorithm: str,
        params: Dict = None
    ) -> Optional[Dict[float, Any]]:
        """Load cached features from disk."""
        params = params or {}
        cache_key = self._get_cache_key(video_path, algorithm, params)

        # Check memory cache first
        if cache_key in self._memory_cache:
            logger.debug(f"Features loaded from memory cache: {cache_key}")
            return self._memory_cache[cache_key]

        # Load from disk
        cache_path = self._get_cache_path(cache_key)
        if not cache_path.exists():
            return None

        try:
            with open(cache_path, 'rb') as f:
                features = pickle.load(f)

            # Store in memory cache (limit size)
            if len(self._memory_cache) < self.max_memory_segments:
                self._memory_cache[cache_key] = features

            logger.debug(f"Features loaded from disk cache: {cache_key}")
            return features

        except Exception as e:
            logger.warning(f"Failed to load cache {cache_key}: {e}")
            return None

    def save_cache(
        self,
        video_path: str,
        algorithm: str,
        features: Dict[float, Any],
        params: Dict = None
    ):
        """Save features to cache."""
        params = params or {}
        cache_key = self._get_cache_key(video_path, algorithm, params)

        # Save to memory
        self._memory_cache[cache_key] = features

        # Save to disk
        cache_path = self._get_cache_path(cache_key)
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(features, f, protocol=pickle.HIGHEST_PROTOCOL)

            logger.debug(f"Features saved to cache: {cache_key}")

        except Exception as e:
            logger.warning(f"Failed to save cache {cache_key}: {e}")

    def compute_features(
        self,
        video_path: str,
        algorithm: str,
        params: Dict = None,
        show_progress: bool = True
    ) -> Dict[float, Any]:
        """
        Compute features for all segments in video.

        Args:
            video_path: Path to video file
            algorithm: Algorithm name for feature extraction
            params: Algorithm parameters
            show_progress: Show progress bar

        Returns:
            Dictionary mapping segment start time to features
        """
        params = params or {}

        # Get video duration
        from duplicateflow.algorithms.base.video_loader import get_video_duration
        duration = get_video_duration(video_path)

        # Calculate segments
        num_segments = int(np.ceil(duration / self.segment_duration))

        logger.info(f"Computing features for {num_segments} segments")

        features = {}

        # Progress bar
        iterator = range(num_segments)
        if show_progress:
            iterator = tqdm(iterator, desc=f"Computing {algorithm} features")

        for i in iterator:
            start_time = i * self.segment_duration
            end_time = min((i + 1) * self.segment_duration, duration)
            segment_duration = end_time - start_time

            # Extract features for this segment
            segment_features = self._extract_segment_features(
                video_path, algorithm, start_time, segment_duration, params
            )

            features[start_time] = segment_features

        return features

    def _extract_segment_features(
        self,
        video_path: str,
        algorithm: str,
        start_time: float,
        duration: float,
        params: Dict
    ) -> Dict[str, Any]:
        """Extract features for a single segment."""
        from duplicateflow.algorithms.base.video_loader import VideoLoader

        # Sample frames from segment
        num_samples = params.get('num_samples', 5)

        features = {
            'start_time': start_time,
            'duration': duration,
            'frames': []
        }

        with VideoLoader(video_path) as loader:
            # Sample frames uniformly across segment
            for i in range(num_samples):
                offset = start_time + (duration * i / (num_samples - 1 if num_samples > 1 else 1))
                frame = loader.get_frame(offset)

                if frame is not None:
                    # Store small version for quick comparison
                    small_frame = cv2.resize(frame, (64, 64))
                    features['frames'].append({
                        'offset': offset,
                        'small_frame': small_frame,
                        'histogram': self._compute_histogram(frame),
                        'hash': self._compute_hash(frame)
                    })

        return features

    def _compute_histogram(self, frame: np.ndarray) -> np.ndarray:
        """Compute color histogram for frame."""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1, 2], None, [8, 8, 8], [0, 180, 0, 256, 0, 256])
        hist = cv2.normalize(hist, hist).flatten()
        return hist

    def _compute_hash(self, frame: np.ndarray) -> int:
        """Compute perceptual hash for frame."""
        # Simple average hash
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (8, 8))
        avg = resized.mean()
        diff = resized > avg
        hash_val = sum([2**i for (i, v) in enumerate(diff.flatten()) if v])
        return hash_val

    def get_or_compute(
        self,
        video_path: str,
        algorithm: str,
        params: Dict = None,
        show_progress: bool = True
    ) -> Dict[float, Any]:
        """Get features from cache or compute if not cached."""
        params = params or {}

        # Try to load from cache
        features = self.load_cache(video_path, algorithm, params)

        if features is not None:
            logger.info(f"Using cached features for {video_path}")
            return features

        # Compute features
        logger.info(f"Computing features for {video_path}")
        features = self.compute_features(video_path, algorithm, params, show_progress)

        # Save to cache
        self.save_cache(video_path, algorithm, features, params)

        return features

    def get_window_features(
        self,
        features: Dict[float, Any],
        window_start: float,
        window_duration: float
    ) -> List[Dict[str, Any]]:
        """
        Get features for a window by combining overlapping segments.

        Args:
            features: Segment features from get_or_compute()
            window_start: Window start time
            window_duration: Window duration

        Returns:
            List of frame features for the window
        """
        window_end = window_start + window_duration

        # Find overlapping segments
        window_features = []

        for segment_start, segment_data in features.items():
            segment_end = segment_start + segment_data['duration']

            # Check if segment overlaps with window
            if segment_end > window_start and segment_start < window_end:
                # Add frames that fall within window
                for frame_data in segment_data['frames']:
                    frame_offset = frame_data['offset']
                    if window_start <= frame_offset < window_end:
                        window_features.append(frame_data)

        return window_features

    def clear_memory_cache(self):
        """Clear in-memory cache."""
        self._memory_cache.clear()
        logger.info("Memory cache cleared")

    def clear_disk_cache(self, algorithm: str = None):
        """Clear disk cache for specific algorithm or all."""
        if algorithm:
            pattern = f"*_{algorithm}_*.pkl"
        else:
            pattern = "*.pkl"

        count = 0
        for cache_file in self.cache_dir.glob(pattern):
            cache_file.unlink()
            count += 1

        logger.info(f"Cleared {count} cache files")
        return count

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        disk_files = list(self.cache_dir.glob("*.pkl"))

        total_size = sum(f.stat().st_size for f in disk_files)

        return {
            'memory_entries': len(self._memory_cache),
            'disk_entries': len(disk_files),
            'total_size_mb': total_size / (1024 * 1024),
            'cache_dir': str(self.cache_dir)
        }
