"""Transition effects for video segments.

This module provides transition effects between video segments,
including fade, wipe, zoom, and other professional effects.
"""

from dataclasses import dataclass
from typing import Optional, Dict
from enum import Enum


class TransitionType(Enum):
    """Types of transitions available."""
    NONE = "none"
    FADE = "fade"
    WIPE_LEFT = "wipe_left"
    WIPE_RIGHT = "wipe_right"
    WIPE_UP = "wipe_up"
    WIPE_DOWN = "wipe_down"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    DISSOLVE = "dissolve"


@dataclass
class Transition:
    """Represents a transition between two video segments.

    Attributes:
        type: Type of transition effect
        duration: Duration of transition in seconds (default: 1.0)
        offset: Optional offset for the transition effect
        easing: Easing function for smooth transitions
    """

    type: TransitionType = TransitionType.NONE
    duration: float = 1.0
    offset: float = 0.0
    easing: str = "linear"

    def to_dict(self) -> dict:
        """Convert transition to dictionary for serialization."""
        return {
            'type': self.type.value,
            'duration': self.duration,
            'offset': self.offset,
            'easing': self.easing
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Transition':
        """Create transition from dictionary."""
        return cls(
            type=TransitionType(data.get('type', 'none')),
            duration=data.get('duration', 1.0),
            offset=data.get('offset', 0.0),
            easing=data.get('easing', 'linear')
        )

    def get_ffmpeg_filter(self, width: int, height: int) -> str:
        """Generate FFmpeg filter string for this transition.

        Args:
            width: Video width in pixels
            height: Video height in pixels

        Returns:
            FFmpeg filter string for xfade filter
        """
        if self.type == TransitionType.NONE:
            return ""

        # Map transition types to FFmpeg xfade transition names
        transition_map = {
            TransitionType.FADE: "fade",
            TransitionType.WIPE_LEFT: "wipeleft",
            TransitionType.WIPE_RIGHT: "wiperight",
            TransitionType.WIPE_UP: "wipeup",
            TransitionType.WIPE_DOWN: "wipedown",
            TransitionType.SLIDE_LEFT: "slideleft",
            TransitionType.SLIDE_RIGHT: "slideright",
            TransitionType.ZOOM_IN: "fadein",
            TransitionType.ZOOM_OUT: "fadeout",
            TransitionType.DISSOLVE: "dissolve"
        }

        xfade_type = transition_map.get(self.type, "fade")

        # Build xfade filter
        # Format: xfade=transition=TYPE:duration=DURATION:offset=OFFSET
        return f"xfade=transition={xfade_type}:duration={self.duration}:offset={self.offset}"

    def __str__(self) -> str:
        """String representation of the transition."""
        if self.type == TransitionType.NONE:
            return "No transition"
        return f"{self.type.value.replace('_', ' ').title()} ({self.duration}s)"


class TransitionPreset:
    """Predefined transition presets for quick access."""

    PRESETS: Dict[str, Transition] = {
        "Quick Fade": Transition(TransitionType.FADE, 0.5),
        "Smooth Fade": Transition(TransitionType.FADE, 1.0),
        "Long Fade": Transition(TransitionType.FADE, 2.0),
        "Wipe Left": Transition(TransitionType.WIPE_LEFT, 1.0),
        "Wipe Right": Transition(TransitionType.WIPE_RIGHT, 1.0),
        "Wipe Up": Transition(TransitionType.WIPE_UP, 1.0),
        "Wipe Down": Transition(TransitionType.WIPE_DOWN, 1.0),
        "Slide Left": Transition(TransitionType.SLIDE_LEFT, 1.0),
        "Slide Right": Transition(TransitionType.SLIDE_RIGHT, 1.0),
        "Zoom In": Transition(TransitionType.ZOOM_IN, 1.5),
        "Zoom Out": Transition(TransitionType.ZOOM_OUT, 1.5),
        "Dissolve": Transition(TransitionType.DISSOLVE, 1.0),
    }

    @classmethod
    def get_preset(cls, name: str) -> Optional[Transition]:
        """Get a preset transition by name."""
        return cls.PRESETS.get(name)

    @classmethod
    def get_preset_names(cls) -> list:
        """Get list of all preset names."""
        return list(cls.PRESETS.keys())


def calculate_transition_offset(segment1_end_time: float,
                                transition_duration: float) -> float:
    """Calculate the offset for a transition between two segments.

    Args:
        segment1_end_time: End time of first segment in seconds
        transition_duration: Duration of transition in seconds

    Returns:
        Offset time in seconds for the xfade filter
    """
    # Transition starts before the end of first segment
    return segment1_end_time - transition_duration
