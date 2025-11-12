"""Pattern parser for Batch Renamer plugin."""

import re
from pathlib import Path
from datetime import datetime


class PatternParser:
    """
    Parse and apply naming patterns to filenames.

    Supports variables like {name}, {date}, {resolution}, {#}, etc.
    """

    def __init__(self):
        """Initialize pattern parser."""
        self.variables = {
            '{name}': self._get_name,
            '{ext}': self._get_extension,
            '{date}': self._get_date,
            '{time}': self._get_time,
            '{resolution}': self._get_resolution,
            '{width}': self._get_width,
            '{height}': self._get_height,
            '{codec}': self._get_codec,
            '{duration}': self._get_duration,
            '{size}': self._get_size,
            '{fps}': self._get_fps,
            '{#}': self._get_index,
            '{##}': self._get_index_padded_2,
            '{###}': self._get_index_padded_3,
            '{####}': self._get_index_padded_4,
        }

    def parse(self, pattern, file_path, metadata, index=0):
        """
        Apply pattern to generate new filename.

        Args:
            pattern (str): Naming pattern with variables.
            file_path (str): Original file path.
            metadata (dict): Video metadata.
            index (int): File index in batch.

        Returns:
            str: New filename.
        """
        result = pattern

        # Replace all variables
        for var, func in self.variables.items():
            if var in result:
                value = func(file_path, metadata, index)
                result = result.replace(var, str(value))

        return result

    def get_available_variables(self):
        """
        Get list of available variables with descriptions.

        Returns:
            list: List of (variable, description) tuples.
        """
        return [
            ('{name}', 'Original filename without extension'),
            ('{ext}', 'File extension'),
            ('{date}', 'File date (YYYY-MM-DD)'),
            ('{time}', 'File time (HH-MM-SS)'),
            ('{resolution}', 'Video resolution (e.g., 1920x1080)'),
            ('{width}', 'Video width in pixels'),
            ('{height}', 'Video height in pixels'),
            ('{codec}', 'Video codec'),
            ('{duration}', 'Duration in seconds'),
            ('{size}', 'File size in MB'),
            ('{fps}', 'Frames per second'),
            ('{#}', 'Index number (1, 2, 3...)'),
            ('{##}', 'Index with 2 digits (01, 02, 03...)'),
            ('{###}', 'Index with 3 digits (001, 002, 003...)'),
            ('{####}', 'Index with 4 digits (0001, 0002, 0003...)'),
        ]

    # Variable extraction methods

    def _get_name(self, file_path, metadata, index):
        """Get original filename without extension."""
        return Path(file_path).stem

    def _get_extension(self, file_path, metadata, index):
        """Get file extension."""
        return Path(file_path).suffix.lstrip('.')

    def _get_date(self, file_path, metadata, index):
        """Get file modification date."""
        if metadata and 'date' in metadata:
            return metadata['date']

        try:
            mtime = Path(file_path).stat().st_mtime
            return datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
        except Exception:
            return 'unknown'

    def _get_time(self, file_path, metadata, index):
        """Get file modification time."""
        if metadata and 'time' in metadata:
            return metadata['time']

        try:
            mtime = Path(file_path).stat().st_mtime
            return datetime.fromtimestamp(mtime).strftime('%H-%M-%S')
        except Exception:
            return 'unknown'

    def _get_resolution(self, file_path, metadata, index):
        """Get video resolution."""
        if metadata and 'resolution' in metadata:
            return metadata['resolution']
        return 'unknown'

    def _get_width(self, file_path, metadata, index):
        """Get video width."""
        if metadata and 'width' in metadata:
            return metadata['width']
        return 'unknown'

    def _get_height(self, file_path, metadata, index):
        """Get video height."""
        if metadata and 'height' in metadata:
            return metadata['height']
        return 'unknown'

    def _get_codec(self, file_path, metadata, index):
        """Get video codec."""
        if metadata and 'codec' in metadata:
            return metadata['codec']
        return 'unknown'

    def _get_duration(self, file_path, metadata, index):
        """Get video duration in seconds."""
        if metadata and 'duration' in metadata:
            return int(metadata['duration'])
        return 'unknown'

    def _get_size(self, file_path, metadata, index):
        """Get file size in MB."""
        if metadata and 'size' in metadata:
            return metadata['size']

        try:
            size_mb = Path(file_path).stat().st_size / (1024 * 1024)
            return f"{size_mb:.1f}MB"
        except Exception:
            return 'unknown'

    def _get_fps(self, file_path, metadata, index):
        """Get frames per second."""
        if metadata and 'fps' in metadata:
            return int(metadata['fps'])
        return 'unknown'

    def _get_index(self, file_path, metadata, index):
        """Get index number (1-based)."""
        return index + 1

    def _get_index_padded_2(self, file_path, metadata, index):
        """Get index with 2-digit padding."""
        return f"{index + 1:02d}"

    def _get_index_padded_3(self, file_path, metadata, index):
        """Get index with 3-digit padding."""
        return f"{index + 1:03d}"

    def _get_index_padded_4(self, file_path, metadata, index):
        """Get index with 4-digit padding."""
        return f"{index + 1:04d}"


class FindReplaceProcessor:
    """Process find/replace operations on filenames."""

    @staticmethod
    def find_replace(text, find_pattern, replace_with, use_regex=False, case_sensitive=True):
        """
        Find and replace in text.

        Args:
            text (str): Input text.
            find_pattern (str): Pattern to find.
            replace_with (str): Replacement text.
            use_regex (bool): Use regex matching.
            case_sensitive (bool): Case-sensitive matching.

        Returns:
            str: Processed text.
        """
        if not find_pattern:
            return text

        if use_regex:
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                return re.sub(find_pattern, replace_with, text, flags=flags)
            except re.error:
                # Invalid regex, return original
                return text
        else:
            if case_sensitive:
                return text.replace(find_pattern, replace_with)
            else:
                # Case-insensitive replace
                pattern = re.compile(re.escape(find_pattern), re.IGNORECASE)
                return pattern.sub(replace_with, text)

    @staticmethod
    def change_case(text, case_mode):
        """
        Change text case.

        Args:
            text (str): Input text.
            case_mode (str): One of: 'lower', 'upper', 'title', 'sentence', 'none'.

        Returns:
            str: Processed text.
        """
        if case_mode == 'lower':
            return text.lower()
        elif case_mode == 'upper':
            return text.upper()
        elif case_mode == 'title':
            return text.title()
        elif case_mode == 'sentence':
            return text.capitalize()
        else:
            return text
