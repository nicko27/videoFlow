"""Audio mixing system for Video Editor.

Provides comprehensive audio control including volume, fade, ducking,
normalization, and audio effects.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple


class AudioFilter(Enum):
    """Audio filter types."""

    NONE = "none"
    NORMALIZE = "normalize"  # Normalize audio levels
    COMPRESSOR = "compressor"  # Dynamic range compression
    EQUALIZER = "equalizer"  # Frequency equalization
    HIGHPASS = "highpass"  # High-pass filter
    LOWPASS = "lowpass"  # Low-pass filter
    NOISE_REDUCTION = "noise_reduction"  # Remove background noise
    REVERB = "reverb"  # Add reverb effect
    DELAY = "delay"  # Add delay effect


class AudioFadeType(Enum):
    """Audio fade types."""

    NONE = "none"
    LINEAR = "linear"  # Linear fade
    EXPONENTIAL = "exponential"  # Exponential fade
    LOGARITHMIC = "logarithmic"  # Logarithmic fade
    S_CURVE = "s_curve"  # S-curve fade


@dataclass
class AudioFade:
    """Audio fade configuration.

    Attributes:
        fade_type: Type of fade (in/out)
        duration: Fade duration in seconds
        curve: Fade curve type
        start_volume: Starting volume (0.0-1.0)
        end_volume: Ending volume (0.0-1.0)
    """

    fade_type: str  # "in" or "out"
    duration: float = 1.0
    curve: AudioFadeType = AudioFadeType.LINEAR
    start_volume: float = 0.0
    end_volume: float = 1.0

    def get_ffmpeg_filter(self, duration: float, fps: float) -> str:
        """Generate FFmpeg audio fade filter.

        Args:
            duration: Total audio duration in seconds
            fps: Video frame rate

        Returns:
            FFmpeg afade filter string
        """
        if self.fade_type == "in":
            return f"afade=t=in:st=0:d={self.duration}:curve={self._get_curve_name()}"
        else:  # fade out
            start_time = duration - self.duration
            return f"afade=t=out:st={start_time}:d={self.duration}:curve={self._get_curve_name()}"

    def _get_curve_name(self) -> str:
        """Get FFmpeg curve name.

        Returns:
            FFmpeg curve identifier
        """
        curve_map = {
            AudioFadeType.LINEAR: "tri",
            AudioFadeType.EXPONENTIAL: "exp",
            AudioFadeType.LOGARITHMIC: "log",
            AudioFadeType.S_CURVE: "qsin"
        }
        return curve_map.get(self.curve, "tri")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            'fade_type': self.fade_type,
            'duration': self.duration,
            'curve': self.curve.value,
            'start_volume': self.start_volume,
            'end_volume': self.end_volume
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AudioFade':
        """Create from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            AudioFade instance
        """
        data = data.copy()
        if 'curve' in data:
            data['curve'] = AudioFadeType(data['curve'])
        return cls(**data)


@dataclass
class AudioDucking:
    """Audio ducking configuration.

    Automatically reduces volume of background audio when foreground audio is present.

    Attributes:
        enabled: Whether ducking is enabled
        threshold: Trigger threshold in dB
        ratio: Reduction ratio (e.g., 0.5 = 50% reduction)
        attack: Attack time in seconds
        release: Release time in seconds
        target_tracks: List of track IDs to duck
    """

    enabled: bool = False
    threshold: float = -20.0  # dB
    ratio: float = 0.3  # Reduce to 30%
    attack: float = 0.1  # 100ms
    release: float = 0.5  # 500ms
    target_tracks: List[str] = field(default_factory=list)

    def get_ffmpeg_filter(self) -> str:
        """Generate FFmpeg sidechaincompress filter.

        Returns:
            FFmpeg filter string
        """
        return (
            f"sidechaincompress="
            f"threshold={self.threshold}dB:"
            f"ratio={1.0 / self.ratio}:"
            f"attack={self.attack * 1000}:"
            f"release={self.release * 1000}"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            'enabled': self.enabled,
            'threshold': self.threshold,
            'ratio': self.ratio,
            'attack': self.attack,
            'release': self.release,
            'target_tracks': self.target_tracks
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AudioDucking':
        """Create from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            AudioDucking instance
        """
        return cls(**data)


@dataclass
class AudioEqualizer:
    """Audio equalizer configuration.

    Attributes:
        enabled: Whether EQ is enabled
        low_gain: Low frequency gain in dB (-20 to +20)
        mid_gain: Mid frequency gain in dB
        high_gain: High frequency gain in dB
        low_freq: Low frequency center (Hz)
        mid_freq: Mid frequency center (Hz)
        high_freq: High frequency center (Hz)
    """

    enabled: bool = False
    low_gain: float = 0.0  # dB
    mid_gain: float = 0.0  # dB
    high_gain: float = 0.0  # dB
    low_freq: int = 100  # Hz
    mid_freq: int = 1000  # Hz
    high_freq: int = 8000  # Hz

    def get_ffmpeg_filter(self) -> str:
        """Generate FFmpeg equalizer filter.

        Returns:
            FFmpeg filter string
        """
        filters = []

        if self.low_gain != 0:
            filters.append(f"equalizer=f={self.low_freq}:t=h:width=200:g={self.low_gain}")

        if self.mid_gain != 0:
            filters.append(f"equalizer=f={self.mid_freq}:t=h:width=200:g={self.mid_gain}")

        if self.high_gain != 0:
            filters.append(f"equalizer=f={self.high_freq}:t=h:width=200:g={self.high_gain}")

        return ",".join(filters) if filters else ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            'enabled': self.enabled,
            'low_gain': self.low_gain,
            'mid_gain': self.mid_gain,
            'high_gain': self.high_gain,
            'low_freq': self.low_freq,
            'mid_freq': self.mid_freq,
            'high_freq': self.high_freq
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AudioEqualizer':
        """Create from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            AudioEqualizer instance
        """
        return cls(**data)


@dataclass
class AudioMixingConfig:
    """Complete audio mixing configuration for a segment.

    Attributes:
        volume: Overall volume (0.0-1.0)
        muted: Whether audio is muted
        fade_in: Optional fade in configuration
        fade_out: Optional fade out configuration
        equalizer: Optional equalizer configuration
        ducking: Optional ducking configuration
        normalize: Whether to normalize audio
        filters: List of additional filters to apply
    """

    volume: float = 1.0
    muted: bool = False
    fade_in: Optional[AudioFade] = None
    fade_out: Optional[AudioFade] = None
    equalizer: Optional[AudioEqualizer] = None
    ducking: Optional[AudioDucking] = None
    normalize: bool = False
    filters: List[AudioFilter] = field(default_factory=list)

    def get_ffmpeg_filters(self, duration: float, fps: float) -> List[str]:
        """Generate all FFmpeg audio filters.

        Args:
            duration: Audio duration in seconds
            fps: Video frame rate

        Returns:
            List of FFmpeg filter strings
        """
        filters = []

        # Volume adjustment
        if not self.muted and self.volume != 1.0:
            filters.append(f"volume={self.volume}")

        # Mute
        if self.muted:
            filters.append("volume=0")

        # Fade in
        if self.fade_in:
            filters.append(self.fade_in.get_ffmpeg_filter(duration, fps))

        # Fade out
        if self.fade_out:
            filters.append(self.fade_out.get_ffmpeg_filter(duration, fps))

        # Normalize
        if self.normalize:
            filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")

        # Equalizer
        if self.equalizer and self.equalizer.enabled:
            eq_filter = self.equalizer.get_ffmpeg_filter()
            if eq_filter:
                filters.append(eq_filter)

        # Additional filters
        for audio_filter in self.filters:
            filter_str = self._get_filter_string(audio_filter)
            if filter_str:
                filters.append(filter_str)

        return filters

    def _get_filter_string(self, audio_filter: AudioFilter) -> str:
        """Get FFmpeg filter string for audio filter.

        Args:
            audio_filter: Audio filter type

        Returns:
            FFmpeg filter string
        """
        filter_map = {
            AudioFilter.NORMALIZE: "loudnorm=I=-16:TP=-1.5:LRA=11",
            AudioFilter.COMPRESSOR: "acompressor=threshold=-20dB:ratio=4:attack=5:release=50",
            AudioFilter.HIGHPASS: "highpass=f=80",
            AudioFilter.LOWPASS: "lowpass=f=10000",
            AudioFilter.NOISE_REDUCTION: "afftdn=nf=-25",
            AudioFilter.REVERB: "aecho=0.8:0.88:60:0.4",
            AudioFilter.DELAY: "aecho=0.8:0.9:1000:0.3"
        }
        return filter_map.get(audio_filter, "")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            'volume': self.volume,
            'muted': self.muted,
            'fade_in': self.fade_in.to_dict() if self.fade_in else None,
            'fade_out': self.fade_out.to_dict() if self.fade_out else None,
            'equalizer': self.equalizer.to_dict() if self.equalizer else None,
            'ducking': self.ducking.to_dict() if self.ducking else None,
            'normalize': self.normalize,
            'filters': [f.value for f in self.filters]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AudioMixingConfig':
        """Create from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            AudioMixingConfig instance
        """
        data = data.copy()

        if 'fade_in' in data and data['fade_in']:
            data['fade_in'] = AudioFade.from_dict(data['fade_in'])

        if 'fade_out' in data and data['fade_out']:
            data['fade_out'] = AudioFade.from_dict(data['fade_out'])

        if 'equalizer' in data and data['equalizer']:
            data['equalizer'] = AudioEqualizer.from_dict(data['equalizer'])

        if 'ducking' in data and data['ducking']:
            data['ducking'] = AudioDucking.from_dict(data['ducking'])

        if 'filters' in data:
            data['filters'] = [AudioFilter(f) for f in data['filters']]

        return cls(**data)


class AudioMixer:
    """Audio mixing utility class.

    Provides methods for audio mixing operations and FFmpeg filter generation.
    """

    @staticmethod
    def create_fade_in(duration: float = 1.0, curve: AudioFadeType = AudioFadeType.LINEAR) -> AudioFade:
        """Create fade in configuration.

        Args:
            duration: Fade duration in seconds
            curve: Fade curve type

        Returns:
            AudioFade configuration
        """
        return AudioFade(
            fade_type="in",
            duration=duration,
            curve=curve,
            start_volume=0.0,
            end_volume=1.0
        )

    @staticmethod
    def create_fade_out(duration: float = 1.0, curve: AudioFadeType = AudioFadeType.LINEAR) -> AudioFade:
        """Create fade out configuration.

        Args:
            duration: Fade duration in seconds
            curve: Fade curve type

        Returns:
            AudioFade configuration
        """
        return AudioFade(
            fade_type="out",
            duration=duration,
            curve=curve,
            start_volume=1.0,
            end_volume=0.0
        )

    @staticmethod
    def create_standard_music_mix() -> AudioMixingConfig:
        """Create standard music mixing preset.

        Returns:
            AudioMixingConfig for background music
        """
        return AudioMixingConfig(
            volume=0.3,  # 30% volume for background
            fade_in=AudioMixer.create_fade_in(2.0),
            fade_out=AudioMixer.create_fade_out(2.0),
            normalize=True,
            filters=[AudioFilter.COMPRESSOR]
        )

    @staticmethod
    def create_dialogue_mix() -> AudioMixingConfig:
        """Create dialogue mixing preset.

        Returns:
            AudioMixingConfig for dialogue
        """
        eq = AudioEqualizer(
            enabled=True,
            low_gain=-3.0,  # Reduce bass rumble
            mid_gain=2.0,  # Boost voice clarity
            high_gain=1.0,  # Slight high-end boost
            mid_freq=2000  # Voice frequency
        )

        return AudioMixingConfig(
            volume=1.0,
            normalize=True,
            equalizer=eq,
            filters=[AudioFilter.NOISE_REDUCTION, AudioFilter.COMPRESSOR]
        )

    @staticmethod
    def create_sfx_mix() -> AudioMixingConfig:
        """Create sound effects mixing preset.

        Returns:
            AudioMixingConfig for sound effects
        """
        return AudioMixingConfig(
            volume=0.7,  # 70% volume
            fade_in=AudioMixer.create_fade_in(0.1),  # Quick fade
            normalize=False  # Keep dynamic range
        )

    @staticmethod
    def mix_multiple_tracks(
        configs: List[Tuple[str, AudioMixingConfig]],
        duration: float,
        fps: float
    ) -> str:
        """Generate FFmpeg filter complex for multiple audio tracks.

        Args:
            configs: List of (track_id, AudioMixingConfig) tuples
            duration: Total duration in seconds
            fps: Video frame rate

        Returns:
            FFmpeg filter_complex string
        """
        filter_chains = []

        for i, (track_id, config) in enumerate(configs):
            # Generate filters for this track
            filters = config.get_ffmpeg_filters(duration, fps)

            if filters:
                # Create filter chain for this input
                chain = f"[{i}:a]" + ",".join(filters) + f"[a{i}]"
                filter_chains.append(chain)
            else:
                # No filters, just label the input
                filter_chains.append(f"[{i}:a]acopy[a{i}]")

        # Mix all audio streams
        if len(configs) > 1:
            mix_inputs = "".join([f"[a{i}]" for i in range(len(configs))])
            filter_chains.append(f"{mix_inputs}amix=inputs={len(configs)}:duration=longest[aout]")

        return ";".join(filter_chains)
