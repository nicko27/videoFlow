"""Scene detection engine for Scene Detector plugin."""

import cv2
import subprocess
import json
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal
from src.core.logger import Logger

logger = Logger.get_logger('SceneDetector.Detector')


class SceneDetectionWorker(QThread):
    """
    Worker thread for scene detection.

    Detects scene changes using histogram comparison.

    Signals:
        progress (int): Progress percentage.
        scene_found (int, int): Start and end frame of detected scene.
        finished (list): List of detected scenes.
        error (str): Error message.
    """

    progress = pyqtSignal(int)
    scene_found = pyqtSignal(int, int)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, video_path, threshold=30.0, min_scene_length=30):
        """
        Initialize scene detection worker.

        Args:
            video_path (str): Input video path.
            threshold (float): Detection threshold (0-100, lower = more sensitive).
            min_scene_length (int): Minimum scene length in frames.
        """
        super().__init__()
        self.video_path = video_path
        self.threshold = threshold
        self.min_scene_length = min_scene_length
        self._stop = False

    def run(self):
        """Execute scene detection process."""
        try:
            scenes = self.detect_scenes()

            if not self._stop:
                self.finished.emit(scenes)

        except Exception as e:
            logger.error(f"Scene detection error: {e}")
            self.error.emit(str(e))

    def detect_scenes(self):
        """
        Detect scenes using histogram comparison.

        Returns:
            list: List of (start_frame, end_frame, timestamp) tuples.
        """
        cap = cv2.VideoCapture(self.video_path)
        try:
            if not cap.isOpened():
                raise Exception("Could not open video file")

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)

            scenes = []
            prev_hist = None
            scene_start = 0
            frame_num = 0

            logger.info(f"Detecting scenes with threshold {self.threshold}")

            while True:
                if self._stop:
                    break

                ret, frame = cap.read()
                if not ret:
                    break

                # Calculate histogram for current frame
                hist = self._calculate_histogram(frame)

                if prev_hist is not None:
                    # Compare with previous frame
                    diff = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CHISQR)

                    # Scene change detected
                    if diff > self.threshold:
                        scene_length = frame_num - scene_start

                        # Only add if scene is long enough
                        if scene_length >= self.min_scene_length:
                            timestamp = scene_start / fps if fps > 0 else 0
                            scenes.append((scene_start, frame_num - 1, timestamp))
                            self.scene_found.emit(scene_start, frame_num - 1)
                            logger.info(f"Scene detected: frames {scene_start}-{frame_num-1}")

                        scene_start = frame_num

                prev_hist = hist
                frame_num += 1

                # Update progress every 10 frames (more frequent)
                if frame_num % 10 == 0:
                    progress = int((frame_num / total_frames) * 100)
                    self.progress.emit(progress)

            # Add final scene
            if scene_start < frame_num:
                scene_length = frame_num - scene_start
                if scene_length >= self.min_scene_length:
                    timestamp = scene_start / fps if fps > 0 else 0
                    scenes.append((scene_start, frame_num - 1, timestamp))
                    self.scene_found.emit(scene_start, frame_num - 1)
        finally:
            cap.release()

        logger.info(f"Scene detection complete: {len(scenes)} scenes found")
        return scenes

    def _calculate_histogram(self, frame):
        """
        Calculate color histogram for a frame.

        Args:
            frame: OpenCV frame.

        Returns:
            Normalized histogram.
        """
        # Calculate histogram for each channel (BGR)
        hist = cv2.calcHist(
            [frame],
            [0, 1, 2],
            None,
            [8, 8, 8],
            [0, 256, 0, 256, 0, 256]
        )

        # Normalize
        hist = cv2.normalize(hist, hist).flatten()
        return hist

    def stop(self):
        """Stop the detection process."""
        self._stop = True


class SceneExportWorker(QThread):
    """
    Worker thread for exporting detected scenes.

    Signals:
        progress (int, int): Current and total scenes.
        scene_complete (int): Scene index.
        finished(): Export complete.
        error (str): Error message.
    """

    progress = pyqtSignal(int, int)
    scene_complete = pyqtSignal(int)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, video_path, scenes, output_folder, export_mode='split'):
        """
        Initialize scene export worker.

        Args:
            video_path (str): Input video path.
            scenes (list): List of (start_frame, end_frame, timestamp) tuples.
            output_folder (str): Output folder path.
            export_mode (str): 'split', 'thumbnails', or 'timestamps'.
        """
        super().__init__()
        self.video_path = video_path
        self.scenes = scenes
        self.output_folder = output_folder
        self.export_mode = export_mode
        self._stop = False

    def run(self):
        """Execute export process."""
        try:
            if self.export_mode == 'split':
                self.export_split_videos()
            elif self.export_mode == 'thumbnails':
                self.export_thumbnails()
            elif self.export_mode == 'timestamps':
                self.export_timestamps()

            if not self._stop:
                self.finished.emit()

        except Exception as e:
            logger.error(f"Export error: {e}")
            self.error.emit(str(e))

    def export_split_videos(self):
        """Export each scene as a separate video file."""
        cap = cv2.VideoCapture(self.video_path)
        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
        finally:
            cap.release()

        input_file = Path(self.video_path)

        for index, (start_frame, end_frame, timestamp) in enumerate(self.scenes):
            if self._stop:
                break

            self.progress.emit(index, len(self.scenes))

            # Calculate time range
            start_time = start_frame / fps if fps > 0 else 0
            end_time = end_frame / fps if fps > 0 else 0
            duration = end_time - start_time

            # Output filename
            output_filename = f"{input_file.stem}_scene_{index+1:03d}{input_file.suffix}"
            output_path = Path(self.output_folder) / output_filename

            # FFmpeg command for extraction
            cmd = [
                'ffmpeg', '-y',
                '-ss', str(start_time),
                '-i', self.video_path,
                '-t', str(duration),
                '-c', 'copy',  # Stream copy
                str(output_path)
            ]

            try:
                subprocess.run(cmd, capture_output=True, check=True)
                self.scene_complete.emit(index)
                logger.info(f"Exported scene {index+1}: {output_filename}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to export scene {index+1}: {e}")
                # Continue with remaining scenes

    def export_thumbnails(self):
        """Export thumbnail for each scene."""
        cap = cv2.VideoCapture(self.video_path)
        try:
            input_file = Path(self.video_path)

            for index, (start_frame, end_frame, timestamp) in enumerate(self.scenes):
                if self._stop:
                    break

                self.progress.emit(index, len(self.scenes))

                # Seek to middle of scene
                mid_frame = (start_frame + end_frame) // 2
                cap.set(cv2.CAP_PROP_POS_FRAMES, mid_frame)

                ret, frame = cap.read()
                if ret:
                    # Save thumbnail
                    output_filename = f"{input_file.stem}_scene_{index+1:03d}.jpg"
                    output_path = Path(self.output_folder) / output_filename
                    cv2.imwrite(str(output_path), frame)

                    self.scene_complete.emit(index)
                    logger.info(f"Exported thumbnail {index+1}: {output_filename}")
        finally:
            cap.release()

    def export_timestamps(self):
        """Export scene timestamps as JSON and CSV."""
        input_file = Path(self.video_path)

        # Prepare data
        cap = cv2.VideoCapture(self.video_path)
        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
        finally:
            cap.release()

        scenes_data = []
        for index, (start_frame, end_frame, timestamp) in enumerate(self.scenes):
            start_time = start_frame / fps if fps > 0 else 0
            end_time = end_frame / fps if fps > 0 else 0

            scenes_data.append({
                'scene': index + 1,
                'start_frame': start_frame,
                'end_frame': end_frame,
                'start_time': start_time,
                'end_time': end_time,
                'duration': end_time - start_time
            })

        # Export JSON
        json_path = Path(self.output_folder) / f"{input_file.stem}_scenes.json"
        with open(json_path, 'w') as f:
            json.dump(scenes_data, f, indent=2)

        logger.info(f"Exported timestamps: {json_path.name}")

        # Export CSV
        csv_path = Path(self.output_folder) / f"{input_file.stem}_scenes.csv"
        with open(csv_path, 'w') as f:
            f.write("Scene,Start Frame,End Frame,Start Time (s),End Time (s),Duration (s)\n")
            for scene in scenes_data:
                f.write(
                    f"{scene['scene']},{scene['start_frame']},{scene['end_frame']},"
                    f"{scene['start_time']:.2f},{scene['end_time']:.2f},{scene['duration']:.2f}\n"
                )

        logger.info(f"Exported timestamps: {csv_path.name}")

        self.progress.emit(len(self.scenes), len(self.scenes))

    def stop(self):
        """Stop the export process."""
        self._stop = True
