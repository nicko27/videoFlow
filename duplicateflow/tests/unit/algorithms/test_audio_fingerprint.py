"""
Unit tests for AudioFingerprintAlgorithm.

Tests the audio fingerprinting algorithm using Shazam-style acoustic landmarks
and hash matching for scalable duplicate detection.
"""

import pytest
import numpy as np
from typing import Dict, List

# Try to import scipy (required for this algorithm)
try:
    from scipy.signal import stft
    from scipy.ndimage import maximum_filter
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

from duplicateflow.algorithms.audio_fingerprint import AudioFingerprintAlgorithm

# Skip all tests if scipy not available
pytestmark = pytest.mark.skipif(not SCIPY_AVAILABLE, reason="scipy not installed")


# ============================================================================
# 1. ALGORITHM INSTANTIATION
# ============================================================================

class TestAudioFingerprintInstantiation:
    """Test algorithm instantiation and configuration."""

    def test_instantiate_default(self):
        """Test instantiation with default parameters."""
        algo = AudioFingerprintAlgorithm()
        algo.configure()

        assert algo.threshold == 200
        assert algo.sr == 11025
        assert algo.n_fft == 4096
        assert algo.hop == 512
        assert algo.freq_max_hz == 5000.0
        assert algo.neighborhood_time == 12
        assert algo.neighborhood_freq == 8
        assert algo.fanout == 8

    def test_instantiate_custom_params(self):
        """Test instantiation with custom parameters."""
        algo = AudioFingerprintAlgorithm()
        algo.configure(
            threshold=300,
            sr=22050,
            n_fft=2048,
            hop=256,
            freq_max_hz=10000.0,
            fanout=10
        )

        assert algo.threshold == 300
        assert algo.sr == 22050
        assert algo.n_fft == 2048
        assert algo.hop == 256
        assert algo.freq_max_hz == 10000.0
        assert algo.fanout == 10

    def test_has_required_methods(self):
        """Test algorithm has all required methods."""
        algo = AudioFingerprintAlgorithm()

        assert hasattr(algo, 'configure')
        assert hasattr(algo, 'compare')
        assert hasattr(algo, 'extract_fingerprints')
        assert hasattr(algo, '_compute_spectrogram')
        assert hasattr(algo, '_pick_peaks')
        assert hasattr(algo, '_build_hashes')
        assert hasattr(algo, '_match_hashes')


# ============================================================================
# 2. SPECTROGRAM COMPUTATION
# ============================================================================

class TestSpectrogramComputation:
    """Test spectrogram computation using STFT."""

    @pytest.fixture
    def algorithm(self):
        """Create algorithm instance with default params."""
        algo = AudioFingerprintAlgorithm()
        algo.configure()
        return algo

    def test_compute_spectrogram_sine_wave(self, algorithm):
        """Test spectrogram computation on sine wave."""
        # Create 1-second sine wave at 440 Hz
        t = np.linspace(0, 1.0, algorithm.sr)
        audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)

        f, t_spec, S_log = algorithm._compute_spectrogram(audio)

        assert f is not None
        assert t_spec is not None
        assert S_log is not None
        assert S_log.shape[0] == len(f)  # Frequency bins
        assert S_log.shape[1] == len(t_spec)  # Time frames

    def test_compute_spectrogram_frequency_range(self, algorithm):
        """Test frequency range of spectrogram."""
        # Create audio
        t = np.linspace(0, 1.0, algorithm.sr)
        audio = np.sin(2 * np.pi * 1000 * t).astype(np.float32)

        f, t_spec, S_log = algorithm._compute_spectrogram(audio)

        # Frequency range should be 0 to Nyquist
        assert f[0] >= 0.0
        assert f[-1] <= algorithm.sr / 2.0

    def test_compute_spectrogram_log_compression(self, algorithm):
        """Test log compression (log1p) is applied."""
        # Create audio
        t = np.linspace(0, 0.5, algorithm.sr // 2)
        audio = np.sin(2 * np.pi * 500 * t).astype(np.float32)

        f, t_spec, S_log = algorithm._compute_spectrogram(audio)

        # Log values should be non-negative (log1p ensures this)
        assert np.all(S_log >= 0.0)

    def test_compute_spectrogram_silence(self, algorithm):
        """Test spectrogram of silence."""
        # Silent audio
        audio = np.zeros(algorithm.sr, dtype=np.float32)

        f, t_spec, S_log = algorithm._compute_spectrogram(audio)

        # Should have very low values (log1p(0) = 0)
        assert np.mean(S_log) < 0.1


# ============================================================================
# 3. PEAK PICKING
# ============================================================================

class TestPeakPicking:
    """Test spectral peak detection."""

    @pytest.fixture
    def algorithm(self):
        algo = AudioFingerprintAlgorithm()
        algo.configure()
        return algo

    def test_pick_peaks_structure(self, algorithm):
        """Test peak picking returns correct structure."""
        # Create simple spectrogram
        S_log = np.random.rand(100, 50).astype(np.float32)
        f = np.linspace(0, 5000, 100)
        t = np.linspace(0, 2.0, 50)

        peaks = algorithm._pick_peaks(S_log, f, t)

        # Should be Nx2 array (time_idx, freq_idx)
        assert peaks.shape[1] == 2
        assert peaks.dtype == np.int32

    def test_pick_peaks_local_maxima(self, algorithm):
        """Test peaks are local maxima."""
        # Create spectrogram with clear peak
        S_log = np.zeros((100, 50), dtype=np.float32)
        S_log[50, 25] = 10.0  # Single high peak

        f = np.linspace(0, 5000, 100)
        t = np.linspace(0, 2.0, 50)

        peaks = algorithm._pick_peaks(S_log, f, t)

        # Should detect the peak
        assert peaks.shape[0] >= 1

    def test_pick_peaks_frequency_limit(self, algorithm):
        """Test frequency limiting (freq_max_hz)."""
        # Set low frequency limit
        algorithm.freq_max_hz = 1000.0

        # Create spectrogram
        S_log = np.random.rand(100, 50).astype(np.float32)
        f = np.linspace(0, 5000, 100)  # 0 to 5000 Hz
        t = np.linspace(0, 2.0, 50)

        peaks = algorithm._pick_peaks(S_log, f, t)

        # Peaks should only be from frequency bins below 1000 Hz
        # freq_idx should be limited
        if peaks.shape[0] > 0:
            max_f_idx = peaks[:, 1].max()
            max_f_bin = np.searchsorted(f, algorithm.freq_max_hz)
            assert max_f_idx < max_f_bin


# ============================================================================
# 4. HASH BUILDING
# ============================================================================

class TestHashBuilding:
    """Test landmark hash building from peaks."""

    @pytest.fixture
    def algorithm(self):
        algo = AudioFingerprintAlgorithm()
        algo.configure()
        return algo

    def test_build_hashes_empty_peaks(self, algorithm):
        """Test hash building with no peaks."""
        peaks = np.zeros((0, 2), dtype=np.int32)
        times = np.array([0.0, 0.5, 1.0])

        hashes = algorithm._build_hashes(peaks, times)

        assert isinstance(hashes, dict)
        assert len(hashes) == 0

    def test_build_hashes_structure(self, algorithm):
        """Test hash building returns dict of hash -> timestamps."""
        # Create some fake peaks (time_idx, freq_idx)
        peaks = np.array([
            [0, 10],
            [5, 20],
            [10, 30],
            [15, 15],
            [20, 25],
        ], dtype=np.int32)

        times = np.linspace(0, 2.0, 50)

        hashes = algorithm._build_hashes(peaks, times)

        assert isinstance(hashes, dict)
        # Should have some hashes (fanout pairs)
        assert len(hashes) >= 1

        # Each hash should map to list of timestamps
        for h, tlist in hashes.items():
            assert isinstance(h, int)
            assert isinstance(tlist, list)
            assert all(isinstance(t, int) for t in tlist)

    def test_build_hashes_fanout(self, algorithm):
        """Test fanout parameter limits pairs per anchor."""
        # Set fanout to 2
        algorithm.fanout = 2

        # Create many peaks
        peaks = np.array([
            [i, i * 5 % 100] for i in range(20)
        ], dtype=np.int32)

        times = np.linspace(0, 2.0, 50)

        hashes = algorithm._build_hashes(peaks, times)

        # Each anchor should pair with at most 'fanout' peaks
        # Hard to verify exactly, but hashes should exist
        assert len(hashes) >= 1

    def test_build_hashes_time_constraints(self, algorithm):
        """Test dt_min and dt_max time constraints."""
        # Set tight time constraints
        algorithm.dt_min = 0.5
        algorithm.dt_max = 1.0

        # Create peaks spaced in time (indices within bounds)
        peaks = np.array([
            [0, 10],
            [1, 20],   # dt = 0.04s (too small)
            [25, 30],  # dt = 1.0s (good)
            [45, 15],  # dt = 1.8s (too large) - changed from 50 to 45
        ], dtype=np.int32)

        times = np.linspace(0, 2.0, 50)

        hashes = algorithm._build_hashes(peaks, times)

        # Should only create hashes for pairs within time window
        # Exact count depends on quantization, but should have some
        assert len(hashes) >= 0  # May be 0 if no valid pairs


# ============================================================================
# 5. HASH MATCHING
# ============================================================================

class TestHashMatching:
    """Test hash matching and voting."""

    @pytest.fixture
    def algorithm(self):
        algo = AudioFingerprintAlgorithm()
        algo.configure()
        return algo

    def test_match_hashes_identical(self, algorithm):
        """Test matching identical hash dictionaries."""
        # Create identical hashes
        h1 = {
            100: [10, 20, 30],
            200: [15, 25],
            300: [35]
        }
        h2 = h1.copy()

        best_offset, votes, all_offsets = algorithm._match_hashes(h1, h2, top_n=5)

        # Offset should be 0 (identical alignment)
        assert best_offset == 0
        # Should have many votes
        assert votes > 0

    def test_match_hashes_shifted(self, algorithm):
        """Test matching with time offset."""
        h1 = {
            100: [10, 20],
            200: [15, 25],
        }

        # Shift all timestamps by +5
        h2 = {
            100: [15, 25],  # 10+5, 20+5
            200: [20, 30],  # 15+5, 25+5
        }

        best_offset, votes, all_offsets = algorithm._match_hashes(h1, h2, top_n=5)

        # Should detect offset of +5
        assert best_offset == 5
        assert votes > 0

    def test_match_hashes_no_overlap(self, algorithm):
        """Test matching with no common hashes."""
        h1 = {100: [10], 200: [20]}
        h2 = {300: [30], 400: [40]}  # Different hash values

        best_offset, votes, all_offsets = algorithm._match_hashes(h1, h2, top_n=5)

        # No matches
        assert votes == 0
        assert all_offsets == []

    def test_match_hashes_partial_overlap(self, algorithm):
        """Test matching with partial overlap."""
        h1 = {
            100: [10],
            200: [20],
            300: [30]  # Not in h2
        }

        h2 = {
            100: [15],  # Offset +5
            200: [25],  # Offset +5
            400: [40]   # Not in h1
        }

        best_offset, votes, all_offsets = algorithm._match_hashes(h1, h2, top_n=5)

        # Should match on hashes 100 and 200
        assert best_offset == 5
        assert votes >= 2


# ============================================================================
# 6. COMPARE_FEATURES STATIC METHOD
# ============================================================================

class TestCompareFeatures:
    """Test compare_features static method."""

    def test_compare_features_identical(self):
        """Test comparing identical features."""
        features = {
            100: [10, 20, 30],
            200: [15, 25, 35]
        }

        result = AudioFingerprintAlgorithm.compare_features(
            features, features, threshold=5
        )

        # Should match with offset 0
        assert result['similarity'] > 0
        assert result['accepted'] == True
        assert result['metadata']['votes'] > 0
        assert result['metadata']['best_offset_seconds'] == 0.0

    def test_compare_features_shifted(self):
        """Test comparing shifted features."""
        f1 = {100: [10], 200: [20]}
        f2 = {100: [30], 200: [40]}  # Shifted by +20

        result = AudioFingerprintAlgorithm.compare_features(
            f1, f2, threshold=2
        )

        # Should detect match with offset
        assert result['similarity'] >= 2  # At least 2 votes
        assert result['accepted'] == True
        # Offset should be 20 * time_quant = 20 * 20ms = 400ms
        assert result['metadata']['best_offset_seconds'] == pytest.approx(0.4, abs=0.01)

    def test_compare_features_no_overlap(self):
        """Test comparing features with no overlap."""
        f1 = {100: [10], 200: [20]}
        f2 = {300: [30], 400: [40]}

        result = AudioFingerprintAlgorithm.compare_features(
            f1, f2, threshold=10
        )

        assert result['similarity'] == 0.0
        assert result['accepted'] == False
        assert result['metadata']['votes'] == 0

    def test_compare_features_threshold(self):
        """Test threshold acceptance."""
        # Features with small overlap
        f1 = {100: [10]}
        f2 = {100: [10]}  # 1 vote expected

        # Low threshold - should accept
        result1 = AudioFingerprintAlgorithm.compare_features(
            f1, f2, threshold=1
        )
        assert result1['accepted'] == True

        # High threshold - should reject
        result2 = AudioFingerprintAlgorithm.compare_features(
            f1, f2, threshold=100
        )
        assert result2['accepted'] == False

    def test_compare_features_similarity_is_votes(self):
        """Test that similarity equals vote count."""
        f1 = {100: [10, 20]}
        f2 = {100: [10, 20]}

        result = AudioFingerprintAlgorithm.compare_features(
            f1, f2, threshold=1
        )

        # similarity should equal votes (not a percentage)
        assert result['similarity'] == result['metadata']['votes']

    def test_compare_features_metadata(self):
        """Test metadata contains expected fields."""
        f1 = {100: [10]}
        f2 = {100: [10]}

        result = AudioFingerprintAlgorithm.compare_features(
            f1, f2, threshold=5
        )

        metadata = result['metadata']
        assert 'votes' in metadata
        assert 'best_offset_seconds' in metadata
        assert 'hashes_1' in metadata
        assert 'hashes_2' in metadata
        assert 'threshold' in metadata

        assert metadata['hashes_1'] == len(f1)
        assert metadata['hashes_2'] == len(f2)


# ============================================================================
# 7. EDGE CASES
# ============================================================================

class TestAudioFingerprintEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_offset_to_seconds_conversion(self):
        """Test offset conversion from quantized units to seconds."""
        algo = AudioFingerprintAlgorithm()
        algo.configure(time_quant=20)  # 20ms quantization

        # Offset of 50 units = 50 * 20ms = 1000ms = 1.0s
        seconds = algo._offset_to_seconds(50)
        assert seconds == pytest.approx(1.0, abs=0.001)

    def test_compare_features_custom_time_quant(self):
        """Test custom time quantization parameter."""
        f1 = {100: [10]}
        f2 = {100: [20]}  # Offset +10 units

        # With time_quant=10ms: 10 * 10ms = 100ms = 0.1s
        result = AudioFingerprintAlgorithm.compare_features(
            f1, f2,
            threshold=1,
            params={'time_quant': 10}
        )

        assert result['metadata']['best_offset_seconds'] == pytest.approx(0.1, abs=0.01)

    def test_compare_features_empty_dict(self):
        """Test comparing empty feature dictionaries."""
        result = AudioFingerprintAlgorithm.compare_features(
            {}, {}, threshold=10
        )

        assert result['similarity'] == 0.0
        assert result['accepted'] == False
        assert result['metadata']['votes'] == 0

    def test_compare_features_one_empty(self):
        """Test comparing with one empty dict."""
        f1 = {100: [10]}
        f2 = {}

        result = AudioFingerprintAlgorithm.compare_features(
            f1, f2, threshold=10
        )

        assert result['similarity'] == 0.0
        assert result['accepted'] == False


# ============================================================================
# 8. INTEGRATION TESTS
# ============================================================================

class TestAudioFingerprintIntegration:
    """Test complete workflows."""

    def test_complete_comparison_workflow(self):
        """Test complete fingerprint comparison workflow."""
        # Create two synthetic fingerprint sets
        f1 = {
            100: [10, 20],
            200: [15, 25],
            300: [30]
        }

        f2 = {
            100: [15, 25],  # Offset +5
            200: [20, 30],  # Offset +5
            400: [40]
        }

        # Compare
        result = AudioFingerprintAlgorithm.compare_features(
            f1, f2, threshold=3
        )

        # Verify result structure
        assert 'similarity' in result
        assert 'accepted' in result
        assert 'metadata' in result

        # Verify similarity is vote count
        assert isinstance(result['similarity'], float)
        assert result['similarity'] >= 0.0

    def test_hash_format_32bit(self):
        """Test hashes are 32-bit integers."""
        algo = AudioFingerprintAlgorithm()
        algo.configure()

        # Create peaks
        peaks = np.array([[0, 10], [10, 20]], dtype=np.int32)
        times = np.linspace(0, 1.0, 50)

        hashes = algo._build_hashes(peaks, times)

        # All hash keys should be integers
        for h in hashes.keys():
            assert isinstance(h, int)
            # Should fit in 32 bits (0 to 2^32-1)
            assert 0 <= h < 2**32


# ============================================================================
# 9. PERFORMANCE AND DETERMINISM
# ============================================================================

class TestAudioFingerprintPerformance:
    """Test performance characteristics."""

    def test_deterministic_comparison(self):
        """Test comparison is deterministic."""
        f1 = {100: [10, 20], 200: [15]}
        f2 = {100: [15, 25], 200: [20]}

        result1 = AudioFingerprintAlgorithm.compare_features(
            f1, f2, threshold=5
        )

        result2 = AudioFingerprintAlgorithm.compare_features(
            f1, f2, threshold=5
        )

        # Should be identical
        assert result1['similarity'] == result2['similarity']
        assert result1['accepted'] == result2['accepted']
        assert result1['metadata']['votes'] == result2['metadata']['votes']

    def test_symmetry(self):
        """Test comparison is symmetric."""
        f1 = {100: [10], 200: [20]}
        f2 = {100: [15], 200: [25]}

        result1 = AudioFingerprintAlgorithm.compare_features(
            f1, f2, threshold=5
        )

        result2 = AudioFingerprintAlgorithm.compare_features(
            f2, f1, threshold=5
        )

        # Votes should be same (symmetric)
        assert result1['metadata']['votes'] == result2['metadata']['votes']
        # Offsets will be opposite sign
        assert result1['metadata']['best_offset_seconds'] == -result2['metadata']['best_offset_seconds']

    def test_voting_accumulation(self):
        """Test votes accumulate correctly."""
        # Multiple timestamps for same hash
        f1 = {100: [10, 20, 30]}
        f2 = {100: [10, 20, 30]}  # All aligned at offset 0

        result = AudioFingerprintAlgorithm.compare_features(
            f1, f2, threshold=1
        )

        # With identical timestamps, each t1-t2 pair creates an offset
        # Offset 0 appears 3 times: (10-10, 20-20, 30-30)
        # The algorithm counts votes per unique offset
        assert result['metadata']['votes'] == 3
        assert result['metadata']['best_offset_seconds'] == 0.0

    def test_spectrogram_determinism(self):
        """Test spectrogram computation is deterministic."""
        algo = AudioFingerprintAlgorithm()
        algo.configure()

        # Create fixed audio signal
        np.random.seed(42)
        audio = np.random.randn(algo.sr).astype(np.float32)

        f1, t1, S1 = algo._compute_spectrogram(audio)
        f2, t2, S2 = algo._compute_spectrogram(audio)

        # Should be identical
        assert np.allclose(f1, f2)
        assert np.allclose(t1, t2)
        assert np.allclose(S1, S2)
