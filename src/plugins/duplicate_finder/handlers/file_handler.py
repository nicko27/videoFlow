"""
File operations handler for the duplicate finder.

This module handles all file-related operations including adding files,
managing file lists, and validating file paths.

Updated: 2025-12-06 (Phase 10 - Added file validation for ISSUE #28)
"""
import os
from typing import List, Tuple
from PyQt6.QtWidgets import QFileDialog

from src.core.logger import Logger
from ..validators import FileValidator, ValidationError

logger = Logger.get_logger('DuplicateFinder.FileHandler')


class FileHandler:
    """
    Handler for file operations in the duplicate finder.

    This class manages file selection, validation, and list operations.
    It provides methods for adding individual files, scanning directories,
    and maintaining the list of files to analyze.

    Example:
        ```python
        handler = FileHandler(file_list_widget)
        added_count = handler.add_files_dialog(parent_window)
        all_files = handler.get_all_files()
        ```
    """

    # Supported video file extensions
    VIDEO_EXTENSIONS = ('.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.m4v')

    def __init__(self, file_list_widget) -> None:
        """
        Initialize the file handler.

        Args:
            file_list_widget: FileListWidget instance for managing the file list UI.
        """
        self.file_list_widget = file_list_widget

        # SECURITY: File validator for path validation (ISSUE #28 fix)
        # Validates file paths to prevent security issues:
        # - Path traversal attacks
        # - Symbolic link exploits
        # - Invalid/corrupt files
        self.file_validator = FileValidator(
            verify_video_format=False  # Skip OpenCV check for performance (done later)
        )

        logger.info("File handler initialized with security validation")

    def add_files_dialog(self, parent=None) -> int:
        """
        Show file selection dialog and add selected files.

        Args:
            parent: Parent widget for the dialog.

        Returns:
            Number of files added.
        """
        files, _ = QFileDialog.getOpenFileNames(
            parent,
            "Select video files",
            "",
            "Videos (*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.m4v);;All files (*.*)"
        )

        if not files:
            return 0

        return self.add_files(files)

    def add_folder_dialog(self, parent=None) -> int:
        """
        Show folder selection dialog and add all video files from the folder.

        This method recursively scans the selected folder and its subfolders
        for video files.

        Args:
            parent: Parent widget for the dialog.

        Returns:
            Number of files added.
        """
        folder = QFileDialog.getExistingDirectory(parent, "Select folder")

        if not folder:
            return 0

        return self.add_folder(folder)

    def add_files(self, file_paths: List[str]) -> int:
        """
        Add files to the file list with security validation.

        This method filters out duplicate files that are already in the list
        and validates all file paths for security (ISSUE #28 fix).

        Args:
            file_paths: List of file paths to add.

        Returns:
            Number of new files added (excluding duplicates and invalid files).
        """
        # SECURITY: Validate all file paths (ISSUE #28 fix)
        # This prevents path traversal, symlink attacks, and invalid files
        valid_files, invalid_files = self.file_validator.validate_paths_batch(
            file_paths,
            continue_on_error=True  # Validate all files, don't stop on first error
        )

        # Log any validation failures
        if invalid_files:
            logger.warning(f"Rejected {len(invalid_files)} invalid files during validation:")
            for file_path, error in invalid_files[:5]:  # Show first 5
                logger.warning(f"  - {os.path.basename(file_path)}: {error}")
            if len(invalid_files) > 5:
                logger.warning(f"  ... and {len(invalid_files) - 5} more")

        # Optimisation O(N) : conversion en set pour lookup rapide
        existing_files = set(self.file_list_widget.get_files())
        new_files = [f for f in valid_files if f not in existing_files]

        if new_files:
            count = self.file_list_widget.add_files(new_files)
            logger.info(
                f"Added {count} new files "
                f"(rejected {len(invalid_files)} invalid, "
                f"skipped {len(valid_files) - len(new_files)} duplicates)"
            )
            return count

        logger.info(f"No new files to add (rejected {len(invalid_files)} invalid)")
        return 0

    def add_folder(self, folder_path: str) -> int:
        """
        Add all video files from a folder and its subfolders with validation.

        Args:
            folder_path: Path to the folder to scan.

        Returns:
            Number of files added (after validation).
        """
        if not os.path.isdir(folder_path):
            logger.warning(f"Invalid folder path: {folder_path}")
            return 0

        # Optimisation O(N) : conversion en set pour lookup rapide
        existing_files = set(self.file_list_widget.get_files())
        found_files = []

        # Recursively scan folder for video files
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(self.VIDEO_EXTENSIONS):
                    file_path = os.path.join(root, file)
                    if file_path not in existing_files:
                        found_files.append(file_path)

        if not found_files:
            logger.info(f"No new video files found in folder: {folder_path}")
            return 0

        # SECURITY: Validate all found files (ISSUE #28 fix)
        valid_files, invalid_files = self.file_validator.validate_paths_batch(
            found_files,
            continue_on_error=True
        )

        if invalid_files:
            logger.warning(
                f"Rejected {len(invalid_files)} invalid files from folder scan "
                f"(total found: {len(found_files)})"
            )

        if valid_files:
            count = self.file_list_widget.add_files(valid_files)
            logger.info(
                f"Added {count} files from folder: {folder_path} "
                f"(rejected {len(invalid_files)} invalid)"
            )
            return count

        return 0

    def clear_files(self) -> None:
        """
        Clear all files from the file list.
        """
        self.file_list_widget.clear_files()
        logger.info("File list cleared")

    def get_all_files(self) -> List[str]:
        """
        Get all files currently in the list.

        Returns:
            List of file paths.
        """
        return self.file_list_widget.get_files()

    def get_file_count(self) -> int:
        """
        Get the number of files in the list.

        Returns:
            Number of files.
        """
        return len(self.file_list_widget.get_files())

    def update_file_status(self, file_path: str, status: str) -> bool:
        """
        Update the status of a file in the list.

        Args:
            file_path: Path to the file.
            status: New status string.

        Returns:
            True if status was updated, False otherwise.
        """
        return self.file_list_widget.update_file_status(file_path, status)

    def validate_files_for_analysis(self) -> Tuple[List[str], List[str]]:
        """
        Validate files and separate into valid and invalid lists.

        This method checks if files exist and are accessible.

        Returns:
            Tuple of (valid_files, invalid_files).
        """
        all_files = self.get_all_files()
        valid_files = []
        invalid_files = []

        for file_path in all_files:
            if os.path.exists(file_path) and os.path.isfile(file_path):
                valid_files.append(file_path)
            else:
                invalid_files.append(file_path)
                logger.warning(f"Invalid or missing file: {file_path}")

        return valid_files, invalid_files

    def update_cache_status(self, file_path: str, is_cached: bool) -> None:
        """
        Update the cache status display for a file.

        Args:
            file_path: Path to the file.
            is_cached: True if file is cached, False otherwise.
        """
        if is_cached:
            self.update_file_status(file_path, "✅ Cached")
        else:
            self.update_file_status(file_path, "⏳ To analyze")

    def batch_update_cache_status(
        self,
        files: List[str],
        cache_checker
    ) -> None:
        """
        Update cache status for multiple files.

        Args:
            files: List of file paths.
            cache_checker: Object with has_hash(file_path) method.
        """
        for file_path in files:
            is_cached = cache_checker.has_hash(file_path)
            self.update_cache_status(file_path, is_cached)
