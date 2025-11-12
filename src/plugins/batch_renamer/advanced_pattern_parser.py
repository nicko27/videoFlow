"""Advanced Pattern Parser with conditions, functions, and transformations."""

import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Callable, List, Tuple
from src.core.logger import Logger

logger = Logger.get_logger('BatchRenamer.AdvancedPatternParser')


class AdvancedPatternParser:
    """
    Advanced pattern parser with support for:
    - Conditional logic: {if:fps>30}60fps{endif}
    - Regex capture groups: {regex:pattern:group_num}
    - Transformation functions: {name:upper}, {name:trim:10}
    - Date formatting: {date:format:DD-MM-YYYY}
    - Custom functions
    """

    def __init__(self):
        """Initialize advanced pattern parser."""
        # Base variable functions
        self.variables = {
            'name': self._get_name,
            'ext': self._get_extension,
            'date': self._get_date,
            'time': self._get_time,
            'resolution': self._get_resolution,
            'width': self._get_width,
            'height': self._get_height,
            'codec': self._get_codec,
            'duration': self._get_duration,
            'size': self._get_size,
            'fps': self._get_fps,
            '#': self._get_index,
            '##': self._get_index_padded_2,
            '###': self._get_index_padded_3,
            '####': self._get_index_padded_4,
        }

        # Transformation functions
        self.transformations = {
            'upper': lambda x: str(x).upper(),
            'lower': lambda x: str(x).lower(),
            'title': lambda x: str(x).title(),
            'capitalize': lambda x: str(x).capitalize(),
            'trim': self._trim_text,
            'pad': self._pad_text,
            'replace': self._replace_text,
            'substr': self._substring,
        }

        # Comparison operators for conditions
        self.operators = {
            '>': lambda a, b: float(a) > float(b),
            '<': lambda a, b: float(a) < float(b),
            '>=': lambda a, b: float(a) >= float(b),
            '<=': lambda a, b: float(a) <= float(b),
            '==': lambda a, b: str(a) == str(b),
            '!=': lambda a, b: str(a) != str(b),
            'contains': lambda a, b: str(b) in str(a),
        }

    def parse(self, pattern: str, file_path: str, metadata: Dict, index: int = 0) -> str:
        """
        Parse advanced pattern with support for conditions, functions, and regex.

        Args:
            pattern: Pattern string with advanced features
            file_path: Original file path
            metadata: Video metadata
            index: File index in batch

        Returns:
            Parsed filename (without extension)

        Examples:
            "{name:upper}" → "MOVIE_NAME"
            "{if:fps>30}60fps{endif}" → "60fps" (if fps > 30)
            "{date:format:DD-MM-YYYY}" → "09-11-2024"
            "{name:trim:20}" → First 20 characters
        """
        result = pattern
        context = {'file_path': file_path, 'metadata': metadata, 'index': index}

        # Step 1: Process conditionals first
        result = self._process_conditionals(result, context)

        # Step 2: Process regex capture groups
        result = self._process_regex_captures(result, file_path)

        # Step 3: Process variables with transformations
        result = self._process_variables(result, context)

        # Step 4: Clean up multiple spaces
        result = re.sub(r'\s+', ' ', result).strip()

        return result

    def _process_conditionals(self, pattern: str, context: Dict) -> str:
        """
        Process conditional statements in pattern.

        Syntax: {if:variable operator value}text{endif}
        Examples:
            {if:fps>30}HFR{endif}
            {if:width>=1920}HD{endif}
            {if:codec==h265}HEVC{endif}
        """
        conditional_pattern = r'\{if:([\w]+)((?:>|<|>=|<=|==|!=|contains))([^\}]+)\}(.*?)\{endif\}'

        def replace_conditional(match):
            var_name = match.group(1)
            operator = match.group(2)
            value = match.group(3).strip()
            content = match.group(4)

            # Get variable value
            var_value = self._get_variable_value(var_name, context)
            if var_value is None or var_value == 'unknown':
                return ''

            # Evaluate condition
            try:
                if operator in self.operators:
                    if self.operators[operator](var_value, value):
                        return content
            except (ValueError, TypeError) as e:
                logger.warning(f"Conditional evaluation error: {e}")

            return ''

        # Process all conditionals
        while '{if:' in pattern:
            old_pattern = pattern
            pattern = re.sub(conditional_pattern, replace_conditional, pattern)
            if pattern == old_pattern:  # Prevent infinite loop
                break

        return pattern

    def _process_regex_captures(self, pattern: str, file_path: str) -> str:
        """
        Process regex capture groups.

        Syntax: {regex:pattern:group_num}
        Example: {regex:Season (\d+):1} → Captures season number
        """
        regex_pattern = r'\{regex:([^:]+):(\d+)\}'

        def replace_regex(match):
            regex = match.group(1)
            group_num = int(match.group(2))

            try:
                original_name = Path(file_path).stem
                regex_match = re.search(regex, original_name, re.IGNORECASE)
                if regex_match and len(regex_match.groups()) >= group_num:
                    return regex_match.group(group_num)
            except re.error as e:
                logger.error(f"Regex error: {e}")

            return ''

        return re.sub(regex_pattern, replace_regex, pattern)

    def _process_variables(self, pattern: str, context: Dict) -> str:
        """
        Process variables with optional transformations.

        Syntax: {variable:function:arg1:arg2}
        Examples:
            {name:upper}
            {name:trim:20}
            {date:format:DD-MM-YYYY}
            {name:replace:old:new}
        """
        variable_pattern = r'\{([\w#]+)(?::([^\}]+))?\}'

        def replace_variable(match):
            var_name = match.group(1)
            transformations = match.group(2)

            # Get base value
            value = self._get_variable_value(var_name, context)
            if value is None:
                return 'unknown'

            # Apply transformations if present
            if transformations:
                value = self._apply_transformations(str(value), transformations, context)

            return str(value)

        return re.sub(variable_pattern, replace_variable, pattern)

    def _get_variable_value(self, var_name: str, context: Dict) -> Any:
        """Get value for a variable."""
        if var_name in self.variables:
            return self.variables[var_name](
                context['file_path'],
                context['metadata'],
                context['index']
            )
        return None

    def _apply_transformations(self, value: str, transformations: str, context: Dict) -> str:
        """
        Apply chain of transformations to value.

        Args:
            value: Input value
            transformations: Colon-separated transformation chain
            context: Pattern context

        Returns:
            Transformed value
        """
        parts = transformations.split(':')
        result = value

        i = 0
        while i < len(parts):
            func_name = parts[i]

            if func_name == 'format' and i + 1 < len(parts):
                # Special handling for date/time formatting
                format_str = parts[i + 1]
                result = self._format_datetime(result, format_str, context)
                i += 2
            elif func_name == 'trim' and i + 1 < len(parts):
                length = int(parts[i + 1])
                result = self._trim_text(result, length)
                i += 2
            elif func_name == 'pad' and i + 1 < len(parts):
                length = int(parts[i + 1])
                pad_char = parts[i + 2] if i + 2 < len(parts) else '0'
                result = self._pad_text(result, length, pad_char)
                i += 3 if i + 2 < len(parts) else 2
            elif func_name == 'replace' and i + 2 < len(parts):
                old_text = parts[i + 1]
                new_text = parts[i + 2]
                result = self._replace_text(result, old_text, new_text)
                i += 3
            elif func_name == 'substr' and i + 2 < len(parts):
                start = int(parts[i + 1])
                end = int(parts[i + 2])
                result = self._substring(result, start, end)
                i += 3
            elif func_name in self.transformations:
                result = self.transformations[func_name](result)
                i += 1
            else:
                i += 1

        return result

    def _format_datetime(self, value: str, format_str: str, context: Dict) -> str:
        """
        Format date/time value.

        Supports custom formats:
        - DD-MM-YYYY → 09-11-2024
        - YYYYMMDD → 20241109
        - DD/MM/YY → 09/11/24
        """
        try:
            metadata = context.get('metadata', {})
            file_path = context.get('file_path', '')

            # Get datetime object
            if 'date' in metadata:
                # Parse existing date string
                date_str = metadata['date']  # Format: YYYY-MM-DD
                dt = datetime.strptime(date_str, '%Y-%m-%d')
            else:
                # Use file modification time
                mtime = Path(file_path).stat().st_mtime
                dt = datetime.fromtimestamp(mtime)

            # Convert custom format to strftime format
            strftime_format = format_str
            strftime_format = strftime_format.replace('DD', '%d')
            strftime_format = strftime_format.replace('MM', '%m')
            strftime_format = strftime_format.replace('YYYY', '%Y')
            strftime_format = strftime_format.replace('YY', '%y')
            strftime_format = strftime_format.replace('HH', '%H')
            strftime_format = strftime_format.replace('mm', '%M')
            strftime_format = strftime_format.replace('SS', '%S')

            return dt.strftime(strftime_format)
        except Exception as e:
            logger.error(f"Date formatting error: {e}")
            return value

    def _trim_text(self, text: str, length: int = 10) -> str:
        """Trim text to specified length."""
        return text[:length]

    def _pad_text(self, text: str, length: int = 10, pad_char: str = '0') -> str:
        """Pad text to specified length."""
        return text.rjust(length, pad_char)

    def _replace_text(self, text: str, old: str, new: str) -> str:
        """Replace text."""
        return text.replace(old, new)

    def _substring(self, text: str, start: int, end: int) -> str:
        """Extract substring."""
        return text[start:end]

    # Base variable extraction methods (same as PatternParser)

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

    def get_help_text(self) -> List[Tuple[str, str]]:
        """
        Get help text for advanced pattern features.

        Returns:
            List of (example, description) tuples
        """
        return [
            ("Basic Variables", ""),
            ("{name}", "Original filename"),
            ("{date}", "File date (YYYY-MM-DD)"),
            ("{resolution}", "Video resolution"),
            ("{fps}", "Frames per second"),
            ("", ""),
            ("Transformations", ""),
            ("{name:upper}", "Uppercase name"),
            ("{name:lower}", "Lowercase name"),
            ("{name:title}", "Title Case"),
            ("{name:trim:20}", "First 20 characters"),
            ("{date:format:DD-MM-YYYY}", "Custom date format"),
            ("{name:replace:old:new}", "Replace text"),
            ("", ""),
            ("Conditionals", ""),
            ("{if:fps>30}HFR{endif}", "Show HFR if fps > 30"),
            ("{if:width>=1920}HD{endif}", "Show HD if width >= 1920"),
            ("{if:codec==h265}HEVC{endif}", "Show HEVC if codec is h265"),
            ("", ""),
            ("Regex Capture", ""),
            ("{regex:Season (\\d+):1}", "Extract season number"),
            ("{regex:\\[(.*?)\\]:1}", "Extract bracketed content"),
        ]
