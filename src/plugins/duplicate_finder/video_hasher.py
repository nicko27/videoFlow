"""Video hashing and comparison module.

This module provides perceptual hashing capabilities for video files, enabling
efficient duplicate detection through frame-based hash comparison. Uses multiple
hashing methods and caching strategies for optimal performance.
"""

import cv2
import numpy as np
import os
import time
from datetime import datetime
from enum import Enum
from .database_manager import VideoDatabase
from .lru_cache import LRUCache
from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.VideoHasher')

class HashMethod(Enum):
    """Available hashing methods for video frames.

    Attributes:
        PHASH: Perceptual hash (most accurate but slower).
        DHASH: Difference hash (faster than pHash).
        AHASH: Average hash (fastest but least accurate).
    """
    PHASH = "pHash"
    DHASH = "dHash"  # Plus rapide que pHash
    AHASH = "aHash"  # Le plus rapide

class VideoHasher:
    """Optimized video hasher with absolute frame positions and permanent memory cache.

    Provides efficient video hashing using perceptual hash algorithms with intelligent
    caching at both memory and database levels. Uses absolute frame positions for
    consistent hashing across multiple runs.

    Features:
        - Multiple hashing methods (pHash, dHash, aHash)
        - Two-level caching (memory + database)
        - Absolute frame position sampling for consistency
        - Batch comparison optimization
        - Corrupted file tracking

    Attributes:
        method (str): Hash method being used (pHash, dHash, or aHash).
        plugin_dir (str): Path to the plugin directory.
        db (VideoDatabase): Database instance for persistent storage.
        hash_cache (dict): Memory cache for video hashes.
        comparison_cache (dict): Memory cache for comparison results.
        absolute_positions (list): Fixed frame indices for sampling.

    Example:
        hasher = VideoHasher(method='pHash')
        hash1, duration1 = hasher.compute_video_hash('video1.mp4')
        hash2, duration2 = hasher.compute_video_hash('video2.mp4')
        similarity = hasher.compare_videos('video1.mp4', 'video2.mp4')
    """

    def __init__(self, method=HashMethod.PHASH.value, enable_preload=True, max_preload_items=1000):
        """Initialize the VideoHasher with specified hashing method.

        Args:
            method (str, optional): Hash method to use ('pHash', 'dHash', or 'aHash').
                Defaults to HashMethod.PHASH.value.
            enable_preload (bool, optional): Enable cache preloading at startup.
                Defaults to True.
            max_preload_items (int, optional): Maximum number of hashes to preload.
                Defaults to 1000. Set to 0 for unlimited (not recommended).
        """
        self.method = method if isinstance(method, str) else method.value
        self.plugin_dir = os.path.dirname(__file__)
        self.db = VideoDatabase()

        # Memory cache PERMANENT for entire session
        self.hash_cache = {}  # file_path -> (hash, duration, mtime)

        # LRU cache for comparisons (limited to 10000 most recent)
        # Prevents unlimited memory growth while keeping hot comparisons fast
        self.comparison_cache = LRUCache(max_size=10000)

        # Fixed absolute positions for consistency
        # Exact frame indices for all videos
        self.absolute_positions = [
            30,    # 1 second at 30fps
            150,   # 5 seconds
            300,   # 10 seconds
            600,   # 20 seconds
            900,   # 30 seconds
            1500,  # 50 seconds
            2100,  # 70 seconds
            3000   # 100 seconds
        ]

        # Smart preload: only recent hashes with file existence check
        if enable_preload:
            self._preload_cache(max_items=max_preload_items)
        else:
            logger.debug("Cache preloading disabled")

        logger.debug("VideoHasher initialized with permanent memory cache")

    def _preload_cache(self, max_items=1000, progress_callback=None):
        """Smart cache preloading with limits and file existence checks.

        Loads only the most recently updated hashes (not all hashes) for files
        that still exist on disk. This prevents slow startup with large databases.

        Args:
            max_items (int): Maximum number of hashes to preload (default: 1000).
                Set to 0 for unlimited (not recommended for large databases).
            progress_callback (callable, optional): Callback for progress updates.
                Called with (current, total, message).

        **OPTIMIZED**:
        - Loads only recent items (ORDER BY updated_at DESC LIMIT)
        - Checks file existence BEFORE loading hash data
        - Uses JSON deserialization (faster and safer than pickle)
        - Limits comparison cache to most recent 5000 items
        """
        try:
            from src.core.serialization import deserialize_numpy_from_json

            start_time = time.time()

            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                # Load hashes - SMART: Only most recent items
                if max_items > 0:
                    query = '''
                        SELECT file_path, hash_data, duration, modification_time, file_size
                        FROM video_files
                        ORDER BY updated_at DESC
                        LIMIT ?
                    '''
                    cursor.execute(query, (max_items,))
                else:
                    # Unlimited - use with caution
                    query = '''
                        SELECT file_path, hash_data, duration, modification_time, file_size
                        FROM video_files
                        ORDER BY updated_at DESC
                    '''
                    cursor.execute(query)

                loaded_hashes = 0
                skipped_missing = 0
                skipped_errors = 0
                rows = cursor.fetchall()
                total_rows = len(rows)

                # Process rows with optional progress tracking
                for idx, row in enumerate(rows):
                    file_path, hash_blob, duration, mtime, file_size = row

                    # OPTIMIZATION: Skip if file no longer exists (don't waste time deserializing)
                    if not os.path.exists(file_path):
                        skipped_missing += 1
                        continue

                    try:
                        # Try JSON first (new format), fallback to pickle (legacy)
                        try:
                            hash_data = deserialize_numpy_from_json(hash_blob.decode('utf-8'))
                        except (UnicodeDecodeError, AttributeError):
                            # Legacy pickle format
                            import pickle
                            hash_data = pickle.loads(hash_blob)

                        self.hash_cache[file_path] = {
                            'hash': hash_data,
                            'duration': duration,
                            'mtime': mtime,
                            'file_size': file_size
                        }
                        loaded_hashes += 1

                        # Progress callback every 100 items
                        if progress_callback and (idx + 1) % 100 == 0:
                            progress_callback(idx + 1, total_rows, f"Loading cache ({loaded_hashes} loaded)")

                    except Exception as e:
                        logger.debug(f"Failed to load hash for {os.path.basename(file_path)}: {e}")
                        skipped_errors += 1
                        continue

                # Load comparisons - SMART: Limit to most recent 5000 (reduced from 50k)
                cursor.execute('''
                    SELECT v1.file_path, v2.file_path, c.similarity
                    FROM comparisons c
                    JOIN video_files v1 ON c.file1_id = v1.id
                    JOIN video_files v2 ON c.file2_id = v2.id
                    ORDER BY c.created_at DESC
                    LIMIT 5000
                ''')

                loaded_comparisons = 0
                for file1, file2, similarity in cursor.fetchall():
                    # Pre-compute cache key to avoid repeated sorting
                    cache_key = (file1, file2) if file1 < file2 else (file2, file1)
                    self.comparison_cache.set(cache_key, similarity)
                    loaded_comparisons += 1

                elapsed = time.time() - start_time

                # Summary log
                summary = f"Cache preload completed in {elapsed:.2f}s: "
                summary += f"{loaded_hashes} hashes, {loaded_comparisons} comparisons"
                if skipped_missing > 0:
                    summary += f" ({skipped_missing} missing files skipped)"
                if skipped_errors > 0:
                    summary += f" ({skipped_errors} errors)"

                logger.info(summary)

                if progress_callback:
                    progress_callback(total_rows, total_rows, "Cache preload complete")

        except Exception as e:
            logger.error(f"Error during cache preload: {e}")

    def compute_frame_hash(self, frame):
        """Calculate the perceptual hash of a single video frame.

        Uses the configured hashing method to generate a binary hash
        representing the visual content of the frame.

        Args:
            frame (numpy.ndarray): Video frame in BGR format.

        Returns:
            numpy.ndarray: Binary hash array, or None if computation fails.
        """
        try:
            # Conversion en gris directement
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            if self.method == "pHash":
                resized = cv2.resize(gray, (32, 32))
                dct = cv2.dct(np.float32(resized))
                dct_low = dct[:8, :8]
                avg = (dct_low[1:, :].mean() + dct_low[0, 1:].mean()) / 2
                return dct_low > avg
                
            elif self.method == "dHash":
                # Difference Hash - plus rapide
                resized = cv2.resize(gray, (9, 8))
                diff = resized[:, 1:] > resized[:, :-1]
                return diff
                
            elif self.method == "aHash":
                # Average Hash - le plus rapide
                resized = cv2.resize(gray, (8, 8))
                avg = resized.mean()
                return resized > avg
                
        except Exception as e:
            logger.error(f"Error calcul hash frame: {e}")
            return None

    def compute_video_hash_fast(self, video_path):
        """Compute video hash using absolute frame positions with caching.

        Extracts frames at fixed absolute positions and computes their hashes.
        Uses memory cache for instant retrieval if the file hasn't changed.
        Stores results in both memory and database caches.

        Args:
            video_path (str): Path to the video file to hash.

        Returns:
            tuple: (hash_array, duration) where hash_array is a numpy array
                of frame hashes and duration is the video length in seconds.

        Raises:
            Exception: If the video cannot be opened or processed.
        """
        try:
            # 1. Check cache mémoire (ultra rapide)
            if video_path in self.hash_cache:
                cache_entry = self.hash_cache[video_path]
                current_mtime = os.path.getmtime(video_path)
                # Checks si le file a changé
                if abs(current_mtime - cache_entry['mtime']) < 1:
                    return cache_entry['hash'], cache_entry['duration']
            
            # 2. Calcul du hash nécessaire
            cv2.setLogLevel(0)
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                raise Exception("Cannot open the video")
            
            try:
                # Récupère les infos de base
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                
                # Validation rapide
                if total_frames <= 0:
                    # Estimation rapide sans parcourir toute the video
                    count = 0
                    while count < 500 and cap.grab():  # Max 500 frames
                        count += 1
                    total_frames = count * 10  # Estimation
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                
                if fps <= 0:
                    fps = 25.0
                
                duration = total_frames / fps
                
                # Filtre les positions selon la longueur de the video
                valid_positions = [pos for pos in self.absolute_positions if pos < total_frames]
                
                # Minimum 3 positions, maximum 8
                if len(valid_positions) < 3:
                    # Pour les très courtes vidéos, positions adaptées
                    if total_frames < 90:
                        valid_positions = [0, total_frames // 2, total_frames - 1]
                    else:
                        valid_positions = [0, 30, 60, total_frames - 1]
                
                hashes = []
                
                for frame_idx in valid_positions:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                    ret, frame = cap.read()
                    
                    if ret and frame is not None:
                        frame_hash = self.compute_frame_hash(frame)
                        if frame_hash is not None:
                            hashes.append(frame_hash)
                    else:
                        # Si failed, essaie the frame suivante
                        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx + 1)
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            frame_hash = self.compute_frame_hash(frame)
                            if frame_hash is not None:
                                hashes.append(frame_hash)
                
                if len(hashes) < 2:
                    raise Exception(f"Seulement {len(hashes)} frames lues")
                
                final_hash = np.stack(hashes)

                # Update ALL caches - OPTIMIZATION: Include file size
                current_mtime = os.path.getmtime(video_path)
                file_size = os.path.getsize(video_path)

                self.hash_cache[video_path] = {
                    'hash': final_hash,
                    'duration': duration,
                    'mtime': current_mtime,
                    'file_size': file_size  # OPTIMIZATION: Cache for early exit
                }

                # Store in DB for persistence
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

                self.db.store_video_hash(
                    video_path,
                    final_hash,
                    duration,
                    width=width,
                    height=height,
                    hash_method=self.method,
                    frames_indices=valid_positions,
                    sampling_method="absolute_optimized"
                )
                
                logger.info(f"Hash créé: {os.path.basename(video_path)} ({len(hashes)} frames aux positions {valid_positions[:3]}...)")
                return final_hash, duration
                
            finally:
                cap.release()
                cv2.setLogLevel(1)
                
        except Exception as e:
            logger.error(f"Error hash {os.path.basename(video_path)}: {e}")
            self.db.mark_file_as_corrupted(video_path, str(e))
            raise

    def compute_video_hash(self, video_path, sample_interval=500):
        """Compute video hash (main entry point).

        Args:
            video_path (str): Path to the video file.
            sample_interval (int, optional): Ignored (kept for compatibility).
                Uses absolute positions instead.

        Returns:
            tuple: (hash_array, duration) from compute_video_hash_fast.
        """
        return self.compute_video_hash_fast(video_path)

    def compare_videos_cached(self, video1_path: str, video2_path: str) -> float:
        """Compare two videos using permanent memory cache.

        Compares video hashes frame-by-frame to determine similarity.
        Uses multi-level caching (memory -> database -> compute) for
        optimal performance.

        **OPTIMIZED**: Uses early-exit strategies and vectorized operations
        for up to 10x faster comparisons.

        Args:
            video1_path (str): Path to the first video file.
            video2_path (str): Path to the second video file.

        Returns:
            float: Similarity percentage (0-100), where 100 is identical.
        """

        # 1. OPTIMIZATION: Pre-compute cache key (avoid repeated sorting)
        cache_key = (video1_path, video2_path) if video1_path < video2_path else (video2_path, video1_path)

        # 2. Check memory cache (instant)
        cached_value = self.comparison_cache.get(cache_key)
        if cached_value is not None:
            return cached_value

        # 3. OPTIMIZATION: Early exit for same file
        if video1_path == video2_path:
            self.comparison_cache.set(cache_key, 100.0)
            return 100.0

        # 4. OPTIMIZATION: Early exit based on file size/duration
        try:
            # Get cached metadata (avoid file I/O)
            meta1 = self.hash_cache.get(video1_path)
            meta2 = self.hash_cache.get(video2_path)

            if meta1 and meta2:
                # If file sizes differ by more than 10%, likely not duplicates
                size1 = meta1.get('file_size', 0)
                size2 = meta2.get('file_size', 0)
                if size1 > 0 and size2 > 0:
                    size_ratio = min(size1, size2) / max(size1, size2)
                    if size_ratio < 0.90:  # 10% tolerance
                        self.comparison_cache.set(cache_key, 0.0)
                        return 0.0

                # If durations differ by more than 5%, likely not duplicates
                dur1 = meta1.get('duration', 0)
                dur2 = meta2.get('duration', 0)
                if dur1 > 0 and dur2 > 0:
                    dur_ratio = min(dur1, dur2) / max(dur1, dur2)
                    if dur_ratio < 0.95:  # 5% tolerance
                        self.comparison_cache.set(cache_key, 0.0)
                        return 0.0
        except Exception:
            pass  # Continue with full comparison

        # 5. Check database cache
        cached_result = self.db.get_cached_comparison(video1_path, video2_path)
        if cached_result is not None:
            self.comparison_cache.set(cache_key, cached_result)
            return cached_result

        # 6. Perform actual comparison
        start_time = time.time()

        try:
            # Get hashes (from memory cache if possible)
            hash1, duration1 = self.compute_video_hash_fast(video1_path)
            hash2, duration2 = self.compute_video_hash_fast(video2_path)

            # OPTIMIZATION: Vectorized comparison (10x faster than loops)
            min_frames = min(len(hash1), len(hash2))

            if min_frames == 0:
                similarity = 0.0
            else:
                # VECTORIZED: Compare all frames at once using numpy
                hash1_subset = hash1[:min_frames]
                hash2_subset = hash2[:min_frames]

                # Single vectorized operation instead of loop
                matches = np.sum(hash1_subset == hash2_subset)
                total = hash1_subset.size

                similarity = (matches / total * 100) if total > 0 else 0.0

            # Cache everywhere
            computation_time = time.time() - start_time

            # Memory cache
            self.comparison_cache.set(cache_key, similarity)

            # Database cache
            self.db.store_comparison(
                video1_path,
                video2_path,
                similarity,
                comparison_method="vectorized_optimized",
                computation_time=computation_time
            )

            return similarity

        except Exception as e:
            logger.error(f"Error comparison: {e}")
            # Cache the failure too
            self.comparison_cache.set(cache_key, 0.0)
            return 0.0

    def compare_videos_optimized(self, video1_path: str, video2_path: str) -> float:
        """Alias for the méthode cachée"""
        return self.compare_videos_cached(video1_path, video2_path)

    def compare_videos(self, video1_path: str, video2_path: str) -> float:
        """Méthode main comparison"""
        return self.compare_videos_cached(video1_path, video2_path)

    def get_cache_stats(self):
        """Get memory cache statistics.

        Returns:
            dict: Dictionary with cache size statistics including:
                - hash_cache_size: Number of cached video hashes
                - comparison_cache_size: Number of cached comparisons
                - total_memory_items: Total cached items
        """
        return {
            'hash_cache_size': len(self.hash_cache),
            'comparison_cache_size': len(self.comparison_cache),
            'comparison_cache_hits': self.comparison_cache.hits,
            'comparison_cache_misses': self.comparison_cache.misses,
            'comparison_cache_hit_rate': self.comparison_cache.get_stats()['hit_rate'],
            'total_memory_items': len(self.hash_cache) + len(self.comparison_cache)
        }

    def clear_memory_cache(self):
        """Clear only the memory cache (preserves database cache)."""
        self.hash_cache.clear()
        self.comparison_cache.clear()
        logger.info("Cache mémoire vidé")

    def clear_cache(self):
        """Clear all caches (memory and database).

        Returns:
            bool: True if successful, False otherwise.
        """
        self.clear_memory_cache()
        return self.db.clear_all_data()

    def preload_comparisons_batch(self, file_pairs):
        """Preload a batch of comparisons from the database with limit.

        Loads comparison results from the database into memory cache for
        faster access. Limited to 5000 pairs to prevent memory overflow.

        Args:
            file_pairs (list): List of (file1, file2) tuples to preload.
        """
        try:
            # Limite le préchargement pour éviter l'overflow mémoire
            max_preload = 5000
            if len(file_pairs) > max_preload:
                logger.debug(f"Préchargement limité à {max_preload} paires on {len(file_pairs)}")
                file_pairs = file_pairs[:max_preload]
            
            loaded = 0
            for file1, file2 in file_pairs:
                cache_key = tuple(sorted([file1, file2]))
                if cache_key not in self.comparison_cache:
                    result = self.db.get_cached_comparison(file1, file2)
                    if result is not None:
                        self.comparison_cache.set(cache_key, result)
                        loaded += 1
            
            if loaded > 0:
                logger.debug(f"Préchargé {loaded} comparaisons en mémoire")
                
        except Exception as e:
            logger.error(f"Error préchargement comparaisons: {e}")

    # Méthodes de compatibilité
    def has_hash(self, file_path):
        # Check cache mémoire d'abord (instantané)
        if file_path in self.hash_cache:
            current_mtime = os.path.getmtime(file_path)
            cache_mtime = self.hash_cache[file_path]['mtime']
            if abs(current_mtime - cache_mtime) < 1:
                return True
        return not self.db.file_needs_reanalysis(file_path)
    
    def is_pair_ignored(self, file1, file2):
        return self.db.is_pair_ignored(file1, file2)
    
    def add_ignored_pair(self, file1, file2):
        return self.db.add_ignored_pair(file1, file2, reason="user_choice")
    
    def get_cached_comparison(self, file1, file2):
        # Check mémoire d'abord
        cache_key = tuple(sorted([file1, file2]))
        cached_value = self.comparison_cache.get(cache_key)
        if cached_value is not None:
            return cached_value
        return self.db.get_cached_comparison(file1, file2)
    
    def get_statistics(self):
        db_stats = self.db.get_statistics()
        cache_stats = self.get_cache_stats()
        return {**db_stats, **cache_stats}

    # Optimisations supplémentaires
    def quick_similarity_test(self, file1, file2):
        """Perform quick similarity test using a single frame at fixed position.

        Compares videos using only one frame at position 300 (10 seconds).
        Useful for fast pre-filtering before full comparison.

        Args:
            file1 (str): Path to the first video file.
            file2 (str): Path to the second video file.

        Returns:
            float: Similarity percentage (0-100), or -1 if test failed.
        """
        try:
            # Position absolue fixe pour cohérence
            test_position = 300  # 10 secondes
            
            cv2.setLogLevel(0)
            cap1 = cv2.VideoCapture(file1)
            cap2 = cv2.VideoCapture(file2)
            
            if not cap1.isOpened() or not cap2.isOpened():
                return -1
            
            # Ajuste si nécessaire
            total1 = int(cap1.get(cv2.CAP_PROP_FRAME_COUNT))
            total2 = int(cap2.get(cv2.CAP_PROP_FRAME_COUNT))
            
            pos1 = min(test_position, total1 - 1) if total1 > 0 else 0
            pos2 = min(test_position, total2 - 1) if total2 > 0 else 0
            
            cap1.set(cv2.CAP_PROP_POS_FRAMES, pos1)
            cap2.set(cv2.CAP_PROP_POS_FRAMES, pos2)
            
            ret1, frame1 = cap1.read()
            ret2, frame2 = cap2.read()
            
            cap1.release()
            cap2.release()
            cv2.setLogLevel(1)
            
            if not ret1 or not ret2:
                return -1
            
            hash1 = self.compute_frame_hash(frame1)
            hash2 = self.compute_frame_hash(frame2)
            
            if hash1 is None or hash2 is None:
                return -1
            
            # Calcul de similarité
            similarity = np.sum(hash1 == hash2) / hash1.size * 100
            
            return similarity
            
        except Exception:
            return -1