"""Rename engine for Batch Renamer plugin."""

import os
from pathlib import Path
from src.core.logger import Logger

logger = Logger.get_logger('BatchRenamer.Renamer')


class RenameEngine:
    """
    Handle file rename operations with undo support.

    Tracks all rename operations to allow undoing changes.
    """

    def __init__(self):
        """Initialize rename engine."""
        self.history = []

    def rename_file(self, old_path, new_filename):
        """
        Rename a single file.

        Args:
            old_path (str): Original file path.
            new_filename (str): New filename (without path).

        Returns:
            tuple: (success: bool, new_path: str, error_msg: str or None)
        """
        try:
            old_path_obj = Path(old_path)
            new_path = old_path_obj.parent / new_filename

            # Check if file already exists
            if new_path.exists() and new_path != old_path_obj:
                return False, None, f"File already exists: {new_filename}"

            # Check if new filename is valid
            if not self._is_valid_filename(new_filename):
                return False, None, f"Invalid filename: {new_filename}"

            # Perform rename
            old_path_obj.rename(new_path)

            # Track for undo
            self.history.append((str(new_path), str(old_path)))

            logger.info(f"Renamed: {old_path_obj.name} → {new_filename}")
            return True, str(new_path), None

        except Exception as e:
            logger.error(f"Error renaming {old_path}: {e}")
            return False, None, str(e)

    def rename_batch(self, rename_list):
        """
        Rename multiple files.

        Args:
            rename_list (list): List of (old_path, new_filename) tuples.

        Returns:
            tuple: (successful_count, failed_list)
        """
        successful = 0
        failed = []

        # Detect duplicate target filenames in batch
        target_names = {}
        for old_path, new_filename in rename_list:
            old_path_obj = Path(old_path)
            new_path = old_path_obj.parent / new_filename
            new_path_str = str(new_path).lower()  # Case-insensitive check

            if new_path_str in target_names:
                failed.append((old_path, f"Duplicate target name in batch: {new_filename}"))
            else:
                target_names[new_path_str] = old_path

        # Filter out files that already failed
        failed_paths = {old_path for old_path, _ in failed}
        rename_list = [(old, new) for old, new in rename_list if old not in failed_paths]

        # Use two-phase rename to avoid race conditions
        # Phase 1: Rename to temporary names
        temp_renames = []
        for old_path, new_filename in rename_list:
            old_path_obj = Path(old_path)
            temp_name = f".tmp_{os.getpid()}_{len(temp_renames)}_{old_path_obj.name}"
            temp_path = old_path_obj.parent / temp_name

            try:
                old_path_obj.rename(temp_path)
                temp_renames.append((str(temp_path), new_filename, str(old_path)))
            except Exception as e:
                logger.error(f"Error in temp rename for {old_path}: {e}")
                failed.append((old_path, str(e)))

        # Phase 2: Rename from temp to final names
        for temp_path, new_filename, original_path in temp_renames:
            temp_path_obj = Path(temp_path)
            new_path = temp_path_obj.parent / new_filename

            try:
                # Final check if target exists
                if new_path.exists():
                    # Rollback temp rename
                    temp_path_obj.rename(original_path)
                    failed.append((original_path, f"File already exists: {new_filename}"))
                else:
                    temp_path_obj.rename(new_path)
                    # Track for undo
                    self.history.append((str(new_path), original_path))
                    successful += 1
                    logger.info(f"Renamed: {Path(original_path).name} → {new_filename}")
            except Exception as e:
                logger.error(f"Error in final rename for {temp_path}: {e}")
                # Try to rollback temp rename
                try:
                    temp_path_obj.rename(original_path)
                except Exception:
                    pass
                failed.append((original_path, str(e)))

        logger.info(f"Batch rename: {successful} successful, {len(failed)} failed")
        return successful, failed

    def undo_last(self):
        """
        Undo the last rename operation.

        Returns:
            tuple: (success: bool, error_msg: str or None)
        """
        if not self.history:
            return False, "No operations to undo"

        try:
            # Peek at history without removing yet
            new_path, old_path = self.history[-1]
            Path(new_path).rename(old_path)
            # Only remove from history if rename succeeded
            self.history.pop()
            logger.info(f"Undone: {Path(new_path).name} → {Path(old_path).name}")
            return True, None

        except Exception as e:
            logger.error(f"Error undoing rename: {e}")
            # Don't remove from history if undo failed
            return False, str(e)

    def undo_all(self):
        """
        Undo all rename operations in reverse order.

        Returns:
            tuple: (successful_count, failed_count)
        """
        successful = 0
        failed = 0

        while self.history:
            success, error = self.undo_last()
            if success:
                successful += 1
            else:
                failed += 1

        logger.info(f"Undo all: {successful} successful, {failed} failed")
        return successful, failed

    def clear_history(self):
        """Clear undo history."""
        self.history.clear()
        logger.info("Undo history cleared")

    def can_undo(self):
        """
        Check if undo is possible.

        Returns:
            bool: True if there are operations to undo.
        """
        return len(self.history) > 0

    def _is_valid_filename(self, filename):
        """
        Check if filename is valid.

        Args:
            filename (str): Filename to check.

        Returns:
            bool: True if valid.
        """
        if not filename:
            return False

        # Check for invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            if char in filename:
                return False

        # Check for reserved names (Windows)
        reserved = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4',
                   'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2',
                   'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']

        name_without_ext = Path(filename).stem.upper()
        if name_without_ext in reserved:
            return False

        return True
