"""Text overlay system for Video Editor.

This module provides comprehensive text overlay functionality including
titles, subtitles, lower thirds, and custom text overlays with animations.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple
from pathlib import Path


class TextPosition(Enum):
    """Text position presets on video canvas."""

    TOP = "top"
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    CENTER = "center"
    BOTTOM = "bottom"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"
    LOWER_THIRD = "lower_third"  # Professional broadcast position
    CUSTOM = "custom"  # User-defined X,Y coordinates


class AnimationType(Enum):
    """Animation types for text overlays."""

    NONE = "none"
    FADE_IN = "fade_in"
    FADE_OUT = "fade_out"
    FADE_IN_OUT = "fade_in_out"
    SLIDE_IN_LEFT = "slide_in_left"
    SLIDE_IN_RIGHT = "slide_in_right"
    SLIDE_IN_TOP = "slide_in_top"
    SLIDE_IN_BOTTOM = "slide_in_bottom"
    SLIDE_OUT_LEFT = "slide_out_left"
    SLIDE_OUT_RIGHT = "slide_out_right"
    TYPEWRITER = "typewriter"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"


class TextAlignment(Enum):
    """Text alignment within its bounding box."""

    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


@dataclass
class TextStyle:
    """Styling configuration for text overlays.

    Attributes:
        font_family: Font family name (system font)
        font_size: Font size in points
        color: Text color in hex format (#RRGGBB)
        alpha: Text opacity (0.0-1.0)
        bold: Enable bold text
        italic: Enable italic text
        underline: Enable underline
        outline_width: Outline width in pixels (0 = no outline)
        outline_color: Outline color in hex format
        shadow_offset: Shadow offset (x, y) in pixels
        shadow_color: Shadow color in hex format
        shadow_alpha: Shadow opacity (0.0-1.0)
        background_color: Background box color (None = no background)
        background_alpha: Background opacity (0.0-1.0)
        background_padding: Padding around text in pixels
        line_spacing: Line spacing multiplier (1.0 = normal)
        alignment: Text alignment
    """

    font_family: str = "Arial"
    font_size: int = 48
    color: str = "#FFFFFF"
    alpha: float = 1.0
    bold: bool = False
    italic: bool = False
    underline: bool = False

    # Outline/Border
    outline_width: int = 0
    outline_color: str = "#000000"

    # Shadow
    shadow_offset: Tuple[int, int] = (0, 0)
    shadow_color: str = "#000000"
    shadow_alpha: float = 0.8

    # Background box
    background_color: Optional[str] = None
    background_alpha: float = 0.8
    background_padding: int = 10

    # Text formatting
    line_spacing: float = 1.0
    alignment: TextAlignment = TextAlignment.CENTER

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        return {
            'font_family': self.font_family,
            'font_size': self.font_size,
            'color': self.color,
            'alpha': self.alpha,
            'bold': self.bold,
            'italic': self.italic,
            'underline': self.underline,
            'outline_width': self.outline_width,
            'outline_color': self.outline_color,
            'shadow_offset': list(self.shadow_offset),
            'shadow_color': self.shadow_color,
            'shadow_alpha': self.shadow_alpha,
            'background_color': self.background_color,
            'background_alpha': self.background_alpha,
            'background_padding': self.background_padding,
            'line_spacing': self.line_spacing,
            'alignment': self.alignment.value
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'TextStyle':
        """Create from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            TextStyle instance
        """
        data = data.copy()
        if 'shadow_offset' in data:
            data['shadow_offset'] = tuple(data['shadow_offset'])
        if 'alignment' in data:
            data['alignment'] = TextAlignment(data['alignment'])
        return cls(**data)


@dataclass
class TextOverlay:
    """Text overlay configuration.

    Represents a text overlay that can be added to a video at a specific
    time with custom styling and animations.

    Attributes:
        text: Text content (supports multiple lines with \n)
        style: Text styling configuration
        position: Position preset on canvas
        custom_position: Custom (x, y) position in pixels (when position=CUSTOM)
        start_frame: Starting frame number
        end_frame: Ending frame number (None = until end of segment)
        animation: Animation type
        animation_duration: Animation duration in seconds
        name: Optional name/label for this overlay
        enabled: Whether this overlay is active
    """

    text: str
    style: TextStyle = field(default_factory=TextStyle)
    position: TextPosition = TextPosition.CENTER
    custom_position: Optional[Tuple[int, int]] = None
    start_frame: int = 0
    end_frame: Optional[int] = None
    animation: AnimationType = AnimationType.NONE
    animation_duration: float = 1.0
    name: str = ""
    enabled: bool = True

    def get_duration_seconds(self, fps: float) -> float:
        """Calculate overlay duration in seconds.

        Args:
            fps: Video frame rate

        Returns:
            Duration in seconds
        """
        if self.end_frame is None:
            return float('inf')
        return (self.end_frame - self.start_frame) / fps

    def get_position_coords(self, video_width: int, video_height: int) -> Tuple[str, str]:
        """Get FFmpeg position coordinates for this text.

        Args:
            video_width: Video width in pixels
            video_height: Video height in pixels

        Returns:
            Tuple of (x_expr, y_expr) for FFmpeg drawtext filter
        """
        if self.position == TextPosition.CUSTOM and self.custom_position:
            return (str(self.custom_position[0]), str(self.custom_position[1]))

        # Predefined positions
        positions = {
            TextPosition.TOP: ("(w-text_w)/2", "50"),
            TextPosition.TOP_LEFT: ("50", "50"),
            TextPosition.TOP_RIGHT: ("w-text_w-50", "50"),
            TextPosition.CENTER: ("(w-text_w)/2", "(h-text_h)/2"),
            TextPosition.BOTTOM: ("(w-text_w)/2", "h-text_h-50"),
            TextPosition.BOTTOM_LEFT: ("50", "h-text_h-50"),
            TextPosition.BOTTOM_RIGHT: ("w-text_w-50", "h-text_h-50"),
            TextPosition.LOWER_THIRD: ("(w-text_w)/2", "h*2/3")
        }

        return positions.get(self.position, positions[TextPosition.CENTER])

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        return {
            'text': self.text,
            'style': self.style.to_dict(),
            'position': self.position.value,
            'custom_position': list(self.custom_position) if self.custom_position else None,
            'start_frame': self.start_frame,
            'end_frame': self.end_frame,
            'animation': self.animation.value,
            'animation_duration': self.animation_duration,
            'name': self.name,
            'enabled': self.enabled
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'TextOverlay':
        """Create from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            TextOverlay instance
        """
        data = data.copy()
        if 'style' in data:
            data['style'] = TextStyle.from_dict(data['style'])
        if 'position' in data:
            data['position'] = TextPosition(data['position'])
        if 'custom_position' in data and data['custom_position']:
            data['custom_position'] = tuple(data['custom_position'])
        if 'animation' in data:
            data['animation'] = AnimationType(data['animation'])
        return cls(**data)

    def get_ffmpeg_filter(
        self,
        video_width: int,
        video_height: int,
        fps: float,
        font_file: Optional[str] = None
    ) -> str:
        """Generate FFmpeg drawtext filter string.

        Args:
            video_width: Video width in pixels
            video_height: Video height in pixels
            fps: Video frame rate
            font_file: Optional path to font file

        Returns:
            FFmpeg drawtext filter string
        """
        x_expr, y_expr = self.get_position_coords(video_width, video_height)

        # Apply slide animation to position if needed
        if self.animation in [
            AnimationType.SLIDE_IN_LEFT,
            AnimationType.SLIDE_IN_RIGHT,
            AnimationType.SLIDE_IN_TOP,
            AnimationType.SLIDE_IN_BOTTOM,
            AnimationType.SLIDE_OUT_LEFT,
            AnimationType.SLIDE_OUT_RIGHT
        ]:
            x_expr, y_expr = self._get_animated_position(x_expr, y_expr, video_width, video_height, fps)

        # Escape text for FFmpeg
        text_escaped = self.text.replace(":", r"\:").replace("'", r"\'")
        text_escaped = text_escaped.replace("\n", r"\n")

        # Build base filter
        parts = [
            f"drawtext=text='{text_escaped}'",
            f"fontfile={font_file}" if font_file else f"font={self.style.font_family}",
            f"fontsize={self.style.font_size}",
            f"fontcolor={self.style.color}@{self.style.alpha}",
            f"x={x_expr}",
            f"y={y_expr}"
        ]

        # Add styling
        if self.style.bold or self.style.italic:
            style_str = ""
            if self.style.bold:
                style_str += "Bold"
            if self.style.italic:
                style_str += "Italic"
            parts.append(f"font_weight={style_str}")

        # Outline/border
        if self.style.outline_width > 0:
            parts.append(f"borderw={self.style.outline_width}")
            parts.append(f"bordercolor={self.style.outline_color}")

        # Shadow
        if self.style.shadow_offset != (0, 0):
            parts.append(f"shadowx={self.style.shadow_offset[0]}")
            parts.append(f"shadowy={self.style.shadow_offset[1]}")
            parts.append(f"shadowcolor={self.style.shadow_color}@{self.style.shadow_alpha}")

        # Background box
        if self.style.background_color:
            parts.append(f"box=1")
            parts.append(f"boxcolor={self.style.background_color}@{self.style.background_alpha}")
            parts.append(f"boxborderw={self.style.background_padding}")

        # Text alignment
        if self.style.alignment != TextAlignment.LEFT:
            # FFmpeg uses text_align parameter
            parts.append(f"text_align={self.style.alignment.value}")

        # Line spacing
        if self.style.line_spacing != 1.0:
            parts.append(f"line_spacing={int(self.style.line_spacing * 10)}")

        # Timing (enable expression)
        start_time = self.start_frame / fps
        if self.end_frame is not None:
            end_time = self.end_frame / fps
            parts.append(f"enable='between(t,{start_time},{end_time})'")
        else:
            parts.append(f"enable='gte(t,{start_time})'")

        # Animation
        if self.animation != AnimationType.NONE:
            anim_expr = self._get_animation_expression(fps)
            if anim_expr:
                parts.append(anim_expr)

        return ":".join(parts)

    def _get_animated_position(
        self,
        base_x: str,
        base_y: str,
        video_width: int,
        video_height: int,
        fps: float
    ) -> Tuple[str, str]:
        """Get animated position expressions for slide animations.

        Args:
            base_x: Base x expression
            base_y: Base y expression
            video_width: Video width in pixels
            video_height: Video height in pixels
            fps: Video frame rate

        Returns:
            Tuple of (animated_x, animated_y) expressions
        """
        start_time = self.start_frame / fps
        anim_end = start_time + self.animation_duration

        # Calculate easing function for smooth animation
        # Using ease-out cubic: progress^0.33 for smoother deceleration
        progress = f"min(1,max(0,(t-{start_time})/{self.animation_duration}))"
        eased_progress = f"pow({progress},0.33)"

        if self.animation == AnimationType.SLIDE_IN_LEFT:
            # Start from left edge (negative), animate to base_x
            start_x = f"-text_w"
            animated_x = f"if(lt(t,{anim_end}),{start_x}+({base_x}-({start_x}))*{eased_progress},{base_x})"
            return (animated_x, base_y)

        elif self.animation == AnimationType.SLIDE_IN_RIGHT:
            # Start from right edge (beyond width), animate to base_x
            start_x = f"w"
            animated_x = f"if(lt(t,{anim_end}),{start_x}+({base_x}-({start_x}))*{eased_progress},{base_x})"
            return (animated_x, base_y)

        elif self.animation == AnimationType.SLIDE_IN_TOP:
            # Start from top edge (negative), animate to base_y
            start_y = f"-text_h"
            animated_y = f"if(lt(t,{anim_end}),{start_y}+({base_y}-({start_y}))*{eased_progress},{base_y})"
            return (base_x, animated_y)

        elif self.animation == AnimationType.SLIDE_IN_BOTTOM:
            # Start from bottom edge (beyond height), animate to base_y
            start_y = f"h"
            animated_y = f"if(lt(t,{anim_end}),{start_y}+({base_y}-({start_y}))*{eased_progress},{base_y})"
            return (base_x, animated_y)

        elif self.animation == AnimationType.SLIDE_OUT_LEFT:
            # Animate from base_x to left edge at end
            if self.end_frame:
                end_time = self.end_frame / fps
                slide_start = end_time - self.animation_duration
                end_x = f"-text_w"
                progress_out = f"min(1,max(0,(t-{slide_start})/{self.animation_duration}))"
                eased_out = f"pow({progress_out},0.33)"
                animated_x = f"if(gt(t,{slide_start}),{base_x}+({end_x}-({base_x}))*{eased_out},{base_x})"
                return (animated_x, base_y)

        elif self.animation == AnimationType.SLIDE_OUT_RIGHT:
            # Animate from base_x to right edge at end
            if self.end_frame:
                end_time = self.end_frame / fps
                slide_start = end_time - self.animation_duration
                end_x = f"w"
                progress_out = f"min(1,max(0,(t-{slide_start})/{self.animation_duration}))"
                eased_out = f"pow({progress_out},0.33)"
                animated_x = f"if(gt(t,{slide_start}),{base_x}+({end_x}-({base_x}))*{eased_out},{base_x})"
                return (animated_x, base_y)

        return (base_x, base_y)

    def _get_animation_expression(self, fps: float) -> Optional[str]:
        """Get FFmpeg expression for animation.

        Args:
            fps: Video frame rate

        Returns:
            FFmpeg expression string or None
        """
        start_time = self.start_frame / fps
        anim_frames = int(self.animation_duration * fps)

        # ===== FADE ANIMATIONS =====
        if self.animation == AnimationType.FADE_IN:
            return f"alpha='if(lt(t,{start_time}+{self.animation_duration}),(t-{start_time})/{self.animation_duration},1)'"

        elif self.animation == AnimationType.FADE_OUT:
            if self.end_frame:
                end_time = self.end_frame / fps
                fade_start = end_time - self.animation_duration
                return f"alpha='if(gt(t,{fade_start}),1-((t-{fade_start})/{self.animation_duration}),1)'"

        elif self.animation == AnimationType.FADE_IN_OUT:
            expr_parts = []
            # Fade in at start
            expr_parts.append(f"if(lt(t,{start_time}+{self.animation_duration}),(t-{start_time})/{self.animation_duration}")
            # Fade out at end
            if self.end_frame:
                end_time = self.end_frame / fps
                fade_start = end_time - self.animation_duration
                expr_parts.append(f"if(gt(t,{fade_start}),1-((t-{fade_start})/{self.animation_duration}),1)")
            else:
                expr_parts.append("1")
            return f"alpha='{','.join(expr_parts)})'"

        # ===== SLIDE ANIMATIONS =====
        # Note: These return None and are handled in get_ffmpeg_filter() by modifying x/y
        elif self.animation in [
            AnimationType.SLIDE_IN_LEFT,
            AnimationType.SLIDE_IN_RIGHT,
            AnimationType.SLIDE_IN_TOP,
            AnimationType.SLIDE_IN_BOTTOM,
            AnimationType.SLIDE_OUT_LEFT,
            AnimationType.SLIDE_OUT_RIGHT
        ]:
            # Slide animations modify x or y expressions, handled separately
            return None

        # ===== ZOOM ANIMATIONS =====
        # Note: FFmpeg drawtext doesn't support dynamic fontsize expressions well
        # These animations combine scale effects with fade for a zoom-like effect
        elif self.animation == AnimationType.ZOOM_IN:
            # Simulate zoom with fade and slight alpha curve
            return f"alpha='if(lt(t,{start_time}+{self.animation_duration}),pow((t-{start_time})/{self.animation_duration},0.5),1)'"

        elif self.animation == AnimationType.ZOOM_OUT:
            if self.end_frame:
                end_time = self.end_frame / fps
                fade_start = end_time - self.animation_duration
                return f"alpha='if(gt(t,{fade_start}),pow(1-((t-{fade_start})/{self.animation_duration}),0.5),1)'"

        # ===== TYPEWRITER ANIMATION =====
        # Note: Complex to implement in FFmpeg drawtext, would need character-by-character reveal
        # Currently returns None (not yet implemented)
        elif self.animation == AnimationType.TYPEWRITER:
            # TODO: Implement typewriter effect (requires complex text manipulation)
            return None

        return None
