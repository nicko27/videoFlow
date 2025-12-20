# Phase 7: Algorithm Testing Plan

**Date**: 2025-12-20
**Status**: PLANNING
**Goal**: Increase algorithm coverage from 10-17% to 60%+
**Current Overall Coverage**: 24.2%

---

## 🎯 Objective

**Current State:**
- Phase 5 Complete: Service Layer at 92.8% average ✅
- Phase 6 Complete: CLI Commands at 82.8% average ✅
- **Algorithms Coverage: 10-17%** ❌ (NEEDS TESTING)
- Overall Coverage: 24.2%

**Phase 7 Goal:**
- Create comprehensive tests for all 14 core algorithms
- Increase algorithm coverage to **60%+** per algorithm
- Increase overall project coverage to **35%+**
- Follow established testing patterns from previous phases

---

## 📊 Current Algorithm Coverage

| Algorithm | Lines | Current Coverage | Target Coverage | Priority |
|-----------|-------|-----------------|-----------------|----------|
| frame_hash.py | 145 | 13% | 60%+ | HIGH |
| ssim.py | 136 | 15% | 60%+ | HIGH |
| color_histogram.py | 119 | 15% | 60%+ | MEDIUM |
| hog_descriptor.py | 119 | 15% | 60%+ | MEDIUM |
| color_moments.py | 129 | 14% | 60%+ | MEDIUM |
| dct_coefficients.py | 137 | 13% | 60%+ | MEDIUM |
| edge_pattern.py | 137 | 13% | 60%+ | MEDIUM |
| template_matching.py | 133 | 13% | 60%+ | MEDIUM |
| feature_matching.py | 173 | 10% | 60%+ | LOW |
| motion_analysis.py | 115 | 14% | 60%+ | LOW |
| optical_flow.py | 111 | 14% | 60%+ | LOW |
| audio_fingerprint.py | 185 | 14% | 60%+ | LOW |
| audio_spectrum.py | 157 | 17% | 60%+ | LOW |
| subsequence_detection.py | 209 | 10% | 60%+ | LOW |

**Total Algorithm Lines:** ~2,005
**Current Average:** 13.6%
**Target Average:** 60%+

---

## 🏗️ Testing Strategy

### Core Principle: Test Real Algorithm Behavior

Unlike services (which we mocked), algorithms need **integration-style tests** with real inputs:

1. **Load Real Test Videos** - Use small test video files (1-2 seconds)
2. **Test Actual Processing** - Run algorithms on real frames
3. **Verify Output Structure** - Check AlgorithmResult format
4. **Test Edge Cases** - Black frames, solid colors, invalid inputs
5. **Test Performance** - Verify execution time is reasonable

### Test Pattern for Each Algorithm

```python
"""
Unit tests for [AlgorithmName].

Tests the [description] algorithm for video similarity detection.
"""

import pytest
import numpy as np
from pathlib import Path
from PIL import Image

from duplicateflow.algorithms.[algorithm_name] import [AlgorithmClass]
from duplicateflow.core.models import AlgorithmResult


class Test[AlgorithmClass]Instantiation:
    """Test algorithm instantiation and configuration."""

    def test_init_default_params(self):
        """Test initialization with default parameters."""
        algo = [AlgorithmClass]()
        assert algo.name == "[algorithm_name]"
        assert algo.weight == 1.0
        assert algo.threshold == 70.0

    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        algo = [AlgorithmClass](
            weight=0.5,
            threshold=80.0,
            enabled=True,
            params={"custom_param": 123}
        )
        assert algo.weight == 0.5
        assert algo.threshold == 80.0
        assert algo.enabled is True
        assert algo.params["custom_param"] == 123


class Test[AlgorithmClass]Compute:
    """Test compute method with real data."""

    @pytest.fixture
    def algorithm(self):
        """Algorithm instance for testing."""
        return [AlgorithmClass]()

    @pytest.fixture
    def sample_frame(self):
        """Create a sample frame (numpy array)."""
        # Create 640x480 RGB frame
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        return frame

    @pytest.fixture
    def identical_frames(self):
        """Create two identical frames."""
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        return frame, frame.copy()

    @pytest.fixture
    def different_frames(self):
        """Create two completely different frames."""
        frame1 = np.zeros((480, 640, 3), dtype=np.uint8)  # Black
        frame2 = np.ones((480, 640, 3), dtype=np.uint8) * 255  # White
        return frame1, frame2

    def test_compute_identical_frames(self, algorithm, identical_frames):
        """Test computation with identical frames."""
        frame1, frame2 = identical_frames

        result = algorithm.compute(frame1, frame2)

        # Verify result structure
        assert isinstance(result, AlgorithmResult)
        assert result.algorithm == "[algorithm_name]"
        assert result.similarity >= 95.0  # Should be very high
        assert result.accepted is True
        assert result.execution_time_ms > 0

    def test_compute_different_frames(self, algorithm, different_frames):
        """Test computation with completely different frames."""
        frame1, frame2 = different_frames

        result = algorithm.compute(frame1, frame2)

        assert isinstance(result, AlgorithmResult)
        assert result.similarity <= 10.0  # Should be very low
        assert result.accepted is False

    def test_compute_result_structure(self, algorithm, sample_frame):
        """Test that result has all required fields."""
        frame = sample_frame

        result = algorithm.compute(frame, frame)

        assert hasattr(result, 'algorithm')
        assert hasattr(result, 'similarity')
        assert hasattr(result, 'accepted')
        assert hasattr(result, 'execution_time_ms')
        assert hasattr(result, 'weight')
        assert hasattr(result, 'metadata')


class Test[AlgorithmClass]EdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def algorithm(self):
        return [AlgorithmClass]()

    def test_compute_black_frames(self, algorithm):
        """Test with all-black frames."""
        black1 = np.zeros((480, 640, 3), dtype=np.uint8)
        black2 = np.zeros((480, 640, 3), dtype=np.uint8)

        result = algorithm.compute(black1, black2)

        # Should handle gracefully (identical blacks = 100% similarity)
        assert result.similarity >= 99.0

    def test_compute_white_frames(self, algorithm):
        """Test with all-white frames."""
        white1 = np.ones((480, 640, 3), dtype=np.uint8) * 255
        white2 = np.ones((480, 640, 3), dtype=np.uint8) * 255

        result = algorithm.compute(white1, white2)

        assert result.similarity >= 99.0

    def test_compute_single_color_frames(self, algorithm):
        """Test with solid color frames."""
        red1 = np.zeros((480, 640, 3), dtype=np.uint8)
        red1[:, :, 0] = 255  # Red channel
        red2 = red1.copy()

        result = algorithm.compute(red1, red2)

        assert result.similarity >= 99.0

    def test_compute_different_sizes(self, algorithm):
        """Test with different frame sizes (should handle or raise error)."""
        frame1 = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        frame2 = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)

        # Depending on implementation, may resize or raise error
        # Test the actual behavior
        try:
            result = algorithm.compute(frame1, frame2)
            # If it succeeds, verify result
            assert isinstance(result, AlgorithmResult)
        except (ValueError, RuntimeError):
            # If it raises, that's also valid behavior
            pass

    def test_compute_invalid_input_none(self, algorithm):
        """Test with None input."""
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        with pytest.raises((ValueError, TypeError, AttributeError)):
            algorithm.compute(None, frame)

    def test_compute_invalid_input_wrong_shape(self, algorithm):
        """Test with wrong shape (not 3D array)."""
        invalid = np.random.randint(0, 255, (640, 3), dtype=np.uint8)  # 2D instead of 3D
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        # Should handle gracefully or raise appropriate error
        try:
            result = algorithm.compute(invalid, frame)
        except (ValueError, RuntimeError, IndexError):
            pass  # Expected


class Test[AlgorithmClass]Helpers:
    """Test helper methods (if any)."""

    def test_preprocess_frame(self):
        """Test frame preprocessing (if applicable)."""
        pass

    def test_extract_features(self):
        """Test feature extraction (if applicable)."""
        pass

    def test_calculate_similarity(self):
        """Test similarity calculation (if applicable)."""
        pass
```

---

## 📝 Implementation Plan

### Priority 1: Core Visual Algorithms (Week 1)

These are the most critical algorithms used in standard duplicate detection:

#### 1. test_frame_hash.py (~400 lines, 18+ tests)
- **Why Important**: Most basic and fastest algorithm, used in all presets
- **Tests**: Perceptual hash, identical frames, rotations, crops, resizing
- **Coverage Target**: 70%+

#### 2. test_ssim.py (~400 lines, 18+ tests)
- **Why Important**: Structural similarity, core quality metric
- **Tests**: Identical, compressed, noise, brightness changes
- **Coverage Target**: 70%+

### Priority 2: Color-Based Algorithms (Week 1)

#### 3. test_color_histogram.py (~350 lines, 15+ tests)
- **Tests**: Color distribution, lighting changes, color shifts
- **Coverage Target**: 65%+

#### 4. test_color_moments.py (~350 lines, 15+ tests)
- **Tests**: Mean/std/skew of color channels
- **Coverage Target**: 65%+

### Priority 3: Pattern-Based Algorithms (Week 2)

#### 5. test_dct_coefficients.py (~350 lines, 15+ tests)
- **Tests**: Frequency domain analysis
- **Coverage Target**: 60%+

#### 6. test_edge_pattern.py (~350 lines, 15+ tests)
- **Tests**: Edge detection, structure matching
- **Coverage Target**: 60%+

#### 7. test_hog_descriptor.py (~350 lines, 15+ tests)
- **Tests**: Histogram of oriented gradients
- **Coverage Target**: 60%+

### Priority 4: Advanced Visual Algorithms (Week 2)

#### 8. test_template_matching.py (~350 lines, 15+ tests)
- **Coverage Target**: 60%+

#### 9. test_feature_matching.py (~400 lines, 18+ tests)
- **Tests**: SIFT/ORB/AKAZE feature matching
- **Coverage Target**: 60%+

### Priority 5: Motion-Based Algorithms (Week 3)

#### 10. test_motion_analysis.py (~350 lines, 15+ tests)
- **Coverage Target**: 60%+

#### 11. test_optical_flow.py (~350 lines, 15+ tests)
- **Coverage Target**: 60%+

### Priority 6: Audio Algorithms (Week 3)

#### 12. test_audio_fingerprint.py (~400 lines, 18+ tests)
- **Coverage Target**: 60%+

#### 13. test_audio_spectrum.py (~350 lines, 15+ tests)
- **Coverage Target**: 60%+

### Priority 7: Special Detection (Week 3)

#### 14. test_subsequence_detection.py (~450 lines, 20+ tests)
- **Tests**: Scene matching, subsequence detection
- **Coverage Target**: 60%+

---

## 📁 Test Data Requirements

### Create Test Assets

```bash
duplicateflow/tests/assets/
├── videos/
│   ├── sample_1sec.mp4 (1 second, 720p, simple scene)
│   ├── sample_black.mp4 (1 second, black frames)
│   ├── sample_white.mp4 (1 second, white frames)
│   ├── sample_red.mp4 (1 second, red frames)
│   └── sample_noise.mp4 (1 second, random noise)
├── frames/
│   ├── frame_black.png (all black)
│   ├── frame_white.png (all white)
│   ├── frame_red.png (solid red)
│   ├── frame_gradient.png (color gradient)
│   └── frame_pattern.png (checkerboard or pattern)
└── audio/
    ├── silence.wav
    ├── tone_440hz.wav
    └── noise.wav
```

### Frame Generation Utilities

```python
# duplicateflow/tests/utils/frame_generator.py

import numpy as np
from PIL import Image

def create_black_frame(width=640, height=480):
    """Create all-black frame."""
    return np.zeros((height, width, 3), dtype=np.uint8)

def create_white_frame(width=640, height=480):
    """Create all-white frame."""
    return np.ones((height, width, 3), dtype=np.uint8) * 255

def create_color_frame(width=640, height=480, r=0, g=0, b=0):
    """Create solid color frame."""
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:, :, 0] = r
    frame[:, :, 1] = g
    frame[:, :, 2] = b
    return frame

def create_noise_frame(width=640, height=480):
    """Create random noise frame."""
    return np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)

def create_gradient_frame(width=640, height=480):
    """Create horizontal gradient frame."""
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    for x in range(width):
        intensity = int((x / width) * 255)
        frame[:, x, :] = intensity
    return frame

def add_noise(frame, noise_level=10):
    """Add random noise to frame."""
    noise = np.random.randint(-noise_level, noise_level, frame.shape, dtype=np.int16)
    noisy = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return noisy

def adjust_brightness(frame, factor=1.2):
    """Adjust frame brightness."""
    adjusted = np.clip(frame.astype(np.float32) * factor, 0, 255).astype(np.uint8)
    return adjusted
```

---

## ✅ Success Criteria

1. **All 14 algorithm test files created** (~5,200 lines total)
2. **All tests passing** (230+ tests)
3. **Each algorithm reaches 60%+ coverage**
4. **Overall project coverage reaches 35%+** (from 24.2%)
5. **No existing tests broken**
6. **Documentation updated** (PHASE7_COMPLETE_SUMMARY.md)
7. **Test utilities created** (frame_generator.py)

---

## 📊 Expected Coverage Impact

### Before Phase 7:
- Overall Coverage: **24.2%**
- Algorithms Coverage: **13.6%** average

### After Phase 7:
- Overall Coverage: **35%+** (estimated)
- Algorithms Coverage: **60%+** per algorithm

### Coverage Breakdown After Phase 7:

| Component | Lines | Before | After | Change |
|-----------|-------|--------|-------|--------|
| Models | ~600 | 95-100% | 95-100% | - |
| Services | ~600 | 92.8% | 92.8% | - |
| CLI Commands | ~700 | 82.8% | 82.8% | - |
| **Algorithms** | **~2,005** | **13.6%** | **60%+** | **+46%** |
| Processing | ~900 | 0% | 0% | - |
| Storage | ~400 | 20% | 20% | - |
| **Total** | **~7,248** | **24.2%** | **~35%** | **+11%** |

---

## 🔧 Implementation Steps

### Step 1: Create Test Utilities
```bash
# Create test utilities directory
mkdir -p duplicateflow/tests/utils
touch duplicateflow/tests/utils/__init__.py
touch duplicateflow/tests/utils/frame_generator.py
```

### Step 2: Create Priority 1 Tests (frame_hash, ssim)
```bash
mkdir -p duplicateflow/tests/unit/algorithms
touch duplicateflow/tests/unit/algorithms/__init__.py
touch duplicateflow/tests/unit/algorithms/test_frame_hash.py
touch duplicateflow/tests/unit/algorithms/test_ssim.py
```

### Step 3: Run Tests and Verify Coverage
```bash
pytest duplicateflow/tests/unit/algorithms/ -v \
  --cov=duplicateflow/algorithms \
  --cov-report=term-missing
```

### Step 4: Create Priority 2-7 Tests
Continue creating test files for remaining algorithms

### Step 5: Create Documentation
```bash
touch duplicateflow/docs/PHASE7_COMPLETE_SUMMARY.md
```

### Step 6: Git Commit
```bash
git add duplicateflow/tests/unit/algorithms/
git add duplicateflow/tests/utils/
git add duplicateflow/docs/PHASE7_COMPLETE_SUMMARY.md
git commit -m "Phase 7 Complete: Algorithm Testing (60%+ per algorithm, 35%+ overall)"
```

---

## 🎯 Phase 7 Estimated Effort

| Task | Files | Lines | Time Estimate |
|------|-------|-------|--------------|
| Test utilities | 1 | ~200 | 1 hour |
| Priority 1 (frame_hash, ssim) | 2 | ~800 | 4 hours |
| Priority 2 (color algorithms) | 2 | ~700 | 3 hours |
| Priority 3 (pattern algorithms) | 3 | ~1,050 | 5 hours |
| Priority 4 (advanced visual) | 2 | ~750 | 4 hours |
| Priority 5 (motion algorithms) | 2 | ~700 | 3 hours |
| Priority 6 (audio algorithms) | 2 | ~750 | 4 hours |
| Priority 7 (subsequence) | 1 | ~450 | 2 hours |
| Documentation | 1 | ~500 | 1 hour |
| Testing & Fixes | - | - | 3 hours |
| **Total** | **15** | **~5,900** | **~30 hours** |

---

## 🚀 Why This Approach Works

1. **Real Integration Tests**: Algorithms tested with actual frame data
2. **Comprehensive Edge Cases**: Black/white frames, noise, size variations
3. **Reusable Utilities**: frame_generator.py creates test frames programmatically
4. **Prioritized Implementation**: Core algorithms first, advanced features later
5. **Measurable Progress**: Each algorithm can be tested independently
6. **No External Dependencies**: Test frames generated in code (no large video files)
7. **Fast Execution**: Small synthetic frames (640x480), quick computation

---

## 📈 Alternative: Simplified Approach

If 60%+ per algorithm is too ambitious, we can target **40%+** instead:

- **40%+ target**: ~15 tests per algorithm, ~250 lines each
- **Total**: ~3,500 lines of test code
- **Effort**: ~18 hours instead of 30 hours
- **Result**: 30% overall coverage instead of 35%

---

## 🎉 Phase 7 Success Definition

**Minimum Success:**
- 10/14 algorithms at 60%+ coverage
- Overall coverage at 32%+
- 200+ new tests created

**Target Success:**
- 12/14 algorithms at 60%+ coverage
- Overall coverage at 35%+
- 230+ new tests created

**Exceptional Success:**
- 14/14 algorithms at 60%+ coverage
- Overall coverage at 38%+
- 250+ new tests created

**Ready for implementation!** 🚀
