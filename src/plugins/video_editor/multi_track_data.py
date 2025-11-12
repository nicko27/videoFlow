"""Multi-track data models for Video Editor.

This module provides data structures for multi-track timeline support,
enabling complex video compositions with multiple layers.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
from pathlib import Path


class TrackType(Enum):
    """Type of track content."""

    VIDEO = "video"  # Video with audio
    AUDIO = "audio"  # Audio only
    OVERLAY = "overlay"  # Overlay video (picture-in-picture)
    TEXT = "text"  # Text overlays only
    EFFECTS = "effects"  # Effects layer


class BlendMode(Enum):
    """How tracks blend with layers below."""

    NORMAL = "normal"  # Standard overlay
    MULTIPLY = "multiply"  # Multiply blend
    SCREEN = "screen"  # Screen blend
    OVERLAY = "overlay"  # Overlay blend
    ADD = "add"  # Additive blend


@dataclass
class TrackSegment:
    """Segment placed on a track.

    Attributes:
        segment_id: Reference to VideoSegment
        start_frame: Starting frame on timeline
        end_frame: Ending frame on timeline
        offset_frame: Offset into source segment
        enabled: Whether segment is active
        opacity: Segment opacity (0.0-1.0)
        volume: Audio volume (0.0-1.0)
        position: Optional (x, y) position for overlay tracks
        scale: Optional scale factor for overlay tracks
    """

    segment_id: str  # UUID or index
    start_frame: int
    end_frame: int
    offset_frame: int = 0
    enabled: bool = True
    opacity: float = 1.0
    volume: float = 1.0
    position: Optional[tuple[int, int]] = None
    scale: Optional[float] = None

    def get_duration(self) -> int:
        """Get segment duration in frames.

        Returns:
            Duration in frames
        """
        return self.end_frame - self.start_frame

    def contains_frame(self, frame: int) -> bool:
        """Check if segment contains a frame.

        Args:
            frame: Frame number

        Returns:
            True if segment contains frame
        """
        return self.start_frame <= frame < self.end_frame

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            'segment_id': self.segment_id,
            'start_frame': self.start_frame,
            'end_frame': self.end_frame,
            'offset_frame': self.offset_frame,
            'enabled': self.enabled,
            'opacity': self.opacity,
            'volume': self.volume,
            'position': list(self.position) if self.position else None,
            'scale': self.scale
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TrackSegment':
        """Create from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            TrackSegment instance
        """
        data = data.copy()
        if 'position' in data and data['position']:
            data['position'] = tuple(data['position'])
        return cls(**data)


@dataclass
class Track:
    """A timeline track that can contain multiple segments.

    Attributes:
        track_id: Unique track identifier
        name: Track display name
        track_type: Type of content
        segments: List of segments on this track
        enabled: Whether track is active
        locked: Whether track is locked for editing
        solo: Whether track is soloed (mutes others)
        muted: Whether track audio is muted
        height: UI height in pixels
        color: Track color for UI
        blend_mode: How track blends with layers below
        opacity: Overall track opacity
    """

    track_id: str
    name: str
    track_type: TrackType = TrackType.VIDEO
    segments: List[TrackSegment] = field(default_factory=list)
    enabled: bool = True
    locked: bool = False
    solo: bool = False
    muted: bool = False
    height: int = 80
    color: str = "#0078D4"
    blend_mode: BlendMode = BlendMode.NORMAL
    opacity: float = 1.0

    def add_segment(self, segment: TrackSegment) -> None:
        """Add segment to track.

        Args:
            segment: Segment to add
        """
        # Insert in sorted order by start_frame
        insert_idx = 0
        for i, existing in enumerate(self.segments):
            if segment.start_frame < existing.start_frame:
                insert_idx = i
                break
            insert_idx = i + 1

        self.segments.insert(insert_idx, segment)

    def remove_segment(self, segment_id: str) -> bool:
        """Remove segment from track.

        Args:
            segment_id: Segment ID to remove

        Returns:
            True if segment was removed
        """
        for i, seg in enumerate(self.segments):
            if seg.segment_id == segment_id:
                self.segments.pop(i)
                return True
        return False

    def get_segment_at_frame(self, frame: int) -> Optional[TrackSegment]:
        """Get segment at specific frame.

        Args:
            frame: Frame number

        Returns:
            TrackSegment if found, None otherwise
        """
        for segment in self.segments:
            if segment.contains_frame(frame):
                return segment
        return None

    def get_active_segments_at_frame(self, frame: int) -> List[TrackSegment]:
        """Get all active segments at frame.

        Args:
            frame: Frame number

        Returns:
            List of active segments
        """
        return [
            seg for seg in self.segments
            if seg.enabled and seg.contains_frame(frame)
        ]

    def has_overlap(self, start_frame: int, end_frame: int) -> bool:
        """Check if time range overlaps with any segment.

        Args:
            start_frame: Range start
            end_frame: Range end

        Returns:
            True if overlap exists
        """
        for segment in self.segments:
            # Check for overlap
            if not (end_frame <= segment.start_frame or start_frame >= segment.end_frame):
                return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            'track_id': self.track_id,
            'name': self.name,
            'track_type': self.track_type.value,
            'segments': [seg.to_dict() for seg in self.segments],
            'enabled': self.enabled,
            'locked': self.locked,
            'solo': self.solo,
            'muted': self.muted,
            'height': self.height,
            'color': self.color,
            'blend_mode': self.blend_mode.value,
            'opacity': self.opacity
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Track':
        """Create from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            Track instance
        """
        data = data.copy()
        if 'track_type' in data:
            data['track_type'] = TrackType(data['track_type'])
        if 'blend_mode' in data:
            data['blend_mode'] = BlendMode(data['blend_mode'])
        if 'segments' in data:
            data['segments'] = [TrackSegment.from_dict(s) for s in data['segments']]
        return cls(**data)


@dataclass
class MultiTrackProject:
    """Complete multi-track project data.

    Attributes:
        tracks: List of tracks (ordered bottom to top)
        total_frames: Total timeline length
        fps: Frame rate
        width: Video width
        height: Video height
        audio_tracks: Number of audio tracks
    """

    tracks: List[Track] = field(default_factory=list)
    total_frames: int = 0
    fps: float = 30.0
    width: int = 1920
    height: int = 1080
    audio_tracks: int = 2

    def add_track(
        self,
        name: str,
        track_type: TrackType = TrackType.VIDEO,
        position: Optional[int] = None
    ) -> Track:
        """Add new track.

        Args:
            name: Track name
            track_type: Type of track
            position: Optional insertion position (None = append)

        Returns:
            Created track
        """
        import uuid
        track = Track(
            track_id=str(uuid.uuid4()),
            name=name,
            track_type=track_type
        )

        if position is None:
            self.tracks.append(track)
        else:
            self.tracks.insert(position, track)

        return track

    def remove_track(self, track_id: str) -> bool:
        """Remove track.

        Args:
            track_id: Track ID to remove

        Returns:
            True if track was removed
        """
        for i, track in enumerate(self.tracks):
            if track.track_id == track_id:
                self.tracks.pop(i)
                return True
        return False

    def get_track_by_id(self, track_id: str) -> Optional[Track]:
        """Get track by ID.

        Args:
            track_id: Track ID

        Returns:
            Track if found
        """
        for track in self.tracks:
            if track.track_id == track_id:
                return track
        return None

    def move_track(self, track_id: str, new_position: int) -> bool:
        """Move track to new position.

        Args:
            track_id: Track to move
            new_position: New position (0 = bottom)

        Returns:
            True if moved
        """
        for i, track in enumerate(self.tracks):
            if track.track_id == track_id:
                track = self.tracks.pop(i)
                self.tracks.insert(new_position, track)
                return True
        return False

    def get_all_segments_at_frame(self, frame: int) -> List[tuple[Track, TrackSegment]]:
        """Get all segments across all tracks at frame.

        Args:
            frame: Frame number

        Returns:
            List of (track, segment) tuples
        """
        result = []
        for track in self.tracks:
            if not track.enabled:
                continue
            for segment in track.get_active_segments_at_frame(frame):
                result.append((track, segment))
        return result

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            'tracks': [track.to_dict() for track in self.tracks],
            'total_frames': self.total_frames,
            'fps': self.fps,
            'width': self.width,
            'height': self.height,
            'audio_tracks': self.audio_tracks
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MultiTrackProject':
        """Create from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            MultiTrackProject instance
        """
        data = data.copy()
        if 'tracks' in data:
            data['tracks'] = [Track.from_dict(t) for t in data['tracks']]
        return cls(**data)
