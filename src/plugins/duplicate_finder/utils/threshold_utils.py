"""
Threshold normalization utilities.

CORRECTION BUG #6: Centralized threshold conversion to handle mixed usage.

This module provides utilities to normalize thresholds between different ranges:
- UI/Database: 0-100 (percentage, user-friendly)
- Algorithms: 0.0-1.0 (decimal, standard for scientific libraries)

Usage:
    from ..utils.threshold_utils import normalize_threshold, to_percentage, to_decimal

    # Convert from any format to decimal (0.0-1.0)
    threshold_decimal = normalize_threshold(85)  # 85% → 0.85
    threshold_decimal = normalize_threshold(0.85)  # 0.85 → 0.85

    # Convert to percentage (0-100)
    threshold_pct = to_percentage(0.85)  # 0.85 → 85.0

    # Convert to decimal (0.0-1.0)
    threshold_dec = to_decimal(85)  # 85 → 0.85
"""

from typing import Union


def normalize_threshold(value: Union[int, float], input_range: str = 'auto') -> float:
    """
    Normalize threshold to decimal range [0.0, 1.0].

    CORRECTION BUG #6: Auto-detect and convert thresholds to standard range.

    Args:
        value: Threshold value (can be 0-100 or 0.0-1.0)
        input_range: 'auto', 'percentage' (0-100), or 'decimal' (0.0-1.0)

    Returns:
        Normalized threshold in [0.0, 1.0] range

    Examples:
        >>> normalize_threshold(85)       # Auto-detect: 85% → 0.85
        0.85
        >>> normalize_threshold(0.85)     # Auto-detect: already decimal
        0.85
        >>> normalize_threshold(100)      # Edge case: 100% → 1.0
        1.0
        >>> normalize_threshold(1.0)      # Edge case: already 1.0
        1.0
    """
    if value is None:
        return 0.0

    # Auto-detect range
    if input_range == 'auto':
        # If value > 1.0, it's likely a percentage
        if value > 1.0:
            input_range = 'percentage'
        else:
            # Ambiguous case (0.0-1.0 could be either)
            # Assume decimal if <= 1.0
            input_range = 'decimal'

    # Convert based on detected/specified range
    if input_range == 'percentage':
        # Convert from 0-100 to 0.0-1.0
        decimal_value = float(value) / 100.0
    else:
        # Already in decimal range
        decimal_value = float(value)

    # Clamp to valid range [0.0, 1.0]
    return max(0.0, min(decimal_value, 1.0))


def to_percentage(value: Union[int, float]) -> float:
    """
    Convert threshold to percentage range [0, 100].

    Args:
        value: Threshold value (auto-detects if decimal or percentage)

    Returns:
        Threshold in [0, 100] range

    Examples:
        >>> to_percentage(0.85)    # 0.85 → 85.0
        85.0
        >>> to_percentage(85)      # Already percentage
        85.0
        >>> to_percentage(1.0)     # 1.0 → 100.0
        100.0
    """
    if value is None:
        return 0.0

    # If already in percentage range (> 1.0), return as-is
    if value > 1.0:
        return max(0.0, min(float(value), 100.0))

    # Convert from decimal to percentage
    percentage = float(value) * 100.0
    return max(0.0, min(percentage, 100.0))


def to_decimal(value: Union[int, float]) -> float:
    """
    Convert threshold to decimal range [0.0, 1.0].

    Alias for normalize_threshold() with clearer name.

    Args:
        value: Threshold value (auto-detects if decimal or percentage)

    Returns:
        Threshold in [0.0, 1.0] range

    Examples:
        >>> to_decimal(85)     # 85% → 0.85
        0.85
        >>> to_decimal(0.85)   # Already decimal
        0.85
    """
    return normalize_threshold(value, input_range='auto')


def validate_threshold(value: Union[int, float], value_range: str = 'auto') -> bool:
    """
    Validate that threshold is within acceptable range.

    Args:
        value: Threshold value to validate
        value_range: 'auto', 'percentage' (0-100), or 'decimal' (0.0-1.0)

    Returns:
        True if valid, False otherwise

    Examples:
        >>> validate_threshold(85)      # Valid percentage
        True
        >>> validate_threshold(0.85)    # Valid decimal
        True
        >>> validate_threshold(150)     # Invalid (> 100)
        False
        >>> validate_threshold(-10)     # Invalid (< 0)
        False
    """
    if value is None:
        return False

    try:
        value = float(value)
    except (ValueError, TypeError):
        return False

    if value_range == 'percentage':
        return 0.0 <= value <= 100.0
    elif value_range == 'decimal':
        return 0.0 <= value <= 1.0
    else:  # auto
        # Valid if within either range
        return (0.0 <= value <= 1.0) or (0.0 <= value <= 100.0)


# Convenience function for common pattern: get threshold from config
def get_threshold_decimal(config: dict, key: str, default: float = 0.85) -> float:
    """
    Get threshold from config dict and normalize to decimal.

    CORRECTION BUG #6: Standardized config threshold extraction.

    Args:
        config: Configuration dictionary
        key: Threshold key name
        default: Default value if key not found (in decimal 0.0-1.0)

    Returns:
        Threshold in [0.0, 1.0] range

    Examples:
        >>> config = {'threshold': 85.0}
        >>> get_threshold_decimal(config, 'threshold', default=0.8)
        0.85
        >>> config = {'threshold': 0.85}
        >>> get_threshold_decimal(config, 'threshold', default=0.8)
        0.85
        >>> config = {}
        >>> get_threshold_decimal(config, 'threshold', default=0.8)
        0.8
    """
    value = config.get(key, default)
    return normalize_threshold(value)


def get_threshold_percentage(config: dict, key: str, default: float = 85.0) -> float:
    """
    Get threshold from config dict and normalize to percentage.

    Args:
        config: Configuration dictionary
        key: Threshold key name
        default: Default value if key not found (in percentage 0-100)

    Returns:
        Threshold in [0, 100] range

    Examples:
        >>> config = {'threshold': 0.85}
        >>> get_threshold_percentage(config, 'threshold', default=80.0)
        85.0
        >>> config = {'threshold': 85}
        >>> get_threshold_percentage(config, 'threshold', default=80.0)
        85.0
    """
    value = config.get(key, default)
    return to_percentage(value)
