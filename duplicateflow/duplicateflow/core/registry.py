"""
Algorithm registry and decorator system.

This module manages the registration and discovery of algorithms:
- @register_algorithm: Decorator to register algorithms
- get_algorithm: Retrieve an algorithm by name
- list_algorithms: List all registered algorithms
- Auto-discovery on import

The registry is a global singleton that stores all available algorithms
and their metadata.
"""

from typing import Dict, Any, List, Optional, Type, Callable
from dataclasses import dataclass
from duplicateflow.sdk.algorithm import Algorithm


@dataclass
class AlgorithmInfo:
    """
    Metadata about a registered algorithm.

    Attributes:
        name: Unique algorithm identifier (e.g., "optical_flow")
        display_name: Human-readable name (e.g., "🌊 Flux Optique")
        short_name: Short display name for tables (e.g., "Flux Optique")
        description: Brief description
        detailed_explanation: Longer explanation of how it works
        category: Algorithm category (statistical, structural, temporal, etc.)
        speed: Relative speed (fast, medium, slow, very_slow)
        default_threshold: Default acceptance threshold (0-100)
        default_params: Default parameters dictionary
        use_case: Best use case description
        algorithm_class: The Algorithm subclass
    """
    name: str
    display_name: str
    short_name: str
    description: str
    detailed_explanation: str
    category: str
    speed: str
    default_threshold: float
    default_params: Dict[str, Any]
    use_case: str
    algorithm_class: Type[Algorithm]


class AlgorithmRegistry:
    """
    Global registry for algorithms.

    This is a singleton that maintains the list of all registered algorithms.
    Algorithms are registered via the @register_algorithm decorator.
    """

    _instance: Optional['AlgorithmRegistry'] = None
    _algorithms: Dict[str, AlgorithmInfo] = {}

    def __new__(cls):
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(
        self,
        name: str,
        algorithm_class: Type[Algorithm],
        display_name: str = None,
        short_name: str = None,
        description: str = "",
        detailed_explanation: str = "",
        category: str = "unknown",
        speed: str = "medium",
        default_threshold: float = 70.0,
        default_params: Dict[str, Any] = None,
        use_case: str = ""
    ) -> None:
        """
        Register an algorithm in the global registry.

        Args:
            name: Unique algorithm identifier
            algorithm_class: Algorithm class (must inherit from Algorithm)
            display_name: Human-readable name (defaults to name)
            short_name: Short name for tables (defaults to display_name)
            description: Brief description
            detailed_explanation: Detailed explanation
            category: Category (statistical, structural, temporal, etc.)
            speed: Speed rating (fast, medium, slow, very_slow)
            default_threshold: Default threshold 0-100
            default_params: Default parameters dictionary
            use_case: Best use case

        Raises:
            ValueError: If algorithm name already registered
            TypeError: If algorithm_class doesn't inherit from Algorithm
        """
        if name in self._algorithms:
            raise ValueError(f"Algorithm '{name}' is already registered")

        if not issubclass(algorithm_class, Algorithm):
            raise TypeError(
                f"Algorithm class must inherit from Algorithm, "
                f"got {algorithm_class}"
            )

        # Set defaults
        if display_name is None:
            display_name = name.replace('_', ' ').title()
        if short_name is None:
            short_name = display_name
        if default_params is None:
            default_params = {'threshold': default_threshold}

        info = AlgorithmInfo(
            name=name,
            display_name=display_name,
            short_name=short_name,
            description=description,
            detailed_explanation=detailed_explanation,
            category=category,
            speed=speed,
            default_threshold=default_threshold,
            default_params=default_params,
            use_case=use_case,
            algorithm_class=algorithm_class
        )

        self._algorithms[name] = info

    def get(self, name: str) -> Optional[AlgorithmInfo]:
        """
        Get algorithm info by name.

        Args:
            name: Algorithm name

        Returns:
            AlgorithmInfo if found, None otherwise
        """
        return self._algorithms.get(name)

    def get_class(self, name: str) -> Optional[Type[Algorithm]]:
        """
        Get algorithm class by name.

        Args:
            name: Algorithm name

        Returns:
            Algorithm class if found, None otherwise
        """
        info = self.get(name)
        return info.algorithm_class if info else None

    def list_all(
        self,
        category: Optional[str] = None,
        speed: Optional[str] = None
    ) -> List[AlgorithmInfo]:
        """
        List all registered algorithms.

        Args:
            category: Filter by category (optional)
            speed: Filter by speed (optional)

        Returns:
            List of AlgorithmInfo objects
        """
        algorithms = list(self._algorithms.values())

        if category:
            algorithms = [a for a in algorithms if a.category == category]

        if speed:
            algorithms = [a for a in algorithms if a.speed == speed]

        return algorithms

    def get_names(self) -> List[str]:
        """
        Get list of all algorithm names.

        Returns:
            List of algorithm names
        """
        return list(self._algorithms.keys())

    def get_categories(self) -> List[str]:
        """
        Get list of all categories.

        Returns:
            List of unique categories
        """
        return list(set(info.category for info in self._algorithms.values()))

    def count(self) -> int:
        """
        Get number of registered algorithms.

        Returns:
            Number of algorithms
        """
        return len(self._algorithms)

    def clear(self) -> None:
        """
        Clear all registered algorithms.

        Warning: This is mainly for testing. Don't use in production.
        """
        self._algorithms.clear()


# Global registry instance
_registry = AlgorithmRegistry()


def register_algorithm(
    name: str,
    display_name: str = None,
    short_name: str = None,
    description: str = "",
    detailed_explanation: str = "",
    category: str = "unknown",
    speed: str = "medium",
    default_threshold: float = 70.0,
    default_params: Dict[str, Any] = None,
    use_case: str = ""
) -> Callable:
    """
    Decorator to register an algorithm.

    This decorator should be applied to Algorithm subclasses to register
    them in the global registry. Once registered, algorithms can be
    discovered and instantiated by name.

    Args:
        name: Unique algorithm identifier (e.g., "optical_flow")
        display_name: Human-readable name (e.g., "🌊 Flux Optique")
        short_name: Short name for tables
        description: Brief description
        detailed_explanation: Detailed explanation
        category: Category (statistical, structural, temporal, audio, ml, dl)
        speed: Speed rating (fast, medium, slow, very_slow)
        default_threshold: Default threshold 0-100
        default_params: Default parameters
        use_case: Best use case description

    Returns:
        Decorated class

    Example:
        >>> @register_algorithm(
        ...     name="optical_flow",
        ...     display_name="🌊 Flux Optique",
        ...     category="motion",
        ...     speed="medium",
        ...     default_threshold=70.0,
        ...     description="Compare optical flow vectors between frames"
        ... )
        >>> class OpticalFlowAlgorithm(Algorithm):
        ...     def configure(self, **params):
        ...         self.threshold = params.get('threshold', 70.0)
        ...
        ...     def compare(self, short_video, long_video, start_time, duration):
        ...         return {'similarity': 0.85, 'accepted': True, 'metadata': {}}
    """
    def decorator(cls: Type[Algorithm]) -> Type[Algorithm]:
        """Inner decorator function."""
        _registry.register(
            name=name,
            algorithm_class=cls,
            display_name=display_name,
            short_name=short_name,
            description=description,
            detailed_explanation=detailed_explanation,
            category=category,
            speed=speed,
            default_threshold=default_threshold,
            default_params=default_params,
            use_case=use_case
        )
        return cls

    return decorator


def get_algorithm(name: str) -> Type[Algorithm]:
    """
    Get an algorithm class by name.

    Args:
        name: Algorithm name

    Returns:
        Algorithm class

    Raises:
        KeyError: If algorithm not found

    Example:
        >>> AlgoClass = get_algorithm("optical_flow")
        >>> algo = AlgoClass()
        >>> algo.configure(threshold=75.0)
    """
    algo_class = _registry.get_class(name)
    if algo_class is None:
        available = ", ".join(_registry.get_names())
        raise KeyError(
            f"Algorithm '{name}' not found. "
            f"Available algorithms: {available}"
        )
    return algo_class


def get_algorithm_info(name: str) -> AlgorithmInfo:
    """
    Get algorithm metadata by name.

    Args:
        name: Algorithm name

    Returns:
        AlgorithmInfo object

    Raises:
        KeyError: If algorithm not found
    """
    info = _registry.get(name)
    if info is None:
        available = ", ".join(_registry.get_names())
        raise KeyError(
            f"Algorithm '{name}' not found. "
            f"Available algorithms: {available}"
        )
    return info


def list_algorithms(
    category: Optional[str] = None,
    speed: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    List all registered algorithms with their metadata.

    Args:
        category: Filter by category (optional)
        speed: Filter by speed (optional)

    Returns:
        List of dictionaries with algorithm metadata

    Example:
        >>> algorithms = list_algorithms(category="motion")
        >>> for algo in algorithms:
        ...     print(f"{algo['name']}: {algo['description']}")
    """
    infos = _registry.list_all(category=category, speed=speed)

    return [
        {
            'name': info.name,
            'display_name': info.display_name,
            'short_name': info.short_name,
            'description': info.description,
            'category': info.category,
            'speed': info.speed,
            'default_threshold': info.default_threshold,
            'use_case': info.use_case
        }
        for info in infos
    ]


def get_algorithm_names() -> List[str]:
    """
    Get list of all registered algorithm names.

    Returns:
        List of algorithm names

    Example:
        >>> names = get_algorithm_names()
        >>> print(f"Available algorithms: {', '.join(names)}")
    """
    return _registry.get_names()


def get_categories() -> List[str]:
    """
    Get list of all algorithm categories.

    Returns:
        List of unique categories

    Example:
        >>> categories = get_categories()
        >>> print(f"Categories: {', '.join(categories)}")
    """
    return _registry.get_categories()


def algorithm_count() -> int:
    """
    Get total number of registered algorithms.

    Returns:
        Number of algorithms
    """
    return _registry.count()
