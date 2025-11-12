"""Export video segments with transition effects using FFmpeg.

This module provides functionality to export video segments with smooth
transitions between them using FFmpeg's xfade filter.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import List, Tuple
from PyQt6.QtCore import QThread, pyqtSignal

from .segment_manager import VideoSegment
from .transitions import Transition, TransitionType, calculate_transition_offset
from .text_overlay import TextOverlay
from src.core.logger import Logger

logger = Logger.get_logger('VideoEditor.TransitionExport')


class TransitionExportWorker(QThread):
    """Worker thread for exporting video with transitions.

    Signals:
        progress: Export progress (0-100)
        status_message: Status update message
        finished: Export completed with output path
        error: Error occurred with error message
    """

    progress = pyqtSignal(int)
    status_message = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, video_path: str, segments: List[VideoSegment],
                 output_path: str, fps: float = 30.0, resolution: Tuple[int, int] = None):
        """Initialize transition export worker.

        Args:
            video_path: Path to source video file
            segments: List of video segments to export
            output_path: Path for output video file
            fps: Frames per second of the video
            resolution: Video resolution (width, height), None for auto-detect
        """
        super().__init__()
        self.video_path = video_path
        self.segments = segments
        self.output_path = output_path
        self.fps = fps
        self.resolution = resolution
        self._stop = False

    def run(self):
        """Execute the export with transitions."""
        try:
            if not self.segments:
                self.error.emit("No segments to export")
                return

            self.status_message.emit("Preparing segments...")

            # If no resolution provided, detect it
            if not self.resolution:
                self.resolution = self._detect_resolution()

            width, height = self.resolution

            # Check if any transitions are used
            has_transitions = any(
                seg.has_transition_out() for seg in self.segments[:-1]
            )

            if not has_transitions:
                # Simple concatenation without re-encoding
                self._export_without_transitions()
            else:
                # Complex export with xfade transitions
                self._export_with_transitions(width, height)

        except Exception as e:
            logger.error(f"Export error: {e}")
            self.error.emit(str(e))

    def _detect_resolution(self) -> Tuple[int, int]:
        """Detect video resolution using ffprobe.

        Returns:
            Tuple of (width, height)
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=width,height',
                '-of', 'csv=p=0',
                self.video_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            width, height = map(int, result.stdout.strip().split(','))
            logger.debug(f"Detected resolution: {width}x{height}")
            return (width, height)

        except Exception as e:
            logger.warning(f"Could not detect resolution: {e}, using default 1920x1080")
            return (1920, 1080)

    def _export_without_transitions(self):
        """Export segments without transitions (simple concatenation)."""
        self.status_message.emit("Exporting segments without transitions...")

        # Create temporary segment files
        temp_segments = []
        temp_dir = tempfile.mkdtemp()

        try:
            # Extract each segment
            for i, segment in enumerate(self.segments):
                if self._stop:
                    return

                self.status_message.emit(f"Extracting segment {i+1}/{len(self.segments)}...")
                self.progress.emit(int((i / len(self.segments)) * 50))

                temp_file = os.path.join(temp_dir, f"segment_{i}.mp4")
                self._extract_segment(segment, temp_file)
                temp_segments.append(temp_file)

            # Concatenate segments
            self.status_message.emit("Merging segments...")
            self.progress.emit(50)

            concat_file = os.path.join(temp_dir, 'concat_list.txt')
            with open(concat_file, 'w') as f:
                for seg_file in temp_segments:
                    f.write(f"file '{seg_file}'\n")

            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c', 'copy',
                self.output_path
            ]

            subprocess.run(cmd, check=True, capture_output=True)

            self.progress.emit(100)
            self.status_message.emit("Export complete!")
            self.finished.emit(self.output_path)

        finally:
            # Cleanup temp files
            for temp_file in temp_segments:
                try:
                    os.unlink(temp_file)
                except Exception as e:
                    logger.warning(f"Could not delete temporary segment file {temp_file}: {str(e)}")
            try:
                os.rmdir(temp_dir)
            except Exception as e:
                logger.debug(f"Could not remove temporary directory {temp_dir}: {str(e)}")

    def _export_with_transitions(self, width: int, height: int):
        """Export segments with xfade transitions.

        Args:
            width: Video width
            height: Video height
        """
        self.status_message.emit("Exporting with transitions...")

        # Extract all segments to temp files
        temp_segments = []
        temp_dir = tempfile.mkdtemp()

        try:
            # Extract segments
            for i, segment in enumerate(self.segments):
                if self._stop:
                    return

                self.status_message.emit(f"Extracting segment {i+1}/{len(self.segments)}...")
                self.progress.emit(int((i / len(self.segments)) * 40))

                temp_file = os.path.join(temp_dir, f"segment_{i}.mp4")
                self._extract_segment(segment, temp_file)
                temp_segments.append(temp_file)

            # Build complex filter graph with xfade
            self.status_message.emit("Building transition effects...")
            self.progress.emit(50)

            filter_complex = self._build_xfade_filter(temp_segments, width, height)

            # Run FFmpeg with complex filter
            self.status_message.emit("Rendering final video...")

            cmd = [
                'ffmpeg', '-y'
            ]

            # Add all input files
            for temp_file in temp_segments:
                cmd.extend(['-i', temp_file])

            # Add filter complex
            cmd.extend([
                '-filter_complex', filter_complex,
                '-map', '[out]',
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '23',
                self.output_path
            ])

            logger.debug(f"FFmpeg command: {' '.join(cmd)}")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Monitor progress
            while process.poll() is None:
                if self._stop:
                    process.terminate()
                    self.error.emit("Export cancelled")
                    return

                # Update progress (50-100%)
                self.progress.emit(50 + (process.poll() or 0))

            if process.returncode == 0:
                self.progress.emit(100)
                self.status_message.emit("Export complete!")
                self.finished.emit(self.output_path)
            else:
                stderr = process.stderr.read()
                logger.error(f"FFmpeg error: {stderr}")
                self.error.emit(f"Export failed: {stderr[:200]}")

        finally:
            # Cleanup
            for temp_file in temp_segments:
                try:
                    os.unlink(temp_file)
                except Exception as e:
                    logger.warning(f"Could not delete temporary segment file {temp_file}: {str(e)}")
            try:
                os.rmdir(temp_dir)
            except Exception as e:
                logger.debug(f"Could not remove temporary directory {temp_dir}: {str(e)}")

    def _extract_segment(self, segment: VideoSegment, output_path: str):
        """Extract a single segment from the source video.

        Args:
            segment: VideoSegment to extract
            output_path: Path for extracted segment
        """
        start_time = segment.start_frame / self.fps
        end_time = segment.end_frame / self.fps
        duration = end_time - start_time

        cmd = [
            'ffmpeg', '-y',
            '-i', self.video_path,
            '-ss', str(start_time),
            '-t', str(duration),
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-crf', '18',
            '-c:a', 'aac',
            output_path
        ]

        subprocess.run(cmd, check=True, capture_output=True)

    def _build_xfade_filter(self, segment_files: List[str],
                           width: int, height: int) -> str:
        """Build FFmpeg filter_complex for xfade transitions.

        Args:
            segment_files: List of segment file paths
            width: Video width
            height: Video height

        Returns:
            Filter complex string for FFmpeg
        """
        if len(segment_files) == 1:
            return "[0:v]copy[out]"

        # Calculate segment durations and transition offsets
        filters = []
        current_offset = 0.0

        for i in range(len(segment_files) - 1):
            segment = self.segments[i]

            # Get segment duration
            segment_duration = (segment.end_frame - segment.start_frame) / self.fps

            # Get transition (if any)
            transition = segment.transition_out
            if not transition or transition.type == TransitionType.NONE:
                # No transition, just concatenate
                transition_duration = 0.0
                transition_filter = ""
            else:
                transition_duration = transition.duration
                # Calculate offset for xfade
                offset = current_offset + segment_duration - transition_duration
                transition_filter = transition.get_ffmpeg_filter(width, height)
                transition_filter += f":offset={offset}"

            if i == 0:
                # First transition
                if transition_filter:
                    filters.append(f"[0:v][1:v]{transition_filter}[v01]")
                    label_in = "v01"
                else:
                    label_in = "0:v"
            else:
                # Subsequent transitions
                label_out = f"v{i}{i+1}" if i < len(segment_files) - 2 else "out"
                if transition_filter:
                    filters.append(f"[{label_in}][{i+1}:v]{transition_filter}[{label_out}]")
                    label_in = label_out
                else:
                    label_in = f"{i+1}:v"

            # Update offset for next transition
            current_offset += segment_duration - transition_duration

        # If no transitions were added, just copy first video
        if not filters:
            return "[0:v]copy[out]"

        # Join all filters
        return ";".join(filters)

    def _build_text_overlay_filter(self, input_label: str, width: int, height: int) -> str:
        """Build FFmpeg filter for text overlays on all segments.

        Args:
            input_label: Input stream label (e.g., "[out]" or "[0:v]")
            width: Video width
            height: Video height

        Returns:
            Filter string with all text overlays applied
        """
        # Collect all text overlays from all segments
        all_overlays = []

        current_time = 0.0
        for segment in self.segments:
            if not hasattr(segment, 'text_overlays') or not segment.text_overlays:
                # Calculate segment duration and add to current time
                segment_duration = (segment.end_frame - segment.start_frame) / self.fps
                current_time += segment_duration
                continue

            # Calculate segment start time in the final video
            segment_start_time = current_time
            segment_duration = (segment.end_frame - segment.start_frame) / self.fps

            for overlay in segment.text_overlays:
                # Adjust overlay timing to global video time
                global_start = segment_start_time + (overlay.start_frame / self.fps)
                global_end = segment_start_time + (overlay.end_frame / self.fps if overlay.end_frame else segment_duration)

                # Create a copy with adjusted timing
                adjusted_overlay = TextOverlay(
                    text=overlay.text,
                    style=overlay.style,
                    position=overlay.position,
                    custom_position=overlay.custom_position,
                    start_frame=int(global_start * self.fps),
                    end_frame=int(global_end * self.fps),
                    animation=overlay.animation,
                    animation_duration=overlay.animation_duration,
                    name=overlay.name,
                    enabled=overlay.enabled
                )

                all_overlays.append(adjusted_overlay)

            current_time += segment_duration

        # If no overlays, return input unchanged
        if not all_overlays:
            return input_label.strip("[]")

        # Build filter chain for all overlays
        current_input = input_label.strip("[]")

        for i, overlay in enumerate(all_overlays):
            if not overlay.enabled:
                continue

            # Generate drawtext filter
            drawtext_filter = overlay.get_ffmpeg_filter(width, height, self.fps)

            # Chain the filter
            if i == len(all_overlays) - 1:
                # Last overlay outputs to [textout]
                filter_str = f"[{current_input}]{drawtext_filter}[textout]"
            else:
                # Intermediate overlays
                filter_str = f"[{current_input}]{drawtext_filter}[text{i}]"
                current_input = f"text{i}"

            # Note: We'll need to chain these in the main filter complex

        return "textout"

    def stop(self):
        """Stop the export operation."""
        self._stop = True
