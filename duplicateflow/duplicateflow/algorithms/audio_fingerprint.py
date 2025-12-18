"""
Audio Fingerprinting algorithm (Shazam-style) for scalable video matching.

Uses acoustic landmarks and hash matching to find duplicates efficiently.
Ideal for N-to-N comparison of millions of videos.
"""

import logging
import subprocess
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path

from duplicateflow.sdk.algorithm import Algorithm
from duplicateflow.core.registry import register_algorithm

logger = logging.getLogger('duplicateflow.algorithms.audio_fingerprint')

try:
    from scipy.signal import stft
    from scipy.ndimage import maximum_filter
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logger.warning("scipy not available - audio_fingerprint algorithm will not work")


@register_algorithm(
    name="audio_fingerprint",
    display_name="🎵 Audio Fingerprint (Shazam-style)",
    category="audio",
    speed="fast",
    default_threshold=200,  # minimum votes for match
    default_params={
        'threshold': 200,  # minimum votes
        'sr': 11025,  # sample rate
        'n_fft': 4096,
        'hop': 512,
        'freq_max_hz': 5000.0,
        'neighborhood_time': 12,
        'neighborhood_freq': 8,
        'amp_percentile': 75.0,
        'max_peaks_per_second': 25,
        'fanout': 8,  # landmark pairs per peak
        'dt_min': 0.5,  # min time delta for pairs
        'dt_max': 3.0,  # max time delta for pairs
        'freq_bin_quant': 2,
        'time_quant': 20,  # ms quantization
    }
)
class AudioFingerprintAlgorithm(Algorithm):
    """
    Audio fingerprinting for duplicate detection at scale.

    This algorithm extracts compact acoustic fingerprints (hashes) from videos
    that can be efficiently compared without frame-by-frame analysis.

    Ideal for:
    - N-to-N comparison of large video collections
    - Finding exact or near-exact audio matches
    - Scaling to millions of videos with database indexing

    Algorithm:
    1. Extract audio and compute spectrogram (STFT)
    2. Find spectral peaks (local maxima in time-frequency space)
    3. Build landmark pairs (anchor peak + nearby peaks)
    4. Hash each pair: (freq1, freq2, time_delta)
    5. Match by finding common hashes and voting on time offsets

    Complexity:
    - Fingerprint extraction: O(duration)
    - Comparison: O(|hashes1| + |hashes2|) - much faster than O(frames)

    Example:
        >>> algo = AudioFingerprintAlgorithm()
        >>> algo.configure(threshold=200, sr=11025)
        >>> result = algo.compare('video1.mp4', 'video2.mp4')
        >>> # Or extract fingerprints separately for database indexing:
        >>> fingerprints = algo.extract_fingerprints('video1.mp4')
    """

    def configure(self, **params):
        """Configure algorithm parameters."""
        if not SCIPY_AVAILABLE:
            raise ImportError(
                "scipy is required for audio_fingerprint algorithm. "
                "Install with: pip install scipy"
            )

        # Threshold (minimum votes for match)
        self.threshold = params.get('threshold', 200)

        # Audio extraction
        self.sr = params.get('sr', 11025)

        # Spectrogram
        self.n_fft = params.get('n_fft', 4096)
        self.hop = params.get('hop', 512)
        self.freq_max_hz = params.get('freq_max_hz', 5000.0)

        # Peak picking
        self.neighborhood_time = params.get('neighborhood_time', 12)
        self.neighborhood_freq = params.get('neighborhood_freq', 8)
        self.amp_percentile = params.get('amp_percentile', 75.0)
        self.max_peaks_per_second = params.get('max_peaks_per_second', 25)

        # Landmark hashing
        self.fanout = params.get('fanout', 8)
        self.dt_min = params.get('dt_min', 0.5)
        self.dt_max = params.get('dt_max', 3.0)
        self.freq_bin_quant = params.get('freq_bin_quant', 2)
        self.time_quant = params.get('time_quant', 20)

        logger.debug(f"Configured audio_fingerprint: sr={self.sr}, threshold={self.threshold}")

    def compare(
        self,
        short_video: str,
        long_video: str,
        start_time: float = None,
        duration: float = None
    ) -> Dict[str, Any]:
        """
        Compare two videos using audio fingerprinting.

        Args:
            short_video: Path to first video
            long_video: Path to second video
            start_time: Not used (full video fingerprinting)
            duration: Not used (full video fingerprinting)

        Returns:
            Dictionary with similarity, accepted, and metadata
        """
        if not SCIPY_AVAILABLE:
            raise ImportError("scipy is required for audio_fingerprint")

        logger.info(f"Extracting fingerprints from {short_video}")
        h1 = self.extract_fingerprints(short_video)

        logger.info(f"Extracting fingerprints from {long_video}")
        h2 = self.extract_fingerprints(long_video)

        logger.info(f"Matching {len(h1)} vs {len(h2)} hashes")
        best_offset, votes, all_offsets = self._match_hashes(h1, h2, top_n=5)

        # Convert offset to seconds
        best_offset_sec = self._offset_to_seconds(best_offset)

        # Similarity = votes (raw vote count, not percentage)
        # For audio fingerprinting, the vote count IS the similarity metric
        similarity = float(votes)
        accepted = votes >= self.threshold

        return {
            'similarity': similarity,
            'accepted': accepted,
            'metadata': {
                'votes': votes,
                'best_offset_seconds': best_offset_sec,
                'top_offsets': [
                    {
                        'offset_seconds': self._offset_to_seconds(off),
                        'votes': v
                    }
                    for off, v in all_offsets
                ],
                'hashes_video1': len(h1),
                'hashes_video2': len(h2),
                'threshold': self.threshold
            }
        }

    def extract_fingerprints(self, video_path: str) -> Dict[int, List[int]]:
        """
        Extract audio fingerprints from video.

        Returns dictionary: hash -> list of timestamps

        This can be called separately to build a fingerprint database
        for efficient N-to-N matching.
        """
        # Extract audio
        audio = self._extract_audio(video_path)

        # Compute spectrogram
        f, t, S_log = self._compute_spectrogram(audio)

        # Pick peaks
        peaks = self._pick_peaks(S_log, f, t)

        # Build landmark hashes
        hashes = self._build_hashes(peaks, t)

        logger.debug(f"Extracted {len(hashes)} unique hashes from {video_path}")

        return hashes

    def _extract_audio(self, video_path: str) -> np.ndarray:
        """Extract audio as PCM float32 mono via ffmpeg."""
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-i", video_path,
            "-vn",  # no video
            "-ac", "1",  # mono
            "-ar", str(self.sr),  # sample rate
            "-f", "f32le",  # float32 little-endian
            "pipe:1",
        ]

        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if p.returncode != 0:
            stderr = p.stderr.decode('utf-8', errors='replace')
            raise RuntimeError(f"ffmpeg failed on {video_path}:\n{stderr}")

        audio = np.frombuffer(p.stdout, dtype=np.float32)

        if audio.size == 0:
            raise RuntimeError(f"No audio samples extracted from {video_path}")

        # Clean and normalize
        audio = np.nan_to_num(audio, nan=0.0, posinf=0.0, neginf=0.0)
        max_val = np.max(np.abs(audio)) + 1e-9
        audio = audio / max_val

        return audio

    def _compute_spectrogram(
        self,
        audio: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Compute STFT spectrogram."""
        f, t, Z = stft(
            audio,
            fs=self.sr,
            nperseg=self.n_fft,
            noverlap=(self.n_fft - self.hop),
            boundary=None,
            padded=False
        )

        S = np.abs(Z)
        S_log = np.log1p(S)  # log compression

        return f, t, S_log

    def _pick_peaks(
        self,
        S_log: np.ndarray,
        f: np.ndarray,
        t: np.ndarray
    ) -> np.ndarray:
        """
        Detect spectral peaks (local maxima).

        Returns Nx2 array: [t_idx, f_idx]
        """
        # Limit frequency range
        max_f_bin = np.searchsorted(f, self.freq_max_hz)
        max_f_bin = max(1, min(max_f_bin, S_log.shape[0]))
        S = S_log[:max_f_bin, :]

        # Local maximum filter
        footprint = (
            2 * self.neighborhood_freq + 1,
            2 * self.neighborhood_time + 1
        )
        local_max = maximum_filter(S, size=footprint, mode="constant")
        peaks_mask = (S == local_max)

        # Amplitude threshold (percentile)
        if np.any(S > 0):
            thresh = np.percentile(S[S > 0], self.amp_percentile)
        else:
            thresh = 0.0
        peaks_mask &= (S >= thresh)

        # Get indices
        f_idx, t_idx = np.where(peaks_mask)

        if t_idx.size == 0:
            return np.zeros((0, 2), dtype=np.int32)

        # Limit density: max peaks per second
        times_sec = t[t_idx]
        sec_bucket = np.floor(times_sec).astype(np.int32)

        # Amplitudes for sorting
        amp = S[f_idx, t_idx]

        # Sort by bucket then amplitude descending
        order = np.lexsort((-amp, sec_bucket))
        sec_bucket = sec_bucket[order]
        t_idx = t_idx[order]
        f_idx = f_idx[order]

        # Keep top N per second
        kept_t = []
        kept_f = []
        counts = {}

        for sb, ti, fi in zip(sec_bucket, t_idx, f_idx):
            c = counts.get(sb, 0)
            if c < self.max_peaks_per_second:
                kept_t.append(ti)
                kept_f.append(fi)
                counts[sb] = c + 1

        peaks = np.stack([
            np.array(kept_t, dtype=np.int32),
            np.array(kept_f, dtype=np.int32)
        ], axis=1)

        return peaks

    def _build_hashes(
        self,
        peaks: np.ndarray,
        times: np.ndarray
    ) -> Dict[int, List[int]]:
        """
        Build landmark hashes from peak pairs.

        Returns dict: hash -> list of anchor timestamps
        """
        if peaks.shape[0] == 0:
            return {}

        # Sort by time
        peaks = peaks[np.argsort(peaks[:, 0])]
        t_idx = peaks[:, 0]
        f_idx = peaks[:, 1]

        # Convert to seconds
        t_sec = times[t_idx]

        hashes: Dict[int, List[int]] = {}

        n = peaks.shape[0]
        for i in range(n):
            t1 = t_sec[i]
            f1 = f_idx[i]

            # Pair with next 'fanout' peaks in time window
            paired = 0
            j = i + 1

            while j < n and paired < self.fanout:
                dt = t_sec[j] - t1

                if dt < self.dt_min:
                    j += 1
                    continue

                if dt > self.dt_max:
                    break

                f2 = f_idx[j]

                # Quantize
                f1q = int(f1 // self.freq_bin_quant)
                f2q = int(f2 // self.freq_bin_quant)
                dtq = int(round(dt * 1000.0 / self.time_quant))

                # Compact hash (32-bit)
                h = (f1q & 0x3FF) | ((f2q & 0x3FF) << 10) | ((dtq & 0xFFF) << 20)

                # Quantized anchor time
                t_anchor_q = int(round(t1 * 1000.0 / self.time_quant))

                hashes.setdefault(h, []).append(t_anchor_q)

                paired += 1
                j += 1

        return hashes

    def _match_hashes(
        self,
        h1: Dict[int, List[int]],
        h2: Dict[int, List[int]],
        top_n: int = 5
    ) -> Tuple[int, int, List[Tuple[int, int]]]:
        """
        Match two hash dictionaries.

        Returns:
            (best_offset, best_votes, top_offsets)
        """
        votes = {}

        # Iterate over smaller dict
        if len(h1) > len(h2):
            h1, h2 = h2, h1

        for h, tlist1 in h1.items():
            tlist2 = h2.get(h)
            if not tlist2:
                continue

            # Limit to prevent explosion
            if len(tlist1) * len(tlist2) > 2000:
                tlist1_s = tlist1[:min(len(tlist1), 50)]
                tlist2_s = tlist2[:min(len(tlist2), 50)]
            else:
                tlist1_s = tlist1
                tlist2_s = tlist2

            # Vote for offsets
            for t1 in tlist1_s:
                for t2 in tlist2_s:
                    off = t2 - t1
                    votes[off] = votes.get(off, 0) + 1

        if not votes:
            return 0, 0, []

        # Top offsets
        top = sorted(votes.items(), key=lambda x: x[1], reverse=True)[:top_n]
        best_offset, best_votes = top[0]

        return best_offset, best_votes, top

    def _offset_to_seconds(self, offset_units: int) -> float:
        """Convert quantized offset to seconds."""
        return (offset_units * self.time_quant) / 1000.0

    @staticmethod
    def compare_features(
        features1: Dict[int, List[int]],
        features2: Dict[int, List[int]],
        threshold: float,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Compare two sets of audio fingerprints.

        Args:
            features1: First fingerprint dict (hash -> timestamps)
            features2: Second fingerprint dict (hash -> timestamps)
            threshold: Minimum votes for match
            params: Optional parameters (time_quant for offset conversion)

        Returns:
            Dictionary with similarity, accepted, and metadata
        """
        # Get time quantization from params (default: 20ms)
        time_quant = params.get('time_quant', 20) if params else 20

        # Match hashes
        votes = {}

        # Iterate over smaller dict
        h1, h2 = (features1, features2) if len(features1) <= len(features2) else (features2, features1)

        for h, tlist1 in h1.items():
            tlist2 = h2.get(h)
            if not tlist2:
                continue

            # Limit to prevent explosion
            if len(tlist1) * len(tlist2) > 2000:
                tlist1_s = tlist1[:min(len(tlist1), 50)]
                tlist2_s = tlist2[:min(len(tlist2), 50)]
            else:
                tlist1_s = tlist1
                tlist2_s = tlist2

            # Vote for offsets
            for t1 in tlist1_s:
                for t2 in tlist2_s:
                    off = t2 - t1
                    votes[off] = votes.get(off, 0) + 1

        if not votes:
            return {
                'similarity': 0.0,
                'accepted': False,
                'metadata': {
                    'votes': 0,
                    'best_offset_seconds': 0.0,
                    'hashes_1': len(features1),
                    'hashes_2': len(features2)
                }
            }

        # Best offset
        best_offset, best_votes = max(votes.items(), key=lambda x: x[1])

        # Convert offset to seconds
        best_offset_sec = (best_offset * time_quant) / 1000.0

        # Similarity = votes (not percentage)
        # For audio fingerprinting, the raw vote count is the similarity metric
        similarity = float(best_votes)
        accepted = best_votes >= threshold

        return {
            'similarity': similarity,
            'accepted': accepted,
            'metadata': {
                'votes': best_votes,
                'best_offset_seconds': best_offset_sec,
                'hashes_1': len(features1),
                'hashes_2': len(features2),
                'threshold': threshold
            }
        }
