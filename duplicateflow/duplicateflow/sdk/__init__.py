"""
DuplicateFlow SDK for algorithm plugins.

This module provides the API for creating custom algorithm plugins:
- Algorithm: Base class for all algorithms
- register_algorithm: Decorator for algorithm registration
- Validator: Base class for validation steps
- LengthValidator: Validates video duration similarity

Example:
    >>> from duplicateflow.sdk import Algorithm, register_algorithm
    >>>
    >>> @register_algorithm(
    ...     name="my_algo",
    ...     display_name="My Algorithm",
    ...     category="structural",
    ...     speed="fast"
    ... )
    >>> class MyAlgorithm(Algorithm):
    ...     def configure(self, **params):
    ...         self.threshold = params.get('threshold', 70.0)
    ...
    ...     def compare(self, short_video, long_video, start_time, duration):
    ...         return {'similarity': 0.85, 'accepted': True, 'metadata': {}}
    >>>
    >>> from duplicateflow.sdk import LengthValidator
    >>> validator = LengthValidator(tolerance_percent=5.0, tolerance_seconds=30.0)
    >>> is_valid, meta = validator.validate("video1.mp4", "video2.mp4")
"""

from duplicateflow.sdk.algorithm import Algorithm
from duplicateflow.sdk.validator import Validator, LengthValidator

__all__ = [
    "Algorithm",
    "Validator",
    "LengthValidator",
]
