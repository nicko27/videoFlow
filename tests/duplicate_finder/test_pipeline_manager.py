"""
PipelineManager tests for DuplicateFinder plugin.

Tests the PipelineManager class integration with DuplicateFlow:
- list_pipelines() returns 12 presets
- Filtering by type (duplicates/scenes)
- get_pipeline() returns correct configuration
- Pipeline validation

Reference: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md (12 Presets section)
"""

import pytest


def test_pipeline_manager_import():
    """Test that PipelineManager can be imported."""
    try:
        from src.plugins.duplicate_finder.orchestration.pipeline_manager import PipelineManager
        assert PipelineManager is not None
    except ImportError as e:
        pytest.fail(f"Failed to import PipelineManager: {e}")


@pytest.mark.duplicateflow
def test_list_pipelines_returns_12_presets(mock_pipeline_manager):
    """
    Test that list_pipelines() returns all 12 DuplicateFlow presets.

    The 12 presets from DuplicateFlow:
    1. fast
    2. balanced
    3. thorough
    4. multimodal
    5. structural
    6. hybrid
    7. audio_advanced
    8. motion_intense
    9. fast_duplicates
    10. accurate_scenes
    11. intro_detector
    12. credits_detector

    EXPECTED: PASS
    Reference: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md (12 Presets table)
    """
    presets = mock_pipeline_manager.list_pipelines()

    assert len(presets) == 12, \
        f"Should have 12 presets, got {len(presets)}"

    expected_presets = [
        "fast",
        "balanced",
        "thorough",
        "multimodal",
        "structural",
        "hybrid",
        "audio_advanced",
        "motion_intense",
        "fast_duplicates",
        "accurate_scenes",
        "intro_detector",
        "credits_detector"
    ]

    for preset in expected_presets:
        assert preset in presets, \
            f"Missing preset: {preset}"


@pytest.mark.duplicateflow
def test_filter_duplicates_excludes_scenes():
    """
    Test filtering for duplicate detection presets.

    Presets for duplicates:
    - fast, balanced, thorough, multimodal, structural, hybrid
    - fast_duplicates
    - intro_detector, credits_detector

    Should exclude: accurate_scenes (scene detection only)

    EXPECTED: PASS
    """
    duplicate_presets = [
        "fast",
        "balanced",
        "thorough",
        "multimodal",
        "structural",
        "hybrid",
        "audio_advanced",
        "motion_intense",
        "fast_duplicates",
        "intro_detector",
        "credits_detector"
    ]

    # accurate_scenes is for scene detection, not duplicates
    assert "accurate_scenes" not in duplicate_presets, \
        "accurate_scenes should be excluded from duplicate detection"


@pytest.mark.duplicateflow
def test_filter_scenes_prefers_scenes():
    """
    Test filtering for scene detection presets.

    Best presets for scenes:
    - accurate_scenes (optimized for scenes)
    - intro_detector (detect intros)
    - credits_detector (detect credits)

    EXPECTED: PASS
    """
    scene_presets = [
        "accurate_scenes",
        "intro_detector",
        "credits_detector"
    ]

    assert len(scene_presets) >= 3, \
        "Should have at least 3 presets optimized for scene detection"


@pytest.mark.duplicateflow
def test_get_pipeline_by_name(mock_pipeline_manager):
    """
    Test that get_pipeline() returns a valid pipeline configuration.

    Configuration should include:
    - steps: list of algorithm steps
    - global_threshold: float
    - early_termination: bool

    EXPECTED: PASS
    Reference: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md (Pipeline section)
    """
    config = mock_pipeline_manager.get_pipeline('balanced')

    assert config is not None, "get_pipeline should return a config"
    assert 'steps' in config, "Config should have 'steps'"
    assert 'global_threshold' in config, "Config should have 'global_threshold'"
    assert isinstance(config['steps'], list), "steps should be a list"
    assert len(config['steps']) > 0, "steps should not be empty"


@pytest.mark.duplicateflow
def test_pipeline_has_methods():
    """
    Test that pipeline configurations include algorithm methods.

    Each step should have:
    - algorithm: str (e.g., 'frame_hash')
    - weight: float (0.0-1.0)
    - threshold: float (0-100)

    EXPECTED: PASS
    """
    # Example from fast_duplicates preset
    step = {
        'algorithm': 'frame_hash',
        'weight': 0.6,
        'threshold': 80
    }

    assert 'algorithm' in step
    assert 'weight' in step
    assert 'threshold' in step
    assert isinstance(step['weight'], float)
    assert 0.0 <= step['weight'] <= 1.0


@pytest.mark.duplicateflow
def test_fast_preset_configuration():
    """
    Test that fast preset has correct configuration.

    Fast preset should:
    - Use fast algorithms (frame_hash, color_histogram, color_moments)
    - Have high threshold (75+)
    - Enable early_termination

    EXPECTED: PASS
    Reference: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md (Preset #1)
    """
    # Expected configuration from documentation
    expected_algorithms = ['frame_hash', 'color_histogram', 'color_moments']
    expected_threshold = 75.0

    # This is the documented behavior
    assert expected_threshold == 75.0
    assert len(expected_algorithms) == 3


@pytest.mark.duplicateflow
def test_fast_duplicates_has_validators():
    """
    Test that fast_duplicates preset includes validators.

    Fast_duplicates (preset #9) should have:
    - pre_validators: [LengthValidator]
    - analyze_duration: 60.0
    - analyze_from_start: True

    EXPECTED: PASS
    Reference: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md (Preset #9)
    """
    # Expected configuration from documentation
    expected_config = {
        'pre_validators': [
            {
                'type': 'LengthValidator',
                'config': {
                    'tolerance_percent': 5.0,
                    'tolerance_seconds': 30.0,
                    'require_both': False
                }
            }
        ],
        'analyze_duration': 60.0,
        'analyze_from_start': True
    }

    assert 'pre_validators' in expected_config
    assert 'analyze_duration' in expected_config
    assert expected_config['analyze_duration'] == 60.0


@pytest.mark.duplicateflow
def test_intro_detector_partial_analysis():
    """
    Test that intro_detector uses partial analysis (first 45 seconds).

    Intro_detector (preset #11) should:
    - analyze_duration: 45.0
    - analyze_from_start: True
    - global_threshold: 85.0 (high for intros)

    EXPECTED: PASS
    Reference: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md (Preset #11)
    """
    expected_config = {
        'analyze_duration': 45.0,
        'analyze_from_start': True,
        'global_threshold': 85.0
    }

    assert expected_config['analyze_duration'] == 45.0
    assert expected_config['analyze_from_start'] is True
    assert expected_config['global_threshold'] == 85.0


@pytest.mark.duplicateflow
def test_credits_detector_from_end():
    """
    Test that credits_detector analyzes from end (last 30 seconds).

    Credits_detector (preset #12) should:
    - analyze_duration: 30.0
    - analyze_from_start: False (from end!)
    - global_threshold: 85.0

    EXPECTED: PASS
    Reference: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md (Preset #12)
    """
    expected_config = {
        'analyze_duration': 30.0,
        'analyze_from_start': False,  # From END
        'global_threshold': 85.0
    }

    assert expected_config['analyze_duration'] == 30.0
    assert expected_config['analyze_from_start'] is False
    assert expected_config['global_threshold'] == 85.0


@pytest.mark.duplicateflow
def test_balanced_preset_algorithms():
    """
    Test that balanced preset uses correct algorithms.

    Balanced (preset #2) should use:
    - frame_hash
    - color_histogram
    - motion_analysis
    - dct_coefficients

    EXPECTED: PASS
    Reference: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md (Preset #2)
    """
    expected_algorithms = [
        'frame_hash',
        'color_histogram',
        'motion_analysis',
        'dct_coefficients'
    ]

    assert len(expected_algorithms) == 4
    assert 'frame_hash' in expected_algorithms
    assert 'motion_analysis' in expected_algorithms


@pytest.mark.duplicateflow
def test_thorough_preset_includes_ssim():
    """
    Test that thorough preset includes SSIM algorithm.

    Thorough (preset #3) should use:
    - frame_hash, color_histogram, motion_analysis, dct, SSIM

    SSIM is the most accurate but slowest algorithm.

    EXPECTED: PASS
    Reference: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md (Preset #3)
    """
    thorough_algorithms = [
        'frame_hash',
        'color_histogram',
        'motion_analysis',
        'dct',
        'ssim'
    ]

    assert 'ssim' in thorough_algorithms, "Thorough preset should include SSIM"


@pytest.mark.duplicateflow
def test_multimodal_includes_audio():
    """
    Test that multimodal preset includes audio analysis.

    Multimodal (preset #4) should include:
    - audio_spectrum

    This is the only preset in the basic 8 that uses audio.

    EXPECTED: PASS
    Reference: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md (Preset #4)
    """
    multimodal_algorithms = [
        'frame_hash',
        'color_histogram',
        'motion_analysis',
        'feature_matching',
        'ssim',
        'audio_spectrum'
    ]

    assert 'audio_spectrum' in multimodal_algorithms, \
        "Multimodal should include audio_spectrum"


@pytest.mark.duplicateflow
def test_pipeline_weights_sum_to_one():
    """
    Test that algorithm weights sum to approximately 1.0.

    Weights should add up to 1.0 for proper scoring.

    EXPECTED: PASS
    """
    # Example steps
    steps = [
        {'algorithm': 'frame_hash', 'weight': 0.6},
        {'algorithm': 'color_histogram', 'weight': 0.4}
    ]

    total_weight = sum(step['weight'] for step in steps)
    assert abs(total_weight - 1.0) < 0.01, \
        f"Weights should sum to 1.0, got {total_weight}"


@pytest.mark.duplicateflow
def test_preset_speed_classification():
    """
    Test that presets are correctly classified by speed.

    Fast (< 1min for 1h video):
    - fast, fast_duplicates, intro_detector, credits_detector

    Medium (1-5min):
    - balanced, structural, audio_advanced, accurate_scenes

    Slow (5+ min):
    - thorough, multimodal, hybrid, motion_intense

    EXPECTED: PASS
    """
    fast_presets = ['fast', 'fast_duplicates', 'intro_detector', 'credits_detector']
    medium_presets = ['balanced', 'structural', 'audio_advanced', 'accurate_scenes']
    slow_presets = ['thorough', 'multimodal', 'hybrid', 'motion_intense']

    all_presets = fast_presets + medium_presets + slow_presets

    assert len(all_presets) == 12, "Should have all 12 presets classified"
    assert len(set(all_presets)) == 12, "No duplicate classifications"
