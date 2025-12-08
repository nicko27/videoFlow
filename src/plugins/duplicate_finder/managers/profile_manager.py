"""
Profile Manager for Duplicate Finder plugin.

Manages configuration profiles (presets) for different use cases:
- Quick: Fast detection with lower accuracy
- Balanced: Good balance between speed and accuracy
- Accurate: Maximum accuracy with slower detection
- Reencoded: Optimized for detecting reencoded videos
- Subsequence: Focused on finding video subsequences

Users can also save and load custom profiles.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

from PyQt6.QtCore import QObject, pyqtSignal

from .unified_config_manager import UnifiedConfig, VideoHashingConfig, ComparisonConfig, AudioFirstConfig, CacheConfig, SubsequenceConfig
from src.core.logger import Logger

logger = Logger.get_logger(__name__)


@dataclass
class ConfigProfile:
    """
    A configuration profile with name, description, and settings.
    """
    name: str
    description: str
    config: UnifiedConfig
    is_builtin: bool = False

    def to_dict(self) -> Dict:
        """Convert profile to dictionary."""
        return {
            'name': self.name,
            'description': self.description,
            'config': asdict(self.config),
            'is_builtin': self.is_builtin
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'ConfigProfile':
        """Create profile from dictionary."""
        # Reconstruct UnifiedConfig from nested dict
        config_data = data['config']
        config = UnifiedConfig(
            hashing=VideoHashingConfig(**config_data['hashing']),
            comparison=ComparisonConfig(**config_data['comparison']),
            audio_first=AudioFirstConfig(**config_data['audio_first']),
            cache=CacheConfig(**config_data['cache']),
            subsequence=SubsequenceConfig(**config_data['subsequence'])
        )
        return cls(
            name=data['name'],
            description=data['description'],
            config=config,
            is_builtin=data.get('is_builtin', False)
        )


class ProfileManager(QObject):
    """
    Manages configuration profiles for the Duplicate Finder.

    Provides:
    - Built-in presets (quick, balanced, accurate, reencoded, subsequence)
    - Custom profile save/load/delete
    - Profile persistence to JSON files
    """

    # Signals
    profile_loaded = pyqtSignal(str)  # profile_name
    profile_saved = pyqtSignal(str)   # profile_name
    profile_deleted = pyqtSignal(str) # profile_name

    def __init__(self, profiles_dir: Optional[Path] = None):
        super().__init__()

        # Profiles directory
        if profiles_dir is None:
            self.profiles_dir = Path.home() / '.videoflow' / 'duplicate_finder' / 'profiles'
        else:
            self.profiles_dir = Path(profiles_dir)

        self.profiles_dir.mkdir(parents=True, exist_ok=True)

        # Storage
        self.profiles: Dict[str, ConfigProfile] = {}

        # Load built-in profiles
        self._create_builtin_profiles()

        # Load custom profiles
        self._load_custom_profiles()

        logger.info(f"ProfileManager initialized with {len(self.profiles)} profiles")

    def _create_builtin_profiles(self):
        """Create built-in configuration profiles."""

        # PROFILE: Quick - Fast detection, lower accuracy
        quick_config = UnifiedConfig(
            hashing=VideoHashingConfig(
                hash_method='aHash',  # Faster but less accurate
                hash_workers=8,
                hash_timeout=30,
                frame_sampling_rate=10  # Sample fewer frames
            ),
            comparison=ComparisonConfig(
                threshold=0.85,  # Lower threshold = more permissive
                workers=6,
                batch_size=1000,
                metadata_filter=False,  # Skip metadata filtering
                flip_detection=False    # Skip flip detection
            ),
            audio_first=AudioFirstConfig(
                enabled=False  # Disable audio-first for speed
            ),
            cache=CacheConfig(
                frame_cache_size=50,  # Smaller cache
                video_cache_size=1000,
                audio_cache_size=500,
                comparison_cache_size=5000,
                hash_cache_size=2000
            ),
            subsequence=SubsequenceConfig(
                enabled=False  # Disable subsequence detection
            )
        )
        self.profiles['quick'] = ConfigProfile(
            name='Quick',
            description='Fast detection with lower accuracy. Best for quick scans of large video collections.',
            config=quick_config,
            is_builtin=True
        )

        # PROFILE: Balanced - Good balance
        balanced_config = UnifiedConfig(
            hashing=VideoHashingConfig(
                hash_method='pHash',
                hash_workers=4,
                hash_timeout=60,
                frame_sampling_rate=5
            ),
            comparison=ComparisonConfig(
                threshold=0.90,
                workers=4,
                batch_size=500,
                metadata_filter=True,
                flip_detection=False
            ),
            audio_first=AudioFirstConfig(
                enabled=True,
                threshold=0.85,
                precision_mode='medium',
                workers=2,
                enable_no_audio_fallback=True
            ),
            cache=CacheConfig(
                frame_cache_size=100,
                video_cache_size=2000,
                audio_cache_size=1000,
                comparison_cache_size=10000,
                hash_cache_size=3000
            ),
            subsequence=SubsequenceConfig(
                enabled=False
            )
        )
        self.profiles['balanced'] = ConfigProfile(
            name='Balanced',
            description='Good balance between speed and accuracy. Recommended for most use cases.',
            config=balanced_config,
            is_builtin=True
        )

        # PROFILE: Accurate - Maximum accuracy
        accurate_config = UnifiedConfig(
            hashing=VideoHashingConfig(
                hash_method='dHash',  # More accurate
                hash_workers=2,
                hash_timeout=120,
                frame_sampling_rate=2  # Sample more frames
            ),
            comparison=ComparisonConfig(
                threshold=0.95,  # Higher threshold = more strict
                workers=2,
                batch_size=200,
                metadata_filter=True,
                flip_detection=True  # Enable flip detection
            ),
            audio_first=AudioFirstConfig(
                enabled=True,
                threshold=0.90,
                precision_mode='high',
                workers=2,
                enable_no_audio_fallback=True,
                enable_lsh_check=True,
                enable_mr_check=True
            ),
            cache=CacheConfig(
                frame_cache_size=200,
                video_cache_size=3000,
                audio_cache_size=2000,
                comparison_cache_size=20000,
                hash_cache_size=5000
            ),
            subsequence=SubsequenceConfig(
                enabled=True,
                min_length_seconds=5,
                threshold=0.92,
                max_gap_seconds=2
            )
        )
        self.profiles['accurate'] = ConfigProfile(
            name='Accurate',
            description='Maximum accuracy with slower detection. Best for critical duplicate detection.',
            config=accurate_config,
            is_builtin=True
        )

        # PROFILE: Reencoded - Detect reencoded videos
        reencoded_config = UnifiedConfig(
            hashing=VideoHashingConfig(
                hash_method='pHash',  # Good for reencoded
                hash_workers=4,
                hash_timeout=90,
                frame_sampling_rate=3
            ),
            comparison=ComparisonConfig(
                threshold=0.88,  # Lower threshold for reencoded
                workers=4,
                batch_size=300,
                metadata_filter=False,  # Metadata changes on reencoding
                flip_detection=True
            ),
            audio_first=AudioFirstConfig(
                enabled=True,
                threshold=0.82,  # Lower audio threshold
                precision_mode='high',
                workers=4,
                enable_no_audio_fallback=True,
                enable_lsh_check=True,
                enable_mr_check=True,
                enable_metadata_check=False  # Skip metadata for reencoded
            ),
            cache=CacheConfig(
                frame_cache_size=150,
                video_cache_size=2500,
                audio_cache_size=1500,
                comparison_cache_size=15000,
                hash_cache_size=4000
            ),
            subsequence=SubsequenceConfig(
                enabled=False
            )
        )
        self.profiles['reencoded'] = ConfigProfile(
            name='Reencoded',
            description='Optimized for detecting reencoded videos with different formats/quality.',
            config=reencoded_config,
            is_builtin=True
        )

        # PROFILE: Subsequence - Find video clips/excerpts
        subsequence_config = UnifiedConfig(
            hashing=VideoHashingConfig(
                hash_method='dHash',
                hash_workers=3,
                hash_timeout=90,
                frame_sampling_rate=3
            ),
            comparison=ComparisonConfig(
                threshold=0.92,
                workers=3,
                batch_size=300,
                metadata_filter=False,  # Duration will differ
                flip_detection=False
            ),
            audio_first=AudioFirstConfig(
                enabled=True,
                threshold=0.88,
                precision_mode='high',
                workers=3,
                enable_no_audio_fallback=True,
                enable_mr_check=True  # Multi-resolution helps
            ),
            cache=CacheConfig(
                frame_cache_size=150,
                video_cache_size=2500,
                audio_cache_size=1500,
                comparison_cache_size=15000,
                hash_cache_size=4000
            ),
            subsequence=SubsequenceConfig(
                enabled=True,
                min_length_seconds=3,  # Shorter clips
                threshold=0.90,
                max_gap_seconds=1
            )
        )
        self.profiles['subsequence'] = ConfigProfile(
            name='Subsequence',
            description='Focused on finding video clips, excerpts, and subsequences within larger videos.',
            config=subsequence_config,
            is_builtin=True
        )

        logger.info("Created 5 built-in profiles")

    def _load_custom_profiles(self):
        """Load custom profiles from disk."""
        try:
            for profile_file in self.profiles_dir.glob('*.json'):
                try:
                    with open(profile_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        profile = ConfigProfile.from_dict(data)
                        profile.is_builtin = False  # Ensure custom profiles are marked
                        self.profiles[profile.name.lower()] = profile
                        logger.debug(f"Loaded custom profile: {profile.name}")
                except Exception as e:
                    logger.error(f"Failed to load profile {profile_file}: {e}")

            custom_count = sum(1 for p in self.profiles.values() if not p.is_builtin)
            logger.info(f"Loaded {custom_count} custom profiles")

        except Exception as e:
            logger.error(f"Error loading custom profiles: {e}")

    def get_profile(self, name: str) -> Optional[ConfigProfile]:
        """
        Get a profile by name.

        Args:
            name: Profile name (case-insensitive)

        Returns:
            ConfigProfile or None if not found
        """
        return self.profiles.get(name.lower())

    def get_all_profiles(self) -> List[ConfigProfile]:
        """Get all available profiles."""
        return list(self.profiles.values())

    def get_builtin_profiles(self) -> List[ConfigProfile]:
        """Get only built-in profiles."""
        return [p for p in self.profiles.values() if p.is_builtin]

    def get_custom_profiles(self) -> List[ConfigProfile]:
        """Get only custom profiles."""
        return [p for p in self.profiles.values() if not p.is_builtin]

    def save_profile(self, name: str, description: str, config: UnifiedConfig) -> bool:
        """
        Save a custom profile.

        Args:
            name: Profile name
            description: Profile description
            config: Configuration to save

        Returns:
            True if saved successfully
        """
        try:
            # Create profile
            profile = ConfigProfile(
                name=name,
                description=description,
                config=config,
                is_builtin=False
            )

            # Save to disk
            profile_path = self.profiles_dir / f"{name.lower()}.json"
            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(profile.to_dict(), f, indent=2)

            # Add to memory
            self.profiles[name.lower()] = profile

            logger.info(f"Saved custom profile: {name}")
            self.profile_saved.emit(name)
            return True

        except Exception as e:
            logger.error(f"Failed to save profile {name}: {e}")
            return False

    def delete_profile(self, name: str) -> bool:
        """
        Delete a custom profile.

        Args:
            name: Profile name

        Returns:
            True if deleted successfully
        """
        profile = self.get_profile(name)

        if not profile:
            logger.warning(f"Profile not found: {name}")
            return False

        if profile.is_builtin:
            logger.warning(f"Cannot delete built-in profile: {name}")
            return False

        try:
            # Delete from disk
            profile_path = self.profiles_dir / f"{name.lower()}.json"
            if profile_path.exists():
                profile_path.unlink()

            # Remove from memory
            del self.profiles[name.lower()]

            logger.info(f"Deleted custom profile: {name}")
            self.profile_deleted.emit(name)
            return True

        except Exception as e:
            logger.error(f"Failed to delete profile {name}: {e}")
            return False

    def load_profile(self, name: str) -> Optional[UnifiedConfig]:
        """
        Load a profile and return its configuration.

        Args:
            name: Profile name

        Returns:
            UnifiedConfig or None if not found
        """
        profile = self.get_profile(name)
        if profile:
            logger.info(f"Loaded profile: {name}")
            self.profile_loaded.emit(name)
            return profile.config
        else:
            logger.warning(f"Profile not found: {name}")
            return None


# Global instance
_profile_manager_instance: Optional[ProfileManager] = None


def get_profile_manager() -> ProfileManager:
    """Get global ProfileManager instance."""
    global _profile_manager_instance
    if _profile_manager_instance is None:
        _profile_manager_instance = ProfileManager()
        logger.info("Created global ProfileManager instance")
    return _profile_manager_instance
