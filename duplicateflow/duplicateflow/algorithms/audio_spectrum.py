"""
Audio Spectrum Algorithm.

Compare audio spectral characteristics using FFT and mel-frequency analysis.
Effective for detecting scenes with similar audio characteristics.
"""

import subprocess
import tempfile
import os
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

from duplicateflow.core import register_algorithm
from duplicateflow.sdk import Algorithm

# Check for scipy availability
try:
    from scipy.fft import fft
    from scipy.signal import spectrogram
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


@register_algorithm(
    name="audio_spectrum",
    display_name="🎵 Spectre Audio",
    short_name="Audio Spectrum",
    description="Compare les caractéristiques spectrales audio via FFT",
    detailed_explanation=(
        "Extrait l'audio des vidéos, calcule les spectrogrammes via FFT, "
        "puis compare les caractéristiques spectrales moyennes. Utilise "
        "plusieurs bandes de fréquences pour capturer les différentes "
        "composantes audio (basses, mediums, aigus)."
    ),
    category="audio",
    speed="medium",
    default_threshold=70.0,
    default_params={
        'threshold': 70.0,
        'num_samples': 10,
        'sample_duration': 2.0,
        'freq_bands': [(0, 250), (250, 2000), (2000, 8000)],
        'search_step': 5.0,
        'max_windows': 100
    },
    use_case="Scènes avec audio caractéristique (musique, dialogues, ambiance)"
)
class AudioSpectrumAlgorithm(Algorithm):
    """
    Audio spectrum comparison algorithm.

    Extracts audio from videos, computes spectrograms using FFT,
    and compares spectral characteristics across frequency bands.

    Algorithm steps:
    1. Extract audio from both videos using ffmpeg
    2. Sample audio at multiple points
    3. Compute FFT spectrogram for each sample
    4. Calculate mean energy per frequency band
    5. Compare spectral signatures using correlation

    Parameters:
        threshold: Minimum similarity score (0-100)
        num_samples: Number of audio samples to extract
        sample_duration: Duration of each sample (seconds)
        freq_bands: List of (low, high) frequency bands in Hz
        search_step: Sliding window step (seconds)
        max_windows: Maximum windows to test
    """

    def configure(self, **params):
        """Configure algorithm parameters."""
        self.threshold = params.get('threshold', 70.0)
        self.num_samples = params.get('num_samples', 10)
        self.sample_duration = params.get('sample_duration', 2.0)
        self.freq_bands = params.get('freq_bands', [(0, 250), (250, 2000), (2000, 8000)])
        self.search_step = params.get('search_step', 5.0)
        self.max_windows = params.get('max_windows', 100)

    def compare(
        self,
        short_video: str,
        long_video: str,
        start_time: float = 0.0,
        duration: float = None
    ) -> Dict[str, Any]:
        """
        Compare videos using audio spectrum analysis.

        Args:
            short_video: Path to short video
            long_video: Path to long video
            start_time: Start position in long video
            duration: Duration to analyze

        Returns:
            Dictionary with similarity, accepted, metadata
        """
        # Check dependencies
        if not SCIPY_AVAILABLE:
            return {
                'similarity': 0.0,
                'accepted': False,
                'metadata': {
                    'error': 'scipy not installed (required for FFT)',
                    'install': 'pip install scipy'
                }
            }

        # Validate inputs
        self._validate_video_path(short_video)
        self._validate_video_path(long_video)

        # Get duration from short video if not provided
        if duration is None:
            duration = self._get_video_duration(short_video)
            if duration is None:
                return {
                    'similarity': 0.0,
                    'accepted': False,
                    'metadata': {'error': 'Could not determine video duration'}
                }

        self._validate_time_params(start_time, duration)

        # Extract audio spectrum from short video
        short_spectra = self._extract_audio_spectra(short_video, 0, duration)

        if len(short_spectra) < 2:
            return {
                'similarity': 0.0,
                'accepted': False,
                'metadata': {
                    'error': 'Insufficient audio samples',
                    'num_samples': len(short_spectra)
                }
            }

        # Get long video duration
        long_duration = self._get_video_duration(long_video)
        if long_duration is None:
            return {
                'similarity': 0.0,
                'accepted': False,
                'metadata': {'error': 'Could not get long video duration'}
            }

        # Calculate window positions
        searchable = max(long_duration - duration, 0)

        if searchable <= 0:
            window_starts = [start_time]
        else:
            step = max(
                self.search_step,
                searchable / self.max_windows
            ) if self.max_windows else self.search_step
            window_starts = np.arange(start_time, start_time + searchable + 1e-6, step)

        # Sliding window search
        best_score = 0.0
        best_offset = 0.0

        for window_start in window_starts:
            # Extract spectra from this window
            long_spectra = self._extract_audio_spectra(
                long_video, window_start, duration
            )

            if len(long_spectra) < 2:
                continue

            # Compare spectra
            score = self._compare_spectra(short_spectra, long_spectra)

            if score > best_score:
                best_score = score
                best_offset = window_start

            # Early termination
            if score >= self.threshold + 5:
                break

        similarity = best_score / 100.0

        return {
            'similarity': similarity,
            'accepted': best_score >= self.threshold,
            'metadata': {
                'best_offset_seconds': best_offset,
                'num_samples': len(short_spectra),
                'windows_tested': len(window_starts),
                'score_percentage': best_score,
                'freq_bands': self.freq_bands
            }
        }

    def _extract_audio_spectra(
        self,
        video_path: str,
        start_time: float,
        duration: float
    ) -> List[np.ndarray]:
        """
        Extract audio spectral features from video.

        Args:
            video_path: Path to video
            start_time: Start time in video
            duration: Duration to extract

        Returns:
            List of spectral feature vectors
        """
        spectra = []

        # Sample positions
        sample_interval = duration / self.num_samples
        sample_positions = [start_time + i * sample_interval for i in range(self.num_samples)]

        for position in sample_positions:
            try:
                # Extract audio segment using ffmpeg
                audio_data = self._extract_audio_segment(
                    video_path, position, self.sample_duration
                )

                if audio_data is not None:
                    # Compute spectral features
                    spectrum = self._compute_spectrum(audio_data)
                    if spectrum is not None:
                        spectra.append(spectrum)

            except Exception:
                continue

        return spectra

    def _extract_audio_segment(
        self,
        video_path: str,
        start_time: float,
        duration: float
    ) -> Optional[np.ndarray]:
        """
        Extract audio segment from video using ffmpeg.

        Args:
            video_path: Path to video
            start_time: Start time
            duration: Duration

        Returns:
            Audio data as numpy array (mono, 16kHz)
        """
        try:
            # Create temporary WAV file
            temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_path = temp_file.name
            temp_file.close()

            # Extract audio with ffmpeg
            cmd = [
                'ffmpeg', '-ss', str(start_time),
                '-i', video_path,
                '-t', str(duration),
                '-vn',  # No video
                '-acodec', 'pcm_s16le',  # PCM 16-bit
                '-ar', '16000',  # 16kHz sample rate
                '-ac', '1',  # Mono
                '-y',  # Overwrite
                temp_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30,
                check=False
            )

            if result.returncode != 0 or not os.path.exists(temp_path):
                return None

            # Read WAV file
            # Simple WAV reading (skip header, read 16-bit samples)
            with open(temp_path, 'rb') as f:
                # Skip WAV header (44 bytes)
                f.seek(44)
                # Read audio data
                audio_bytes = f.read()

            # Clean up
            os.unlink(temp_path)

            # Convert to numpy array
            audio_data = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
            audio_data = audio_data / 32768.0  # Normalize to [-1, 1]

            return audio_data

        except Exception:
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass
            return None

    def _compute_spectrum(self, audio_data: np.ndarray) -> Optional[np.ndarray]:
        """
        Compute spectral features from audio data.

        Args:
            audio_data: Audio samples (mono, normalized)

        Returns:
            Spectral feature vector (energy per frequency band)
        """
        if len(audio_data) < 100:
            return None

        # Compute FFT
        fft_result = fft(audio_data)
        magnitude = np.abs(fft_result[:len(fft_result)//2])

        # Sample rate is 16kHz
        sample_rate = 16000
        freqs = np.fft.fftfreq(len(audio_data), 1/sample_rate)[:len(magnitude)]

        # Compute energy per frequency band
        features = []
        for low, high in self.freq_bands:
            # Find indices for this band
            band_mask = (freqs >= low) & (freqs < high)
            band_energy = np.mean(magnitude[band_mask]) if np.any(band_mask) else 0.0
            features.append(band_energy)

        return np.array(features, dtype=np.float32)

    def _compare_spectra(
        self,
        spectra1: List[np.ndarray],
        spectra2: List[np.ndarray]
    ) -> float:
        """
        Compare two sets of spectral features.

        Args:
            spectra1: Spectral features from first video
            spectra2: Spectral features from second video

        Returns:
            Similarity score (0-100)
        """
        if not spectra1 or not spectra2:
            return 0.0

        # Average spectra
        avg_spectrum1 = np.mean(spectra1, axis=0)
        avg_spectrum2 = np.mean(spectra2, axis=0)

        # Normalize
        norm1 = np.linalg.norm(avg_spectrum1)
        norm2 = np.linalg.norm(avg_spectrum2)

        if norm1 < 1e-6 or norm2 < 1e-6:
            return 0.0

        avg_spectrum1 = avg_spectrum1 / norm1
        avg_spectrum2 = avg_spectrum2 / norm2

        # Compute cosine similarity
        similarity = np.dot(avg_spectrum1, avg_spectrum2)

        # Convert to 0-100 scale
        return float(max(0.0, min(100.0, similarity * 100.0)))

    def _get_video_duration(self, video_path: str) -> Optional[float]:
        """Get video duration using ffprobe."""
        try:
            cmd = [
                'ffprobe', '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                video_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                check=False
            )

            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())

        except Exception:
            pass

        return None

    def extract_features(self, video_path: str) -> List[np.ndarray]:
        """
        Extract audio spectral features from entire video.

        Args:
            video_path: Path to video

        Returns:
            List of spectral feature vectors
        """
        if not SCIPY_AVAILABLE:
            return []

        # Get video duration
        duration = self._get_video_duration(video_path)
        if duration is None:
            return []

        # Extract spectra from entire video
        spectra = self._extract_audio_spectra(video_path, 0, duration)

        return spectra

    def get_cli_params(self):
        """Return CLI parameters."""
        return [
            {
                'names': ['--audio-num-samples'],
                'type': 'int',
                'default': 10,
                'help': 'Number of audio samples to extract'
            },
            {
                'names': ['--audio-sample-duration'],
                'type': 'float',
                'default': 2.0,
                'help': 'Duration of each audio sample (seconds)'
            }
        ]

    def get_requirements(self):
        """Return package requirements."""
        return [
            'numpy>=1.24.0',
            'scipy>=1.10.0'
        ]

    @staticmethod
    def compare_features(
        features1: List[np.ndarray],
        features2: List[np.ndarray],
        threshold: float,
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Compare two sets of audio spectral features.

        Args:
            features1: List of spectral vectors from first video
            features2: List of spectral vectors from second video
            threshold: Minimum similarity score (0-100)
            params: Optional parameters (not used)

        Returns:
            Dictionary with similarity, accepted, and metadata
        """
        if not features1 or not features2:
            return {
                'similarity': 0.0,
                'accepted': False,
                'metadata': {
                    'error': 'Empty feature sets',
                    'num_spectra_1': len(features1),
                    'num_spectra_2': len(features2)
                }
            }

        # Average spectra
        avg_spectrum1 = np.mean(features1, axis=0)
        avg_spectrum2 = np.mean(features2, axis=0)

        # Normalize
        norm1 = np.linalg.norm(avg_spectrum1)
        norm2 = np.linalg.norm(avg_spectrum2)

        if norm1 < 1e-6 or norm2 < 1e-6:
            return {
                'similarity': 0.0,
                'accepted': False,
                'metadata': {
                    'error': 'Zero norm spectra',
                    'num_spectra_1': len(features1),
                    'num_spectra_2': len(features2)
                }
            }

        norm_spectrum1 = avg_spectrum1 / norm1
        norm_spectrum2 = avg_spectrum2 / norm2

        # Compute cosine similarity
        similarity = np.dot(norm_spectrum1, norm_spectrum2)

        # Convert to 0-100 scale
        similarity_score = float(max(0.0, min(100.0, similarity * 100.0)))

        return {
            'similarity': similarity_score,
            'accepted': similarity_score >= threshold,
            'metadata': {
                'num_spectra_1': len(features1),
                'num_spectra_2': len(features2),
                'norm_1': float(norm1),
                'norm_2': float(norm2)
            }
        }
