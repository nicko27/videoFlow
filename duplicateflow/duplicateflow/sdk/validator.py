"""
Base class for video validation/verification steps.

Validators are used in pipelines to verify video pairs before or after
comparison, enabling pre-filtering or post-verification logic.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import cv2
from pathlib import Path


class Validator(ABC):
    """
    Abstract base class for video validators.

    Validators can be used to:
    - Pre-filter video pairs before comparison (e.g., length validation)
    - Post-verify comparison results (e.g., scene boundary validation)
    - Add metadata to pipeline results

    Subclasses must implement:
    - validate(): Perform the actual validation

    Subclasses can optionally override:
    - get_metadata(): Return validator-specific metadata

    Example:
        >>> class MyValidator(Validator):
        ...     def __init__(self, max_diff=5.0):
        ...         super().__init__()
        ...         self.max_diff = max_diff
        ...
        ...     def validate(self, video1, video2, result=None):
        ...         # Check some condition
        ...         return True, {"reason": "OK"}
    """

    def __init__(self):
        """Initialize the validator."""
        self.name = self.__class__.__name__

    @abstractmethod
    def validate(
        self,
        video1: str,
        video2: str,
        result: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Validate a video pair.

        Args:
            video1: Path to first video
            video2: Path to second video
            result: Optional comparison result for post-validation

        Returns:
            Tuple of (is_valid, metadata):
            - is_valid (bool): Whether validation passed
            - metadata (dict): Validation metadata (reasons, measurements, etc.)

        Example:
            >>> validator = LengthValidator(tolerance_percent=5.0)
            >>> is_valid, meta = validator.validate("short.mp4", "long.mp4")
            >>> print(f"Valid: {is_valid}, Diff: {meta['length_diff_seconds']}")
        """
        pass

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get validator configuration metadata.

        Returns:
            Dictionary with validator configuration
        """
        return {
            'name': self.name,
            'type': self.__class__.__name__
        }

    def _get_video_duration(self, video_path: str) -> float:
        """
        Get duration of a video in seconds.

        Args:
            video_path: Path to video file

        Returns:
            Duration in seconds

        Raises:
            FileNotFoundError: If video doesn't exist
            RuntimeError: If video can't be opened
        """
        path = Path(video_path)
        if not path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        cap = cv2.VideoCapture(str(video_path))
        try:
            if not cap.isOpened():
                raise RuntimeError(f"Cannot open video: {video_path}")

            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)

            if fps <= 0:
                raise RuntimeError(f"Invalid FPS for video: {video_path}")

            duration = frame_count / fps
            return duration
        finally:
            cap.release()

    def __repr__(self) -> str:
        """String representation."""
        return f"{self.__class__.__name__}()"


class LengthValidator(Validator):
    """
    Validates that two videos have similar durations.

    Accepts videos if their duration difference is within specified tolerances.
    Supports both percentage-based and absolute (seconds) tolerances.

    Example:
        >>> # Accept if duration diff <= 5% OR <= 30 seconds
        >>> validator = LengthValidator(
        ...     tolerance_percent=5.0,
        ...     tolerance_seconds=30.0
        ... )
        >>>
        >>> is_valid, meta = validator.validate("video1.mp4", "video2.mp4")
        >>> if is_valid:
        ...     print(f"Videos match (diff: {meta['length_diff_seconds']:.1f}s)")
        ... else:
        ...     print(f"Videos too different: {meta['reason']}")
    """

    def __init__(
        self,
        tolerance_percent: Optional[float] = None,
        tolerance_seconds: Optional[float] = None,
        require_both: bool = False
    ):
        """
        Initialize length validator.

        Args:
            tolerance_percent: Maximum percentage difference (e.g., 5.0 for 5%)
                              If None, only check tolerance_seconds
            tolerance_seconds: Maximum absolute difference in seconds (e.g., 30.0)
                               If None, only check tolerance_percent
            require_both: If True, BOTH tolerances must pass (AND logic)
                         If False, EITHER tolerance can pass (OR logic)

        Raises:
            ValueError: If both tolerances are None
        """
        super().__init__()

        if tolerance_percent is None and tolerance_seconds is None:
            raise ValueError("At least one tolerance must be specified")

        self.tolerance_percent = tolerance_percent
        self.tolerance_seconds = tolerance_seconds
        self.require_both = require_both

    def validate(
        self,
        video1: str,
        video2: str,
        result: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Validate that videos have similar durations.

        Args:
            video1: Path to first video
            video2: Path to second video
            result: Unused (for interface compatibility)

        Returns:
            Tuple of (is_valid, metadata):
            - is_valid: True if duration difference is within tolerance
            - metadata: Duration info and validation details
        """
        # Get durations
        duration1 = self._get_video_duration(video1)
        duration2 = self._get_video_duration(video2)

        # Calculate differences
        diff_seconds = abs(duration1 - duration2)
        longer_duration = max(duration1, duration2)

        # Avoid division by zero
        if longer_duration > 0:
            diff_percent = (diff_seconds / longer_duration) * 100.0
        else:
            diff_percent = 0.0

        # Check tolerances
        percent_ok = True
        seconds_ok = True

        if self.tolerance_percent is not None:
            percent_ok = diff_percent <= self.tolerance_percent

        if self.tolerance_seconds is not None:
            seconds_ok = diff_seconds <= self.tolerance_seconds

        # Apply logic (AND vs OR)
        if self.require_both:
            is_valid = percent_ok and seconds_ok
            reason = "Both tolerances satisfied" if is_valid else "Failed one or more tolerances"
        else:
            is_valid = percent_ok or seconds_ok
            if is_valid:
                if percent_ok and seconds_ok:
                    reason = "Both tolerances satisfied"
                elif percent_ok:
                    reason = f"Within {self.tolerance_percent}% tolerance"
                else:
                    reason = f"Within {self.tolerance_seconds}s tolerance"
            else:
                reason = "Exceeded both tolerances"

        metadata = {
            'duration1': duration1,
            'duration2': duration2,
            'length_diff_seconds': diff_seconds,
            'length_diff_percent': diff_percent,
            'percent_ok': percent_ok,
            'seconds_ok': seconds_ok,
            'reason': reason,
            'tolerance_percent': self.tolerance_percent,
            'tolerance_seconds': self.tolerance_seconds,
            'require_both': self.require_both
        }

        return is_valid, metadata

    def get_metadata(self) -> Dict[str, Any]:
        """Get validator configuration."""
        return {
            'name': self.name,
            'type': 'LengthValidator',
            'tolerance_percent': self.tolerance_percent,
            'tolerance_seconds': self.tolerance_seconds,
            'require_both': self.require_both
        }

    def __repr__(self) -> str:
        """String representation."""
        parts = []
        if self.tolerance_percent is not None:
            parts.append(f"±{self.tolerance_percent}%")
        if self.tolerance_seconds is not None:
            parts.append(f"±{self.tolerance_seconds}s")

        logic = " AND " if self.require_both else " OR "
        tolerance_str = logic.join(parts)

        return f"LengthValidator({tolerance_str})"
