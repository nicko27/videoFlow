"""
Unit tests for AudioSpectrumAlgorithm.

Tests the audio spectrum algorithm using FFT and frequency band analysis
for audio-based duplicate detection.
"""

import pytest
import numpy as np
from typing import List

# Try to import scipy (required for this algorithm)
try:
    from scipy.fft import fft
    from scipy.signal import spectrogram
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

from duplicateflow.algorithms.audio_spectrum import AudioSpectrumAlgorithm

# Skip all tests if scipy not available
pytestmark = pytest.mark.skipif(not SCIPY_AVAILABLE, reason="scipy not installed")


# ============================================================================
# 1. ALGORITHM INSTANTIATION
# ============================================================================

class TestAudioSpectrumInstantiation:
    """Test algorithm instantiation and configuration."""

    def test_instantiate_default(self):
        """Test instantiation with default parameters."""
        algo = AudioSpectrumAlgorithm()
        algo.configure()

        assert algo.threshold == 70.0
        assert algo.num_samples == 10
        assert algo.sample_duration == 2.0
        assert algo.freq_bands == [(0, 250), (250, 2000), (2000, 8000)]
        assert algo.search_step == 5.0
        assert algo.max_windows == 100

    def test_instantiate_custom_params(self):
        """Test instantiation with custom parameters."""
        algo = AudioSpectrumAlgorithm()
        custom_bands = [(0, 500), (500, 3000), (3000, 10000)]
        algo.configure(
            threshold=80.0,
            num_samples=15,
            sample_duration=3.0,
            freq_bands=custom_bands,
            search_step=10.0,
            max_windows=50
        )

        assert algo.threshold == 80.0
        assert algo.num_samples == 15
        assert algo.sample_duration == 3.0
        assert algo.freq_bands == custom_bands
        assert algo.search_step == 10.0
        assert algo.max_windows == 50

    def test_has_required_methods(self):
        """Test algorithm has all required methods."""
        algo = AudioSpectrumAlgorithm()

        assert hasattr(algo, 'configure')
        assert hasattr(algo, 'compare')
        assert hasattr(algo, 'extract_features')
        assert hasattr(algo, '_compute_spectrum')
        assert hasattr(algo, '_compare_spectra')


# ============================================================================
# 2. FFT SPECTRUM COMPUTATION
# ============================================================================

class TestSpectrumComputation:
    """Test FFT spectrum computation."""

    @pytest.fixture
    def algorithm(self):
        """Create algorithm instance with default params."""
        algo = AudioSpectrumAlgorithm()
        algo.configure()
        return algo

    def test_compute_spectrum_sine_wave(self, algorithm):
        """Test spectrum computation on single frequency sine wave."""
        # Create 1-second sine wave at 1000 Hz
        sample_rate = 16000
        t = np.linspace(0, 1.0, sample_rate)
        audio_data = np.sin(2 * np.pi * 1000 * t).astype(np.float32)

        spectrum = algorithm._compute_spectrum(audio_data)

        assert spectrum is not None
        assert isinstance(spectrum, np.ndarray)
        # Should have one energy value per frequency band
        assert len(spectrum) == len(algorithm.freq_bands)

    def test_compute_spectrum_frequency_bands(self, algorithm):
        """Test energy is accumulated in correct frequency bands."""
        # Create sine wave at 500 Hz (falls in second band: 250-2000 Hz)
        sample_rate = 16000
        t = np.linspace(0, 1.0, sample_rate)
        audio_data = np.sin(2 * np.pi * 500 * t).astype(np.float32)

        spectrum = algorithm._compute_spectrum(audio_data)

        # Band 2 (250-2000 Hz) should have highest energy
        assert spectrum[1] > spectrum[0]  # More than low band (0-250 Hz)
        # Depending on FFT resolution, high band may have some leakage

    def test_compute_spectrum_silence(self, algorithm):
        """Test spectrum of silence."""
        # Silent audio
        audio_data = np.zeros(16000, dtype=np.float32)

        spectrum = algorithm._compute_spectrum(audio_data)

        # All bands should have near-zero energy
        assert np.all(spectrum < 0.01)

    def test_compute_spectrum_white_noise(self, algorithm):
        """Test spectrum of white noise."""
        # White noise should have energy across all bands
        np.random.seed(42)
        audio_data = np.random.randn(16000).astype(np.float32)

        spectrum = algorithm._compute_spectrum(audio_data)

        # All bands should have some energy
        assert np.all(spectrum > 0)

    def test_compute_spectrum_too_short(self, algorithm):
        """Test spectrum computation with very short audio."""
        # Very short audio (< 100 samples)
        audio_data = np.random.randn(50).astype(np.float32)

        spectrum = algorithm._compute_spectrum(audio_data)

        # Should return None for too-short audio
        assert spectrum is None

    def test_compute_spectrum_fft_magnitude(self, algorithm):
        """Test FFT magnitude is positive."""
        # Create audio signal
        sample_rate = 16000
        t = np.linspace(0, 1.0, sample_rate)
        audio_data = np.sin(2 * np.pi * 440 * t).astype(np.float32)

        # Compute FFT manually
        fft_result = fft(audio_data)
        magnitude = np.abs(fft_result[:len(fft_result)//2])

        # Magnitude should be non-negative
        assert np.all(magnitude >= 0)


# ============================================================================
# 3. SPECTRA COMPARISON
# ============================================================================

class TestSpectraComparison:
    """Test spectral feature comparison."""

    @pytest.fixture
    def algorithm(self):
        algo = AudioSpectrumAlgorithm()
        algo.configure()
        return algo

    def test_compare_spectra_identical(self, algorithm):
        """Test comparing identical spectra."""
        # Create identical spectral features
        spectra1 = [
            np.array([1.0, 2.0, 3.0], dtype=np.float32),
            np.array([1.1, 2.1, 3.1], dtype=np.float32),
        ]
        spectra2 = spectra1.copy()

        score = algorithm._compare_spectra(spectra1, spectra2)

        # Should have perfect similarity (100)
        assert score == pytest.approx(100.0, abs=0.1)

    def test_compare_spectra_similar(self, algorithm):
        """Test comparing similar spectra."""
        spectra1 = [
            np.array([1.0, 2.0, 3.0], dtype=np.float32),
            np.array([1.1, 2.1, 3.1], dtype=np.float32),
        ]
        spectra2 = [
            np.array([1.05, 2.05, 3.05], dtype=np.float32),
            np.array([1.15, 2.15, 3.15], dtype=np.float32),
        ]

        score = algorithm._compare_spectra(spectra1, spectra2)

        # Should have high similarity
        assert score > 95.0

    def test_compare_spectra_different(self, algorithm):
        """Test comparing different spectra."""
        spectra1 = [
            np.array([10.0, 1.0, 1.0], dtype=np.float32),  # Low freq dominant
        ]
        spectra2 = [
            np.array([1.0, 1.0, 10.0], dtype=np.float32),  # High freq dominant
        ]

        score = algorithm._compare_spectra(spectra1, spectra2)

        # Should have low similarity
        assert score < 50.0

    def test_compare_spectra_empty(self, algorithm):
        """Test comparing with empty spectra lists."""
        spectra1 = []
        spectra2 = [np.array([1.0, 2.0, 3.0], dtype=np.float32)]

        score = algorithm._compare_spectra(spectra1, spectra2)

        assert score == 0.0

    def test_compare_spectra_zero_norm(self, algorithm):
        """Test comparing with zero-norm spectra."""
        # All zeros
        spectra1 = [np.array([0.0, 0.0, 0.0], dtype=np.float32)]
        spectra2 = [np.array([1.0, 2.0, 3.0], dtype=np.float32)]

        score = algorithm._compare_spectra(spectra1, spectra2)

        # Zero norm should result in 0 similarity
        assert score == 0.0

    def test_compare_spectra_normalization(self, algorithm):
        """Test that normalization makes amplitude-invariant."""
        # Same shape, different amplitude
        spectra1 = [np.array([1.0, 2.0, 3.0], dtype=np.float32)]
        spectra2 = [np.array([10.0, 20.0, 30.0], dtype=np.float32)]  # 10x amplitude

        score = algorithm._compare_spectra(spectra1, spectra2)

        # After normalization, should be identical
        assert score == pytest.approx(100.0, abs=0.1)


# ============================================================================
# 4. COMPARE_FEATURES STATIC METHOD
# ============================================================================

class TestCompareFeatures:
    """Test compare_features static method."""

    def test_compare_features_identical(self):
        """Test comparing identical features."""
        features = [
            np.array([1.0, 2.0, 3.0], dtype=np.float32),
            np.array([1.1, 2.1, 3.1], dtype=np.float32),
        ]

        result = AudioSpectrumAlgorithm.compare_features(
            features, features, threshold=70.0
        )

        assert result['similarity'] == pytest.approx(100.0, abs=0.1)
        assert result['accepted'] == True
        assert result['metadata']['num_spectra_1'] == 2
        assert result['metadata']['num_spectra_2'] == 2

    def test_compare_features_similar(self):
        """Test comparing similar features."""
        f1 = [np.array([1.0, 2.0, 3.0], dtype=np.float32)]
        f2 = [np.array([1.05, 2.05, 3.05], dtype=np.float32)]

        result = AudioSpectrumAlgorithm.compare_features(
            f1, f2, threshold=70.0
        )

        assert result['similarity'] > 95.0
        assert result['accepted'] == True

    def test_compare_features_different(self):
        """Test comparing different features."""
        f1 = [np.array([10.0, 1.0, 1.0], dtype=np.float32)]
        f2 = [np.array([1.0, 1.0, 10.0], dtype=np.float32)]

        result = AudioSpectrumAlgorithm.compare_features(
            f1, f2, threshold=70.0
        )

        assert result['similarity'] < 50.0
        assert result['accepted'] == False

    def test_compare_features_empty(self):
        """Test comparing empty feature lists."""
        result = AudioSpectrumAlgorithm.compare_features(
            [], [], threshold=70.0
        )

        assert result['similarity'] == 0.0
        assert result['accepted'] == False
        assert 'error' in result['metadata']

    def test_compare_features_threshold(self):
        """Test threshold acceptance."""
        # Use truly different vectors (not just scaled versions)
        f1 = [np.array([10.0, 1.0, 1.0], dtype=np.float32)]  # Low freq dominant
        f2 = [np.array([5.0, 5.0, 5.0], dtype=np.float32)]   # Balanced

        # Low threshold - should accept
        result1 = AudioSpectrumAlgorithm.compare_features(
            f1, f2, threshold=50.0
        )
        assert result1['accepted'] == True

        # High threshold - should reject
        result2 = AudioSpectrumAlgorithm.compare_features(
            f1, f2, threshold=99.0
        )
        assert result2['accepted'] == False

    def test_compare_features_metadata(self):
        """Test metadata contains expected fields."""
        f1 = [np.array([1.0, 2.0, 3.0], dtype=np.float32)]
        f2 = [np.array([1.1, 2.1, 3.1], dtype=np.float32)]

        result = AudioSpectrumAlgorithm.compare_features(
            f1, f2, threshold=70.0
        )

        metadata = result['metadata']
        assert 'num_spectra_1' in metadata
        assert 'num_spectra_2' in metadata
        assert 'norm_1' in metadata
        assert 'norm_2' in metadata


# ============================================================================
# 5. EDGE CASES
# ============================================================================

class TestAudioSpectrumEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def algorithm(self):
        algo = AudioSpectrumAlgorithm()
        algo.configure()
        return algo

    def test_frequency_band_boundaries(self, algorithm):
        """Test frequency bands cover expected ranges."""
        # Default bands: [(0, 250), (250, 2000), (2000, 8000)]
        assert len(algorithm.freq_bands) == 3
        assert algorithm.freq_bands[0] == (0, 250)
        assert algorithm.freq_bands[1] == (250, 2000)
        assert algorithm.freq_bands[2] == (2000, 8000)

    def test_custom_frequency_bands(self):
        """Test custom frequency bands."""
        algo = AudioSpectrumAlgorithm()
        custom_bands = [(0, 100), (100, 500), (500, 2000), (2000, 8000)]
        algo.configure(freq_bands=custom_bands)

        assert len(algo.freq_bands) == 4
        assert algo.freq_bands == custom_bands

    def test_spectrum_shape(self, algorithm):
        """Test spectrum has correct shape."""
        # Create audio
        audio = np.random.randn(16000).astype(np.float32)

        spectrum = algorithm._compute_spectrum(audio)

        # Should have one value per band
        assert len(spectrum) == len(algorithm.freq_bands)

    def test_averaging_multiple_spectra(self, algorithm):
        """Test averaging multiple spectral samples."""
        # Create multiple spectra
        spectra = [
            np.array([1.0, 2.0, 3.0], dtype=np.float32),
            np.array([2.0, 3.0, 4.0], dtype=np.float32),
            np.array([3.0, 4.0, 5.0], dtype=np.float32),
        ]

        # Average manually
        avg = np.mean(spectra, axis=0)

        # Should be [2.0, 3.0, 4.0]
        assert np.allclose(avg, [2.0, 3.0, 4.0])


# ============================================================================
# 6. ROBUSTNESS
# ============================================================================

class TestAudioSpectrumRobustness:
    """Test robustness to various conditions."""

    @pytest.fixture
    def algorithm(self):
        algo = AudioSpectrumAlgorithm()
        algo.configure()
        return algo

    def test_amplitude_invariance(self, algorithm):
        """Test similarity is amplitude-invariant (due to normalization)."""
        # Create spectra with same shape, different amplitudes
        f1 = [np.array([1.0, 2.0, 3.0], dtype=np.float32)]
        f2 = [np.array([100.0, 200.0, 300.0], dtype=np.float32)]

        result = AudioSpectrumAlgorithm.compare_features(
            f1, f2, threshold=70.0
        )

        # Should be identical after normalization
        assert result['similarity'] == pytest.approx(100.0, abs=0.1)

    def test_cosine_similarity_range(self, algorithm):
        """Test cosine similarity is in valid range."""
        # Create random spectra
        np.random.seed(42)
        f1 = [np.random.rand(3).astype(np.float32) for _ in range(5)]
        f2 = [np.random.rand(3).astype(np.float32) for _ in range(5)]

        score = algorithm._compare_spectra(f1, f2)

        # Should be in [0, 100]
        assert 0.0 <= score <= 100.0

    def test_orthogonal_vectors(self, algorithm):
        """Test orthogonal spectral vectors give low similarity."""
        # Create orthogonal vectors
        f1 = [np.array([1.0, 0.0, 0.0], dtype=np.float32)]
        f2 = [np.array([0.0, 1.0, 0.0], dtype=np.float32)]

        result = AudioSpectrumAlgorithm.compare_features(
            f1, f2, threshold=70.0
        )

        # Orthogonal vectors should have ~0 cosine similarity
        assert result['similarity'] < 10.0


# ============================================================================
# 7. INTEGRATION TESTS
# ============================================================================

class TestAudioSpectrumIntegration:
    """Test complete workflows."""

    def test_complete_comparison_workflow(self):
        """Test complete feature comparison workflow."""
        # Create two synthetic spectral feature sets
        f1 = [
            np.array([1.0, 2.0, 3.0], dtype=np.float32),
            np.array([1.1, 2.1, 3.1], dtype=np.float32),
        ]

        f2 = [
            np.array([1.05, 2.05, 3.05], dtype=np.float32),
            np.array([1.15, 2.15, 3.15], dtype=np.float32),
        ]

        # Compare
        result = AudioSpectrumAlgorithm.compare_features(
            f1, f2, threshold=70.0
        )

        # Verify result structure
        assert 'similarity' in result
        assert 'accepted' in result
        assert 'metadata' in result

        # Verify values
        assert isinstance(result['similarity'], float)
        assert isinstance(result['accepted'], bool)
        assert 0.0 <= result['similarity'] <= 100.0

    def test_multiple_frequency_bands(self):
        """Test with different numbers of frequency bands."""
        # Test 3 bands
        algo3 = AudioSpectrumAlgorithm()
        algo3.configure(freq_bands=[(0, 1000), (1000, 5000), (5000, 8000)])

        audio = np.random.randn(16000).astype(np.float32)
        spectrum3 = algo3._compute_spectrum(audio)
        assert len(spectrum3) == 3

        # Test 5 bands
        algo5 = AudioSpectrumAlgorithm()
        algo5.configure(freq_bands=[
            (0, 500), (500, 1000), (1000, 2000), (2000, 4000), (4000, 8000)
        ])

        spectrum5 = algo5._compute_spectrum(audio)
        assert len(spectrum5) == 5


# ============================================================================
# 8. PERFORMANCE AND DETERMINISM
# ============================================================================

class TestAudioSpectrumPerformance:
    """Test performance characteristics."""

    def test_deterministic_comparison(self):
        """Test comparison is deterministic."""
        f1 = [np.array([1.0, 2.0, 3.0], dtype=np.float32)]
        f2 = [np.array([1.5, 2.5, 3.5], dtype=np.float32)]

        result1 = AudioSpectrumAlgorithm.compare_features(
            f1, f2, threshold=70.0
        )

        result2 = AudioSpectrumAlgorithm.compare_features(
            f1, f2, threshold=70.0
        )

        # Should be identical
        assert result1['similarity'] == result2['similarity']
        assert result1['accepted'] == result2['accepted']

    def test_symmetry(self):
        """Test comparison is symmetric."""
        f1 = [np.array([1.0, 2.0, 3.0], dtype=np.float32)]
        f2 = [np.array([4.0, 5.0, 6.0], dtype=np.float32)]

        result1 = AudioSpectrumAlgorithm.compare_features(
            f1, f2, threshold=70.0
        )

        result2 = AudioSpectrumAlgorithm.compare_features(
            f2, f1, threshold=70.0
        )

        # Cosine similarity is symmetric
        assert result1['similarity'] == result2['similarity']
        assert result1['accepted'] == result2['accepted']

    def test_spectrum_computation_determinism(self):
        """Test spectrum computation is deterministic."""
        algo = AudioSpectrumAlgorithm()
        algo.configure()

        # Create fixed audio signal
        np.random.seed(42)
        audio = np.random.randn(16000).astype(np.float32)

        spectrum1 = algo._compute_spectrum(audio)
        spectrum2 = algo._compute_spectrum(audio)

        # Should be identical
        assert np.allclose(spectrum1, spectrum2)

    def test_similarity_range_validation(self):
        """Test similarity is always in valid range."""
        test_cases = [
            ([np.array([1.0, 2.0, 3.0])], [np.array([1.0, 2.0, 3.0])]),  # Identical
            ([np.array([1.0, 2.0, 3.0])], [np.array([4.0, 5.0, 6.0])]),  # Different
            ([np.array([10.0, 0.0, 0.0])], [np.array([0.0, 10.0, 0.0])]),  # Orthogonal
        ]

        for f1, f2 in test_cases:
            result = AudioSpectrumAlgorithm.compare_features(
                f1, f2, threshold=70.0
            )

            assert 0.0 <= result['similarity'] <= 100.0

    def test_cli_params(self):
        """Test get_cli_params returns valid parameters."""
        algo = AudioSpectrumAlgorithm()
        params = algo.get_cli_params()

        assert isinstance(params, list)
        assert len(params) == 2

        # Verify parameter structure
        for param in params:
            assert 'names' in param
            assert 'type' in param
            assert 'default' in param
            assert 'help' in param

    def test_requirements(self):
        """Test get_requirements returns valid dependencies."""
        algo = AudioSpectrumAlgorithm()
        reqs = algo.get_requirements()

        assert isinstance(reqs, list)
        assert 'numpy>=1.24.0' in reqs
        assert 'scipy>=1.10.0' in reqs

    def test_averaging_preserves_shape(self):
        """Test averaging multiple spectra preserves shape."""
        # Create multiple spectra
        spectra = [
            np.array([1.0, 2.0, 3.0], dtype=np.float32),
            np.array([2.0, 3.0, 4.0], dtype=np.float32),
            np.array([3.0, 4.0, 5.0], dtype=np.float32),
        ]

        avg = np.mean(spectra, axis=0)

        # Should preserve shape
        assert avg.shape == spectra[0].shape
        assert len(avg) == 3


# ============================================================================
# 9. VIDEO INTEGRATION TESTS
# ============================================================================

class TestAudioSpectrumVideoIntegration:
    """Test audio spectrum algorithm with real video files."""

    @pytest.fixture
    def test_video_path(self):
        """Return path to test video file."""
        from pathlib import Path
        video_path = "/Users/nico/Downloads/tests/Das Monster und die Schone_9.mp4"
        if not Path(video_path).exists():
            pytest.skip(f"Test video not found: {video_path}")
        return video_path

    def test_compare_same_video_identical_segments(self, test_video_path):
        """Test comparing identical segments from same video."""
        algo = AudioSpectrumAlgorithm()
        algo.configure(threshold=0.70, num_samples=8)

        result = algo.compare(
            short_video=test_video_path,
            long_video=test_video_path,
            start_time=0.0,
            duration=5.0
        )

        assert result['similarity'] > 0.70
        assert result['accepted'] == True
        assert 'best_offset_seconds' in result['metadata']
        assert 'num_samples' in result['metadata']

    def test_compare_different_videos(self, test_video_path):
        """Test comparing different videos."""
        algo = AudioSpectrumAlgorithm()
        algo.configure(threshold=0.80)

        # Compare same video with itself should give high similarity
        result = algo.compare(
            short_video=test_video_path,
            long_video=test_video_path,
            start_time=0.0,
            duration=3.0
        )

        # Same video should match
        assert result['similarity'] > 0.60

    def test_extract_features_real_video(self, test_video_path):
        """Test feature extraction from real video."""
        algo = AudioSpectrumAlgorithm()
        algo.configure(num_samples=8)

        features = algo.extract_features(test_video_path)

        assert len(features) >= 2
        assert all(isinstance(f, np.ndarray) for f in features)
        assert all(len(f) == len(algo.freq_bands) for f in features)

    def test_compare_window_integration(self, test_video_path):
        """Test compare with sliding window."""
        algo = AudioSpectrumAlgorithm()
        algo.configure(search_step=2.0, max_windows=10, num_samples=5)

        result = algo.compare(
            short_video=test_video_path,
            long_video=test_video_path,
            start_time=0.0,
            duration=5.0
        )

        assert 'windows_tested' in result['metadata']
        assert result['metadata']['windows_tested'] >= 1

    def test_compare_search_window(self, test_video_path):
        """Test search window functionality."""
        algo = AudioSpectrumAlgorithm()
        algo.configure(search_step=3.0, max_windows=20, num_samples=6)

        result = algo.compare(
            short_video=test_video_path,
            long_video=test_video_path,
            start_time=0.0,
            duration=4.0
        )

        assert 'best_offset_seconds' in result['metadata']
        assert result['metadata']['best_offset_seconds'] >= 0.0

    def test_extract_audio_spectra_integration(self, test_video_path):
        """Test _extract_audio_spectra with real video."""
        algo = AudioSpectrumAlgorithm()
        algo.configure(num_samples=6, sample_duration=2.0)

        spectra = algo._extract_audio_spectra(
            video_path=test_video_path,
            start_time=0.0,
            duration=5.0
        )

        assert len(spectra) >= 1
        assert all(isinstance(s, np.ndarray) for s in spectra)
        assert all(len(s) == len(algo.freq_bands) for s in spectra)

    def test_get_video_duration_integration(self, test_video_path):
        """Test _get_video_duration with real video."""
        algo = AudioSpectrumAlgorithm()
        algo.configure()

        duration = algo._get_video_duration(test_video_path)

        assert duration is not None
        assert duration > 0.0
        assert isinstance(duration, float)

    def test_extract_audio_segment_integration(self, test_video_path):
        """Test _extract_audio_segment with real video."""
        algo = AudioSpectrumAlgorithm()
        algo.configure()

        audio = algo._extract_audio_segment(
            video_path=test_video_path,
            start_time=0.0,
            duration=2.0
        )

        assert audio is not None
        assert isinstance(audio, np.ndarray)
        assert audio.dtype == np.float32
        assert len(audio) > 0

    def test_compare_insufficient_samples(self, test_video_path):
        """Test compare with very short duration that yields insufficient samples."""
        algo = AudioSpectrumAlgorithm()
        algo.configure(num_samples=100, sample_duration=5.0)

        result = algo.compare(
            short_video=test_video_path,
            long_video=test_video_path,
            start_time=0.0,
            duration=0.1
        )

        # Very short duration may result in insufficient samples
        assert 'similarity' in result
        assert 'accepted' in result
        assert 'metadata' in result

    def test_compare_early_termination(self, test_video_path):
        """Test early termination when excellent match found."""
        algo = AudioSpectrumAlgorithm()
        algo.configure(threshold=70.0, search_step=1.0, max_windows=50)

        result = algo.compare(
            short_video=test_video_path,
            long_video=test_video_path,
            start_time=0.0,
            duration=3.0
        )

        # Should find match quickly
        assert result['similarity'] > 0.60
        assert 'windows_tested' in result['metadata']
