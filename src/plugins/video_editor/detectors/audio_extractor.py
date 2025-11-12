"""Audio extraction engine for Audio Extractor plugin."""

import subprocess
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal
from src.core.logger import Logger
from src.core.validators import FFmpegValidator

logger = Logger.get_logger('AudioExtractor.Extractor')


class AudioExtractionWorker(QThread):
    """
    Worker thread for audio extraction.

    Extracts audio from videos using FFmpeg with configurable formats,
    bitrates, and normalization.

    Signals:
        progress (int, int): Current and total video count.
        file_complete (int, str): Index and output path.
        finished(): Extraction complete.
        error (str): Error message.
    """

    progress = pyqtSignal(int, int)
    file_complete = pyqtSignal(int, str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    # Format configurations
    FORMATS = {
        'MP3': {'codec': 'libmp3lame', 'ext': '.mp3'},
        'AAC': {'codec': 'aac', 'ext': '.m4a'},
        'WAV': {'codec': 'pcm_s16le', 'ext': '.wav'},
        'FLAC': {'codec': 'flac', 'ext': '.flac'},
        'OGG': {'codec': 'libvorbis', 'ext': '.ogg'},
    }

    def __init__(self, videos, output_format='MP3', bitrate=192,
                 normalize=False, output_folder=None, start_time=None, end_time=None,
                 custom_filename=None):
        """
        Initialize audio extraction worker.

        Args:
            videos (list): List of video file paths.
            output_format (str): Output format (MP3, AAC, WAV, FLAC, OGG).
            bitrate (int): Audio bitrate in kbps.
            normalize (bool): Apply volume normalization.
            output_folder (str, optional): Output folder path.
            start_time (float, optional): Start time in seconds.
            end_time (float, optional): End time in seconds.
            custom_filename (str, optional): Custom output filename (without extension).
        """
        super().__init__()
        self.videos = videos
        self.output_format = output_format
        self.bitrate = bitrate
        self.normalize = normalize
        self.output_folder = output_folder
        self.start_time = start_time
        self.end_time = end_time
        self.custom_filename = custom_filename
        self._stop = False
        self._current_process = None

    def run(self):
        """Execute extraction process."""
        try:
            for index, video_path in enumerate(self.videos):
                if self._stop:
                    break

                self.progress.emit(index, len(self.videos))

                # Extract audio
                output_path = self.extract_audio(video_path, index)

                if output_path:
                    self.file_complete.emit(index, output_path)
                else:
                    logger.error(f"Extraction failed for {video_path}")

            if not self._stop:
                self.finished.emit()

        except Exception as e:
            logger.error(f"Extraction error: {e}")
            self.error.emit(str(e))

    def extract_audio(self, video_path, index):
        """
        Extract audio from a single video file.

        Args:
            video_path (str): Input video path.
            index (int): Video index in list.

        Returns:
            str: Output file path or None if failed.
        """
        try:
            # Get format info
            format_info = self.FORMATS[self.output_format]

            # Determine output path
            if self.output_folder:
                output_dir = Path(self.output_folder)
            else:
                output_dir = Path(video_path).parent

            # Create output filename
            input_file = Path(video_path)
            if self.custom_filename:
                # Use custom filename if provided
                output_filename = f"{self.custom_filename}{format_info['ext']}"
            else:
                # Use input video stem by default
                output_filename = f"{input_file.stem}{format_info['ext']}"
            output_path = output_dir / output_filename

            # Build FFmpeg command
            cmd = self.build_ffmpeg_command(video_path, str(output_path), format_info)

            # Execute extraction
            logger.info(f"Extracting audio from {input_file.name} to {self.output_format}")

            self._current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Wait for completion
            stdout, stderr = self._current_process.communicate()

            if self._current_process.returncode == 0:
                logger.info(f"Successfully extracted audio from {input_file.name}")
                return str(output_path)
            else:
                logger.error(f"FFmpeg error: {stderr}")
                return None

        except Exception as e:
            logger.error(f"Error extracting audio from {video_path}: {e}")
            return None

    def build_ffmpeg_command(self, input_path, output_path, format_info):
        """
        Build FFmpeg command for audio extraction.

        Args:
            input_path (str): Input video path.
            output_path (str): Output audio path.
            format_info (dict): Format configuration.

        Returns:
            list: FFmpeg command arguments.
        """
        cmd = ['ffmpeg', '-y']  # Overwrite output

        # Time range
        if self.start_time is not None:
            cmd.extend(['-ss', str(self.start_time)])

        cmd.extend(['-i', input_path])

        if self.end_time is not None:
            duration = self.end_time - (self.start_time or 0)
            cmd.extend(['-t', str(duration)])

        # No video
        cmd.append('-vn')

        # Audio codec
        cmd.extend(['-c:a', format_info['codec']])

        # Bitrate (not for WAV/FLAC)
        if self.output_format not in ['WAV', 'FLAC']:
            cmd.extend(['-b:a', f'{self.bitrate}k'])

        # Volume normalization
        if self.normalize:
            cmd.extend(['-af', 'loudnorm'])

        # Metadata preservation
        cmd.extend(['-map_metadata', '0'])

        # Output
        cmd.append(output_path)

        return cmd

    def stop(self):
        """Stop the extraction process."""
        self._stop = True
        if self._current_process:
            try:
                self._current_process.terminate()
                self._current_process.wait(timeout=3)
            except Exception:
                try:
                    self._current_process.kill()
                except Exception:
                    pass
