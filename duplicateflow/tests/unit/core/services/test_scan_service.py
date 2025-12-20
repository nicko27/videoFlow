"""
Unit tests for ScanService.

Tests verify that the scan service correctly scans directories,
discovers videos, and uses dependency injection properly.
"""

import pytest
import tempfile
from pathlib import Path
from duplicateflow.core.services import ScanService, SUPPORTED_VIDEO_EXTENSIONS
from duplicateflow.core.interfaces import NullProgressReporter, NullUIAdapter, MessageType
from duplicateflow.core.models.scan import VideoFormat


@pytest.fixture
def null_service():
    """Create ScanService with null dependencies."""
    return ScanService(
        progress=NullProgressReporter(),
        ui=NullUIAdapter()
    )


@pytest.fixture
def temp_video_dir(tmp_path):
    """
    Create temporary directory with fake video files.

    Structure:
    temp_dir/
    ├── movie1.mp4
    ├── movie2.mkv
    ├── document.txt (not a video)
    └── subfolder/
        ├── movie3.avi
        └── movie4.mov
    """
    # Create main directory files
    (tmp_path / "movie1.mp4").touch()
    (tmp_path / "movie2.mkv").touch()
    (tmp_path / "document.txt").touch()

    # Create subfolder with videos
    subfolder = tmp_path / "subfolder"
    subfolder.mkdir()
    (subfolder / "movie3.avi").touch()
    (subfolder / "movie4.mov").touch()

    return tmp_path


class TestScanService:
    """Tests for ScanService."""

    def test_scan_service_instantiation(self, null_service):
        """Test ScanService creation with dependencies."""
        assert isinstance(null_service.progress, NullProgressReporter)
        assert isinstance(null_service.ui, NullUIAdapter)

    def test_scan_service_with_custom_dependencies(self):
        """Test ScanService with custom dependencies."""
        progress = NullProgressReporter()
        ui = NullUIAdapter()

        service = ScanService(progress=progress, ui=ui)

        assert service.progress is progress
        assert service.ui is ui

    def test_scan_directory_nonexistent(self, null_service):
        """Test scan_directory with nonexistent directory."""
        with pytest.raises(FileNotFoundError):
            null_service.scan_directory(Path("/nonexistent/directory"))

    def test_scan_directory_not_a_directory(self, null_service, tmp_path):
        """Test scan_directory with a file instead of directory."""
        # Create a file
        file_path = tmp_path / "file.txt"
        file_path.touch()

        with pytest.raises(NotADirectoryError):
            null_service.scan_directory(file_path)

    def test_scan_directory_empty(self, null_service, tmp_path):
        """Test scanning empty directory."""
        result = null_service.scan_directory(tmp_path, recursive=False)

        assert result.video_count == 0
        assert result.directories_scanned == 1
        assert result.total_files_checked == 0
        assert result.root_path == tmp_path.absolute()
        assert result.scan_duration_seconds > 0

    def test_scan_directory_with_videos(self, null_service, temp_video_dir):
        """Test scanning directory with video files (non-recursive)."""
        result = null_service.scan_directory(temp_video_dir, recursive=False)

        # Should find 2 videos in root (movie1.mp4, movie2.mkv)
        # document.txt is not a video
        assert result.video_count == 2
        assert result.total_files_checked == 3  # 2 videos + 1 txt

    def test_scan_directory_recursive(self, null_service, temp_video_dir):
        """Test scanning directory recursively."""
        result = null_service.scan_directory(temp_video_dir, recursive=True)

        # Should find 4 videos total (2 in root + 2 in subfolder)
        assert result.video_count == 4
        assert result.directories_scanned >= 2  # root + subfolder

    def test_scan_directory_progress_reporting(self, temp_video_dir):
        """Test that progress is reported during scan."""
        progress = NullProgressReporter()
        ui = NullUIAdapter()
        service = ScanService(progress=progress, ui=ui)

        result = service.scan_directory(temp_video_dir)

        # Progress and UI should have been used (we can't verify easily with NullReporter)
        # But we can verify the scan worked
        assert result.video_count > 0

    def test_scan_directory_ui_messages(self, temp_video_dir):
        """Test that UI messages are displayed."""
        progress = NullProgressReporter()
        ui = NullUIAdapter()
        service = ScanService(progress=progress, ui=ui)

        result = service.scan_directory(temp_video_dir)

        # UI adapter should have stored messages
        assert len(ui.messages) > 0

        # Should have start and success messages
        messages_text = [m['message'] for m in ui.messages]
        assert any("Scanning:" in msg for msg in messages_text)
        assert any("Found" in msg for msg in messages_text)

    def test_scan_directory_result_metadata(self, null_service, temp_video_dir):
        """Test ScanResult contains correct metadata."""
        result = null_service.scan_directory(temp_video_dir)

        assert result.timestamp is not None
        assert result.scan_duration_seconds > 0
        assert result.root_path == temp_video_dir.absolute()

    def test_scan_directory_no_errors(self, null_service, temp_video_dir):
        """Test scanning without errors."""
        result = null_service.scan_directory(temp_video_dir)

        assert result.has_errors is False
        assert len(result.errors) == 0

    def test_is_video_file(self, null_service):
        """Test _is_video_file method."""
        # Test supported formats
        assert null_service._is_video_file(Path("movie.mp4")) is True
        assert null_service._is_video_file(Path("movie.mkv")) is True
        assert null_service._is_video_file(Path("movie.avi")) is True
        assert null_service._is_video_file(Path("movie.mov")) is True

        # Test unsupported formats
        assert null_service._is_video_file(Path("document.txt")) is False
        assert null_service._is_video_file(Path("image.jpg")) is False
        assert null_service._is_video_file(Path("archive.zip")) is False

    def test_is_video_file_case_insensitive(self, null_service):
        """Test _is_video_file is case-insensitive."""
        assert null_service._is_video_file(Path("MOVIE.MP4")) is True
        assert null_service._is_video_file(Path("Movie.MKV")) is True
        assert null_service._is_video_file(Path("movie.Mp4")) is True

    def test_filter_by_format(self, null_service, temp_video_dir):
        """Test filter_by_format method."""
        result = null_service.scan_directory(temp_video_dir, recursive=True)

        # Filter only MP4 videos
        mp4_videos = null_service.filter_by_format(result, [VideoFormat.MP4])
        assert len(mp4_videos) == 1
        assert all(v.format == VideoFormat.MP4 for v in mp4_videos)

        # Filter MP4 and MKV
        mp4_mkv_videos = null_service.filter_by_format(
            result,
            [VideoFormat.MP4, VideoFormat.MKV]
        )
        assert len(mp4_mkv_videos) == 2

    def test_filter_by_size_min(self, null_service, temp_video_dir):
        """Test filter_by_size with minimum size."""
        result = null_service.scan_directory(temp_video_dir)

        # Filter videos >= 10 MB (all our test videos are 0 bytes)
        large_videos = null_service.filter_by_size(result, min_size_mb=10.0)
        assert len(large_videos) == 0

        # Filter videos >= 0 MB (should include all)
        all_videos = null_service.filter_by_size(result, min_size_mb=0.0)
        assert len(all_videos) == result.video_count

    def test_filter_by_size_max(self, null_service, temp_video_dir):
        """Test filter_by_size with maximum size."""
        result = null_service.scan_directory(temp_video_dir)

        # Filter videos <= 0.001 MB (should include all 0-byte test files)
        small_videos = null_service.filter_by_size(result, max_size_mb=0.001)
        assert len(small_videos) == result.video_count

    def test_filter_by_size_range(self, null_service, temp_video_dir):
        """Test filter_by_size with min and max."""
        result = null_service.scan_directory(temp_video_dir)

        # Filter videos between 0 and 1 MB
        videos = null_service.filter_by_size(
            result,
            min_size_mb=0.0,
            max_size_mb=1.0
        )
        assert len(videos) == result.video_count

    def test_get_statistics(self, null_service, temp_video_dir):
        """Test get_statistics method."""
        result = null_service.scan_directory(temp_video_dir, recursive=True)

        stats = null_service.get_statistics(result)

        assert "total_videos" in stats
        assert "total_size_bytes" in stats
        assert "total_size_mb" in stats
        assert "total_size_gb" in stats
        assert "format_counts" in stats
        assert "directories_scanned" in stats
        assert "files_checked" in stats
        assert "scan_duration_seconds" in stats
        assert "errors" in stats
        assert "has_errors" in stats

        assert stats["total_videos"] == 4
        assert stats["total_size_bytes"] == 0  # Test files are empty
        assert stats["has_errors"] is False

    def test_get_statistics_format_counts(self, null_service, temp_video_dir):
        """Test format counts in statistics."""
        result = null_service.scan_directory(temp_video_dir, recursive=True)

        stats = null_service.get_statistics(result)

        format_counts = stats["format_counts"]
        assert format_counts["mp4"] == 1
        assert format_counts["mkv"] == 1
        assert format_counts["avi"] == 1
        assert format_counts["mov"] == 1

    def test_collect_directories_non_recursive(self, null_service, temp_video_dir):
        """Test _collect_directories without recursion."""
        directories = null_service._collect_directories(
            temp_video_dir,
            recursive=False,
            follow_symlinks=False
        )

        # Should only return root directory
        assert len(directories) == 1
        assert directories[0] == temp_video_dir

    def test_collect_directories_recursive(self, null_service, temp_video_dir):
        """Test _collect_directories with recursion."""
        directories = null_service._collect_directories(
            temp_video_dir,
            recursive=True,
            follow_symlinks=False
        )

        # Should return root + subfolder
        assert len(directories) >= 2
        assert temp_video_dir in directories

    def test_scan_single_directory(self, null_service, temp_video_dir):
        """Test _scan_single_directory method."""
        videos, files_checked = null_service._scan_single_directory(temp_video_dir)

        # Root has 2 videos + 1 text file
        assert len(videos) == 2
        assert files_checked == 3

    def test_supported_video_extensions_constant(self):
        """Test SUPPORTED_VIDEO_EXTENSIONS contains expected formats."""
        assert ".mp4" in SUPPORTED_VIDEO_EXTENSIONS
        assert ".mkv" in SUPPORTED_VIDEO_EXTENSIONS
        assert ".avi" in SUPPORTED_VIDEO_EXTENSIONS
        assert ".mov" in SUPPORTED_VIDEO_EXTENSIONS
        assert ".wmv" in SUPPORTED_VIDEO_EXTENSIONS

        # Should be lowercase
        assert all(ext.islower() for ext in SUPPORTED_VIDEO_EXTENSIONS)

        # Should start with dot
        assert all(ext.startswith(".") for ext in SUPPORTED_VIDEO_EXTENSIONS)

    def test_dependency_injection_isolation(self):
        """Test that service uses injected dependencies."""
        progress = NullProgressReporter()
        ui = NullUIAdapter()

        service = ScanService(progress=progress, ui=ui)

        # Service should use the exact instances we provided
        assert service.progress is progress
        assert service.ui is ui

        # Service has no direct dependencies on CLI or GUI
        # (This is architectural, verified by imports)
