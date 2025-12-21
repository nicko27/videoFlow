"""
Unit tests for FingerprintIndex and Match classes.

Tests the inverted index for N-to-N video matching using SQLite.
"""

import pytest
import sqlite3
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from duplicateflow.processing.fingerprint_index import FingerprintIndex, Match


class TestMatchDataclass:
    """Test Match dataclass and utility methods."""

    def test_match_creation(self):
        """Test creating a Match object."""
        match = Match(
            video1_id=1,
            video2_id=2,
            video1_path="/video1.mp4",
            video2_path="/video2.mp4",
            offset_seconds=123.5,
            votes=500,
            confidence=85.0,
            match_type="DUPLICATE"
        )

        assert match.video1_id == 1
        assert match.video2_id == 2
        assert match.offset_seconds == 123.5
        assert match.votes == 500
        assert match.confidence == 85.0
        assert match.match_type == "DUPLICATE"

    def test_format_offset_hours(self):
        """Test offset formatting with hours."""
        match = Match(
            video1_id=1, video2_id=2,
            video1_path="v1", video2_path="v2",
            offset_seconds=3665.0,  # 1:01:05
            votes=100, confidence=50.0, match_type="SCENE"
        )

        assert match.format_offset() == "1:01:05"

    def test_format_offset_minutes_only(self):
        """Test offset formatting without hours."""
        match = Match(
            video1_id=1, video2_id=2,
            video1_path="v1", video2_path="v2",
            offset_seconds=125.0,  # 2:05
            votes=100, confidence=50.0, match_type="SCENE"
        )

        assert match.format_offset() == "2:05"

    def test_format_offset_seconds_only(self):
        """Test offset formatting with only seconds."""
        match = Match(
            video1_id=1, video2_id=2,
            video1_path="v1", video2_path="v2",
            offset_seconds=45.0,  # 0:45
            votes=100, confidence=50.0, match_type="SCENE"
        )

        assert match.format_offset() == "0:45"

    def test_classify_match_duplicate(self):
        """Test DUPLICATE classification (high confidence + near zero offset)."""
        match_type = Match.classify_match(confidence=85.0, offset_seconds=5.0)
        assert match_type == "DUPLICATE"

        # Exactly at threshold
        match_type = Match.classify_match(confidence=80.0, offset_seconds=10.0)
        assert match_type == "DUPLICATE"

    def test_classify_match_scene(self):
        """Test SCENE classification (high confidence + significant offset)."""
        match_type = Match.classify_match(confidence=75.0, offset_seconds=120.0)
        assert match_type == "SCENE"

        # At threshold
        match_type = Match.classify_match(confidence=60.0, offset_seconds=50.0)
        assert match_type == "SCENE"

    def test_classify_match_extract(self):
        """Test EXTRACT classification (medium confidence)."""
        match_type = Match.classify_match(confidence=40.0, offset_seconds=0.0)
        assert match_type == "EXTRACT"

        # At threshold
        match_type = Match.classify_match(confidence=15.0, offset_seconds=100.0)
        assert match_type == "EXTRACT"

    def test_classify_match_uncertain(self):
        """Test UNCERTAIN classification (low confidence)."""
        match_type = Match.classify_match(confidence=10.0, offset_seconds=0.0)
        assert match_type == "UNCERTAIN"

        # Very low
        match_type = Match.classify_match(confidence=5.0, offset_seconds=50.0)
        assert match_type == "UNCERTAIN"


class TestFingerprintIndexInit:
    """Test FingerprintIndex initialization."""

    def test_init_default_path(self):
        """Test initialization with default database path."""
        # Use in-memory database for testing
        index = FingerprintIndex(db_path=':memory:')

        assert index.db_path == Path(':memory:')

    def test_init_custom_path(self, tmp_path):
        """Test initialization with custom database path."""
        db_path = tmp_path / "test_fingerprints.db"
        index = FingerprintIndex(db_path=str(db_path))

        assert index.db_path == db_path
        assert db_path.exists()

    def test_init_creates_schema(self, tmp_path):
        """Test that initialization creates database tables."""
        db_path = tmp_path / "test_fingerprints.db"
        index = FingerprintIndex(db_path=str(db_path))

        # Check tables exist
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]

        assert 'videos' in tables
        assert 'fingerprints' in tables

        conn.close()


class TestFingerprintIndexIndexVideo:
    """Test video indexing functionality."""

    @pytest.fixture
    def index(self, tmp_path):
        """Create index with temporary database."""
        db_path = tmp_path / "test.db"
        return FingerprintIndex(db_path=str(db_path))

    @pytest.fixture
    def mock_algorithm(self):
        """Create mock algorithm for fingerprint extraction."""
        algo = Mock()
        # Return synthetic fingerprints: hash -> [timestamps]
        algo.extract_fingerprints = Mock(return_value={
            12345: [100, 200, 300],  # Hash 12345 appears at 100ms, 200ms, 300ms
            67890: [150, 250],
            11111: [50]
        })
        return algo

    def test_index_video_success(self, index, mock_algorithm, tmp_path):
        """Test successful video indexing."""
        # Create dummy video file
        video_path = tmp_path / "video.mp4"
        video_path.touch()

        # Mock get_video_duration
        with patch('duplicateflow.algorithms.base.video_loader.get_video_duration') as mock_duration:
            mock_duration.return_value = 30.0

            video_id = index.index_video(str(video_path), mock_algorithm)

        assert video_id is not None
        assert video_id > 0

        # Verify database contains video
        conn = sqlite3.connect(str(index.db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT path, duration, hash_count FROM videos WHERE id = ?", (video_id,))
        row = cursor.fetchone()

        assert row is not None
        assert Path(row[0]) == video_path.resolve()
        assert row[1] == 30.0  # duration
        assert row[2] == 3  # hash_count (3 unique hashes)

        # Verify fingerprints inserted
        cursor.execute("SELECT COUNT(*) FROM fingerprints WHERE video_id = ?", (video_id,))
        fingerprint_count = cursor.fetchone()[0]

        # Should have 6 fingerprints total (3+2+1)
        assert fingerprint_count == 6

        conn.close()

    def test_index_video_already_indexed_skip(self, index, mock_algorithm, tmp_path):
        """Test that already-indexed video is skipped (MD5 deduplication)."""
        video_path = tmp_path / "video.mp4"
        video_path.write_text("video content")

        with patch('duplicateflow.algorithms.base.video_loader.get_video_duration', return_value=30.0):
            # Index first time
            video_id1 = index.index_video(str(video_path), mock_algorithm)

            # Index second time (should skip)
            video_id2 = index.index_video(str(video_path), mock_algorithm, force=False)

        # Should return same ID without re-extracting
        assert video_id1 == video_id2
        # extract_fingerprints should only be called once
        assert mock_algorithm.extract_fingerprints.call_count == 1

    def test_index_video_force_reindex(self, index, mock_algorithm, tmp_path):
        """Test forcing re-index of already-indexed video."""
        video_path = tmp_path / "video.mp4"
        video_path.write_text("video content")

        with patch('duplicateflow.algorithms.base.video_loader.get_video_duration', return_value=30.0):
            # Index first time
            video_id1 = index.index_video(str(video_path), mock_algorithm)

            # Force re-index
            video_id2 = index.index_video(str(video_path), mock_algorithm, force=True)

        # Should return same ID but re-extract
        assert video_id1 == video_id2
        # extract_fingerprints should be called twice
        assert mock_algorithm.extract_fingerprints.call_count == 2

    def test_index_video_file_changed(self, index, mock_algorithm, tmp_path):
        """Test re-indexing when file content changes."""
        video_path = tmp_path / "video.mp4"
        video_path.write_text("original content")

        with patch('duplicateflow.algorithms.base.video_loader.get_video_duration', return_value=30.0):
            # Index first time
            video_id1 = index.index_video(str(video_path), mock_algorithm)

            # Change file content (different MD5)
            video_path.write_text("modified content")

            # Index again (should detect change and re-index)
            video_id2 = index.index_video(str(video_path), mock_algorithm)

        # Should be same video ID but re-indexed
        assert video_id1 == video_id2
        # extract_fingerprints should be called twice
        assert mock_algorithm.extract_fingerprints.call_count == 2


class TestFingerprintIndexFindMatches:
    """Test finding matches for a video."""

    @pytest.fixture
    def index_with_videos(self, tmp_path):
        """Create index with multiple indexed videos."""
        db_path = tmp_path / "test.db"
        index = FingerprintIndex(db_path=str(db_path))

        # Create dummy videos
        video1 = tmp_path / "video1.mp4"
        video2 = tmp_path / "video2.mp4"
        video3 = tmp_path / "video3.mp4"

        video1.write_text("video1 content")
        video2.write_text("video2 content")
        video3.write_text("video3 content")

        # Mock algorithm with matching hashes
        algo1 = Mock()
        algo1.extract_fingerprints = Mock(return_value={
            100: [1000, 2000, 3000],  # Many shared with video2
            200: [1500, 2500],
            300: [500]
        })

        algo2 = Mock()
        algo2.extract_fingerprints = Mock(return_value={
            100: [1000, 2000, 3000],  # Same hash, same timestamps (duplicate)
            200: [1500, 2500],
            400: [800]  # Different hash
        })

        algo3 = Mock()
        algo3.extract_fingerprints = Mock(return_value={
            500: [1000],  # Completely different hashes
            600: [2000]
        })

        with patch('duplicateflow.algorithms.base.video_loader.get_video_duration', return_value=60.0):
            index.index_video(str(video1), algo1)
            index.index_video(str(video2), algo2)
            index.index_video(str(video3), algo3)

        return index, str(video1), str(video2), str(video3)

    def test_find_matches_exact_duplicate(self, index_with_videos):
        """Test finding exact duplicate (same hashes, same offsets)."""
        index, video1, video2, video3 = index_with_videos

        matches = index.find_matches(video1, min_votes=3, time_quant=20)

        # Should find video2 as match
        assert len(matches) >= 1

        # Best match should be video2
        best_match = matches[0]
        assert video2 in best_match.video2_path or video2 in best_match.video1_path

        # Should have high votes (5 matching fingerprints)
        assert best_match.votes >= 3

    def test_find_matches_no_match(self, index_with_videos):
        """Test finding matches when no videos match."""
        index, video1, video2, video3 = index_with_videos

        # video3 has completely different hashes, so should not match
        matches = index.find_matches(video3, min_votes=3, time_quant=20)

        # Should have no matches (or only very weak ones below threshold)
        assert len(matches) == 0

    def test_find_matches_min_votes_filter(self, index_with_videos):
        """Test that min_votes parameter filters weak matches."""
        index, video1, video2, video3 = index_with_videos

        # High min_votes should reduce matches
        matches_high = index.find_matches(video1, min_votes=1000, time_quant=20)

        # Low min_votes should allow more matches
        matches_low = index.find_matches(video1, min_votes=1, time_quant=20)

        # Should have fewer matches with higher threshold
        assert len(matches_high) <= len(matches_low)

    def test_find_matches_max_matches_limit(self, index_with_videos):
        """Test max_matches parameter limits results."""
        index, video1, video2, video3 = index_with_videos

        matches = index.find_matches(video1, min_votes=1, max_matches=1)

        # Should not exceed max_matches
        assert len(matches) <= 1

    def test_find_matches_video_not_indexed(self, index_with_videos, tmp_path):
        """Test finding matches for non-indexed video."""
        index, video1, video2, video3 = index_with_videos

        # Create new video not in index
        new_video = tmp_path / "new_video.mp4"
        new_video.touch()

        matches = index.find_matches(str(new_video), min_votes=1)

        # Should return empty list
        assert len(matches) == 0


class TestFingerprintIndexDatabase:
    """Test database operations."""

    @pytest.fixture
    def index(self, tmp_path):
        """Create index with temporary database."""
        db_path = tmp_path / "test.db"
        return FingerprintIndex(db_path=str(db_path))

    def test_get_stats_empty(self, index):
        """Test getting stats from empty index."""
        stats = index.get_stats()

        assert stats['video_count'] == 0
        assert stats['fingerprint_count'] == 0
        assert stats['unique_hashes'] == 0
        assert stats['avg_hashes_per_video'] == 0.0

    def test_get_stats_with_data(self, index, tmp_path):
        """Test getting stats with indexed videos."""
        # Create and index a video
        video = tmp_path / "video.mp4"
        video.write_text("content")

        algo = Mock()
        algo.extract_fingerprints = Mock(return_value={
            100: [1000, 2000],
            200: [1500]
        })

        with patch('duplicateflow.algorithms.base.video_loader.get_video_duration', return_value=60.0):
            index.index_video(str(video), algo)

        stats = index.get_stats()

        assert stats['video_count'] == 1
        assert stats['fingerprint_count'] == 3  # 2 + 1
        assert stats['unique_hashes'] == 2  # 100, 200
        assert stats['avg_hashes_per_video'] == 2.0

    def test_remove_video(self, index, tmp_path):
        """Test removing a video from index."""
        video = tmp_path / "video.mp4"
        video.write_text("content")

        algo = Mock()
        algo.extract_fingerprints = Mock(return_value={100: [1000]})

        with patch('duplicateflow.algorithms.base.video_loader.get_video_duration', return_value=60.0):
            index.index_video(str(video), algo)

        # Verify indexed
        stats_before = index.get_stats()
        assert stats_before['video_count'] == 1

        # Remove video
        index.remove_video(str(video))

        # Verify removed (video should be deleted)
        stats_after = index.get_stats()
        assert stats_after['video_count'] == 0
        # Note: fingerprints may or may not be cascade deleted depending on SQLite FK configuration
        # Just verify video is removed

    def test_clear_index(self, index, tmp_path):
        """Test clearing entire index."""
        # Create and index multiple videos
        for i in range(3):
            video = tmp_path / f"video{i}.mp4"
            video.write_text(f"content{i}")

            algo = Mock()
            algo.extract_fingerprints = Mock(return_value={100 + i: [1000]})

            with patch('duplicateflow.algorithms.base.video_loader.get_video_duration', return_value=60.0):
                index.index_video(str(video), algo)

        # Verify videos indexed
        stats_before = index.get_stats()
        assert stats_before['video_count'] == 3

        # Clear index
        index.clear_index()

        # Verify empty
        stats_after = index.get_stats()
        assert stats_after['video_count'] == 0
        assert stats_after['fingerprint_count'] == 0


class TestFingerprintIndexExport:
    """Test export functionality."""

    @pytest.fixture
    def matches(self):
        """Create sample matches."""
        return [
            Match(
                video1_id=1, video2_id=2,
                video1_path="/video1.mp4",
                video2_path="/video2.mp4",
                offset_seconds=10.5,
                votes=500,
                confidence=85.0,
                match_type="DUPLICATE"
            ),
            Match(
                video1_id=1, video2_id=3,
                video1_path="/video1.mp4",
                video2_path="/video3.mp4",
                offset_seconds=120.0,
                votes=300,
                confidence=65.0,
                match_type="SCENE"
            )
        ]

    def test_export_json(self, tmp_path, matches):
        """Test exporting matches to JSON."""
        index = FingerprintIndex(db_path=':memory:')

        output_file = tmp_path / "matches.json"
        index.export_matches(matches, str(output_file), format='json')

        # Verify file created
        assert output_file.exists()

        # Verify content
        import json
        with open(output_file, 'r') as f:
            data = json.load(f)

        assert len(data) == 2
        assert data[0]['video1'] == "/video1.mp4"
        assert data[0]['video2'] == "/video2.mp4"
        assert data[0]['votes'] == 500
        assert data[0]['confidence'] == 85.0
        assert data[0]['match_type'] == "DUPLICATE"

    def test_export_csv(self, tmp_path, matches):
        """Test exporting matches to CSV."""
        index = FingerprintIndex(db_path=':memory:')

        output_file = tmp_path / "matches.csv"
        index.export_matches(matches, str(output_file), format='csv')

        # Verify file created
        assert output_file.exists()

        # Verify content
        import csv
        with open(output_file, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)

        # Header + 2 data rows
        assert len(rows) == 3
        assert rows[0] == ['video1', 'video2', 'offset_seconds', 'votes', 'confidence', 'match_type']
        assert rows[1][0] == "/video1.mp4"
        assert rows[1][3] == "500"

    def test_export_empty_matches(self, tmp_path):
        """Test exporting empty matches list."""
        index = FingerprintIndex(db_path=':memory:')

        output_file = tmp_path / "empty.json"
        index.export_matches([], str(output_file), format='json')

        # Should create empty file
        assert output_file.exists()

        import json
        with open(output_file, 'r') as f:
            data = json.load(f)

        assert data == []
