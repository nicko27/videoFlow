"""
DuplicateFlow Native API Adapter

This module provides a clean interface to DuplicateFlow's native registry API,
replacing the old AVAILABLE_METHODS static dictionary approach.

Instead of copying metadata, we query the DuplicateFlow registry directly.
"""

import sys
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import asdict

logger = logging.getLogger('DuplicateFinder.DuplicateFlowAPI')


# Try to load DuplicateFlow
DUPLICATEFLOW_AVAILABLE = False

try:
    # Add duplicateflow to path
    project_root = Path(__file__).parents[4]
    duplicateflow_path = project_root / "duplicateflow"

    if duplicateflow_path.exists() and str(duplicateflow_path) not in sys.path:
        sys.path.insert(0, str(duplicateflow_path))

    from duplicateflow import __version__
    from duplicateflow.core import (
        list_algorithms,
        get_algorithm_info,
        get_algorithm_names,
        get_categories,
        algorithm_count,
    )
    from duplicateflow.pipeline import list_presets, get_preset

    DUPLICATEFLOW_AVAILABLE = True
    logger.info(f"✅ DuplicateFlow API loaded successfully (v{__version__})")

except ImportError as e:
    logger.warning(f"⚠️ DuplicateFlow not available: {e}")

    # Fallback stubs
    def list_algorithms(*args, **kwargs):
        return []

    def get_algorithm_info(name: str):
        raise ValueError(f"DuplicateFlow not available, cannot get algorithm '{name}'")

    def get_algorithm_names():
        return []

    def get_categories():
        return []

    def algorithm_count():
        return 0

    def list_presets():
        return []

    def get_preset(name: str):
        raise ValueError(f"DuplicateFlow not available, cannot get preset '{name}'")


def get_all_algorithms_dict() -> Dict[str, Dict[str, Any]]:
    """
    Get all DuplicateFlow algorithms in the old AVAILABLE_METHODS format.

    This is a compatibility function for code that expects the old dict format.
    Returns a dict mapping algorithm name -> metadata dict.

    Returns:
        Dict mapping algorithm names to metadata dicts with keys:
        - display_name
        - short_name (if available)
        - description
        - detailed_explanation
        - category
        - speed
        - default_params (dict with 'threshold' key)
        - use_case
    """
    if not DUPLICATEFLOW_AVAILABLE:
        return {}

    result = {}

    for algo_dict in list_algorithms():
        # list_algorithms() returns dicts, not AlgorithmInfo objects
        # Get AlgorithmInfo object for detailed_explanation and default_params
        algo_name = algo_dict['name']
        algo_info = get_algorithm_info(algo_name)

        result[algo_name] = {
            'display_name': algo_dict['display_name'],
            'short_name': algo_dict.get('short_name', algo_dict['display_name']),
            'description': algo_dict['description'],
            'detailed_explanation': algo_info.detailed_explanation,
            'category': algo_dict['category'],
            'speed': _map_speed_to_french(algo_dict['speed']),
            'default_params': algo_info.default_params.copy(),
            'use_case': algo_dict.get('use_case', ''),
        }

    return result


def _map_speed_to_french(speed: str) -> str:
    """Map English speed names to French for backward compatibility."""
    mapping = {
        'fast': 'Rapide',
        'medium': 'Moyen',
        'slow': 'Lent',
        'very_slow': 'Très Lent',
    }
    return mapping.get(speed, speed)


def get_duplicateflow_presets() -> Dict[str, Dict]:
    """
    Get all DuplicateFlow presets in PipelineManager format.

    Returns:
        Dict mapping preset name -> preset config with keys:
        - name
        - description
        - mode
        - methods (list of method configs)
    """
    if not DUPLICATEFLOW_AVAILABLE:
        return {}

    presets_dict = {}

    for preset_name in list_presets():
        try:
            preset = get_preset(preset_name)

            # Convert to PipelineManager format
            methods = []
            for algo_config in preset.get('algorithms', []):
                methods.append({
                    'name': algo_config.get('name'),
                    'enabled': algo_config.get('enabled', True),
                    'weight': algo_config.get('weight', 1.0),
                    'parameters': algo_config.get('params', {})
                })

            presets_dict[f"{preset_name} (DuplicateFlow)"] = {
                'name': f"{preset_name} (DuplicateFlow)",
                'description': preset.get('description', f'DuplicateFlow preset: {preset_name}'),
                'mode': preset.get('mode', 'weighting'),
                'methods': methods,
            }
        except Exception as e:
            logger.warning(f"Failed to load preset '{preset_name}': {e}")

    return presets_dict


def is_duplicateflow_algorithm(name: str) -> bool:
    """
    Check if an algorithm name is a DuplicateFlow algorithm.

    Args:
        name: Algorithm name

    Returns:
        True if this is a DuplicateFlow algorithm
    """
    if not DUPLICATEFLOW_AVAILABLE:
        return False

    return name in get_algorithm_names()


__all__ = [
    'DUPLICATEFLOW_AVAILABLE',
    'list_algorithms',
    'get_algorithm_info',
    'get_algorithm_names',
    'get_categories',
    'algorithm_count',
    'get_all_algorithms_dict',
    'get_duplicateflow_presets',
    'is_duplicateflow_algorithm',
    'list_presets',
    'get_preset',
]
