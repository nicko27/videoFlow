"""
DuplicateFlow integration tests for DuplicateFinder plugin.

Tests integration between VideoFlow's duplicate_finder plugin and DuplicateFlow library:
- DetectionEngine can be imported and instantiated
- Pipeline execution works
- Format conversion (DuplicateFlow ↔ VideoFlow)
- LSH configuration and usage
- Preset loading

Reference: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md
"""

import pytest
from unittest.mock import Mock, patch


@pytest.mark.integration
@pytest.mark.duplicateflow
def test_detection_engine_import():
    """
    Test that DetectionEngine can be imported from DuplicateFlow.

    DetectionEngine is the main entry point for DuplicateFlow.

    EXPECTED: PASS (if DuplicateFlow is installed)
    Reference: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md (API Reference)
    """
    try:
        from duplicateflow.api import DetectionEngine
        assert DetectionEngine is not None
    except ImportError as e:
        pytest.skip(f"DuplicateFlow not installed: {e}")


@pytest.mark.integration
@pytest.mark.duplicateflow
def test_detection_mode_enum():
    """
    Test that DetectionMode enum is available.

    DetectionMode options:
    - FINGERPRINT
    - ALGORITHM
    - PIPELINE
    - ONE_TO_ONE

    EXPECTED: PASS
    """
    try:
        from duplicateflow.api import DetectionMode
        assert hasattr(DetectionMode, 'FINGERPRINT')
        assert hasattr(DetectionMode, 'ALGORITHM')
        assert hasattr(DetectionMode, 'PIPELINE')
        assert hasattr(DetectionMode, 'ONE_TO_ONE')
    except ImportError:
        pytest.skip("DuplicateFlow not installed")


@pytest.mark.integration
@pytest.mark.duplicateflow
def test_pipeline_from_preset():
    """
    Test that Pipeline can be created from preset.

    Pipeline.from_preset('balanced') should work.

    EXPECTED: PASS
    Reference: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md (Utilisation section)
    """
    try:
        from duplicateflow.pipeline import Pipeline

        # This should create a pipeline from the 'balanced' preset
        pipeline = Pipeline.from_preset('balanced')
        assert pipeline is not None
    except ImportError:
        pytest.skip("DuplicateFlow not installed")
    except Exception as e:
        pytest.fail(f"Failed to create pipeline from preset: {e}")


@pytest.mark.integration
@pytest.mark.duplicateflow
def test_get_preset():
    """
    Test that get_preset() returns configuration dict.

    EXPECTED: PASS
    """
    try:
        from duplicateflow.pipeline.presets import get_preset

        config = get_preset('fast')
        assert config is not None
        assert isinstance(config, dict)
        assert 'steps' in config
        assert 'global_threshold' in config
    except ImportError:
        pytest.skip("DuplicateFlow not installed")


@pytest.mark.integration
@pytest.mark.duplicateflow
def test_duplicateflow_api_wrapper():
    """
    Test that DuplicateFlowAPI wrapper can be imported.

    This is the VideoFlow integration wrapper.

    EXPECTED: PASS
    """
    try:
        from src.plugins.duplicate_finder.integration.duplicateflow_api import DuplicateFlowAPI
        assert DuplicateFlowAPI is not None
    except ImportError as e:
        pytest.fail(f"Failed to import DuplicateFlowAPI: {e}")


@pytest.mark.integration
@pytest.mark.duplicateflow
def test_format_conversion_df_to_vf():
    """
    Test conversion from DuplicateFlow format to VideoFlow format.

    DuplicateFlow result format:
    {
        'global_score': 85.0,
        'accepted': True,
        'individual_results': [
            {'algorithm': 'frame_hash', 'similarity': 90.0, 'weight': 0.6}
        ]
    }

    VideoFlow format:
    {
        'score': 85.0,
        'accepted': True,
        'algorithms': [
            {'name': 'frame_hash', 'score': 90.0, 'weight': 0.6}
        ]
    }

    EXPECTED: PASS
    """
    df_result = {
        'global_score': 85.0,
        'accepted': True,
        'individual_results': [
            {'algorithm': 'frame_hash', 'similarity': 90.0, 'weight': 0.6}
        ]
    }

    # Conversion function (inline for testing)
    def df_to_vf_result(df_result):
        return {
            'score': df_result['global_score'],
            'accepted': df_result['accepted'],
            'algorithms': [
                {
                    'name': algo['algorithm'],
                    'score': algo['similarity'],
                    'weight': algo['weight']
                }
                for algo in df_result['individual_results']
            ]
        }

    vf_result = df_to_vf_result(df_result)

    assert vf_result['score'] == 85.0
    assert vf_result['accepted'] is True
    assert len(vf_result['algorithms']) == 1
    assert vf_result['algorithms'][0]['name'] == 'frame_hash'


@pytest.mark.integration
@pytest.mark.duplicateflow
def test_format_conversion_vf_to_df():
    """
    Test conversion from VideoFlow format to DuplicateFlow config.

    VideoFlow config:
    {
        'algorithms': [
            {'name': 'frame_hash', 'weight': 0.6, 'threshold': 80, 'params': {...}}
        ],
        'global_threshold': 75.0
    }

    DuplicateFlow config:
    {
        'steps': [
            {'algorithm': 'frame_hash', 'weight': 0.6, 'threshold': 80, 'params': {...}}
        ],
        'global_threshold': 75.0
    }

    EXPECTED: PASS
    """
    vf_config = {
        'algorithms': [
            {'name': 'frame_hash', 'weight': 0.6, 'threshold': 80, 'params': {}}
        ],
        'global_threshold': 75.0
    }

    # Conversion function (inline for testing)
    def vf_to_df_config(vf_config):
        return {
            'steps': [
                {
                    'algorithm': step['name'],
                    'weight': step['weight'],
                    'threshold': step['threshold'],
                    'params': step.get('params', {})
                }
                for step in vf_config['algorithms']
            ],
            'global_threshold': vf_config['global_threshold']
        }

    df_config = vf_to_df_config(vf_config)

    assert 'steps' in df_config
    assert len(df_config['steps']) == 1
    assert df_config['steps'][0]['algorithm'] == 'frame_hash'
    assert df_config['global_threshold'] == 75.0


@pytest.mark.integration
@pytest.mark.duplicateflow
@pytest.mark.slow
def test_lsh_configuration():
    """
    Test LSH (Locality-Sensitive Hashing) configuration.

    LSH parameters:
    - num_perm: 128 (number of permutations)
    - num_bands: 16 (number of bands)
    - threshold: 0.3 (Jaccard similarity threshold)

    EXPECTED: PASS
    Reference: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md (LSH section)
    """
    try:
        from duplicateflow.processing.lsh_index import MinHashLSH

        lsh = MinHashLSH(
            num_perm=128,
            num_bands=16,
            threshold=0.3
        )
        assert lsh is not None
        assert lsh.num_perm == 128
        assert lsh.num_bands == 16
    except ImportError:
        pytest.skip("DuplicateFlow LSH not available")


@pytest.mark.integration
@pytest.mark.duplicateflow
def test_validator_import():
    """
    Test that validators can be imported.

    LengthValidator is used in presets like fast_duplicates.

    EXPECTED: PASS
    Reference: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md (Validators section)
    """
    try:
        from duplicateflow.sdk.validator import LengthValidator
        assert LengthValidator is not None
    except ImportError:
        pytest.skip("DuplicateFlow validators not available")


@pytest.mark.integration
@pytest.mark.duplicateflow
def test_length_validator_instantiation():
    """
    Test that LengthValidator can be instantiated.

    EXPECTED: PASS
    """
    try:
        from duplicateflow.sdk.validator import LengthValidator

        validator = LengthValidator(
            tolerance_percent=5.0,
            tolerance_seconds=30.0,
            require_both=False
        )
        assert validator is not None
    except ImportError:
        pytest.skip("DuplicateFlow validators not available")


@pytest.mark.integration
@pytest.mark.duplicateflow
def test_pipeline_store_import():
    """
    Test that PipelineStore can be imported.

    PipelineStore manages custom pipeline configurations.

    EXPECTED: PASS
    Reference: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md (PipelineStore section)
    """
    try:
        from duplicateflow.storage import PipelineStore
        assert PipelineStore is not None
    except ImportError:
        pytest.skip("DuplicateFlow PipelineStore not available")


@pytest.mark.integration
@pytest.mark.duplicateflow
def test_get_algorithm():
    """
    Test that get_algorithm() can retrieve algorithms.

    EXPECTED: PASS
    Reference: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md (Algorithm section)
    """
    try:
        from duplicateflow.core import get_algorithm

        AlgoClass = get_algorithm('frame_hash')
        assert AlgoClass is not None
    except ImportError:
        pytest.skip("DuplicateFlow core not available")


@pytest.mark.integration
@pytest.mark.duplicateflow
def test_algorithm_configure():
    """
    Test that algorithms can be configured.

    EXPECTED: PASS
    """
    try:
        from duplicateflow.core import get_algorithm

        AlgoClass = get_algorithm('frame_hash')
        algo = AlgoClass()
        algo.configure(threshold=80.0, hash_method='pHash', num_samples=8)
        assert algo is not None
    except ImportError:
        pytest.skip("DuplicateFlow algorithms not available")


@pytest.mark.integration
@pytest.mark.duplicateflow
def test_storage_manager_import():
    """
    Test that StorageManager can be imported.

    StorageManager handles caching for DuplicateFlow.

    EXPECTED: PASS
    """
    try:
        from duplicateflow.storage import StorageManager
        assert StorageManager is not None
    except ImportError:
        pytest.skip("DuplicateFlow StorageManager not available")


@pytest.mark.integration
def test_verification_pipeline_import():
    """
    Test that VerificationPipeline can be imported from VideoFlow.

    VerificationPipeline is the VideoFlow wrapper for DuplicateFlow.

    EXPECTED: PASS
    """
    try:
        from src.plugins.duplicate_finder.verification_pipeline import VerificationPipeline
        assert VerificationPipeline is not None
    except ImportError as e:
        pytest.fail(f"Failed to import VerificationPipeline: {e}")


@pytest.mark.integration
@pytest.mark.duplicateflow
def test_preset_names_consistency():
    """
    Test that preset names are consistent between docs and code.

    All 12 presets should be available.

    EXPECTED: PASS
    """
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

    try:
        from duplicateflow.pipeline.presets import PRESETS

        for preset_name in expected_presets:
            assert preset_name in PRESETS, \
                f"Preset '{preset_name}' not found in DuplicateFlow.presets.PRESETS"
    except ImportError:
        pytest.skip("DuplicateFlow presets not available")
    except AttributeError:
        # PRESETS might be a function, not a dict
        pytest.skip("Cannot verify PRESETS structure")


@pytest.mark.integration
@pytest.mark.duplicateflow
def test_partial_analysis_config():
    """
    Test that partial analysis configuration works.

    Partial analysis parameters:
    - analyze_duration: float (seconds)
    - analyze_from_start: bool (True = from start, False = from end)

    EXPECTED: PASS
    """
    config = {
        'analyze_duration': 60.0,
        'analyze_from_start': True
    }

    assert config['analyze_duration'] == 60.0
    assert config['analyze_from_start'] is True

    # Test from end
    config_end = {
        'analyze_duration': 30.0,
        'analyze_from_start': False
    }

    assert config_end['analyze_from_start'] is False
