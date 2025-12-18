"""
Fingerprint database index for scalable N-to-N video matching.

Builds an inverted index: hash -> list of (video_id, timestamp)
Allows finding matches across millions of videos without pairwise comparison.
"""

import logging
import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional, Set
from dataclasses import dataclass
from tqdm import tqdm
import time

logger = logging.getLogger('duplicateflow.processing.fingerprint_index')


@dataclass
class Match:
    """Represents a match between two videos."""
    video1_id: int
    video2_id: int
    video1_path: str
    video2_path: str
    offset_seconds: float
    votes: int
    confidence: float
    match_type: str  # "DUPLICATE", "SCENE", "EXTRACT", "UNCERTAIN"

    def format_offset(self) -> str:
        """
        Format offset as H:MM:SS.

        Returns:
            Formatted time string (e.g., "1:23:45")
        """
        abs_offset = abs(self.offset_seconds)
        hours = int(abs_offset // 3600)
        minutes = int((abs_offset % 3600) // 60)
        seconds = int(abs_offset % 60)

        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"

    @staticmethod
    def classify_match(confidence: float, offset_seconds: float) -> str:
        """
        Classify match type based on confidence and offset.

        Classification logic:
        - DUPLICATE: High confidence (≥80%) AND offset near 0 (±10s)
          → Same video or exact copy
        - SCENE: High confidence (≥60%) AND significant offset
          → Same scene/extract at different position
        - EXTRACT: Medium confidence (15-60%) AND any offset
          → Partial match, likely subsequence
        - UNCERTAIN: Low confidence (<15%)
          → Potentially false positive

        Args:
            confidence: Confidence percentage (0-100)
            offset_seconds: Time offset in seconds

        Returns:
            Match type string
        """
        abs_offset = abs(offset_seconds)

        if confidence >= 80.0 and abs_offset <= 10.0:
            return "DUPLICATE"
        elif confidence >= 60.0:
            return "SCENE"
        elif confidence >= 15.0:
            return "EXTRACT"
        else:
            return "UNCERTAIN"


class FingerprintIndex:
    """
    Inverted index for audio fingerprints enabling fast N-to-N matching.

    Instead of O(N²) pairwise comparisons, this builds an inverted index
    where each hash points to all videos containing it. Matching becomes
    a lookup operation.

    Architecture:
    - videos table: id, path, duration, hash_count, indexed_at
    - fingerprints table: video_id, hash, timestamp
    - Index on (hash, video_id) for fast lookups

    Workflow:
    1. Index all videos: extract fingerprints and insert into DB
    2. Find matches: for each video, query index for common hashes
    3. Vote counting: aggregate votes for offset estimation

    Example:
        >>> index = FingerprintIndex('fingerprints.db')
        >>> index.index_video('video1.mp4', algorithm)
        >>> index.index_video('video2.mp4', algorithm)
        >>> matches = index.find_matches('video1.mp4', min_votes=200)
        >>> # Or batch index entire directory
        >>> index.index_directory('/videos', algorithm, workers=8)
    """

    def __init__(self, db_path: str = None):
        """
        Initialize fingerprint index.

        Args:
            db_path: Path to SQLite database (default: ~/.duplicateflow/fingerprints.db)
        """
        if db_path is None:
            db_path = Path.home() / '.duplicateflow' / 'fingerprints.db'

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_database()

        logger.info(f"Initialized fingerprint index: {self.db_path}")

    def _compute_file_md5(self, file_path: str) -> str:
        """
        Compute MD5 hash of file for deduplication.

        Args:
            file_path: Path to file

        Returns:
            MD5 hex digest
        """
        import hashlib
        md5 = hashlib.md5()

        with open(file_path, 'rb') as f:
            # Read in chunks to handle large files
            for chunk in iter(lambda: f.read(8192), b''):
                md5.update(chunk)

        return md5.hexdigest()

    def _init_database(self):
        """Initialize database schema."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Videos table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                md5 TEXT,
                duration REAL,
                hash_count INTEGER,
                indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Index on MD5 for fast duplicate file detection
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_videos_md5
            ON videos(md5)
        """)

        # Fingerprints table (inverted index)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fingerprints (
                video_id INTEGER NOT NULL,
                hash INTEGER NOT NULL,
                timestamp INTEGER NOT NULL,
                FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
            )
        """)

        # Critical index for fast hash lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_fingerprints_hash_video
            ON fingerprints(hash, video_id)
        """)

        # Index for video lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_fingerprints_video
            ON fingerprints(video_id)
        """)

        conn.commit()
        conn.close()

    def index_video(
        self,
        video_path: str,
        algorithm: Any,
        force: bool = False
    ) -> int:
        """
        Index a video by extracting and storing its fingerprints.

        Args:
            video_path: Path to video file
            algorithm: AudioFingerprintAlgorithm instance
            force: Re-index even if already indexed

        Returns:
            Video ID in database
        """
        video_path = str(Path(video_path).resolve())

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Compute MD5 for duplicate detection
        logger.debug(f"Computing MD5 for {video_path}")
        try:
            md5_hash = self._compute_file_md5(video_path)
        except Exception as e:
            logger.error(f"Failed to compute MD5 for {video_path}: {e}")
            conn.close()
            raise

        # Check if file already indexed by MD5 (same file, possibly different path)
        cursor.execute("SELECT id, path FROM videos WHERE md5 = ?", (md5_hash,))
        md5_match = cursor.fetchone()

        if md5_match is not None and not force:
            existing_id, existing_path = md5_match
            if existing_path != video_path:
                logger.info(f"File already indexed at different path: {existing_path}")
                # Update path to new location
                cursor.execute("UPDATE videos SET path = ? WHERE id = ?", (video_path, existing_id))
                conn.commit()
            else:
                logger.debug(f"Video already indexed: {video_path} (id={existing_id})")
            conn.close()
            return existing_id

        # Check if path already indexed (but different file content)
        cursor.execute("SELECT id FROM videos WHERE path = ?", (video_path,))
        path_match = cursor.fetchone()

        if path_match is not None:
            # File at this path changed - re-index
            video_id = path_match[0]
            cursor.execute("DELETE FROM fingerprints WHERE video_id = ?", (video_id,))
            logger.info(f"File changed, re-indexing: {video_path}")
        else:
            video_id = None

        # Extract fingerprints
        logger.info(f"Extracting fingerprints: {video_path}")
        start = time.time()

        try:
            hashes = algorithm.extract_fingerprints(video_path)
        except Exception as e:
            logger.error(f"Failed to extract fingerprints from {video_path}: {e}")
            conn.close()
            raise

        extract_time = time.time() - start

        # Get duration
        try:
            from duplicateflow.algorithms.base.video_loader import get_video_duration
            duration = get_video_duration(video_path)
        except:
            duration = None

        # Insert or update video record
        if video_id is None:
            cursor.execute(
                "INSERT INTO videos (path, md5, duration, hash_count) VALUES (?, ?, ?, ?)",
                (video_path, md5_hash, duration, len(hashes))
            )
            video_id = cursor.lastrowid
        else:
            cursor.execute(
                "UPDATE videos SET md5 = ?, duration = ?, hash_count = ?, indexed_at = CURRENT_TIMESTAMP WHERE id = ?",
                (md5_hash, duration, len(hashes), video_id)
            )

        # Insert fingerprints (batch for performance)
        fingerprint_data = []
        for hash_val, timestamps in hashes.items():
            for ts in timestamps:
                fingerprint_data.append((video_id, hash_val, ts))

        cursor.executemany(
            "INSERT INTO fingerprints (video_id, hash, timestamp) VALUES (?, ?, ?)",
            fingerprint_data
        )

        conn.commit()
        conn.close()

        logger.info(
            f"Indexed {video_path}: {len(hashes)} unique hashes, "
            f"{len(fingerprint_data)} total fingerprints in {extract_time:.2f}s"
        )

        return video_id

    def index_directory(
        self,
        directory: str,
        algorithm: Any,
        pattern: str = "*",
        recursive: bool = True,
        workers: int = 4,
        force: bool = False
    ):
        """
        Index all videos in a directory with parallel processing.

        Args:
            directory: Directory path
            algorithm: AudioFingerprintAlgorithm instance
            pattern: File pattern (e.g., "*.mp4", "*" for all videos)
            recursive: Scan subdirectories recursively (default: True)
            workers: Number of parallel workers (default: 4)
            force: Re-index existing videos
        """
        directory = Path(directory)

        # Find all video files
        video_files = []
        video_extensions = ['mp4', 'mkv', 'avi', 'mov', 'webm', 'flv', 'wmv', 'm4v']

        if recursive:
            # Recursive search
            for ext in video_extensions:
                if pattern == '*':
                    video_files.extend(directory.glob(f"**/*.{ext}"))
                else:
                    video_files.extend(directory.glob(f"**/{pattern}.{ext}"))
        else:
            # Non-recursive search (only current directory)
            for ext in video_extensions:
                if pattern == '*':
                    video_files.extend(directory.glob(f"*.{ext}"))
                else:
                    video_files.extend(directory.glob(f"{pattern}.{ext}"))

        logger.info(f"Found {len(video_files)} videos in {directory} (recursive={recursive})")

        if workers > 1:
            # Parallel indexing
            from concurrent.futures import ThreadPoolExecutor, as_completed

            with ThreadPoolExecutor(max_workers=workers) as executor:
                # Submit all tasks
                future_to_video = {
                    executor.submit(self.index_video, str(video_path), algorithm, force): video_path
                    for video_path in video_files
                }

                # Progress bar
                for future in tqdm(as_completed(future_to_video), total=len(video_files), desc="Indexing videos"):
                    video_path = future_to_video[future]
                    try:
                        future.result()
                    except Exception as e:
                        logger.error(f"Failed to index {video_path}: {e}")
                        continue
        else:
            # Sequential indexing
            for video_path in tqdm(video_files, desc="Indexing videos"):
                try:
                    self.index_video(str(video_path), algorithm, force=force)
                except Exception as e:
                    logger.error(f"Failed to index {video_path}: {e}")
                    continue

    def find_matches(
        self,
        video_path: str,
        min_votes: int = 200,
        max_matches: int = 100,
        time_quant: int = 20
    ) -> List[Match]:
        """
        Find all matching videos in the index.

        Args:
            video_path: Path to query video
            min_votes: Minimum votes for a match
            max_matches: Maximum matches to return
            time_quant: Time quantization (from algorithm config)

        Returns:
            List of Match objects sorted by votes descending
        """
        video_path = str(Path(video_path).resolve())

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Get video ID
        cursor.execute("SELECT id FROM videos WHERE path = ?", (video_path,))
        row = cursor.fetchone()

        if row is None:
            logger.warning(f"Video not indexed: {video_path}")
            conn.close()
            return []

        video_id = row[0]

        logger.info(f"Finding matches for video_id={video_id}")

        # Get all hashes for this video
        cursor.execute(
            "SELECT hash, timestamp FROM fingerprints WHERE video_id = ?",
            (video_id,)
        )
        query_hashes = {}
        for hash_val, ts in cursor.fetchall():
            query_hashes.setdefault(hash_val, []).append(ts)

        logger.info(f"Query video has {len(query_hashes)} unique hashes")

        # Find matching videos by hash
        # For each hash, find all other videos that contain it
        candidate_videos: Set[int] = set()

        for hash_val in query_hashes.keys():
            cursor.execute(
                "SELECT DISTINCT video_id FROM fingerprints WHERE hash = ? AND video_id != ?",
                (hash_val, video_id)
            )
            for (other_video_id,) in cursor.fetchall():
                candidate_videos.add(other_video_id)

        logger.info(f"Found {len(candidate_videos)} candidate videos")

        if not candidate_videos:
            conn.close()
            return []

        # For each candidate, compute offset votes
        matches = []

        for other_video_id in tqdm(
            candidate_videos,
            desc="Computing matches",
            disable=len(candidate_videos) < 10
        ):
            # Get hashes for other video
            cursor.execute(
                "SELECT hash, timestamp FROM fingerprints WHERE video_id = ?",
                (other_video_id,)
            )
            other_hashes = {}
            for hash_val, ts in cursor.fetchall():
                other_hashes.setdefault(hash_val, []).append(ts)

            # Compute offset votes
            votes_dict = {}

            for hash_val, tlist1 in query_hashes.items():
                tlist2 = other_hashes.get(hash_val)
                if not tlist2:
                    continue

                # Limit combinations
                if len(tlist1) * len(tlist2) > 2000:
                    tlist1_s = tlist1[:min(len(tlist1), 50)]
                    tlist2_s = tlist2[:min(len(tlist2), 50)]
                else:
                    tlist1_s = tlist1
                    tlist2_s = tlist2

                for t1 in tlist1_s:
                    for t2 in tlist2_s:
                        offset = t2 - t1
                        votes_dict[offset] = votes_dict.get(offset, 0) + 1

            if not votes_dict:
                continue

            # Best offset
            best_offset, best_votes = max(votes_dict.items(), key=lambda x: x[1])

            if best_votes < min_votes:
                continue

            # Get video path
            cursor.execute("SELECT path FROM videos WHERE id = ?", (other_video_id,))
            other_path = cursor.fetchone()[0]

            # Compute confidence (normalized by smaller hash count)
            hash_count1 = len(query_hashes)
            hash_count2 = len(other_hashes)
            confidence = best_votes / min(hash_count1, hash_count2) * 100.0

            # Convert offset to seconds
            offset_seconds = (best_offset * time_quant) / 1000.0

            # Normalize: ensure offset is positive by swapping videos if needed
            if offset_seconds < 0:
                # Swap videos and invert offset
                final_video1_id = other_video_id
                final_video2_id = video_id
                final_video1_path = other_path
                final_video2_path = video_path
                final_offset = -offset_seconds
            else:
                final_video1_id = video_id
                final_video2_id = other_video_id
                final_video1_path = video_path
                final_video2_path = other_path
                final_offset = offset_seconds

            # Classify match type
            match_type = Match.classify_match(confidence, final_offset)

            matches.append(Match(
                video1_id=final_video1_id,
                video2_id=final_video2_id,
                video1_path=final_video1_path,
                video2_path=final_video2_path,
                offset_seconds=final_offset,
                votes=best_votes,
                confidence=confidence,
                match_type=match_type
            ))

        conn.close()

        # Sort by votes descending
        matches.sort(key=lambda m: m.votes, reverse=True)

        logger.info(f"Found {len(matches)} matches (>= {min_votes} votes)")

        return matches[:max_matches]

    def find_all_matches(
        self,
        min_votes: int = 200,
        max_pairs: int = 10000
    ) -> List[Match]:
        """
        Find all matching pairs in the entire database.

        This performs an all-to-all comparison using the index,
        but only returns pairs with sufficient votes.

        Args:
            min_votes: Minimum votes for a match
            max_pairs: Maximum pairs to return

        Returns:
            List of Match objects
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Get all videos
        cursor.execute("SELECT id, path FROM videos ORDER BY id")
        videos = cursor.fetchall()

        logger.info(f"Finding matches across {len(videos)} videos")

        all_matches = []
        seen_pairs = set()

        for video_id, video_path in tqdm(videos, desc="Processing videos"):
            matches = self.find_matches(
                video_path,
                min_votes=min_votes,
                max_matches=max_pairs
            )

            for match in matches:
                # Avoid duplicates (v1-v2 and v2-v1)
                pair = tuple(sorted([match.video1_id, match.video2_id]))
                if pair in seen_pairs:
                    continue

                seen_pairs.add(pair)
                all_matches.append(match)

                if len(all_matches) >= max_pairs:
                    logger.info(f"Reached max_pairs limit: {max_pairs}")
                    conn.close()
                    return all_matches

        conn.close()

        logger.info(f"Found {len(all_matches)} total matches")

        return all_matches

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Video count
        cursor.execute("SELECT COUNT(*) FROM videos")
        video_count = cursor.fetchone()[0]

        # Total fingerprints
        cursor.execute("SELECT COUNT(*) FROM fingerprints")
        fingerprint_count = cursor.fetchone()[0]

        # Unique hashes
        cursor.execute("SELECT COUNT(DISTINCT hash) FROM fingerprints")
        unique_hashes = cursor.fetchone()[0]

        # Average hashes per video
        cursor.execute("SELECT AVG(hash_count) FROM videos")
        avg_hashes = cursor.fetchone()[0] or 0

        # Database size
        db_size_mb = self.db_path.stat().st_size / (1024 * 1024)

        conn.close()

        return {
            'video_count': video_count,
            'fingerprint_count': fingerprint_count,
            'unique_hashes': unique_hashes,
            'avg_hashes_per_video': avg_hashes,
            'db_size_mb': db_size_mb,
            'db_path': str(self.db_path)
        }

    def remove_video(self, video_path: str):
        """Remove a video from the index."""
        video_path = str(Path(video_path).resolve())

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("DELETE FROM videos WHERE path = ?", (video_path,))
        deleted = cursor.rowcount

        conn.commit()
        conn.close()

        if deleted > 0:
            logger.info(f"Removed video from index: {video_path}")
        else:
            logger.warning(f"Video not found in index: {video_path}")

    def clear_index(self):
        """Clear all data from the index."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("DELETE FROM fingerprints")
        cursor.execute("DELETE FROM videos")

        conn.commit()
        conn.close()

        logger.info("Index cleared")

    def export_matches(
        self,
        matches: List[Match],
        output_file: str,
        format: str = 'json'
    ):
        """
        Export matches to file.

        Args:
            matches: List of Match objects
            output_file: Output file path
            format: 'json' or 'csv'
        """
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format == 'json':
            import json
            data = [
                {
                    'video1': m.video1_path,
                    'video2': m.video2_path,
                    'offset_seconds': m.offset_seconds,
                    'votes': m.votes,
                    'confidence': m.confidence,
                    'match_type': m.match_type
                }
                for m in matches
            ]

            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2)

        elif format == 'csv':
            import csv
            with open(output_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'video1', 'video2', 'offset_seconds', 'votes', 'confidence', 'match_type'
                ])
                for m in matches:
                    writer.writerow([
                        m.video1_path,
                        m.video2_path,
                        f"{m.offset_seconds:.3f}",
                        m.votes,
                        f"{m.confidence:.2f}",
                        m.match_type
                    ])

        logger.info(f"Exported {len(matches)} matches to {output_path}")
