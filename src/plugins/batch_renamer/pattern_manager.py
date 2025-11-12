"""Pattern Manager for intelligent pattern detection and management."""

import os
import re
import yaml
from pathlib import Path
from typing import List, Dict, Set, Tuple
from collections import Counter
from src.core.logger import Logger

logger = Logger.get_logger('BatchRenamer.PatternManager')


class PatternPosition:
    """Pattern position in filename."""
    ANYWHERE = "anywhere"
    START = "start"
    END = "end"


class PatternManager:
    """
    Manages removal patterns with intelligent detection.

    Features:
    - Load/save patterns from YAML
    - Detect common patterns in filenames
    - Support pattern position (start/end/anywhere)
    - Suggest patterns based on frequency
    """

    def __init__(self, config_path: str = None):
        """
        Initialize pattern manager.

        Args:
            config_path: Path to YAML config file. If None, uses default location.
        """
        if config_path is None:
            # Default location in user's config directory
            config_dir = Path.home() / '.videoflow' / 'batch_renamer'
            config_dir.mkdir(parents=True, exist_ok=True)
            config_path = config_dir / 'patterns.yaml'

        self.config_path = Path(config_path)
        self.patterns: List[Dict] = []

        # Load existing patterns or create default
        if self.config_path.exists():
            self.load_patterns()
        else:
            self._create_default_patterns()
            self.save_patterns()

    def _create_default_patterns(self):
        """Create default common patterns."""
        self.patterns = [
            # Video codecs
            {'pattern': 'x264', 'position': PatternPosition.ANYWHERE, 'enabled': True, 'description': 'H.264 codec tag'},
            {'pattern': 'x265', 'position': PatternPosition.ANYWHERE, 'enabled': True, 'description': 'H.265 codec tag'},
            {'pattern': 'h264', 'position': PatternPosition.ANYWHERE, 'enabled': True, 'description': 'H.264 codec tag'},
            {'pattern': 'h265', 'position': PatternPosition.ANYWHERE, 'enabled': True, 'description': 'H.265 codec tag'},
            {'pattern': 'hevc', 'position': PatternPosition.ANYWHERE, 'enabled': True, 'description': 'HEVC codec'},
            {'pattern': 'avc', 'position': PatternPosition.ANYWHERE, 'enabled': True, 'description': 'AVC codec'},
            {'pattern': 'xvid', 'position': PatternPosition.ANYWHERE, 'enabled': True, 'description': 'XviD codec'},
            {'pattern': 'divx', 'position': PatternPosition.ANYWHERE, 'enabled': True, 'description': 'DivX codec'},

            # Quality/Resolution tags
            {'pattern': '1080p', 'position': PatternPosition.ANYWHERE, 'enabled': True, 'description': '1080p resolution'},
            {'pattern': '720p', 'position': PatternPosition.ANYWHERE, 'enabled': True, 'description': '720p resolution'},
            {'pattern': '480p', 'position': PatternPosition.ANYWHERE, 'enabled': True, 'description': '480p resolution'},
            {'pattern': '4k', 'position': PatternPosition.ANYWHERE, 'enabled': True, 'description': '4K resolution'},
            {'pattern': 'uhd', 'position': PatternPosition.ANYWHERE, 'enabled': True, 'description': 'UHD resolution'},
            {'pattern': 'hd', 'position': PatternPosition.ANYWHERE, 'enabled': True, 'description': 'HD tag'},
            {'pattern': 'bluray', 'position': PatternPosition.ANYWHERE, 'enabled': True, 'description': 'BluRay source'},
            {'pattern': 'brrip', 'position': PatternPosition.ANYWHERE, 'enabled': True, 'description': 'BluRay Rip'},
            {'pattern': 'webrip', 'position': PatternPosition.ANYWHERE, 'enabled': True, 'description': 'Web Rip'},
            {'pattern': 'web-dl', 'position': PatternPosition.ANYWHERE, 'enabled': True, 'description': 'Web Download'},
            {'pattern': 'dvdrip', 'position': PatternPosition.ANYWHERE, 'enabled': True, 'description': 'DVD Rip'},

            # Audio tags
            {'pattern': 'aac', 'position': PatternPosition.ANYWHERE, 'enabled': True, 'description': 'AAC audio'},
            {'pattern': 'ac3', 'position': PatternPosition.ANYWHERE, 'enabled': True, 'description': 'AC3 audio'},
            {'pattern': 'dts', 'position': PatternPosition.ANYWHERE, 'enabled': True, 'description': 'DTS audio'},
            {'pattern': 'dd5.1', 'position': PatternPosition.ANYWHERE, 'enabled': True, 'description': 'Dolby Digital 5.1'},
            {'pattern': 'atmos', 'position': PatternPosition.ANYWHERE, 'enabled': True, 'description': 'Dolby Atmos'},

            # Release groups/tags
            {'pattern': 'yify', 'position': PatternPosition.ANYWHERE, 'enabled': True, 'description': 'YIFY release group'},
            {'pattern': 'rarbg', 'position': PatternPosition.ANYWHERE, 'enabled': True, 'description': 'RARBG tag'},
            {'pattern': 'etrg', 'position': PatternPosition.ANYWHERE, 'enabled': True, 'description': 'ETRG release group'},

            # Common separators/patterns at end
            {'pattern': r'\[.*?\]', 'position': PatternPosition.END, 'enabled': True, 'description': 'Brackets at end', 'is_regex': True},
            {'pattern': r'\(.*?\)', 'position': PatternPosition.END, 'enabled': True, 'description': 'Parentheses at end', 'is_regex': True},
        ]

    def load_patterns(self):
        """Load patterns from YAML file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                self.patterns = data.get('patterns', [])
                logger.info(f"Loaded {len(self.patterns)} patterns from {self.config_path}")
        except Exception as e:
            logger.error(f"Error loading patterns: {e}")
            self._create_default_patterns()

    def save_patterns(self):
        """Save patterns to YAML file."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump({'patterns': self.patterns}, f, default_flow_style=False, allow_unicode=True)
                logger.info(f"Saved {len(self.patterns)} patterns to {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving patterns: {e}")

    def add_pattern(self, pattern: str, position: str = PatternPosition.ANYWHERE,
                   description: str = "", is_regex: bool = False):
        """
        Add a new pattern.

        Args:
            pattern: Pattern string or regex
            position: Where the pattern can be found (anywhere/start/end)
            description: Human-readable description
            is_regex: True if pattern is a regex
        """
        # Check if pattern already exists
        for existing in self.patterns:
            if existing['pattern'].lower() == pattern.lower():
                logger.warning(f"Pattern '{pattern}' already exists")
                return False

        new_pattern = {
            'pattern': pattern,
            'position': position,
            'enabled': True,
            'description': description or f"Custom pattern: {pattern}"
        }

        if is_regex:
            new_pattern['is_regex'] = True

        self.patterns.append(new_pattern)
        self.save_patterns()
        logger.info(f"Added pattern: {pattern} ({position})")
        return True

    def remove_pattern(self, pattern: str):
        """Remove a pattern by its string value."""
        original_count = len(self.patterns)
        self.patterns = [p for p in self.patterns if p['pattern'] != pattern]

        if len(self.patterns) < original_count:
            self.save_patterns()
            logger.info(f"Removed pattern: {pattern}")
            return True
        return False

    def toggle_pattern(self, pattern: str):
        """Enable/disable a pattern."""
        for p in self.patterns:
            if p['pattern'] == pattern:
                p['enabled'] = not p.get('enabled', True)
                self.save_patterns()
                logger.info(f"Toggled pattern: {pattern} -> {p['enabled']}")
                return True
        return False

    def get_enabled_patterns(self) -> List[Dict]:
        """Get only enabled patterns."""
        return [p for p in self.patterns if p.get('enabled', True)]

    def apply_patterns(self, filename: str) -> str:
        """
        Apply all enabled patterns to remove them from filename.

        Args:
            filename: Original filename (without extension)

        Returns:
            Cleaned filename
        """
        result = filename

        for pattern_dict in self.get_enabled_patterns():
            pattern = pattern_dict['pattern']
            position = pattern_dict.get('position', PatternPosition.ANYWHERE)
            is_regex = pattern_dict.get('is_regex', False)

            if is_regex:
                # Use regex pattern
                try:
                    if position == PatternPosition.START:
                        result = re.sub(f'^{pattern}', '', result, flags=re.IGNORECASE).strip()
                    elif position == PatternPosition.END:
                        result = re.sub(f'{pattern}$', '', result, flags=re.IGNORECASE).strip()
                    else:  # ANYWHERE
                        result = re.sub(pattern, '', result, flags=re.IGNORECASE).strip()
                except Exception as e:
                    logger.error(f"Error applying regex pattern '{pattern}': {e}")
            else:
                # Simple string matching (case-insensitive)
                pattern_lower = pattern.lower()

                if position == PatternPosition.START:
                    if result.lower().startswith(pattern_lower):
                        result = result[len(pattern):].strip()
                elif position == PatternPosition.END:
                    if result.lower().endswith(pattern_lower):
                        result = result[:-len(pattern)].strip()
                else:  # ANYWHERE
                    # Replace all occurrences (case-insensitive)
                    result = re.sub(re.escape(pattern), '', result, flags=re.IGNORECASE).strip()

            # Clean up multiple spaces and common separators
            result = re.sub(r'[\s._-]+', ' ', result).strip(' ._-')

        return result

    def detect_patterns(self, filenames: List[str], min_frequency: int = 3,
                       min_length: int = 3) -> List[Tuple[str, int, str]]:
        """
        Intelligently detect common patterns in filenames with advanced detection.

        Args:
            filenames: List of filenames to analyze
            min_frequency: Minimum number of occurrences to consider
            min_length: Minimum pattern length

        Returns:
            List of (pattern, count, suggested_position) tuples, sorted by frequency
        """
        if not filenames:
            return []

        # Extract basenames without extensions
        basenames = [Path(f).stem for f in filenames]

        # Collect all potential patterns
        pattern_candidates = Counter()
        position_suggestions = {}
        pattern_examples = {}  # Store examples for each pattern

        # 1. Word-based patterns (split by common separators)
        for basename in basenames:
            # Split by common separators
            words = re.split(r'[\s._\-\[\]()]+', basename.lower())

            for word in words:
                if len(word) >= min_length and word.strip():
                    # Check if it looks like a codec/tag (alphanumeric with possible dots)
                    if re.match(r'^[a-z0-9.]+$', word):
                        pattern_candidates[word] += 1

                        # Store example
                        if word not in pattern_examples:
                            pattern_examples[word] = basename

                        # Suggest position based on where it appears
                        if not position_suggestions.get(word):
                            if basename.lower().startswith(word):
                                position_suggestions[word] = PatternPosition.START
                            elif basename.lower().endswith(word):
                                position_suggestions[word] = PatternPosition.END
                            else:
                                position_suggestions[word] = PatternPosition.ANYWHERE

        # 2. Advanced pattern detection
        advanced_patterns = [
            # Years (1900-2099)
            (r'\b(19|20)\d{2}\b', 'year'),
            # Resolutions
            (r'\b(480|720|1080|2160)[pi]\b', 'resolution'),
            (r'\b(4k|8k|uhd|fhd|hd|sd)\b', 'quality'),
            # Codecs
            (r'\b(h\.?264|h\.?265|x\.?264|x\.?265|hevc|avc|xvid|divx|mpeg[24]?)\b', 'codec'),
            # Audio
            (r'\b(aac|ac3|dts|dd[57]\.1|atmos|truehd|flac|mp3)\b', 'audio'),
            # Sources
            (r'\b(bluray|brrip|bdrip|webrip|web-?dl|hdtv|dvdrip|dvd|cam|ts|tc)\b', 'source'),
            # Languages
            (r'\b(multi|vostfr|french|english|truefrench|vff|vfq)\b', 'language'),
            # Editions
            (r'\b(extended|unrated|directors?\.cut|remastered|theatrical)\b', 'edition'),
            # Release groups (uppercase words at end)
            (r'[-.]([A-Z]{3,})\b', 'group'),
            # Episode patterns
            (r'\b[sS]\d{1,2}[eE]\d{1,2}\b', 'episode'),
            # Brackets/Parentheses content
            (r'\[([^\]]+)\]', 'bracketed'),
            (r'\(([^\)]+)\)', 'parenthesized'),
        ]

        for basename in basenames:
            for pattern_regex, category in advanced_patterns:
                matches = re.finditer(pattern_regex, basename, re.IGNORECASE)
                for match in matches:
                    matched_text = match.group(1) if match.lastindex else match.group(0)
                    matched_text_lower = matched_text.lower().strip()

                    if len(matched_text_lower) >= min_length:
                        pattern_candidates[matched_text_lower] += 1

                        if matched_text_lower not in pattern_examples:
                            pattern_examples[matched_text_lower] = basename

                        # Determine position
                        if not position_suggestions.get(matched_text_lower):
                            start_pos = basename.lower().find(matched_text_lower)
                            end_pos = start_pos + len(matched_text_lower)

                            if start_pos < len(basename) * 0.2:  # First 20%
                                position_suggestions[matched_text_lower] = PatternPosition.START
                            elif end_pos > len(basename) * 0.8:  # Last 20%
                                position_suggestions[matched_text_lower] = PatternPosition.END
                            else:
                                position_suggestions[matched_text_lower] = PatternPosition.ANYWHERE

        # 3. Detect common separators that should be cleaned
        separator_patterns = {
            r'\.+': 'dots',
            r'_+': 'underscores',
            r'-+': 'dashes',
        }

        # Filter by frequency and exclude already existing patterns
        existing_patterns_lower = {p['pattern'].lower() for p in self.patterns}

        detected = []
        for pattern, count in pattern_candidates.most_common():
            if count >= min_frequency and pattern not in existing_patterns_lower:
                position = position_suggestions.get(pattern, PatternPosition.ANYWHERE)
                example = pattern_examples.get(pattern, '')
                detected.append((pattern, count, position, example))

        logger.info(f"Detected {len(detected)} new patterns from {len(filenames)} files")
        return detected

    def get_pattern_stats(self, filenames: List[str]) -> Dict:
        """
        Get statistics about how many files would be affected by each pattern.

        Args:
            filenames: List of filenames to analyze

        Returns:
            Dict mapping pattern -> count of affected files
        """
        stats = {}
        basenames = [Path(f).stem for f in filenames]

        for pattern_dict in self.get_enabled_patterns():
            pattern = pattern_dict['pattern']
            is_regex = pattern_dict.get('is_regex', False)
            count = 0

            for basename in basenames:
                if is_regex:
                    if re.search(pattern, basename, re.IGNORECASE):
                        count += 1
                else:
                    if pattern.lower() in basename.lower():
                        count += 1

            if count > 0:
                stats[pattern] = count

        return stats
