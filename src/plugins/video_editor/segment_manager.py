"""Gestionnaire de segments vidéo"""

from dataclasses import dataclass
from typing import List, Optional, Dict
import json

@dataclass
class VideoSegment:
    """Représente un segment vidéo"""
    start_frame: int
    end_frame: Optional[int] = None
    name: str = ""
    color: str = "#0078D4"
    
    def is_complete(self) -> bool:
        """Vérifie si le segment est complet"""
        return self.end_frame is not None
    
    def duration(self) -> int:
        """Retourne la durée en frames"""
        if not self.is_complete():
            return 0
        return self.end_frame - self.start_frame
    
    def to_dict(self) -> dict:
        """Convertit en dictionnaire"""
        return {
            'start_frame': self.start_frame,
            'end_frame': self.end_frame,
            'name': self.name,
            'color': self.color
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'VideoSegment':
        """Crée depuis un dictionnaire"""
        return cls(**data)

class SegmentManager:
    """Gère les segments vidéo"""
    
    def __init__(self):
        self.segments: List[VideoSegment] = []
        self.current_segment: Optional[VideoSegment] = None
        self.colors = [
            "#0078D4",  # Bleu
            "#107C10",  # Vert
            "#D83B01",  # Orange
            "#E81123",  # Rouge
            "#744DA9",  # Violet
        ]
        self.color_index = 0
    
    def start_segment(self, frame: int) -> VideoSegment:
        """Commence un nouveau segment"""
        # Si un segment est en cours, on l'annule
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
        """Termine le segment en cours"""
        if self.current_segment and frame > self.current_segment.start_frame:
            self.current_segment.end_frame = frame
            self.segments.append(self.current_segment)
            segment = self.current_segment
            self.current_segment = None
            return segment
        return None
    
    def cancel_current_segment(self):
        """Annule le segment en cours"""
        self.current_segment = None
    
    def remove_segment(self, index: int):
        """Supprime un segment"""
        if 0 <= index < len(self.segments):
            self.segments.pop(index)
    
    def get_all_segments(self) -> List[VideoSegment]:
        """Retourne tous les segments complets"""
        return self.segments.copy()
    
    def get_current_segment(self) -> Optional[VideoSegment]:
        """Retourne le segment en cours"""
        return self.current_segment
    
    def clear(self):
        """Efface tous les segments"""
        self.segments.clear()
        self.current_segment = None
        self.color_index = 0
    
    def save_to_file(self, filepath: str):
        """Sauvegarde les segments dans un fichier"""
        data = {
            'segments': [s.to_dict() for s in self.segments]
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_from_file(self, filepath: str):
        """Charge les segments depuis un fichier"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                self.segments = [
                    VideoSegment.from_dict(s) for s in data.get('segments', [])
                ]
        except (FileNotFoundError, json.JSONDecodeError):
            self.segments = []
