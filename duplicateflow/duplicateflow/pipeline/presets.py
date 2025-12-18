"""
Pre-configured pipeline presets for common use cases.

This module provides ready-to-use pipeline configurations optimized
for different scenarios:
- FAST_PRESET: Quick detection (~30s for 1h video)
- BALANCED_PRESET: Balance speed/accuracy (~2min for 1h)
- THOROUGH_PRESET: Maximum accuracy (~5min for 1h)
- MULTIMODAL_PRESET: Visual + audio (~8min for 1h)
- STRUCTURAL_PRESET: Geometric similarity (~2min for 1h)
- HYBRID_PRESET: Subsequence detection (~4min for 1h)
- AUDIO_ADVANCED_PRESET: Advanced audio fingerprinting (~3min for 1h)
- MOTION_INTENSE_PRESET: Dense motion analysis (~6min for 1h)
"""

from typing import Dict, Any


# Fast Preset: ~30 seconds for 1 hour video
# Uses only fast algorithms with optimized parameters
FAST_PRESET = {
    'steps': [
        {
            'algorithm': 'frame_hash',
            'weight': 0.3,
            'threshold': 85,
            'params': {
                'hash_method': 'pHash',
                'num_samples': 8
            }
        },
        {
            'algorithm': 'color_histogram',
            'weight': 0.35,
            'threshold': 70,
            'params': {
                'num_samples': 5,
                'bins': (32, 32, 32)
            }
        },
        {
            'algorithm': 'color_moments',
            'weight': 0.35,
            'threshold': 75,
            'params': {
                'num_samples': 5
            }
        }
    ],
    'global_threshold': 75.0,
    'early_termination': True,
    'early_termination_margin': 10.0
}


# Balanced Preset: ~2 minutes for 1 hour video
# Good balance between speed and accuracy
BALANCED_PRESET = {
    'steps': [
        {
            'algorithm': 'frame_hash',
            'weight': 0.2,
            'threshold': 80,
            'params': {
                'hash_method': 'pHash',
                'num_samples': 8
            }
        },
        {
            'algorithm': 'color_histogram',
            'weight': 0.25,
            'threshold': 70,
            'params': {
                'num_samples': 5,
                'bins': (32, 32, 32)
            }
        },
        {
            'algorithm': 'motion_analysis',
            'weight': 0.25,
            'threshold': 70,
            'params': {
                'num_samples': 5
            }
        },
        {
            'algorithm': 'dct_coefficients',
            'weight': 0.3,
            'threshold': 70,
            'params': {
                'num_coeffs': 64
            }
        }
    ],
    'global_threshold': 70.0,
    'early_termination': True,
    'early_termination_margin': 10.0
}


# Thorough Preset: ~5 minutes for 1 hour video
# Maximum accuracy with perceptual algorithms
THOROUGH_PRESET = {
    'steps': [
        {
            'algorithm': 'frame_hash',
            'weight': 0.15,
            'threshold': 85,
            'params': {
                'hash_method': 'pHash',
                'num_samples': 8
            }
        },
        {
            'algorithm': 'color_histogram',
            'weight': 0.15,
            'threshold': 70,
            'params': {
                'num_samples': 5,
                'bins': (32, 32, 32)
            }
        },
        {
            'algorithm': 'motion_analysis',
            'weight': 0.2,
            'threshold': 70,
            'params': {
                'num_samples': 5
            }
        },
        {
            'algorithm': 'dct_coefficients',
            'weight': 0.15,
            'threshold': 70,
            'params': {
                'num_coeffs': 64
            }
        },
        {
            'algorithm': 'ssim',
            'weight': 0.35,
            'threshold': 0.70,
            'params': {
                'sample_interval': 5.0
            }
        }
    ],
    'global_threshold': 70.0,
    'early_termination': False,
    'early_termination_margin': 10.0
}


# Multimodal Preset: ~8 minutes for 1 hour video
# Combines visual and audio analysis
MULTIMODAL_PRESET = {
    'steps': [
        {
            'algorithm': 'frame_hash',
            'weight': 0.1,
            'threshold': 80,
            'params': {
                'hash_method': 'pHash',
                'num_samples': 8
            }
        },
        {
            'algorithm': 'color_histogram',
            'weight': 0.15,
            'threshold': 70,
            'params': {
                'num_samples': 5,
                'bins': (32, 32, 32)
            }
        },
        {
            'algorithm': 'motion_analysis',
            'weight': 0.15,
            'threshold': 70,
            'params': {
                'num_samples': 5
            }
        },
        {
            'algorithm': 'feature_matching',
            'weight': 0.2,
            'threshold': 30,
            'params': {
                'detector': 'ORB',
                'max_features': 500
            }
        },
        {
            'algorithm': 'ssim',
            'weight': 0.2,
            'threshold': 0.70,
            'params': {
                'sample_interval': 5.0
            }
        },
        {
            'algorithm': 'audio_spectrum',
            'weight': 0.2,
            'threshold': 70,
            'params': {
                'num_samples': 10,
                'sample_duration': 2.0
            }
        }
    ],
    'global_threshold': 70.0,
    'early_termination': False,
    'early_termination_margin': 10.0
}


# Structural Preset: Focus on structural patterns
STRUCTURAL_PRESET = {
    'steps': [
        {
            'algorithm': 'edge_pattern',
            'weight': 0.25,
            'threshold': 70,
            'params': {
                'num_samples': 5,
                'canny_low': 50,
                'canny_high': 150
            }
        },
        {
            'algorithm': 'feature_matching',
            'weight': 0.25,
            'threshold': 30,
            'params': {
                'detector': 'ORB',
                'max_features': 500
            }
        },
        {
            'algorithm': 'hog_descriptor',
            'weight': 0.25,
            'threshold': 70,
            'params': {
                'cell_size': (8, 8),
                'block_size': (2, 2),
                'nbins': 9
            }
        },
        {
            'algorithm': 'template_matching',
            'weight': 0.25,
            'threshold': 80,
            'params': {
                'num_templates': 5,
                'template_size': (64, 64)
            }
        }
    ],
    'global_threshold': 70.0,
    'early_termination': True,
    'early_termination_margin': 10.0
}


# Hybrid Preset: Use hybrid algorithm for long subsequences
HYBRID_PRESET = {
    'steps': [
        {
            'algorithm': 'subsequence_detection',
            'weight': 0.6,
            'threshold': 70,
            'params': {
                'signature_points': 3,
                'hash_weight': 0.6,
                'motion_weight': 0.4
            }
        },
        {
            'algorithm': 'ssim',
            'weight': 0.4,
            'threshold': 0.70,
            'params': {
                'sample_interval': 5.0
            }
        }
    ],
    'global_threshold': 70.0,
    'early_termination': False,
    'early_termination_margin': 10.0
}


# Audio Advanced Preset: Advanced audio duplicate detection at scale
# Uses Shazam-style acoustic fingerprinting for N-to-N matching
AUDIO_ADVANCED_PRESET = {
    'steps': [
        {
            'algorithm': 'audio_fingerprint',
            'weight': 0.5,
            'threshold': 200,
            'params': {
                'sr': 11025,
                'n_fft': 512,
                'hop_length': 64
            }
        },
        {
            'algorithm': 'audio_spectrum',
            'weight': 0.3,
            'threshold': 70,
            'params': {
                'num_samples': 10,
                'sample_duration': 2.0
            }
        },
        {
            'algorithm': 'frame_hash',
            'weight': 0.2,
            'threshold': 80,
            'params': {
                'hash_method': 'pHash',
                'num_samples': 5
            }
        }
    ],
    'global_threshold': 70.0,
    'early_termination': True,
    'early_termination_margin': 10.0
}


# Motion Intense Preset: Advanced motion and temporal analysis
# Uses dense optical flow for complex motion patterns
MOTION_INTENSE_PRESET = {
    'steps': [
        {
            'algorithm': 'optical_flow',
            'weight': 0.35,
            'threshold': 70,
            'params': {
                'num_samples': 5,
                'method': 'farneback'
            }
        },
        {
            'algorithm': 'motion_analysis',
            'weight': 0.30,
            'threshold': 70,
            'params': {
                'num_samples': 5
            }
        },
        {
            'algorithm': 'dct_coefficients',
            'weight': 0.20,
            'threshold': 70,
            'params': {
                'num_coeffs': 64
            }
        },
        {
            'algorithm': 'ssim',
            'weight': 0.15,
            'threshold': 0.70,
            'params': {
                'sample_interval': 5.0
            }
        }
    ],
    'global_threshold': 70.0,
    'early_termination': False,
    'early_termination_margin': 10.0
}


# Map preset names to configurations
PRESETS = {
    'fast': FAST_PRESET,
    'balanced': BALANCED_PRESET,
    'thorough': THOROUGH_PRESET,
    'multimodal': MULTIMODAL_PRESET,
    'structural': STRUCTURAL_PRESET,
    'hybrid': HYBRID_PRESET,
    'audio_advanced': AUDIO_ADVANCED_PRESET,
    'motion_intense': MOTION_INTENSE_PRESET
}


def get_preset(name: str) -> Dict[str, Any]:
    """
    Get preset configuration by name.

    Args:
        name: Preset name (fast, balanced, thorough, multimodal, structural,
              hybrid, audio_advanced, motion_intense)

    Returns:
        Preset configuration dictionary

    Raises:
        ValueError: If preset name not found
    """
    name = name.lower()
    if name not in PRESETS:
        available = ', '.join(PRESETS.keys())
        raise ValueError(
            f"Unknown preset '{name}'. Available presets: {available}"
        )

    return PRESETS[name].copy()


def list_presets() -> list:
    """
    List all available preset names.

    Returns:
        List of preset names
    """
    return list(PRESETS.keys())
