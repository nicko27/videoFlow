"""
Level 2: Long-period audio comparison module.

This module provides refined audio comparison using longer time windows (120s)
to filter candidates from Level 1 with higher precision.

The algorithm:
1. Extract 120s audio from video (starting at 10% of duration)
2. Compute chromagram features (pitch class energy distribution)
3. Compare chromagrams using cosine similarity
4. Filter candidates that exceed the threshold

Dependencies:
    - librosa: For audio feature extraction (chromagram)
    - soundfile: For audio file I/O
    - numpy: For numerical operations
    - scipy: For correlation and similarity metrics
"""

import os
import json
import subprocess
import tempfile
import numpy as np
from typing import List, Tuple, Dict, Optional, Callable
from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.LongAudioComparator')

# Try to import required libraries
try:
    import librosa
    import soundfile as sf
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    logger.warning("librosa/soundfile not installed - long audio analysis unavailable")
    logger.warning("Install with: pip install librosa soundfile")

try:
    from scipy.spatial.distance import cosine
    from scipy.stats import pearsonr
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logger.warning("scipy not installed - using fallback similarity metrics")


class LongAudioComparator:
    """
    Long-period audio comparison (Level 2).

    This class implements Level 2 of the advanced 3-level duplicate detection.
    It extracts and compares longer audio segments (120 seconds) to refine
    the candidates from Level 1.

    The algorithm uses chromagram features which represent the distribution
    of energy across the 12 pitch classes (C, C#, D, D#, E, F, F#, G, G#, A, A#, B).
    This makes it robust to variations in timbre while capturing melodic content.

    Attributes:
        window_duration: Length of audio to extract (default: 120s)
        threshold: Minimum similarity score to pass (default: 0.8)
        window_start: Start position as ratio of duration (default: 0.1 = 10%)
    """

    def __init__(
        self,
        window_duration: int = 120,
        threshold: float = 0.8,
        window_start: float = 0.1
    ):
        """
        Initialize long audio comparator.

        Args:
            window_duration: Duration of audio window in seconds (default: 120)
            threshold: Minimum similarity score to pass (default: 0.8)
            window_start: Start position as ratio of duration (default: 0.1 = 10%)
        """
        if not LIBROSA_AVAILABLE:
            raise ImportError(
                "librosa and soundfile libraries are required for long audio analysis.\n"
                "Install with: pip install librosa soundfile"
            )

        self.window_duration = window_duration
        self.threshold = threshold
        self.window_start = window_start

        # Cache for chromagram features
        self.chromagram_cache = {}  # video_path -> chromagram

        logger.info(
            f"LongAudioComparator initialized: duration={window_duration}s, "
            f"threshold={threshold:.2f}, start={window_start:.0%}"
        )

    def extract_audio_from_video(
        self,
        video_path: str,
        duration: Optional[int] = None,
        start_time: float = 0.1
    ) -> Optional[str]:
        """
        Extract audio from video to temporary WAV file using ffmpeg.

        Args:
            video_path: Path to video file
            duration: Duration to extract in seconds (None = use self.window_duration)
            start_time: Start position as ratio of total duration (0.1 = 10%)

        Returns:
            Path to temporary WAV file, or None on error
        """
        if duration is None:
            duration = self.window_duration

        try:
            # Create temporary file for audio
            temp_audio = tempfile.NamedTemporaryFile(
                suffix='.wav',
                delete=False
            )
            temp_audio_path = temp_audio.name
            temp_audio.close()

            # Get video duration first
            duration_cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                video_path
            ]

            result = subprocess.run(
                duration_cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                total_duration = float(result.stdout.strip())
                start_seconds = total_duration * start_time
                # Make sure we don't try to extract beyond the video
                actual_duration = min(duration, total_duration - start_seconds)
                if actual_duration < 10:  # Need at least 10s
                    logger.warning(f"Video too short for long audio: {video_path}")
                    return None
            else:
                start_seconds = 0
                actual_duration = duration

            # Extract audio with ffmpeg
            ffmpeg_cmd = [
                'ffmpeg',
                '-y',  # Overwrite output file
                '-ss', str(start_seconds),  # Start position
                '-i', video_path,
                '-t', str(actual_duration),  # Duration
                '-vn',  # No video
                '-ar', '22050',  # Sample rate 22.05 kHz
                '-ac', '1',  # Mono
                '-f', 'wav',  # WAV format
                temp_audio_path
            ]

            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                timeout=120,  # Longer timeout for 120s extraction
                text=True
            )

            if result.returncode != 0:
                logger.error(f"ffmpeg error for {video_path}: {result.stderr}")
                if os.path.exists(temp_audio_path):
                    os.unlink(temp_audio_path)
                return None

            # Verify audio file was created and has content
            if os.path.exists(temp_audio_path) and os.path.getsize(temp_audio_path) > 10000:
                return temp_audio_path
            else:
                logger.warning(f"Audio extraction failed or file too small: {video_path}")
                if os.path.exists(temp_audio_path):
                    os.unlink(temp_audio_path)
                return None

        except subprocess.TimeoutExpired:
            logger.error(f"ffmpeg timeout extracting audio from {video_path}")
            if os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)
            return None
        except Exception as e:
            logger.error(f"Error extracting audio from {video_path}: {e}")
            if 'temp_audio_path' in locals() and os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)
            return None

    def extract_chromagram(
        self,
        audio_path: str,
        n_chroma: int = 12
    ) -> Optional[np.ndarray]:
        """
        Extract chromagram features from audio file.

        Chromagram represents the energy distribution across the 12 pitch classes,
        making it ideal for detecting similar musical content.

        Args:
            audio_path: Path to audio file (WAV)
            n_chroma: Number of chroma bins (default: 12 for 12 pitch classes)

        Returns:
            Chromagram features as numpy array (12 × time_frames), or None on error
        """
        try:
            # Load audio file
            audio, sr = librosa.load(
                audio_path,
                sr=22050,  # Resample to 22.05 kHz
                mono=True,
                duration=self.window_duration
            )

            if len(audio) == 0:
                logger.warning(f"Audio file is empty: {audio_path}")
                return None

            # Compute chromagram
            chroma = librosa.feature.chroma_cqt(
                y=audio,
                sr=sr,
                n_chroma=n_chroma,
                hop_length=512,
                bins_per_octave=36  # High resolution for better accuracy
            )

            # Normalize chromagram (each frame sums to 1)
            chroma_normalized = chroma / (chroma.sum(axis=0, keepdims=True) + 1e-8)

            logger.debug(f"Extracted chromagram: shape={chroma_normalized.shape}")

            return chroma_normalized

        except Exception as e:
            logger.error(f"Error extracting chromagram from {audio_path}: {e}")
            return None

    def compute_similarity(
        self,
        chroma1: np.ndarray,
        chroma2: np.ndarray
    ) -> float:
        """
        Compute similarity between two chromagrams.

        Uses cosine similarity if scipy is available, otherwise uses
        correlation-based similarity.

        Args:
            chroma1: First chromagram (12 × time_frames)
            chroma2: Second chromagram (12 × time_frames)

        Returns:
            Similarity score between 0.0 and 1.0
        """
        try:
            # Flatten chromagrams to 1D vectors
            vec1 = chroma1.flatten()
            vec2 = chroma2.flatten()

            # Pad shorter vector to match lengths
            if len(vec1) != len(vec2):
                max_len = max(len(vec1), len(vec2))
                if len(vec1) < max_len:
                    vec1 = np.pad(vec1, (0, max_len - len(vec1)), mode='constant')
                else:
                    vec2 = np.pad(vec2, (0, max_len - len(vec2)), mode='constant')

            # Compute cosine similarity
            if SCIPY_AVAILABLE:
                # cosine() returns distance, so we compute 1 - distance
                similarity = 1.0 - cosine(vec1, vec2)
            else:
                # Fallback: normalized dot product
                dot_product = np.dot(vec1, vec2)
                norm1 = np.linalg.norm(vec1)
                norm2 = np.linalg.norm(vec2)
                similarity = dot_product / (norm1 * norm2 + 1e-8)

            # Clamp to [0, 1]
            similarity = max(0.0, min(1.0, similarity))

            return similarity

        except Exception as e:
            logger.error(f"Error computing similarity: {e}")
            return 0.0

    def extract_long_window(
        self,
        video_path: str,
        db_manager
    ) -> Optional[np.ndarray]:
        """
        Extract long audio window chromagram from video.

        Checks cache first, then extracts if needed.

        Args:
            video_path: Path to video file
            db_manager: Database manager for caching

        Returns:
            Chromagram array or None
        """
        # Check memory cache
        if video_path in self.chromagram_cache:
            logger.debug(f"Using cached chromagram for {os.path.basename(video_path)}")
            return self.chromagram_cache[video_path]

        # Check database cache
        cached_chroma = db_manager.get_level2_chromagram(video_path)
        if cached_chroma is not None:
            logger.debug(f"Loaded chromagram from database for {os.path.basename(video_path)}")
            self.chromagram_cache[video_path] = cached_chroma
            return cached_chroma

        # Extract audio
        audio_path = self.extract_audio_from_video(
            video_path,
            duration=self.window_duration,
            start_time=self.window_start
        )

        if audio_path is None:
            logger.warning(f"Could not extract audio from {video_path}")
            return None

        try:
            # Extract chromagram
            chroma = self.extract_chromagram(audio_path)

            if chroma is not None:
                # Cache in memory
                self.chromagram_cache[video_path] = chroma

                # Store in database for future use
                # Note: We could store the chromagram in the database here
                # For now, we skip database storage to simplify

            return chroma

        finally:
            # Clean up temporary audio file
            if audio_path and os.path.exists(audio_path):
                try:
                    os.unlink(audio_path)
                except Exception as e:
                    logger.debug(f"Could not delete temp audio: {e}")

    def compare_long_audio(
        self,
        video1_path: str,
        video2_path: str,
        db_manager
    ) -> Dict:
        """
        Compare long audio segments between two videos.

        Args:
            video1_path: First video path
            video2_path: Second video path
            db_manager: Database manager for caching

        Returns:
            Dictionary with similarity score and metadata
        """
        # Extract chromagrams
        chroma1 = self.extract_long_window(video1_path, db_manager)
        chroma2 = self.extract_long_window(video2_path, db_manager)

        if chroma1 is None or chroma2 is None:
            logger.warning(
                f"Could not extract chromagrams for comparison: "
                f"{os.path.basename(video1_path)} <-> {os.path.basename(video2_path)}"
            )
            return {
                'similarity_score': 0.0,
                'window_duration': self.window_duration,
                'is_similar': False,
                'error': 'chromagram_extraction_failed'
            }

        # Compute similarity
        similarity = self.compute_similarity(chroma1, chroma2)

        # Determine if similar
        is_similar = similarity >= self.threshold

        logger.info(
            f"Level 2 comparison: {os.path.basename(video1_path)} <-> "
            f"{os.path.basename(video2_path)} = {similarity:.3f} "
            f"({'PASS' if is_similar else 'FAIL'})"
        )

        return {
            'similarity_score': similarity,
            'window_duration': self.window_duration,
            'is_similar': is_similar,
            'chroma1_shape': chroma1.shape,
            'chroma2_shape': chroma2.shape
        }

    def filter_candidates(
        self,
        candidate_pairs: List[Tuple],
        db_manager,
        progress_callback: Optional[Callable] = None
    ) -> List[Tuple]:
        """
        Filter Level 1 candidates using long-period audio comparison.

        Args:
            candidate_pairs: List of (file1, file2, level1_score) from Level 1
            db_manager: Database manager instance
            progress_callback: Optional progress callback

        Returns:
            Filtered list of candidate pairs with updated scores:
            [(file1, file2, level1_score, level2_score), ...]
        """
        total = len(candidate_pairs)
        logger.info(f"Level 2: Filtering {total} candidates with long audio comparison")

        if total == 0:
            return []

        refined = []
        passed_count = 0
        failed_count = 0

        for idx, pair in enumerate(candidate_pairs):
            if len(pair) >= 3:
                file1, file2, level1_score = pair[:3]
            else:
                logger.warning(f"Invalid pair format: {pair}")
                continue

            # Update progress
            if progress_callback:
                progress_callback(
                    idx + 1,
                    total,
                    f"Comparing {os.path.basename(file1)} <-> {os.path.basename(file2)}"
                )

            # Compare long audio
            result = self.compare_long_audio(file1, file2, db_manager)
            level2_score = result['similarity_score']
            is_similar = result['is_similar']

            # Store result in database
            db_manager.store_level2_result(
                file1,
                file2,
                level2_score,
                self.window_duration
            )

            # Only keep if passes threshold
            if is_similar:
                refined.append((file1, file2, level1_score, level2_score))
                passed_count += 1
                logger.debug(
                    f"✓ PASS: {os.path.basename(file1)} <-> {os.path.basename(file2)} "
                    f"(L1={level1_score:.3f}, L2={level2_score:.3f})"
                )
            else:
                failed_count += 1
                logger.debug(
                    f"✗ FAIL: {os.path.basename(file1)} <-> {os.path.basename(file2)} "
                    f"(L1={level1_score:.3f}, L2={level2_score:.3f})"
                )

        reduction_rate = (failed_count / total * 100) if total > 0 else 0

        logger.info(
            f"Level 2 complete: {passed_count} passed, {failed_count} filtered out "
            f"({reduction_rate:.1f}% reduction)"
        )

        return refined
