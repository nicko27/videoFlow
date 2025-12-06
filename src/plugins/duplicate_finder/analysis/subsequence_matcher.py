"""
Subsequence matching for scene extraction detection.

This module detects when a short video is an extracted scene from a longer video.
Uses sliding window approach to find matching segments.
"""

import os
import numpy as np
from typing import List, Tuple, Dict, Optional, Callable
from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.SubsequenceMatcher')

try:
    from .lsh_audio import LSHAudioAnalyzer
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    logger.warning("LSH Audio not available")


class SubsequenceMatcher:
    """
    Detects if a short video is an extracted scene from a longer video.

    Uses sliding window approach:
    1. Extract signatures from short video (beginning, middle, end)
    2. Search for these signatures in long video using sliding window
    3. Find best matching position
    """

    def __init__(
        self,
        threshold: float = 0.6,
        window_duration: int = 30,
        step_seconds: int = 15
    ):
        """
        Initialize subsequence matcher.

        Args:
            threshold: Minimum similarity to consider a match (default: 0.6)
            window_duration: Duration of comparison window in seconds (default: 30)
            step_seconds: Step size for sliding window in seconds (default: 15)
        """
        self.threshold = threshold
        self.window_duration = window_duration
        self.step_seconds = step_seconds

        if AUDIO_AVAILABLE:
            self.audio_analyzer = LSHAudioAnalyzer(
                threshold=threshold,
                audio_duration=window_duration
            )
        else:
            self.audio_analyzer = None

        logger.info(
            f"SubsequenceMatcher initialized: threshold={threshold:.2f}, "
            f"window={window_duration}s, step={step_seconds}s"
        )

    def get_video_duration(self, video_path: str) -> Optional[float]:
        """Get video duration in seconds."""
        import subprocess
        try:
            cmd = [
                'ffprobe', '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return float(result.stdout.strip())
        except Exception as e:
            logger.error(f"Error getting duration for {video_path}: {e}")
        return None

    def extract_signature_at_time(
        self,
        video_path: str,
        time_seconds: float,
        db_manager
    ):
        """
        Extract audio signature at specific time position.

        Args:
            video_path: Path to video
            time_seconds: Time in seconds (absolute, not ratio)
            db_manager: Database manager

        Returns:
            MinHash signature or None
        """
        if not self.audio_analyzer:
            return None

        try:
            # Get video duration to calculate ratio
            duration = self.get_video_duration(video_path)
            if not duration:
                return None

            # Calculate position as ratio
            position_ratio = time_seconds / duration

            # Extract audio at this position
            audio_path = self.audio_analyzer.extract_audio_from_video(
                video_path,
                duration=self.window_duration,
                start_time=position_ratio
            )

            if not audio_path:
                return None

            try:
                # Extract MFCC
                mfcc = self.audio_analyzer.extract_audio_features(audio_path)
                if mfcc is None:
                    return None

                # Compute signature
                signature = self.audio_analyzer.compute_lsh_signature(mfcc)
                return signature

            finally:
                # Cleanup
                if audio_path and os.path.exists(audio_path):
                    try:
                        os.unlink(audio_path)
                    except OSError as e:
                        logger.debug(f"Could not delete temporary audio file {audio_path}: {e}")

        except Exception as e:
            logger.error(f"Error extracting signature at {time_seconds}s: {e}")
            return None

    def find_best_match(
        self,
        short_video: str,
        long_video: str,
        db_manager,
        progress_callback: Optional[Callable] = None
    ) -> Optional[Dict]:
        """
        Find if short video is a scene extracted from long video.

        Args:
            short_video: Path to shorter video (potential extract)
            long_video: Path to longer video (potential source)
            db_manager: Database manager
            progress_callback: Optional progress callback

        Returns:
            Dictionary with match info or None if no match:
            {
                'is_match': bool,
                'similarity': float,
                'position_seconds': float,
                'position_ratio': float,
                'confidence': str  # 'high', 'medium', 'low'
            }
        """
        if not self.audio_analyzer:
            logger.error("Audio analyzer not available")
            return None

        # Get durations
        short_duration = self.get_video_duration(short_video)
        long_duration = self.get_video_duration(long_video)

        if not short_duration or not long_duration:
            logger.error("Could not get video durations")
            return None

        logger.info(
            f"Searching for {os.path.basename(short_video)} ({short_duration:.1f}s) "
            f"in {os.path.basename(long_video)} ({long_duration:.1f}s)"
        )

        # Extract signature from beginning of short video (first 30s)
        short_sig = self.extract_signature_at_time(short_video, 0, db_manager)
        if not short_sig:
            logger.warning(f"Could not extract signature from short video")
            return None

        # Slide window through long video
        best_match = {
            'is_match': False,
            'similarity': 0.0,
            'position_seconds': 0.0,
            'position_ratio': 0.0,
            'confidence': 'none'
        }

        # Calculate number of windows
        num_windows = int((long_duration - self.window_duration) / self.step_seconds) + 1

        logger.info(f"Testing {num_windows} positions in long video...")

        for i in range(num_windows):
            position_seconds = i * self.step_seconds

            if progress_callback:
                progress_callback(
                    i + 1,
                    num_windows,
                    f"Testing position {position_seconds:.0f}s / {long_duration:.0f}s"
                )

            # Extract signature at this position
            long_sig = self.extract_signature_at_time(
                long_video,
                position_seconds,
                db_manager
            )

            if not long_sig:
                continue

            # Compare signatures
            similarity = short_sig.jaccard(long_sig)

            logger.debug(
                f"Position {position_seconds:.0f}s: similarity={similarity:.4f}"
            )

            # Update best match
            if similarity > best_match['similarity']:
                best_match['similarity'] = similarity
                best_match['position_seconds'] = position_seconds
                best_match['position_ratio'] = position_seconds / long_duration

                # Determine confidence
                if similarity >= 0.85:
                    best_match['confidence'] = 'high'
                elif similarity >= 0.7:
                    best_match['confidence'] = 'medium'
                elif similarity >= self.threshold:
                    best_match['confidence'] = 'low'

                logger.info(
                    f"New best match at {position_seconds:.0f}s: "
                    f"similarity={similarity:.4f} ({best_match['confidence']})"
                )

        # Determine if it's a match
        best_match['is_match'] = best_match['similarity'] >= self.threshold

        if best_match['is_match']:
            logger.info(
                f"✓ MATCH FOUND: Short video matches long video at "
                f"{best_match['position_seconds']:.0f}s "
                f"({best_match['position_ratio']*100:.1f}%) with "
                f"similarity={best_match['similarity']:.4f}"
            )
        else:
            logger.info(
                f"✗ NO MATCH: Best similarity was {best_match['similarity']:.4f} "
                f"(threshold={self.threshold:.2f})"
            )

        return best_match

    def compare_pair(
        self,
        video1: str,
        video2: str,
        db_manager,
        progress_callback: Optional[Callable] = None
    ) -> Optional[Dict]:
        """
        Compare two videos and detect if one is an extract of the other.

        Automatically determines which is shorter and searches for it in the longer one.

        Args:
            video1: First video path
            video2: Second video path
            db_manager: Database manager
            progress_callback: Optional progress callback

        Returns:
            Match info dictionary or None
        """
        # Get durations
        dur1 = self.get_video_duration(video1)
        dur2 = self.get_video_duration(video2)

        if not dur1 or not dur2:
            return None

        # Determine short and long videos
        if dur1 < dur2:
            short_video = video1
            long_video = video2
            short_is_first = True
        else:
            short_video = video2
            long_video = video1
            short_is_first = False

        logger.info(
            f"Comparing: SHORT={os.path.basename(short_video)} ({dur1 if short_is_first else dur2:.1f}s) "
            f"vs LONG={os.path.basename(long_video)} ({dur2 if short_is_first else dur1:.1f}s)"
        )

        # Find match
        result = self.find_best_match(short_video, long_video, db_manager, progress_callback)

        if result:
            result['short_video'] = short_video
            result['long_video'] = long_video

        return result
