"""
Level 1: LSH audio fingerprinting module.

This module provides fast initial filtering using Locality Sensitive Hashing (LSH)
on audio features to identify candidate pairs for deeper analysis.

Dependencies:
    - datasketch: For LSH indexing and similarity search
    - librosa: For audio feature extraction (MFCC)
    - soundfile: For audio file I/O

Installation:
    pip install datasketch librosa soundfile
"""

import os
import json
import hashlib
import subprocess
import tempfile
import numpy as np
from typing import List, Tuple, Dict, Optional, Callable
from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.LSHAudioAnalyzer')

# Try to import required libraries
try:
    from datasketch import MinHash, MinHashLSH
    DATASKETCH_AVAILABLE = True
except ImportError:
    DATASKETCH_AVAILABLE = False
    logger.warning("datasketch not installed - LSH analysis unavailable")
    logger.warning("Install with: pip install datasketch")

try:
    import librosa
    import soundfile as sf
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    logger.warning("librosa/soundfile not installed - audio analysis unavailable")
    logger.warning("Install with: pip install librosa soundfile")


class LSHAudioAnalyzer:
    """
    LSH-based audio fingerprinting (Level 1).

    This class implements Level 1 of the advanced 3-level duplicate detection.
    It uses Locality Sensitive Hashing to quickly find candidate pairs with
    similar audio content.

    The algorithm:
    1. Extract audio from video (30 seconds)
    2. Compute MFCC features (Mel-Frequency Cepstral Coefficients)
    3. Create LSH signature from MFCC windows
    4. Query LSH index to find similar videos
    5. Return candidate pairs with Jaccard similarity > threshold

    Attributes:
        n_bands: Number of LSH bands (default: 20)
        n_rows: Number of rows per band (default: 5)
        threshold: Jaccard similarity threshold (default: 0.7)
        num_perm: Total number of permutations (bands × rows = 100)
    """

    def __init__(
        self,
        n_bands: int = 20,
        n_rows: int = 5,
        threshold: float = 0.7,
        audio_duration: int = 30
    ):
        """
        Initialize LSH audio analyzer.

        Args:
            n_bands: Number of LSH bands (default: 20)
            n_rows: Number of rows per band (default: 5)
            threshold: Jaccard similarity threshold (default: 0.7)
            audio_duration: Duration of audio to analyze in seconds (default: 30)
        """
        if not DATASKETCH_AVAILABLE:
            raise ImportError(
                "datasketch library is required for LSH analysis.\n"
                "Install with: pip install datasketch"
            )

        if not LIBROSA_AVAILABLE:
            raise ImportError(
                "librosa and soundfile libraries are required for audio analysis.\n"
                "Install with: pip install librosa soundfile"
            )

        self.n_bands = n_bands
        self.n_rows = n_rows
        self.threshold = threshold
        self.audio_duration = audio_duration
        self.num_perm = n_bands * n_rows

        # Initialize LSH index
        self.lsh_index = MinHashLSH(
            threshold=threshold,
            num_perm=self.num_perm
        )

        # Cache for video signatures
        self.signatures = {}  # video_path -> MinHash

        logger.info(
            f"LSHAudioAnalyzer initialized: bands={n_bands}, rows={n_rows}, "
            f"num_perm={self.num_perm}, threshold={threshold:.2f}, "
            f"audio_duration={audio_duration}s"
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
            duration: Duration to extract in seconds (None = use self.audio_duration)
            start_time: Start position as ratio of total duration (0.1 = 10%)

        Returns:
            Path to temporary WAV file, or None on error
        """
        if duration is None:
            duration = self.audio_duration

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
            else:
                start_seconds = 0  # Fallback to beginning

            # Extract audio with ffmpeg
            ffmpeg_cmd = [
                'ffmpeg',
                '-y',  # Overwrite output file
                '-ss', str(start_seconds),  # Start position
                '-i', video_path,
                '-t', str(duration),  # Duration
                '-vn',  # No video
                '-ar', '22050',  # Sample rate 22.05 kHz
                '-ac', '1',  # Mono
                '-f', 'wav',  # WAV format
                temp_audio_path
            ]

            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                timeout=60,
                text=True
            )

            if result.returncode != 0:
                logger.error(f"ffmpeg error for {video_path}: {result.stderr}")
                if os.path.exists(temp_audio_path):
                    os.unlink(temp_audio_path)
                return None

            # Verify audio file was created and has content
            if os.path.exists(temp_audio_path) and os.path.getsize(temp_audio_path) > 1000:
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

    def extract_audio_features(
        self,
        audio_path: str,
        n_mfcc: int = 13
    ) -> Optional[np.ndarray]:
        """
        Extract MFCC features from audio file.

        MFCC (Mel-Frequency Cepstral Coefficients) captures the timbral
        characteristics of audio, making it ideal for similarity comparison.

        Args:
            audio_path: Path to audio file (WAV)
            n_mfcc: Number of MFCC coefficients to extract (default: 13)

        Returns:
            MFCC features as numpy array (n_mfcc × time_frames), or None on error
        """
        try:
            # Load audio file
            audio, sr = librosa.load(
                audio_path,
                sr=22050,  # Resample to 22.05 kHz
                mono=True,
                duration=self.audio_duration
            )

            if len(audio) == 0:
                logger.warning(f"Audio file is empty: {audio_path}")
                return None

            # Compute MFCC features
            mfcc = librosa.feature.mfcc(
                y=audio,
                sr=sr,
                n_mfcc=n_mfcc,
                n_fft=2048,
                hop_length=512
            )

            # Normalize MFCC (mean=0, std=1 for each coefficient)
            mfcc_normalized = (mfcc - mfcc.mean(axis=1, keepdims=True)) / (
                mfcc.std(axis=1, keepdims=True) + 1e-8
            )

            logger.debug(f"Extracted MFCC: shape={mfcc_normalized.shape}")

            return mfcc_normalized

        except Exception as e:
            logger.error(f"Error extracting MFCC from {audio_path}: {e}")
            return None

    def compute_lsh_signature(
        self,
        mfcc_features: np.ndarray,
        window_size: int = 20
    ) -> Optional[MinHash]:
        """
        Compute LSH signature (MinHash) from MFCC features.

        Creates a MinHash signature by sliding a window over MFCC frames
        and hashing quantized feature vectors.

        Args:
            mfcc_features: MFCC array (n_mfcc × time_frames)
            window_size: Number of frames per window (default: 20)

        Returns:
            MinHash signature, or None on error
        """
        try:
            minhash = MinHash(num_perm=self.num_perm)

            n_mfcc, n_frames = mfcc_features.shape

            # Slide window over time frames
            for i in range(0, n_frames - window_size + 1, window_size // 2):
                # Extract window
                window = mfcc_features[:, i:i + window_size]

                # Flatten and quantize to integers
                window_flat = window.flatten()
                # Quantize to 8-bit integers for hashing
                window_quantized = (window_flat * 127).astype(np.int8)

                # Update MinHash with window bytes
                minhash.update(window_quantized.tobytes())

            return minhash

        except Exception as e:
            logger.error(f"Error computing LSH signature: {e}")
            return None

    def add_to_index(
        self,
        video_path: str,
        signature: MinHash,
        video_id: str
    ) -> bool:
        """
        Add LSH signature to the index for similarity search.

        Args:
            video_path: Video file path
            signature: MinHash signature
            video_id: Unique identifier for the video

        Returns:
            True if successfully added
        """
        try:
            # Use video_path as key for LSH index
            self.lsh_index.insert(video_path, signature)

            # Cache signature
            self.signatures[video_path] = signature

            logger.debug(f"Added to LSH index: {os.path.basename(video_path)}")
            return True

        except Exception as e:
            logger.error(f"Error adding to LSH index: {e}")
            return False

    def process_video(
        self,
        video_path: str,
        db_manager
    ) -> Optional[MinHash]:
        """
        Process a single video: extract audio, compute features, create LSH signature.

        Args:
            video_path: Path to video file
            db_manager: Database manager for caching

        Returns:
            MinHash signature, or None on error
        """
        # Check if signature already exists in database
        cached_lsh = db_manager.get_lsh_fingerprint(video_path)
        if cached_lsh:
            logger.debug(f"Using cached LSH for {os.path.basename(video_path)}")
            # Reconstruct MinHash from cached data
            # Note: This is simplified - in production you'd want to serialize/deserialize properly
            return None  # For now, recompute

        # Extract audio
        audio_path = self.extract_audio_from_video(video_path)
        if audio_path is None:
            logger.warning(f"Could not extract audio from {video_path}")
            return None

        try:
            # Extract MFCC features
            mfcc = self.extract_audio_features(audio_path)
            if mfcc is None:
                return None

            # Compute LSH signature
            signature = self.compute_lsh_signature(mfcc)
            if signature is None:
                return None

            # Store in database
            # Convert MinHash to storable format
            signature_data = np.array(signature.hashvalues)
            signature_bands = json.dumps(signature.hashvalues.tolist())

            db_manager.store_lsh_fingerprint(
                video_path,
                signature_data,
                signature_bands,
                self.n_bands,
                self.n_rows
            )

            logger.debug(f"Processed and stored LSH for {os.path.basename(video_path)}")

            return signature

        finally:
            # Clean up temporary audio file
            if audio_path and os.path.exists(audio_path):
                try:
                    os.unlink(audio_path)
                except Exception as e:
                    logger.debug(f"Could not delete temp audio: {e}")

    def find_candidates(
        self,
        video_paths: List[str],
        db_manager,
        progress_callback: Optional[Callable] = None
    ) -> List[Tuple]:
        """
        Find candidate pairs using LSH similarity.

        Processes all videos, builds LSH index, and queries for similar pairs.

        Args:
            video_paths: List of video file paths to analyze
            db_manager: Database manager instance
            progress_callback: Optional callback(current, total, status_msg)

        Returns:
            List of candidate tuples: (file1_path, file2_path, jaccard_similarity)
        """
        total = len(video_paths)
        logger.info(f"Starting LSH analysis on {total} videos")

        # Phase 1: Process all videos and build index
        processed_count = 0
        failed_count = 0

        for idx, video_path in enumerate(video_paths):
            if progress_callback:
                progress_callback(
                    idx + 1,
                    total,
                    f"Processing {os.path.basename(video_path)}"
                )

            # Process video
            signature = self.process_video(video_path, db_manager)

            if signature:
                # Add to LSH index
                video_id = hashlib.md5(video_path.encode()).hexdigest()
                self.add_to_index(video_path, signature, video_id)
                processed_count += 1
            else:
                failed_count += 1

        logger.info(
            f"LSH indexing complete: {processed_count} processed, "
            f"{failed_count} failed"
        )

        # Phase 2: Find similar pairs by querying index
        candidates = []
        seen_pairs = set()

        for idx, video_path in enumerate(video_paths):
            if video_path not in self.signatures:
                continue  # Skip videos that failed processing

            if progress_callback:
                progress_callback(
                    idx + 1,
                    total,
                    f"Finding candidates for {os.path.basename(video_path)}"
                )

            # Query LSH index for similar videos
            signature = self.signatures[video_path]
            similar_videos = self.lsh_index.query(signature)

            # Process similar videos
            for similar_path in similar_videos:
                if similar_path == video_path:
                    continue  # Skip self

                # Create canonical pair (sorted to avoid duplicates)
                pair = tuple(sorted([video_path, similar_path]))
                if pair in seen_pairs:
                    continue  # Already processed

                seen_pairs.add(pair)

                # Calculate Jaccard similarity
                similar_sig = self.signatures[similar_path]
                jaccard_sim = signature.jaccard(similar_sig)

                # Only include if above threshold
                if jaccard_sim >= self.threshold:
                    candidates.append((pair[0], pair[1], jaccard_sim))

                    logger.debug(
                        f"Candidate pair: {os.path.basename(pair[0])} <-> "
                        f"{os.path.basename(pair[1])} (Jaccard={jaccard_sim:.3f})"
                    )

        # Sort by similarity (descending)
        candidates.sort(key=lambda x: x[2], reverse=True)

        logger.info(
            f"LSH Level 1 complete: {len(candidates)} candidate pairs found "
            f"(threshold={self.threshold:.2f})"
        )

        return candidates

    def estimate_similarity(
        self,
        video1_path: str,
        video2_path: str,
        db_manager
    ) -> Optional[float]:
        """
        Estimate similarity between two specific videos using LSH.

        Args:
            video1_path: First video path
            video2_path: Second video path
            db_manager: Database manager

        Returns:
            Jaccard similarity score (0.0-1.0), or None on error
        """
        # Process both videos
        sig1 = self.process_video(video1_path, db_manager)
        sig2 = self.process_video(video2_path, db_manager)

        if sig1 is None or sig2 is None:
            return None

        # Calculate Jaccard similarity
        similarity = sig1.jaccard(sig2)

        logger.info(
            f"LSH similarity: {os.path.basename(video1_path)} <-> "
            f"{os.path.basename(video2_path)} = {similarity:.3f}"
        )

        return similarity
