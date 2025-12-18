"""
Integration module for external detection systems.

Currently supports:
- DuplicateFlow (19 algorithms + 8 presets) via native API

This module now uses DuplicateFlow's native registry API instead of
static metadata copies, ensuring we always have up-to-date algorithm info.
"""

from .duplicateflow_api import (
    DUPLICATEFLOW_AVAILABLE,
    list_algorithms,
    get_algorithm_info,
    get_algorithm_names,
    get_categories,
    algorithm_count,
    get_all_algorithms_dict,
    get_duplicateflow_presets,
    is_duplicateflow_algorithm,
    list_presets,
    get_preset,
)

# Backward compatibility aliases
get_all_algorithms = get_all_algorithms_dict

__all__ = [
    'DUPLICATEFLOW_AVAILABLE',
    'list_algorithms',
    'get_algorithm_info',
    'get_algorithm_names',
    'get_categories',
    'algorithm_count',
    'get_all_algorithms_dict',
    'get_all_algorithms',  # Backward compat
    'get_duplicateflow_presets',
    'is_duplicateflow_algorithm',
    'list_presets',
    'get_preset',
]
