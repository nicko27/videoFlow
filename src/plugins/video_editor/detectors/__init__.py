"""Detectors module for Video Editor."""

from .black_frame_detector import BlackFrameDetector, BlackFrameDetectorDialog
from .scene_detector import SceneDetectionWorker, SceneExportWorker
from .audio_extractor import AudioExtractionWorker

__all__ = [
    'BlackFrameDetector',
    'BlackFrameDetectorDialog',
    'SceneDetectionWorker',
    'SceneExportWorker',
    'AudioExtractionWorker'
]
