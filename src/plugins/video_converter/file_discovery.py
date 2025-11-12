"""Background file discovery worker.

This module provides a threaded worker for discovering video files in
directories with real-time progress updates and filtering.
"""

from PyQt6.QtCore import QThread, pyqtSignal
from pathlib import Path
from typing import List, Set
import os

from src.core.logger import Logger

logger = Logger.get_logger('VideoConverter.FileDiscovery')


class FastFileDiscoveryWorker(QThread):
    """Worker thread for fast video file discovery with real-time updates.

    Scans directories for video files meeting size criteria, emitting signals
    for each discovered file and progress updates.

    Signals:
        file_found: Emitted when a file is found (file_path, size_bytes, size_mb).
        progress: Emitted periodically (discovered_count, current_folder).
        finished: Emitted when scanning completes (total_discovered).
        batch_update: Emitted periodically to trigger UI batch updates.
    """

    file_found = pyqtSignal(str, int, int)  # file_path, size_bytes, size_mb
    progress = pyqtSignal(int, str)  # discovered_count, current_folder
    finished = pyqtSignal(int)  # total_discovered
    batch_update = pyqtSignal()  # Signal for batch UI updates

    def __init__(self, folders: List[Path], min_size_mb: int = 100):
        """Initialize the discovery worker.

        Args:
            folders: List of folders to scan.
            min_size_mb: Minimum file size in MB (default: 100).
        """
        super().__init__()
        self.folders = folders
        self.min_size_bytes = min_size_mb * 1024 * 1024
        self.is_running = True
        self.discovered_count = 0

        # Common video extensions for performance
        self.video_exts: Set[str] = {
            '.mp4', '.avi', '.mkv', '.mov', '.flv', '.webm', '.wmv'
        }

        # Batch update counter
        self.batch_counter = 0
        self.batch_size = 5  # Update UI every 5 discoveries

    def run(self) -> None:
        """Execute the file discovery scan."""
        try:
            for folder in self.folders:
                if not self.is_running or not folder.exists():
                    continue

                self.progress.emit(self.discovered_count, str(folder))
                self._scan_fast(folder, max_depth=4)

        except Exception as e:
            logger.error(f"Error during file discovery: {e}")
        finally:
            # Final update if needed
            if self.batch_counter > 0:
                self.batch_update.emit()
            self.finished.emit(self.discovered_count)

    def _scan_fast(
        self,
        directory: Path,
        max_depth: int,
        current_depth: int = 0
    ) -> None:
        """Perform optimized directory scan with depth limits.

        Args:
            directory: Directory to scan.
            max_depth: Maximum recursion depth.
            current_depth: Current depth level (default: 0).
        """
        if not self.is_running or current_depth > max_depth:
            return

        try:
            # Use scandir for better performance than iterdir
            with os.scandir(directory) as entries:
                for entry in entries:
                    if not self.is_running:
                        break

                    try:
                        if entry.is_file():
                            self._process_file(entry)

                        elif entry.is_dir() and current_depth < max_depth:
                            self._process_directory(entry, max_depth, current_depth)

                    except (OSError, PermissionError):
                        # Skip inaccessible files/directories
                        continue

        except (OSError, PermissionError):
            logger.debug(f"Cannot access folder: {directory}")

    def _process_file(self, entry: os.DirEntry) -> None:
        """Process a file entry.

        Args:
            entry: Directory entry for the file.
        """
        file_path = Path(entry.path)

        # Quick extension check
        if file_path.suffix.lower() not in self.video_exts:
            return

        stat_info = entry.stat()
        if stat_info.st_size < self.min_size_bytes:
            return

        # Check for _cvt suffix quickly
        if entry.name.endswith('_cvt' + file_path.suffix):
            return

        size_mb = int(stat_info.st_size / (1024 * 1024))
        self.file_found.emit(entry.path, stat_info.st_size, size_mb)
        self.discovered_count += 1

        # Batch update to avoid UI overload
        self.batch_counter += 1
        if self.batch_counter >= self.batch_size:
            self.batch_update.emit()
            self.batch_counter = 0
            # Give UI time to update
            self.msleep(10)

    def _process_directory(
        self,
        entry: os.DirEntry,
        max_depth: int,
        current_depth: int
    ) -> None:
        """Process a directory entry.

        Args:
            entry: Directory entry for the folder.
            max_depth: Maximum recursion depth.
            current_depth: Current depth level.
        """
        # Skip system and hidden folders
        skip_folders = {
            '$RECYCLE.BIN', 'System Volume Information', '__pycache__',
            'node_modules', '.git', '.svn', 'Thumbs.db'
        }

        if not entry.name.startswith('.') and entry.name not in skip_folders:
            self._scan_fast(Path(entry.path), max_depth, current_depth + 1)

    def stop(self) -> None:
        """Stop the discovery process."""
        self.is_running = False
