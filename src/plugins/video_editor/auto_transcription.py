"""Automatic transcription system using Whisper AI.

Provides automatic subtitle generation from video audio using
OpenAI's Whisper speech recognition model.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
import subprocess
import json
import tempfile


class WhisperModel(Enum):
    """Whisper model sizes."""

    TINY = "tiny"  # ~39M params, fastest
    BASE = "base"  # ~74M params
    SMALL = "small"  # ~244M params
    MEDIUM = "medium"  # ~769M params
    LARGE = "large"  # ~1550M params, most accurate


class TranscriptionLanguage(Enum):
    """Supported languages for transcription."""

    AUTO = "auto"  # Auto-detect
    ENGLISH = "en"
    FRENCH = "fr"
    SPANISH = "es"
    GERMAN = "de"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    CHINESE = "zh"
    JAPANESE = "ja"
    KOREAN = "ko"
    RUSSIAN = "ru"
    ARABIC = "ar"
    HINDI = "hi"


@dataclass
class TranscriptionWord:
    """A single transcribed word with timing.

    Attributes:
        word: The transcribed word
        start: Start time in seconds
        end: End time in seconds
        confidence: Confidence score (0.0-1.0)
    """

    word: str
    start: float
    end: float
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            'word': self.word,
            'start': self.start,
            'end': self.end,
            'confidence': self.confidence
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TranscriptionWord':
        """Create from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            TranscriptionWord instance
        """
        return cls(**data)


@dataclass
class TranscriptionSegment:
    """A transcribed segment with multiple words.

    Attributes:
        id: Segment ID
        text: Complete segment text
        start: Start time in seconds
        end: End time in seconds
        words: Individual words with timing
        language: Detected language
        confidence: Overall confidence score
    """

    id: int
    text: str
    start: float
    end: float
    words: List[TranscriptionWord] = field(default_factory=list)
    language: str = "en"
    confidence: float = 1.0

    def get_duration(self) -> float:
        """Get segment duration in seconds.

        Returns:
            Duration in seconds
        """
        return self.end - self.start

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            'id': self.id,
            'text': self.text,
            'start': self.start,
            'end': self.end,
            'words': [w.to_dict() for w in self.words],
            'language': self.language,
            'confidence': self.confidence
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TranscriptionSegment':
        """Create from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            TranscriptionSegment instance
        """
        data = data.copy()
        if 'words' in data:
            data['words'] = [TranscriptionWord.from_dict(w) for w in data['words']]
        return cls(**data)


@dataclass
class TranscriptionResult:
    """Complete transcription result.

    Attributes:
        segments: List of transcription segments
        language: Detected language
        duration: Total audio duration
        model_used: Whisper model used
        word_count: Total word count
    """

    segments: List[TranscriptionSegment] = field(default_factory=list)
    language: str = "en"
    duration: float = 0.0
    model_used: str = "base"
    word_count: int = 0

    def get_full_text(self) -> str:
        """Get complete transcription text.

        Returns:
            Full text
        """
        return " ".join(seg.text for seg in self.segments)

    def get_segments_in_range(self, start: float, end: float) -> List[TranscriptionSegment]:
        """Get segments within time range.

        Args:
            start: Start time in seconds
            end: End time in seconds

        Returns:
            List of segments in range
        """
        return [
            seg for seg in self.segments
            if not (seg.end <= start or seg.start >= end)
        ]

    def export_to_srt(self, output_path: str):
        """Export transcription to SRT subtitle format.

        Args:
            output_path: Output SRT file path
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(self.segments, start=1):
                # SRT index
                f.write(f"{i}\n")

                # Timestamp
                start_time = self._format_srt_timestamp(segment.start)
                end_time = self._format_srt_timestamp(segment.end)
                f.write(f"{start_time} --> {end_time}\n")

                # Text
                f.write(f"{segment.text}\n\n")

    def export_to_vtt(self, output_path: str):
        """Export transcription to WebVTT format.

        Args:
            output_path: Output VTT file path
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("WEBVTT\n\n")

            for segment in self.segments:
                # Timestamp
                start_time = self._format_vtt_timestamp(segment.start)
                end_time = self._format_vtt_timestamp(segment.end)
                f.write(f"{start_time} --> {end_time}\n")

                # Text
                f.write(f"{segment.text}\n\n")

    def _format_srt_timestamp(self, seconds: float) -> str:
        """Format timestamp for SRT format.

        Args:
            seconds: Time in seconds

        Returns:
            Formatted timestamp (HH:MM:SS,mmm)
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def _format_vtt_timestamp(self, seconds: float) -> str:
        """Format timestamp for VTT format.

        Args:
            seconds: Time in seconds

        Returns:
            Formatted timestamp (HH:MM:SS.mmm)
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            'segments': [seg.to_dict() for seg in self.segments],
            'language': self.language,
            'duration': self.duration,
            'model_used': self.model_used,
            'word_count': self.word_count
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TranscriptionResult':
        """Create from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            TranscriptionResult instance
        """
        data = data.copy()
        if 'segments' in data:
            data['segments'] = [TranscriptionSegment.from_dict(s) for s in data['segments']]
        return cls(**data)


class WhisperTranscriber:
    """Whisper AI transcription service.

    Uses OpenAI's Whisper model for automatic speech recognition.
    """

    def __init__(self, model: WhisperModel = WhisperModel.BASE):
        """Initialize transcriber.

        Args:
            model: Whisper model to use
        """
        self.model = model
        self._check_whisper_installation()

    def _check_whisper_installation(self) -> bool:
        """Check if Whisper is installed.

        Returns:
            True if Whisper is available

        Raises:
            RuntimeError: If Whisper is not installed
        """
        try:
            import whisper
            return True
        except ImportError:
            raise RuntimeError(
                "Whisper not installed. Install with: pip install openai-whisper"
            )

    def transcribe_video(
        self,
        video_path: str,
        language: TranscriptionLanguage = TranscriptionLanguage.AUTO,
        word_timestamps: bool = True
    ) -> TranscriptionResult:
        """Transcribe audio from video file.

        Args:
            video_path: Path to video file
            language: Target language (auto-detect if AUTO)
            word_timestamps: Include word-level timestamps

        Returns:
            TranscriptionResult with segments

        Raises:
            FileNotFoundError: If video file doesn't exist
            RuntimeError: If transcription fails
        """
        if not Path(video_path).exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # Extract audio to temporary file
        audio_path = self._extract_audio(video_path)

        try:
            # Import Whisper
            import whisper

            # Load model
            model = whisper.load_model(self.model.value)

            # Transcribe
            options = {
                "word_timestamps": word_timestamps,
                "verbose": False
            }

            if language != TranscriptionLanguage.AUTO:
                options["language"] = language.value

            result = model.transcribe(audio_path, **options)

            # Convert to our format
            transcription = self._convert_whisper_result(result)

            return transcription

        finally:
            # Clean up temporary audio file
            Path(audio_path).unlink(missing_ok=True)

    def _extract_audio(self, video_path: str) -> str:
        """Extract audio from video to temporary file.

        Args:
            video_path: Path to video file

        Returns:
            Path to temporary audio file

        Raises:
            RuntimeError: If audio extraction fails
        """
        # Create temporary audio file
        temp_audio = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_audio.close()

        # Extract audio using FFmpeg
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # PCM 16-bit
            '-ar', '16000',  # 16kHz (Whisper requirement)
            '-ac', '1',  # Mono
            '-y',  # Overwrite
            temp_audio.name
        ]

        try:
            subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            return temp_audio.name
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to extract audio: {e.stderr.decode()}")

    def _convert_whisper_result(self, result: Dict[str, Any]) -> TranscriptionResult:
        """Convert Whisper result to our format.

        Args:
            result: Whisper transcription result

        Returns:
            TranscriptionResult
        """
        segments = []
        word_count = 0

        for seg_data in result.get('segments', []):
            # Extract words if available
            words = []
            if 'words' in seg_data:
                for word_data in seg_data['words']:
                    words.append(TranscriptionWord(
                        word=word_data.get('word', ''),
                        start=word_data.get('start', 0.0),
                        end=word_data.get('end', 0.0),
                        confidence=word_data.get('probability', 1.0)
                    ))
                    word_count += 1

            # Create segment
            segment = TranscriptionSegment(
                id=seg_data.get('id', 0),
                text=seg_data.get('text', '').strip(),
                start=seg_data.get('start', 0.0),
                end=seg_data.get('end', 0.0),
                words=words,
                language=result.get('language', 'en')
            )
            segments.append(segment)

        return TranscriptionResult(
            segments=segments,
            language=result.get('language', 'en'),
            duration=segments[-1].end if segments else 0.0,
            model_used=self.model.value,
            word_count=word_count
        )

    def transcribe_audio_file(
        self,
        audio_path: str,
        language: TranscriptionLanguage = TranscriptionLanguage.AUTO,
        word_timestamps: bool = True
    ) -> TranscriptionResult:
        """Transcribe audio file directly.

        Args:
            audio_path: Path to audio file
            language: Target language
            word_timestamps: Include word-level timestamps

        Returns:
            TranscriptionResult

        Raises:
            FileNotFoundError: If audio file doesn't exist
        """
        if not Path(audio_path).exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        import whisper

        model = whisper.load_model(self.model.value)

        options = {
            "word_timestamps": word_timestamps,
            "verbose": False
        }

        if language != TranscriptionLanguage.AUTO:
            options["language"] = language.value

        result = model.transcribe(audio_path, **options)

        return self._convert_whisper_result(result)


class AutoSubtitleGenerator:
    """Generates subtitles automatically from transcription."""

    def __init__(self, max_chars_per_line: int = 42, max_lines: int = 2):
        """Initialize subtitle generator.

        Args:
            max_chars_per_line: Maximum characters per subtitle line
            max_lines: Maximum number of lines per subtitle
        """
        self.max_chars_per_line = max_chars_per_line
        self.max_lines = max_lines

    def generate_subtitles(
        self,
        transcription: TranscriptionResult,
        max_duration: float = 5.0
    ) -> List[TranscriptionSegment]:
        """Generate optimized subtitles from transcription.

        Args:
            transcription: Transcription result
            max_duration: Maximum subtitle duration in seconds

        Returns:
            List of subtitle segments
        """
        subtitles = []

        for segment in transcription.segments:
            # Split long segments if needed
            if segment.get_duration() > max_duration:
                sub_segments = self._split_segment(segment, max_duration)
                subtitles.extend(sub_segments)
            else:
                # Check if text needs wrapping
                wrapped_text = self._wrap_text(segment.text)
                segment.text = wrapped_text
                subtitles.append(segment)

        return subtitles

    def _split_segment(
        self,
        segment: TranscriptionSegment,
        max_duration: float
    ) -> List[TranscriptionSegment]:
        """Split long segment into shorter ones.

        Args:
            segment: Segment to split
            max_duration: Maximum duration

        Returns:
            List of split segments
        """
        if not segment.words:
            # Can't split without word timestamps
            return [segment]

        sub_segments = []
        current_words = []
        current_start = segment.words[0].start

        for word in segment.words:
            current_words.append(word)
            duration = word.end - current_start

            if duration >= max_duration:
                # Create sub-segment
                text = " ".join(w.word for w in current_words)
                sub_seg = TranscriptionSegment(
                    id=len(sub_segments),
                    text=self._wrap_text(text),
                    start=current_start,
                    end=word.end,
                    words=current_words.copy(),
                    language=segment.language
                )
                sub_segments.append(sub_seg)

                # Reset for next segment
                current_words = []
                if len(segment.words) > segment.words.index(word) + 1:
                    current_start = segment.words[segment.words.index(word) + 1].start

        # Add remaining words
        if current_words:
            text = " ".join(w.word for w in current_words)
            sub_seg = TranscriptionSegment(
                id=len(sub_segments),
                text=self._wrap_text(text),
                start=current_start,
                end=segment.words[-1].end,
                words=current_words,
                language=segment.language
            )
            sub_segments.append(sub_seg)

        return sub_segments

    def _wrap_text(self, text: str) -> str:
        """Wrap text to fit subtitle constraints.

        Args:
            text: Text to wrap

        Returns:
            Wrapped text
        """
        words = text.split()
        lines = []
        current_line = []
        current_length = 0

        for word in words:
            word_length = len(word) + (1 if current_line else 0)  # +1 for space

            if current_length + word_length > self.max_chars_per_line:
                # Start new line
                if current_line:
                    lines.append(" ".join(current_line))
                    current_line = [word]
                    current_length = len(word)
                else:
                    # Single word too long, add anyway
                    lines.append(word)
                    current_length = 0
            else:
                current_line.append(word)
                current_length += word_length

        # Add last line
        if current_line:
            lines.append(" ".join(current_line))

        # Limit to max lines
        if len(lines) > self.max_lines:
            lines = lines[:self.max_lines]

        return "\n".join(lines)
