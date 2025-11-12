"""Export Service - Business logic for video export operations.

This service handles video export operations using FFmpeg.
"""

import subprocess
from typing import List, Optional, Dict, Any
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal
from ..segment_manager import VideoSegment
from ..utils.time_utils import TimeCode
from src.core.logger import Logger

logger = Logger.get_logger('VideoEditor.ExportService')


class ExportPreset:
    """Predefined export presets for common platforms."""

    YOUTUBE_1080P = {
        'name': 'YouTube 1080p',
        'codec': 'libx264',
        'crf': 23,
        'resolution': (1920, 1080),
        'fps': 30,
        'audio_codec': 'aac',
        'audio_bitrate': '128k'
    }

    YOUTUBE_4K = {
        'name': 'YouTube 4K',
        'codec': 'libx264',
        'crf': 18,
        'resolution': (3840, 2160),
        'fps': 30,
        'audio_codec': 'aac',
        'audio_bitrate': '192k'
    }

    INSTAGRAM_FEED = {
        'name': 'Instagram Feed',
        'codec': 'libx264',
        'crf': 23,
        'resolution': (1080, 1080),  # Square
        'fps': 30,
        'audio_codec': 'aac',
        'audio_bitrate': '128k'
    }

    INSTAGRAM_STORY = {
        'name': 'Instagram Story',
        'codec': 'libx264',
        'crf': 23,
        'resolution': (1080, 1920),  # Vertical
        'fps': 30,
        'audio_codec': 'aac',
        'audio_bitrate': '128k'
    }

    TWITTER = {
        'name': 'Twitter',
        'codec': 'libx264',
        'crf': 23,
        'resolution': (1280, 720),
        'fps': 30,
        'audio_codec': 'aac',
        'audio_bitrate': '128k'
    }

    @classmethod
    def get_all_presets(cls) -> Dict[str, Dict[str, Any]]:
        """Get all available presets."""
        return {
            'youtube_1080p': cls.YOUTUBE_1080P,
            'youtube_4k': cls.YOUTUBE_4K,
            'instagram_feed': cls.INSTAGRAM_FEED,
            'instagram_story': cls.INSTAGRAM_STORY,
            'twitter': cls.TWITTER
        }


class ExportService(QObject):
    """Service for handling video export operations.

    Signals:
        export_started: Emitted when export starts
        export_progress: Emitted during export (current, total)
        export_finished: Emitted when export completes successfully (output_path)
        export_failed: Emitted when export fails (error_message)
    """

    export_started = pyqtSignal()
    export_progress = pyqtSignal(int, int)  # current, total
    export_finished = pyqtSignal(str)  # output_path
    export_failed = pyqtSignal(str)  # error_message

    def __init__(self):
        """Initialize the export service."""
        super().__init__()

    def validate_ffmpeg(self) -> bool:
        """Check if FFmpeg is available.

        Returns:
            True if FFmpeg is available, False otherwise
        """
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"FFmpeg validation failed: {str(e)}")
            return False

    def extract_segment(
        self,
        video_path: str,
        segment: VideoSegment,
        output_path: str,
        fps: float,
        codec: str = 'libx264',
        crf: int = 23
    ) -> bool:
        """Extract a single segment to a file.

        Args:
            video_path: Path to source video
            segment: Segment to extract
            output_path: Path for output file
            fps: Frames per second
            codec: Video codec to use
            crf: Constant Rate Factor for quality (lower = better)

        Returns:
            True if successful, False otherwise
        """
        timecode = TimeCode(fps)

        start_time = timecode.frames_to_seconds(segment.start_frame)
        end_time = timecode.frames_to_seconds(segment.end_frame)
        duration = end_time - start_time

        cmd = [
            'ffmpeg',
            '-ss', str(start_time),
            '-i', video_path,
            '-t', str(duration),
            '-c:v', codec,
        ]

        if codec != 'copy':
            cmd.extend(['-crf', str(crf)])
            cmd.extend(['-c:a', 'aac'])
        else:
            cmd.extend(['-c:a', 'copy'])

        cmd.extend(['-y', output_path])

        try:
            logger.info(f"Extracting segment to {output_path}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode != 0:
                error_msg = f"FFmpeg error: {result.stderr[:500]}"
                logger.error(error_msg)
                return False

            logger.info(f"Segment extracted successfully")
            return True

        except subprocess.TimeoutExpired:
            logger.error("FFmpeg timeout during extraction")
            return False
        except Exception as e:
            logger.error(f"Error extracting segment: {str(e)}")
            return False

    def export_frame_as_image(
        self,
        video_path: str,
        frame_num: int,
        output_path: str,
        fps: float,
        quality: int = 2  # 2-31 for JPEG, lower is better
    ) -> bool:
        """Export a single frame as an image.

        Args:
            video_path: Path to source video
            frame_num: Frame number to export
            output_path: Path for output image
            fps: Frames per second
            quality: JPEG quality (2-31, lower is better)

        Returns:
            True if successful, False otherwise
        """
        timecode = TimeCode(fps)
        timestamp = timecode.frames_to_seconds(frame_num)

        # Determine format from extension
        ext = Path(output_path).suffix.lower()
        if ext == '.png':
            codec_args = ['-c:v', 'png']
        else:  # Default to JPEG
            codec_args = ['-c:v', 'mjpeg', '-q:v', str(quality)]

        cmd = [
            'ffmpeg',
            '-ss', str(timestamp),
            '-i', video_path,
            '-frames:v', '1',
        ] + codec_args + [
            '-y',
            output_path
        ]

        try:
            logger.info(f"Exporting frame {frame_num} to {output_path}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                error_msg = f"FFmpeg error: {result.stderr[:500]}"
                logger.error(error_msg)
                return False

            logger.info("Frame exported successfully")
            return True

        except Exception as e:
            logger.error(f"Error exporting frame: {str(e)}")
            return False

    def extract_audio(
        self,
        video_path: str,
        output_path: str,
        start_time: Optional[float] = None,
        duration: Optional[float] = None,
        codec: str = 'aac',
        bitrate: str = '192k'
    ) -> bool:
        """Extract audio from video.

        Args:
            video_path: Path to source video
            output_path: Path for output audio file
            start_time: Optional start time in seconds
            duration: Optional duration in seconds
            codec: Audio codec to use
            bitrate: Audio bitrate

        Returns:
            True if successful, False otherwise
        """
        cmd = ['ffmpeg']

        if start_time is not None:
            cmd.extend(['-ss', str(start_time)])

        cmd.extend(['-i', video_path])

        if duration is not None:
            cmd.extend(['-t', str(duration)])

        cmd.extend([
            '-vn',  # No video
            '-c:a', codec,
            '-b:a', bitrate,
            '-y',
            output_path
        ])

        try:
            logger.info(f"Extracting audio to {output_path}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode != 0:
                error_msg = f"FFmpeg error: {result.stderr[:500]}"
                logger.error(error_msg)
                return False

            logger.info("Audio extracted successfully")
            return True

        except Exception as e:
            logger.error(f"Error extracting audio: {str(e)}")
            return False

    def get_video_info(self, video_path: str) -> Optional[Dict[str, Any]]:
        """Get video information using ffprobe.

        Args:
            video_path: Path to video file

        Returns:
            Dictionary with video info, or None if failed
        """
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            video_path
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                import json
                return json.loads(result.stdout)
            return None

        except Exception as e:
            logger.error(f"Error getting video info: {str(e)}")
            return None

    def apply_preset(
        self,
        video_path: str,
        output_path: str,
        preset_name: str,
        start_time: Optional[float] = None,
        duration: Optional[float] = None
    ) -> bool:
        """Export video with a predefined preset.

        Args:
            video_path: Path to source video
            output_path: Path for output file
            preset_name: Name of preset to use
            start_time: Optional start time in seconds
            duration: Optional duration in seconds

        Returns:
            True if successful, False otherwise
        """
        presets = ExportPreset.get_all_presets()

        if preset_name not in presets:
            logger.error(f"Unknown preset: {preset_name}")
            return False

        preset = presets[preset_name]

        cmd = ['ffmpeg']

        if start_time is not None:
            cmd.extend(['-ss', str(start_time)])

        cmd.extend(['-i', video_path])

        if duration is not None:
            cmd.extend(['-t', str(duration)])

        # Video settings
        cmd.extend([
            '-c:v', preset['codec'],
            '-crf', str(preset['crf']),
            '-r', str(preset['fps'])
        ])

        # Resolution
        if 'resolution' in preset:
            width, height = preset['resolution']
            cmd.extend(['-s', f'{width}x{height}'])

        # Audio settings
        cmd.extend([
            '-c:a', preset['audio_codec'],
            '-b:a', preset['audio_bitrate']
        ])

        cmd.extend(['-y', output_path])

        try:
            logger.info(f"Exporting with preset: {preset['name']}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600
            )

            if result.returncode != 0:
                error_msg = f"FFmpeg error: {result.stderr[:500]}"
                logger.error(error_msg)
                return False

            logger.info("Export completed successfully")
            return True

        except Exception as e:
            logger.error(f"Error exporting with preset: {str(e)}")
            return False
