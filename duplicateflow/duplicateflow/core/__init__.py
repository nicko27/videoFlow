"""
Core components of DuplicateFlow.

This module contains the fundamental building blocks:
- models: Data structures (VerificationResult, MethodResult)
- registry: Algorithm registration and discovery
- pipeline: Pipeline execution engine (to be implemented)
- executor: Parallel execution (to be implemented)
- exceptions: Custom exceptions
"""

from duplicateflow.core.models import (
    VerificationResult,
    MethodResult,
    VerificationStatus,
)

from duplicateflow.core.registry import (
    register_algorithm,
    get_algorithm,
    get_algorithm_info,
    list_algorithms,
    get_algorithm_names,
    get_categories,
    algorithm_count,
)

__all__ = [
    # Models
    "VerificationResult",
    "MethodResult",
    "VerificationStatus",
    # Registry
    "register_algorithm",
    "get_algorithm",
    "get_algorithm_info",
    "list_algorithms",
    "get_algorithm_names",
    "get_categories",
    "algorithm_count",
]
