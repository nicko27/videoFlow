"""Handlingnaire de segments vidéo"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
import json
from .transitions import Transition, TransitionType
from .text_overlay import TextOverlay

@dataclass
class VideoSegment:
    """Représente un segment vidéo"""
    start_frame: int
    end_frame: Optional[int] = None
    name: str = ""
    color: str = "#0078D4"
    transition_in: Optional[Transition] = None
    transition_out: Optional[Transition] = None
    text_overlays: List[TextOverlay] = field(default_factory=list)

    def is_complete(self) -> bool:
        """Checks si the segment est complet"""
        return self.end_frame is not None

    def duration(self) -> int:
        """Returns la duration en frames"""
        if not self.is_complete():
            return 0
        return self.end_frame - self.start_frame

    def has_transition_in(self) -> bool:
        """Check if segment has an incoming transition"""
        return self.transition_in is not None and self.transition_in.type != TransitionType.NONE

    def has_transition_out(self) -> bool:
        """Check if segment has an outgoing transition"""
        return self.transition_out is not None and self.transition_out.type != TransitionType.NONE

    def has_text_overlays(self) -> bool:
        """Check if segment has text overlays"""
        return len(self.text_overlays) > 0

    def add_text_overlay(self, overlay: TextOverlay):
        """Add a text overlay to this segment"""
        self.text_overlays.append(overlay)

    def remove_text_overlay(self, index: int):
        """Remove a text overlay by index"""
        if 0 <= index < len(self.text_overlays):
            self.text_overlays.pop(index)

    def to_dict(self) -> dict:
        """Converts en dictionnaire"""
        data = {
            'start_frame': self.start_frame,
            'end_frame': self.end_frame,
            'name': self.name,
            'color': self.color
        }
        if self.transition_in:
            data['transition_in'] = self.transition_in.to_dict()
        if self.transition_out:
            data['transition_out'] = self.transition_out.to_dict()
        if self.text_overlays:
            data['text_overlays'] = [overlay.to_dict() for overlay in self.text_overlays]
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'VideoSegment':
        """Crée depuis un dictionnaire"""
        data = data.copy()  # Don't modify original
        transition_in = None
        transition_out = None
        text_overlays = []

        if 'transition_in' in data:
            transition_in = Transition.from_dict(data.pop('transition_in'))
        if 'transition_out' in data:
            transition_out = Transition.from_dict(data.pop('transition_out'))
        if 'text_overlays' in data:
            text_overlays = [TextOverlay.from_dict(o) for o in data.pop('text_overlays')]

        segment = cls(**data)
        segment.transition_in = transition_in
        segment.transition_out = transition_out
        segment.text_overlays = text_overlays
        return segment

class SegmentManager:
    """Gère the segments vidéo"""
    
    def __init__(self):
        self.segments: List[VideoSegment] = []
        self.current_segment: Optional[VideoSegment] = None
        self.colors = [
            "#0078D4",  # Blue
            "#107C10",  # Green
            "#D83B01",  # Orange
            "#E81123",  # Red
            "#744DA9",  # Violet
        ]
        self.color_index = 0
    
    def start_segment(self, frame: int) -> VideoSegment:
        """Commence un nouveau segment"""
        # Si un segment est in progress, on l'annule
        self.cancel_current_segment()
        
        # Créer le nouveau segment
        color = self.colors[self.color_index % len(self.colors)]
        self.color_index += 1
        
        self.current_segment = VideoSegment(
            start_frame=frame,
            color=color
        )
        return self.current_segment
    
    def end_segment(self, frame: int) -> Optional[VideoSegment]:
        """Finishes the segment in progress"""
        if self.current_segment and frame > self.current_segment.start_frame:
            self.current_segment.end_frame = frame
            self.segments.append(self.current_segment)
            segment = self.current_segment
            self.current_segment = None
            return segment
        return None
    
    def cancel_current_segment(self):
        """Cancels the segment in progress"""
        self.current_segment = None
    
    def remove_segment(self, index: int):
        """Removes un segment"""
        if 0 <= index < len(self.segments):
            self.segments.pop(index)
    
    def get_all_segments(self) -> List[VideoSegment]:
        """Returns tous the segments complets"""
        return self.segments.copy()
    
    def get_current_segment(self) -> Optional[VideoSegment]:
        """Returns the segment in progress"""
        return self.current_segment
    
    def clear(self):
        """Efface tous the segments"""
        self.segments.clear()
        self.current_segment = None
        self.color_index = 0
    
    def save_to_file(self, filepath: str):
        """Saves the segments in un file"""
        data = {
            'segments': [s.to_dict() for s in self.segments]
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_from_file(self, filepath: str):
        """Loads the segments depuis un file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                self.segments = [
                    VideoSegment.from_dict(s) for s in data.get('segments', [])
                ]
        except (FileNotFoundError, json.JSONDecodeError):
            self.segments = []
