"""
Scan service for discovering video files.

This service provides core business logic for scanning directories
and discovering video files. It uses dependency injection to report
progress and display messages without depending on CLI or GUI.
"""

import time
from pathlib import Path
from typing import List, Set, Optional
from datetime import datetime

from duplicateflow.core.interfaces import IProgressReporter, IUIAdapter, MessageType
from duplicateflow.core.models.scan import VideoFile, ScanResult, VideoFormat


# Supported video extensions
SUPPORTED_VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".avi", ".mov", ".wmv",
    ".flv", ".webm", ".m4v", ".mpg", ".mpeg"
}


class ScanService:
    """
    Service for scanning directories and discovering video files.

    This is a pure business logic service that uses dependency injection
    to report progress and display messages. It has ZERO dependencies
    on CLI or GUI implementations.

    Attributes:
        progress: Progress reporter (injected)
        ui: UI adapter (injected)

    Example:
        >>> from duplicateflow.core.interfaces import NullProgressReporter, NullUIAdapter
        >>> service = ScanService(
        ...     progress=NullProgressReporter(),
        ...     ui=NullUIAdapter()
        ... )
        >>> result = service.scan_directory(Path("/videos"))
    """

    def __init__(
        self,
        progress: IProgressReporter,
        ui: IUIAdapter
    ):
        """
        Initialize scan service with dependencies.

        Args:
            progress: Progress reporter for tracking scan progress
            ui: UI adapter for displaying messages
        """
        self.progress = progress
        self.ui = ui

    def scan_directory(
        self,
        root_path: Path,
        recursive: bool = True,
        follow_symlinks: bool = False
    ) -> ScanResult:
        """
        Scan a directory for video files.

        Args:
            root_path: Directory to scan
            recursive: If True, scan subdirectories recursively
            follow_symlinks: If True, follow symbolic links

        Returns:
            ScanResult with discovered videos

        Raises:
            FileNotFoundError: If root_path doesn't exist
            NotADirectoryError: If root_path is not a directory

        Example:
            >>> result = service.scan_directory(Path("/videos"))
            >>> print(f"Found {result.video_count} videos")
        """
        # Validate input
        if not root_path.exists():
            raise FileNotFoundError(f"Directory not found: {root_path}")

        if not root_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {root_path}")

        # Initialize tracking
        start_time = time.time()
        videos: List[VideoFile] = []
        errors: List[str] = []
        directories_scanned = 0
        total_files_checked = 0

        # Display start message
        self.ui.display_message(
            f"Scanning: {root_path}",
            MessageType.INFO
        )

        # Collect all directories to scan
        directories = self._collect_directories(
            root_path,
            recursive,
            follow_symlinks
        )

        # Start progress tracking
        self.progress.start_phase(
            "scan",
            total=len(directories),
            message="Scanning directories for videos"
        )

        # Scan each directory
        for idx, directory in enumerate(directories):
            try:
                # Scan this directory
                dir_videos, dir_files = self._scan_single_directory(directory)

                videos.extend(dir_videos)
                total_files_checked += dir_files
                directories_scanned += 1

                # Update progress
                self.progress.update(
                    "scan",
                    current=idx + 1,
                    message=f"Scanned {directories_scanned} directories, found {len(videos)} videos"
                )

            except PermissionError as e:
                error_msg = f"Permission denied: {directory}"
                errors.append(error_msg)
                self.ui.display_message(error_msg, MessageType.WARNING)

            except Exception as e:
                error_msg = f"Error scanning {directory}: {str(e)}"
                errors.append(error_msg)
                self.ui.display_message(error_msg, MessageType.ERROR)

        # Finish progress
        self.progress.finish_phase(
            "scan",
            message=f"Scan complete: {len(videos)} videos found"
        )

        # Calculate duration
        scan_duration = time.time() - start_time

        # Display success message
        self.ui.display_message(
            f"Found {len(videos)} videos in {scan_duration:.2f}s",
            MessageType.SUCCESS
        )

        # Create and return result
        return ScanResult(
            videos=videos,
            directories_scanned=directories_scanned,
            total_files_checked=total_files_checked,
            scan_duration_seconds=scan_duration,
            timestamp=datetime.now(),
            root_path=root_path.absolute(),
            errors=errors,
        )

    def _collect_directories(
        self,
        root_path: Path,
        recursive: bool,
        follow_symlinks: bool
    ) -> List[Path]:
        """
        Collect all directories to scan.

        Args:
            root_path: Root directory
            recursive: If True, collect subdirectories
            follow_symlinks: If True, follow symlinks

        Returns:
            List of directories to scan
        """
        directories = [root_path]

        if recursive:
            try:
                for item in root_path.rglob("*"):
                    if item.is_dir():
                        # Check symlinks
                        if item.is_symlink() and not follow_symlinks:
                            continue
                        directories.append(item)
            except PermissionError:
                # If we can't access subdirectories, just scan root
                pass

        return directories

    def _scan_single_directory(
        self,
        directory: Path
    ) -> tuple[List[VideoFile], int]:
        """
        Scan a single directory for video files.

        Args:
            directory: Directory to scan

        Returns:
            Tuple of (list of VideoFile objects, total files checked)
        """
        videos: List[VideoFile] = []
        files_checked = 0

        try:
            for item in directory.iterdir():
                # Skip directories
                if item.is_dir():
                    continue

                # Skip symlinks (they'll be handled by their targets)
                if item.is_symlink():
                    continue

                files_checked += 1

                # Check if it's a video file
                if self._is_video_file(item):
                    try:
                        video = VideoFile.from_path(item)
                        videos.append(video)
                    except Exception:
                        # Skip files we can't read
                        pass

        except PermissionError:
            # Re-raise to be caught by caller
            raise

        return videos, files_checked

    def _is_video_file(self, path: Path) -> bool:
        """
        Check if a file is a supported video file.

        Args:
            path: File path to check

        Returns:
            True if file is a supported video format
        """
        return path.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS

    def filter_by_format(
        self,
        scan_result: ScanResult,
        formats: List[VideoFormat]
    ) -> List[VideoFile]:
        """
        Filter videos by format.

        Args:
            scan_result: Scan result to filter
            formats: List of formats to keep

        Returns:
            Filtered list of videos

        Example:
            >>> videos = service.filter_by_format(
            ...     result,
            ...     [VideoFormat.MP4, VideoFormat.MKV]
            ... )
        """
        return [
            video for video in scan_result.videos
            if video.format in formats
        ]

    def filter_by_size(
        self,
        scan_result: ScanResult,
        min_size_mb: Optional[float] = None,
        max_size_mb: Optional[float] = None
    ) -> List[VideoFile]:
        """
        Filter videos by file size.

        Args:
            scan_result: Scan result to filter
            min_size_mb: Minimum size in MB (inclusive)
            max_size_mb: Maximum size in MB (inclusive)

        Returns:
            Filtered list of videos

        Example:
            >>> # Get videos between 100MB and 1GB
            >>> videos = service.filter_by_size(result, 100, 1024)
        """
        videos = scan_result.videos

        if min_size_mb is not None:
            videos = [v for v in videos if v.size_mb >= min_size_mb]

        if max_size_mb is not None:
            videos = [v for v in videos if v.size_mb <= max_size_mb]

        return videos

    def get_statistics(self, scan_result: ScanResult) -> dict:
        """
        Get statistics about scan result.

        Args:
            scan_result: Scan result to analyze

        Returns:
            Dictionary with statistics

        Example:
            >>> stats = service.get_statistics(result)
            >>> print(stats["total_videos"])
            >>> print(stats["total_size_gb"])
        """
        return {
            "total_videos": scan_result.video_count,
            "total_size_bytes": scan_result.total_size_bytes,
            "total_size_mb": scan_result.total_size_mb,
            "total_size_gb": scan_result.total_size_gb,
            "format_counts": scan_result.get_format_counts(),
            "directories_scanned": scan_result.directories_scanned,
            "files_checked": scan_result.total_files_checked,
            "scan_duration_seconds": scan_result.scan_duration_seconds,
            "errors": len(scan_result.errors),
            "has_errors": scan_result.has_errors,
        }
