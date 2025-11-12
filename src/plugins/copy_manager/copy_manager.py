"""Core copy management functionality.

This module provides the CopyManager class which handles file and folder copying
operations with progress tracking and macOS metadata preservation.
"""

import os
import shutil
from pathlib import Path
import osxmetadata
from src.core.logger import Logger

logger = Logger.get_logger('CopyManager')

class CopyManager:
    """Handles file and folder copy operations with metadata preservation.

    Provides functionality for copying files and folders with progress tracking,
    metadata preservation (macOS-specific), and automatic unique naming for
    duplicate files.

    Attributes:
        total_size (int): Total size in bytes of items to copy.
        copied_size (int): Size in bytes already copied (for progress tracking).
    """

    def __init__(self):
        """Initialize the CopyManager with zero counters."""
        self.total_size = 0
        self.copied_size = 0
    
    def calculate_total_size(self, source_path):
        """Calculate the total size of items to copy"""
        total_size = 0
        try:
            if os.path.isfile(source_path):
                total_size = os.path.getsize(source_path)
            else:
                for root, dirs, files in os.walk(source_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            total_size += os.path.getsize(file_path)
                        except OSError as e:
                            logger.warning(f"Unable to calculate size of {file_path}: {e}")
                            continue

            return total_size
        except Exception as e:
            logger.error(f"Error calculating total size: {e}")
            return 0

    def copy_with_progress(self, source_path, dest_path, progress_callback=None):
        """Copy file or folder with progress tracking"""
        try:
            # Calculate total size
            self.total_size = self.calculate_total_size(source_path)
            self.copied_size = 0

            if self.total_size == 0:
                logger.warning("Total size is zero, cannot track progress")
                return self.copy_file(source_path, dest_path)

            if os.path.isfile(source_path):
                return self._copy_file_with_progress(source_path, dest_path, progress_callback)
            else:
                return self._copy_dir_with_progress(source_path, dest_path, progress_callback)

        except Exception as e:
            logger.error(f"Error during copy: {e}")
            return None

    def _copy_file_with_progress(self, source_path, dest_path, progress_callback):
        """Copy a single file with progress tracking.

        Args:
            source_path (str): Path to the source file.
            dest_path (str): Path to the destination file.
            progress_callback (callable, optional): Callback function that receives
                progress percentage (0-100).

        Returns:
            str: Destination path if successful, None if failed.
        """
        try:
            # Create destination folder if necessary
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)

            # Copy file in blocks
            with open(source_path, 'rb') as fsrc:
                with open(dest_path, 'wb') as fdst:
                    while True:
                        buffer = fsrc.read(8388608)  # 8MB per block
                        if not buffer:
                            break
                        fdst.write(buffer)
                        self.copied_size += len(buffer)
                        if progress_callback:
                            progress = min(100, int((self.copied_size / self.total_size) * 100))
                            progress_callback(progress)

            # Copy metadata
            self.copy_metadata(source_path, dest_path)
            return dest_path

        except Exception as e:
            logger.error(f"Error copying file {source_path}: {e}")
            if os.path.exists(dest_path):
                try:
                    os.remove(dest_path)
                except Exception as e:
                    logger.debug(f"Could not remove destination file: {e}")
            return None

    def _copy_dir_with_progress(self, source_path, dest_path, progress_callback):
        """Copy a directory recursively with progress tracking.

        Args:
            source_path (str): Path to the source directory.
            dest_path (str): Path to the destination directory.
            progress_callback (callable, optional): Callback function that receives
                progress percentage (0-100).

        Returns:
            str: Destination path if successful, None if failed.
        """
        try:
            # Create destination folder
            os.makedirs(dest_path, exist_ok=True)

            # Copy each file
            for root, dirs, files in os.walk(source_path):
                # Create subfolders
                for dir_name in dirs:
                    src_dir = os.path.join(root, dir_name)
                    dst_dir = os.path.join(dest_path, os.path.relpath(src_dir, source_path))
                    os.makedirs(dst_dir, exist_ok=True)

                # Copy files
                for file_name in files:
                    src_file = os.path.join(root, file_name)
                    dst_file = os.path.join(dest_path, os.path.relpath(src_file, source_path))

                    # Copy file
                    self._copy_file_with_progress(src_file, dst_file, progress_callback)

            return dest_path

        except Exception as e:
            logger.error(f"Error copying folder {source_path}: {e}")
            if os.path.exists(dest_path):
                try:
                    shutil.rmtree(dest_path)
                except Exception as e:
                    logger.debug(f"Could not remove destination directory: {e}")
            return None

    def copy_metadata(self, source_path, dest_path):
        """Copy metadata from one file to another"""
        try:
            # Get source metadata
            source_meta = osxmetadata.OSXMetaData(source_path)
            dest_meta = osxmetadata.OSXMetaData(dest_path)

            # List of attributes to copy
            attributes = [
                'kMDItemWhereFroms',
                'kMDItemDownloadedDate',
                'kMDItemCreator',
                '_kMDItemUserTags',
                'kMDItemFinderComment'
            ]

            # Copy each attribute
            for attr in attributes:
                try:
                    if hasattr(source_meta, attr):
                        value = getattr(source_meta, attr)
                        if value:
                            setattr(dest_meta, attr, value)
                except Exception as e:
                    logger.warning(f"Unable to copy attribute {attr}: {e}")
                    continue

            logger.debug("Metadata copied successfully")
            return True

        except Exception as e:
            logger.error(f"Error copying metadata: {str(e)}")
            return False

    def get_unique_name(self, path):
        """Generate a unique filename if the file already exists.

        Appends a counter in parentheses to the filename before the extension
        until a unique name is found (e.g., file.txt -> file (1).txt).

        Args:
            path (str): Original file path.

        Returns:
            str: Unique file path that doesn't exist.
        """
        if not os.path.exists(path):
            return path

        base, ext = os.path.splitext(path)
        counter = 1

        while True:
            new_name = f"{base} ({counter}){ext}"
            if not os.path.exists(new_name):
                return new_name
            counter += 1

    def count_items(self, path):
        """Count the total number of folders and files in a directory.

        Args:
            path (str): Path to the directory to count.

        Returns:
            int: Total count of folders and files (minimum 1).
        """
        total = 0
        for root, dirs, files in os.walk(path):
            total += len(dirs)  # Count folders
            total += len(files)  # Count files
        return max(total, 1)  # At least 1 to avoid division by zero
