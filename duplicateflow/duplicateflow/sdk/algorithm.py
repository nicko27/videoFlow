"""
Base class for all DuplicateFlow algorithms.

This module defines the Algorithm abstract base class that all comparison
algorithms must inherit from. It provides a standard interface for:
- Configuration
- Video comparison
- CLI parameter generation
- Dependency declaration
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pathlib import Path


class Algorithm(ABC):
    """
    Abstract base class for video comparison algorithms.

    All DuplicateFlow algorithms must inherit from this class and implement
    the required methods. The class provides a standard interface that allows
    algorithms to be registered, configured, and executed uniformly.

    Subclasses must implement:
    - configure(): Set algorithm parameters
    - compare(): Perform the actual video comparison

    Subclasses can optionally override:
    - get_cli_params(): Define CLI parameters
    - get_requirements(): Declare Python dependencies
    - validate_config(): Validate configuration
    - cleanup(): Clean up resources after execution

    Example:
        >>> @register_algorithm(
        ...     name="my_algo",
        ...     display_name="My Algorithm",
        ...     category="structural",
        ...     speed="fast",
        ...     default_threshold=75.0
        ... )
        >>> class MyAlgorithm(Algorithm):
        ...     def configure(self, **params):
        ...         self.threshold = params.get('threshold', 75.0)
        ...
        ...     def compare(self, short_video, long_video, start_time, duration):
        ...         # Implementation...
        ...         return {
        ...             'similarity': 0.85,
        ...             'accepted': True,
        ...             'metadata': {}
        ...         }
    """

    def __init__(self):
        """Initialize the algorithm."""
        self.name = self.__class__.__name__
        self.configured = False
        self._config = {}

    @abstractmethod
    def configure(self, **params) -> None:
        """
        Configure the algorithm with parameters.

        This method is called before compare() to set up the algorithm
        with user-provided or default parameters.

        Args:
            **params: Algorithm-specific parameters
                Common parameters:
                - threshold (float): Acceptance threshold (0-100)
                - max_frames (int): Maximum frames to analyze
                - timeout (int): Maximum execution time in seconds

        Example:
            >>> algo = MyAlgorithm()
            >>> algo.configure(threshold=80.0, max_frames=50)
        """
        self._config = params
        self.configured = True

    @abstractmethod
    def compare(
        self,
        short_video: str,
        long_video: str,
        start_time: float = 0.0,
        duration: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Compare two videos and return similarity result.

        This is the core method that performs the actual comparison.
        It should be stateless and deterministic (same inputs = same outputs).

        Args:
            short_video: Path to the short video (scene to find)
            long_video: Path to the long video (where to search)
            start_time: Start position in long_video (seconds)
            duration: Duration to analyze from start_time (seconds)
                     If None, use duration of short_video

        Returns:
            Dictionary with required keys:
            - similarity (float): Similarity score 0.0-1.0
            - accepted (bool): True if score >= threshold
            - metadata (dict): Algorithm-specific information
                Recommended metadata:
                - frames_analyzed (int): Number of frames processed
                - execution_time_ms (float): Internal timing
                - error (str): Error message if any

        Raises:
            FileNotFoundError: If video files don't exist
            ValueError: If parameters are invalid
            RuntimeError: If comparison fails

        Example:
            >>> result = algo.compare(
            ...     short_video="/path/to/scene.mp4",
            ...     long_video="/path/to/movie.mp4",
            ...     start_time=120.0,
            ...     duration=60.0
            ... )
            >>> print(result)
            {
                'similarity': 0.85,
                'accepted': True,
                'metadata': {
                    'frames_analyzed': 30,
                    'mean_color_diff': 0.15
                }
            }
        """
        pass

    def get_cli_params(self) -> List[Dict[str, Any]]:
        """
        Return CLI parameters for this algorithm.

        This method defines which parameters can be set via command line.
        Each parameter is a dictionary with Click option specifications.

        Returns:
            List of parameter dictionaries with keys:
            - names (list): Parameter names (e.g., ['--my-algo-threshold'])
            - type (str): Parameter type ('int', 'float', 'str', 'bool')
            - default: Default value
            - help (str): Help text
            - required (bool): Whether parameter is required

        Example:
            >>> def get_cli_params(self):
            ...     return [
            ...         {
            ...             'names': ['--optical-flow-max-frames'],
            ...             'type': 'int',
            ...             'default': 30,
            ...             'help': 'Maximum frames to analyze',
            ...             'required': False
            ...         },
            ...         {
            ...             'names': ['--optical-flow-threshold'],
            ...             'type': 'float',
            ...             'default': 70.0,
            ...             'help': 'Acceptance threshold (0-100)',
            ...             'required': False
            ...         }
            ...     ]
        """
        return []

    def get_requirements(self) -> List[str]:
        """
        Return Python package requirements.

        This method declares which packages are needed to run this algorithm.
        Used for:
        - Installation validation
        - Requirements.txt generation
        - Dependency checking

        Returns:
            List of package specifications (pip format)
            Examples:
            - "opencv-python>=4.8.0"
            - "librosa>=0.10.0"
            - "torch>=2.0.0"

        Example:
            >>> def get_requirements(self):
            ...     return [
            ...         'opencv-python>=4.8.0',
            ...         'numpy>=1.24.0',
            ...         'scipy>=1.10.0'
            ...     ]
        """
        return []

    def validate_config(self) -> bool:
        """
        Validate the current configuration.

        Called after configure() to ensure parameters are valid.
        Should raise ValueError if configuration is invalid.

        Returns:
            True if configuration is valid

        Raises:
            ValueError: If configuration is invalid

        Example:
            >>> def validate_config(self):
            ...     if self.threshold < 0 or self.threshold > 100:
            ...         raise ValueError("Threshold must be 0-100")
            ...     return True
        """
        return True

    def cleanup(self) -> None:
        """
        Clean up resources after execution.

        Called after compare() to release any resources (memory, files, etc.).
        Override if your algorithm needs cleanup.

        Example:
            >>> def cleanup(self):
            ...     # Close video captures
            ...     if hasattr(self, '_video_capture'):
            ...         self._video_capture.release()
        """
        pass

    def _validate_video_path(self, path: str) -> Path:
        """
        Validate that a video file exists.

        Args:
            path: Path to video file

        Returns:
            Path object

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        video_path = Path(path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {path}")
        return video_path

    def _validate_time_params(
        self,
        start_time: float,
        duration: Optional[float]
    ) -> None:
        """
        Validate time parameters.

        Args:
            start_time: Start time in seconds
            duration: Duration in seconds (or None)

        Raises:
            ValueError: If parameters are invalid
        """
        if start_time is not None and start_time < 0:
            raise ValueError(f"start_time must be >= 0, got {start_time}")

        if duration is not None and duration <= 0:
            raise ValueError(f"duration must be > 0, got {duration}")

    def __repr__(self) -> str:
        """String representation."""
        config_str = ", ".join(f"{k}={v}" for k, v in self._config.items())
        return f"{self.__class__.__name__}({config_str})"
