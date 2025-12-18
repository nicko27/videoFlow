"""
Main CLI commands for DuplicateFlow.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Optional

import click

import duplicateflow.algorithms
from duplicateflow import __version__
from duplicateflow.core import list_algorithms as get_all_algorithms, get_algorithm
from duplicateflow.pipeline import Pipeline, list_presets as get_all_presets, get_preset
from duplicateflow.storage import StorageManager


@click.group()
@click.version_option(version=__version__, prog_name="duplicateflow")
@click.option('--verbose', '-v', count=True, help='Increase verbosity (can be repeated: -v, -vv, -vvv)')
@click.option('--quiet', '-q', is_flag=True, help='Suppress all output except errors')
def cli(verbose, quiet):
    """
    DuplicateFlow - Video Subsequence Detection Tool

    Detect video subsequences (20min-1h) in longer videos using 13 free algorithms.
    """
    # Configure logging
    if quiet:
        log_level = logging.ERROR
    elif verbose >= 3:
        log_level = logging.DEBUG
    elif verbose == 2:
        log_level = logging.INFO
    elif verbose == 1:
        log_level = logging.WARNING
    else:
        log_level = logging.ERROR

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


@cli.command()
@click.argument('input_dir', type=click.Path(exists=True))
@click.option('--algorithm', '-a', default='audio_fingerprint', help='Algorithm to use (default: audio_fingerprint)')
@click.option('--db', type=click.Path(), default=None, help='Database path (default: ~/.duplicateflow/fingerprints.db)')
@click.option('--recursive/--no-recursive', '-r', default=True, help='Scan subdirectories recursively (default: enabled)')
@click.option('--pattern', default='*', help='File pattern to match (default: all video files)')
@click.option('--force', is_flag=True, help='Re-index existing videos')
@click.option('--workers', '-w', default=4, help='Number of parallel workers (default: 4)')
def index(input_dir, algorithm, db, pattern, recursive, force, workers):
    """
    Index videos for fast N-to-N matching using audio fingerprints.

    This builds a searchable database of audio fingerprints that enables
    finding matches across millions of videos without pairwise comparison.

    Example:
        duplicateflow index /videos --algorithm audio_fingerprint
    """
    from duplicateflow.processing.fingerprint_index import FingerprintIndex

    # Get algorithm
    AlgoClass = get_algorithm(algorithm)
    algo = AlgoClass()
    algo.configure()

    # Initialize index
    index_obj = FingerprintIndex(db_path=db)

    # Index directory
    click.echo(f"Indexing videos in {input_dir}...")
    click.echo(f"Recursive: {recursive}, Workers: {workers}, Pattern: {pattern}")
    index_obj.index_directory(
        directory=input_dir,
        algorithm=algo,
        pattern=pattern,
        recursive=recursive,
        workers=workers,
        force=force
    )

    # Show stats
    stats = index_obj.get_stats()
    click.echo("\nIndex statistics:")
    click.echo(f"  Videos: {stats['video_count']}")
    click.echo(f"  Fingerprints: {stats['fingerprint_count']:,}")
    click.echo(f"  Unique hashes: {stats['unique_hashes']:,}")
    click.echo(f"  Avg hashes/video: {stats['avg_hashes_per_video']:.0f}")
    click.echo(f"  Database size: {stats['db_size_mb']:.2f} MB")
    click.echo(f"  Database: {stats['db_path']}")


@cli.command()
@click.option('--db', type=click.Path(), default=None, help='Database path (default: ~/.duplicateflow/fingerprints.db)')
def stats(db):
    """Show fingerprint index statistics."""
    from duplicateflow.processing.fingerprint_index import FingerprintIndex

    if db is None:
        db = Path.home() / '.duplicateflow' / 'fingerprints.db'

    index_obj = FingerprintIndex(db_path=str(db))
    stats_data = index_obj.get_stats()

    click.echo("\n" + "=" * 70)
    click.echo("  FINGERPRINT INDEX STATISTICS")
    click.echo("=" * 70)
    click.echo(f"\nDatabase: {stats_data['db_path']}")
    click.echo(f"Database size: {stats_data['db_size_mb']:.2f} MB")
    click.echo(f"\nVideos indexed: {stats_data['video_count']}")
    click.echo(f"Total fingerprints: {stats_data['fingerprint_count']:,}")
    click.echo(f"Unique hashes: {stats_data['unique_hashes']:,}")
    click.echo(f"Avg hashes per video: {stats_data['avg_hashes_per_video']:.0f}")
    click.echo()


@cli.command()
@click.option('--db', type=click.Path(), default=None, help='Database path (default: ~/.duplicateflow/fingerprints.db)')
@click.confirmation_option(prompt='Are you sure you want to clear the entire index?')
def clear(db):
    """Clear all data from the fingerprint index."""
    from duplicateflow.processing.fingerprint_index import FingerprintIndex

    if db is None:
        db = Path.home() / '.duplicateflow' / 'fingerprints.db'

    index_obj = FingerprintIndex(db_path=str(db))
    index_obj.clear_index()

    click.echo("✓ Index cleared successfully")
    click.echo(f"  Database: {db}")


# Helper functions for find_duplicates
def _find_duplicates_fingerprint(input_dir, db, algorithm, recursive, workers,
                                 min_votes, min_confidence, max_pairs, use_lsh, lsh_threshold):
    """Find duplicates using audio fingerprinting (original mode)."""
    from duplicateflow.processing.fingerprint_index import FingerprintIndex
    import sqlite3
    from tqdm import tqdm

    # Default DB path in user directory (shared across all scans)
    if db is None:
        db = Path.home() / '.duplicateflow' / 'fingerprints.db'

    click.echo(f"Database:   {db}\n")

    # Initialize index
    index_obj = FingerprintIndex(db_path=str(db))

    # Get algorithm
    AlgoClass = get_algorithm(algorithm)
    algo = AlgoClass()
    algo.configure()

    # Always index directory (will skip already-indexed files via MD5)
    click.echo("=" * 70)
    click.echo("STEP 1/3: Indexing new videos")
    click.echo("=" * 70)
    click.echo()

    stats_before = index_obj.get_stats()

    # Index directory (automatically skips indexed files)
    index_obj.index_directory(
        directory=input_dir,
        algorithm=algo,
        recursive=recursive,
        workers=workers,
        force=False  # Always False now (MD5 handles deduplication)
    )

    # Show updated stats
    stats_after = index_obj.get_stats()
    new_videos = stats_after['video_count'] - stats_before['video_count']

    click.echo()
    if new_videos > 0:
        click.echo(f"✓ Indexed {new_videos} new video(s)")
        click.echo(f"  • Total videos:       {stats_after['video_count']}")
        click.echo(f"  • Total fingerprints: {stats_after['fingerprint_count']:,}")
        click.echo(f"  • Unique hashes:      {stats_after['unique_hashes']:,}")
        click.echo(f"  • Database size:      {stats_after['db_size_mb']:.2f} MB")
    else:
        click.echo(f"✓ All videos already indexed ({stats_after['video_count']} total)")
    click.echo()

    # Decide whether to use LSH
    enable_lsh = use_lsh and stats_after['video_count'] >= lsh_threshold

    # Find matches
    click.echo("=" * 70)
    click.echo("STEP 2/3: Finding matching pairs")
    if enable_lsh:
        click.echo("(Using LSH acceleration)")
    click.echo("=" * 70)
    click.echo()

    if enable_lsh:
        # Use LSH-accelerated matching
        from duplicateflow.processing.lsh_index import LSHFingerprintIndex
        lsh_index = LSHFingerprintIndex(index_obj, num_perm=128, num_bands=16)

        # Find all matches using LSH
        all_matches = []
        conn = sqlite3.connect(str(index_obj.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT id, path FROM videos")
        videos = cursor.fetchall()
        conn.close()

        for video_id, video_path in tqdm(videos, desc="Processing videos"):
            matches_for_video = lsh_index.find_matches_fast(
                video_path,
                min_votes=min_votes,
                max_matches=max_pairs
            )
            all_matches.extend(matches_for_video)

        # Remove duplicates
        seen_pairs = set()
        unique_matches = []
        for m in all_matches:
            pair = tuple(sorted([m.video1_id, m.video2_id]))
            if pair not in seen_pairs:
                seen_pairs.add(pair)
                unique_matches.append(m)

        matches = unique_matches
    else:
        # Standard matching
        matches = index_obj.find_all_matches(
            min_votes=min_votes,
            max_pairs=max_pairs
        )

    # Filter by confidence to remove false positives
    matches = [m for m in matches if m.confidence >= min_confidence]

    return matches


def _find_duplicates_algorithm(input_dir, algorithm, recursive, threshold,
                               min_confidence, max_pairs, workers, use_cache):
    """Find duplicates using a single algorithm (pairwise N-to-N)."""
    from glob import glob
    from tqdm import tqdm
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from dataclasses import dataclass

    @dataclass
    class PairwiseMatch:
        video1_path: str
        video2_path: str
        similarity: float
        confidence: float
        match_type: str
        metadata: dict

        def format_offset(self):
            return "N/A"  # No offset for non-fingerprint algorithms

        @property
        def votes(self):
            return 0  # No votes for non-fingerprint algorithms

    # Collect all videos
    click.echo("=" * 70)
    click.echo("STEP 1/3: Collecting videos")
    click.echo("=" * 70)
    click.echo()

    if recursive:
        pattern = str(Path(input_dir) / "**" / "*")
    else:
        pattern = str(Path(input_dir) / "*")

    extensions = ('.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.wmv', '.m4v')
    all_files = glob(pattern, recursive=recursive)
    videos = [f for f in all_files if f.lower().endswith(extensions)]

    click.echo(f"✓ Found {len(videos)} video(s)")
    click.echo()

    if len(videos) < 2:
        click.echo("Error: Need at least 2 videos to compare", err=True)
        return []

    # Get algorithm
    AlgoClass = get_algorithm(algorithm)
    algo = AlgoClass()

    # Configure algorithm with threshold if provided
    if threshold is not None:
        algo.configure(threshold=threshold)
    else:
        algo.configure()

    # Use storage for caching if enabled
    storage = StorageManager() if use_cache else None

    # Find all pairs to compare
    click.echo("=" * 70)
    click.echo("STEP 2/3: Comparing all pairs")
    click.echo("=" * 70)
    click.echo()

    total_pairs = len(videos) * (len(videos) - 1) // 2
    click.echo(f"Total comparisons: {total_pairs}")
    click.echo()

    matches = []

    def compare_pair(i, j):
        """Compare a single pair of videos."""
        video1 = videos[i]
        video2 = videos[j]

        try:
            # Check cache first
            result = None
            if storage and use_cache:
                config = algo.get_config()
                result = storage.get_cached_result(video1, video2, algorithm, config)

            # Run comparison if not cached
            if result is None:
                result = algo.compare(video1, video2)

                # Cache result
                if storage and use_cache:
                    config = algo.get_config()
                    storage.store_result(video1, video2, algorithm, config, result)

            # Convert similarity to 0-100 scale if needed
            similarity = result['similarity']
            if similarity <= 1.0:
                similarity = similarity * 100.0

            # Classify match type based on similarity
            if similarity >= 80.0:
                match_type = "DUPLICATE"
            elif similarity >= 60.0:
                match_type = "SCENE"
            elif similarity >= 15.0:
                match_type = "EXTRACT"
            else:
                match_type = "UNCERTAIN"

            return PairwiseMatch(
                video1_path=video1,
                video2_path=video2,
                similarity=similarity,
                confidence=similarity,  # Use similarity as confidence
                match_type=match_type,
                metadata=result.get('metadata', {})
            )
        except Exception as e:
            click.echo(f"Error comparing {Path(video1).name} vs {Path(video2).name}: {e}", err=True)
            return None

    # Parallel execution
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = []
        for i in range(len(videos)):
            for j in range(i + 1, len(videos)):
                futures.append(executor.submit(compare_pair, i, j))

        # Collect results with progress bar
        for future in tqdm(as_completed(futures), total=total_pairs, desc="Comparing pairs"):
            match = future.result()
            if match and match.confidence >= min_confidence:
                matches.append(match)

    # Sort by confidence
    matches.sort(key=lambda m: m.confidence, reverse=True)

    # Limit to max_pairs
    matches = matches[:max_pairs]

    return matches


def _find_duplicates_pipeline(input_dir, pipeline_name, recursive, threshold,
                              min_confidence, max_pairs, workers, use_cache):
    """Find duplicates using a pipeline (pairwise N-to-N with weighted scoring)."""
    from glob import glob
    from tqdm import tqdm
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from dataclasses import dataclass

    @dataclass
    class PairwiseMatch:
        video1_path: str
        video2_path: str
        similarity: float
        confidence: float
        match_type: str
        metadata: dict

        def format_offset(self):
            return "N/A"

        @property
        def votes(self):
            return 0

    # Collect all videos
    click.echo("=" * 70)
    click.echo("STEP 1/3: Collecting videos")
    click.echo("=" * 70)
    click.echo()

    if recursive:
        pattern = str(Path(input_dir) / "**" / "*")
    else:
        pattern = str(Path(input_dir) / "*")

    extensions = ('.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.wmv', '.m4v')
    all_files = glob(pattern, recursive=recursive)
    videos = [f for f in all_files if f.lower().endswith(extensions)]

    click.echo(f"✓ Found {len(videos)} video(s)")
    click.echo()

    if len(videos) < 2:
        click.echo("Error: Need at least 2 videos to compare", err=True)
        return []

    # Create pipeline
    pipeline = Pipeline.from_preset(pipeline_name, storage=StorageManager() if use_cache else None)

    # Override global threshold if provided
    if threshold is not None:
        pipeline.global_threshold = threshold

    # Find all pairs to compare
    click.echo("=" * 70)
    click.echo("STEP 2/3: Comparing all pairs")
    click.echo("=" * 70)
    click.echo()

    total_pairs = len(videos) * (len(videos) - 1) // 2
    click.echo(f"Total comparisons: {total_pairs}")
    click.echo(f"Pipeline: {pipeline_name}")
    click.echo()

    matches = []

    def compare_pair(i, j):
        """Compare a single pair of videos."""
        video1 = videos[i]
        video2 = videos[j]

        try:
            result = pipeline.compare(video1, video2, use_cache=use_cache)

            similarity = result['global_score']

            # Classify match type
            if similarity >= 80.0:
                match_type = "DUPLICATE"
            elif similarity >= 60.0:
                match_type = "SCENE"
            elif similarity >= 15.0:
                match_type = "EXTRACT"
            else:
                match_type = "UNCERTAIN"

            return PairwiseMatch(
                video1_path=video1,
                video2_path=video2,
                similarity=similarity,
                confidence=similarity,
                match_type=match_type,
                metadata=result.get('metadata', {})
            )
        except Exception as e:
            click.echo(f"Error comparing {Path(video1).name} vs {Path(video2).name}: {e}", err=True)
            return None

    # Parallel execution
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = []
        for i in range(len(videos)):
            for j in range(i + 1, len(videos)):
                futures.append(executor.submit(compare_pair, i, j))

        # Collect results with progress bar
        for future in tqdm(as_completed(futures), total=total_pairs, desc="Comparing pairs"):
            match = future.result()
            if match and match.confidence >= min_confidence:
                matches.append(match)

    # Sort by confidence
    matches.sort(key=lambda m: m.confidence, reverse=True)

    # Limit to max_pairs
    matches = matches[:max_pairs]

    return matches


def _export_pairwise_matches(matches, output_path, format='json'):
    """Export pairwise matches to JSON or CSV."""
    import csv

    output_path = Path(output_path)

    if format == 'json':
        # Export as JSON
        export_data = []
        for m in matches:
            export_data.append({
                'video1': str(m.video1_path),
                'video2': str(m.video2_path),
                'confidence': round(m.confidence, 2),
                'match_type': m.match_type,
                'metadata': m.metadata
            })

        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)

    elif format == 'csv':
        # Export as CSV
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['video1', 'video2', 'confidence', 'match_type'])

            for m in matches:
                writer.writerow([
                    str(m.video1_path),
                    str(m.video2_path),
                    round(m.confidence, 2),
                    m.match_type
                ])


@cli.command()
@click.argument('input_dir', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), default=None, help='Output file (JSON or CSV, optional)')
@click.option('--db', type=click.Path(), default=None, help='Database path (only for audio_fingerprint, default: ~/.duplicateflow/fingerprints.db)')
@click.option('--algorithm', '-a', default=None, help='Single algorithm to use (default: audio_fingerprint). Mutually exclusive with --pipeline')
@click.option('--pipeline', '-p', default=None, help='Pipeline preset to use (fast/balanced/thorough/multimodal/structural/hybrid). Mutually exclusive with --algorithm')
@click.option('--recursive/--no-recursive', '-r', default=True, help='Scan subdirectories recursively (default: enabled)')
@click.option('--workers', '-w', default=4, help='Number of parallel workers (default: 4)')
@click.option('--threshold', '-t', default=None, type=float, help='Detection threshold (algorithm-specific, overrides default)')
@click.option('--min-votes', default=200, help='Minimum votes for audio_fingerprint (ignored for other algorithms)')
@click.option('--min-confidence', default=15.0, help='Minimum confidence %% for a valid match (filters false positives)')
@click.option('--max-pairs', default=10000, help='Maximum pairs to return')
@click.option('--format', type=click.Choice(['json', 'csv']), default='json', help='Output format')
@click.option('--use-lsh/--no-lsh', default=True, help='Use LSH for audio_fingerprint (auto-enabled for >100 videos, ignored for other algorithms)')
@click.option('--lsh-threshold', default=100, help='Activate LSH when video count >= this threshold (audio_fingerprint only)')
@click.option('--show-all', is_flag=True, help='Show all matches (not just top 10)')
@click.option('--cache/--no-cache', default=True, help='Use caching for pipeline/algorithm results (default: enabled)')
def find_duplicates(input_dir, output, db, algorithm, pipeline, recursive, workers, threshold, min_votes, min_confidence, max_pairs, format, use_lsh, lsh_threshold, show_all, cache):
    """
    Find all duplicate videos in a directory (one command does everything).

    This command supports three modes:

    1. AUDIO FINGERPRINTING (default, scalable to millions):
       duplicateflow find-duplicates ~/Videos

    2. SINGLE ALGORITHM (pairwise N-to-N):
       duplicateflow find-duplicates ~/Videos --algorithm frame_hash

    3. PIPELINE (multi-algorithm weighted scoring):
       duplicateflow find-duplicates ~/Videos --pipeline balanced

    Examples:
        # Audio fingerprinting (default, fastest for N-to-N)
        duplicateflow find-duplicates ~/Videos

        # Single algorithm
        duplicateflow find-duplicates ~/Videos --algorithm color_histogram --threshold 75

        # Pipeline preset
        duplicateflow find-duplicates ~/Videos --pipeline thorough

        # Export results
        duplicateflow find-duplicates ~/Videos -o matches.json --show-all
    """
    # Validate mutually exclusive options
    if algorithm and pipeline:
        click.echo("Error: --algorithm and --pipeline are mutually exclusive", err=True)
        sys.exit(1)

    # Determine mode
    if pipeline:
        mode = 'pipeline'
    elif algorithm and algorithm != 'audio_fingerprint':
        mode = 'algorithm'
    else:
        mode = 'fingerprint'
        algorithm = 'audio_fingerprint'  # Default

    # Header
    click.echo("\n" + "=" * 70)
    if mode == 'fingerprint':
        click.echo("  DUPLICATEFLOW - Audio Fingerprint N-to-N Detection")
    elif mode == 'algorithm':
        click.echo(f"  DUPLICATEFLOW - {algorithm} N-to-N Detection")
    else:
        click.echo(f"  DUPLICATEFLOW - Pipeline '{pipeline}' N-to-N Detection")
    click.echo("=" * 70)
    click.echo(f"\nProcessing: {input_dir}")
    if output:
        click.echo(f"Output:     {output}")
    click.echo()

    # Mode-specific processing
    if mode == 'fingerprint':
        matches = _find_duplicates_fingerprint(
            input_dir, db, algorithm, recursive, workers, min_votes,
            min_confidence, max_pairs, use_lsh, lsh_threshold
        )
    elif mode == 'algorithm':
        matches = _find_duplicates_algorithm(
            input_dir, algorithm, recursive, threshold, min_confidence,
            max_pairs, workers, cache
        )
    else:  # pipeline
        matches = _find_duplicates_pipeline(
            input_dir, pipeline, recursive, threshold, min_confidence,
            max_pairs, workers, cache
        )

    if not matches:
        click.echo(f"✗ No matches found with min_confidence={min_confidence}%")
        click.echo("   Try lowering --min-confidence")
        click.echo()
        return

    click.echo(f"✓ Found {len(matches)} matching pairs (after filtering)!")
    click.echo()

    # Display all matches on screen
    click.echo("=" * 70)
    click.echo("STEP 3/3: Results")
    click.echo("=" * 70)
    click.echo()

    display_count = len(matches) if show_all else min(10, len(matches))

    for i, match in enumerate(matches[:display_count], 1):
        v1_name = Path(match.video1_path).name
        v2_name = Path(match.video2_path).name

        # Visual indicators based on match type
        if match.match_type == "DUPLICATE":
            type_icon = "🔁"  # Duplicate (high confidence, offset ≈ 0)
            confidence_marker = "✓✓✓"
        elif match.match_type == "SCENE":
            type_icon = "🎬"  # Scene (high confidence, significant offset)
            confidence_marker = "✓✓ "
        elif match.match_type == "EXTRACT":
            type_icon = "✂️ "  # Extract (medium confidence)
            confidence_marker = "✓  "
        else:  # UNCERTAIN
            type_icon = "❓"  # Uncertain (low confidence)
            confidence_marker = "?  "

        click.echo(f"{i:3d}. {type_icon} {confidence_marker} {match.match_type} (confidence: {match.confidence:.1f}%)")
        click.echo(f"     Video 1: {v1_name}")

        # Show offset for fingerprint mode, otherwise just show video 2
        if mode == 'fingerprint':
            click.echo(f"     Video 2: {v2_name} (starts at {match.format_offset()} in video 1)")
            click.echo(f"     Votes: {match.votes}")
        else:
            click.echo(f"     Video 2: {v2_name}")
        click.echo()

    if len(matches) > display_count:
        click.echo(f"... and {len(matches) - display_count} more matches")
        click.echo(f"    (use --show-all to display all matches)")
        click.echo()

    # Export to file if requested
    if output:
        click.echo("-" * 70)
        if mode == 'fingerprint':
            # Use fingerprint index export
            from duplicateflow.processing.fingerprint_index import FingerprintIndex
            if db is None:
                db = Path.home() / '.duplicateflow' / 'fingerprints.db'
            index_obj = FingerprintIndex(db_path=str(db))
            index_obj.export_matches(matches, output, format=format)
        else:
            # Export for algorithm/pipeline mode
            _export_pairwise_matches(matches, output, format)

        click.echo(f"✓ Results exported to: {output}")
        click.echo()

    # Summary
    click.echo("=" * 70)
    click.echo("SUMMARY")
    click.echo("=" * 70)

    # Count videos
    if mode == 'fingerprint':
        video_count = len(set(m.video1_path for m in matches) | set(m.video2_path for m in matches))
    else:
        video_count = len(set(m.video1_path for m in matches) | set(m.video2_path for m in matches))

    click.echo(f"Total videos processed: {video_count}")
    click.echo(f"Matching pairs found:   {len(matches)}")
    click.echo()
    click.echo("By Match Type:")
    click.echo(f"  🔁 DUPLICATE (exact copies):     {sum(1 for m in matches if m.match_type == 'DUPLICATE')}")
    click.echo(f"  🎬 SCENE (same scene/extract):   {sum(1 for m in matches if m.match_type == 'SCENE')}")
    click.echo(f"  ✂️  EXTRACT (partial match):      {sum(1 for m in matches if m.match_type == 'EXTRACT')}")
    click.echo(f"  ❓ UNCERTAIN (low confidence):   {sum(1 for m in matches if m.match_type == 'UNCERTAIN')}")
    click.echo()
    click.echo("By Confidence:")
    click.echo(f"  High confidence (≥80%):   {sum(1 for m in matches if m.confidence >= 80)}")
    click.echo(f"  Medium confidence (≥60%): {sum(1 for m in matches if 60 <= m.confidence < 80)}")
    click.echo(f"  Low confidence (<60%):    {sum(1 for m in matches if m.confidence < 60)}")
    click.echo()
    click.echo("✓ Done!")
    click.echo()


@cli.command()
@click.argument('short_video', type=click.Path(exists=True))
@click.argument('long_video', type=click.Path(exists=True))
@click.option('--preset', '-p', type=str, default='balanced',
              help='Pipeline preset to use (default: balanced)')
@click.option('--algorithm', '-a', type=str, default=None,
              help='Single algorithm to use (overrides preset)')
@click.option('--threshold', '-t', type=float, default=None,
              help='Detection threshold (0-100 for most, 0-1 for ssim)')
@click.option('--output', '-o', type=click.Choice(['text', 'json']), default='text',
              help='Output format')
@click.option('--cache/--no-cache', default=True,
              help='Use result caching (default: enabled)')
@click.option('--progress/--no-progress', default=True,
              help='Show progress bar (default: enabled)')
def compare(short_video, long_video, preset, algorithm, threshold, output, cache, progress):
    """
    Compare two videos to detect if short video is in long video.
    
    Examples:
        duplicateflow compare short.mp4 long.mp4
        duplicateflow compare short.mp4 long.mp4 --preset thorough
        duplicateflow compare short.mp4 long.mp4 --algorithm frame_hash --threshold 85
    """
    try:
        # Single algorithm mode
        if algorithm:
            AlgoClass = get_algorithm(algorithm)
            algo = AlgoClass()
            
            # Configure with threshold if provided
            config = {}
            if threshold is not None:
                config['threshold'] = threshold
            algo.configure(**config)
            
            # Run comparison
            result = algo.compare(
                short_video=short_video,
                long_video=long_video
            )
            
            # Format output
            if output == 'json':
                click.echo(json.dumps(result, indent=2))
            else:
                similarity = result['similarity']
                if similarity <= 1.0:
                    similarity *= 100
                    
                click.echo(f"Algorithm: {algorithm}")
                click.echo(f"Similarity: {similarity:.2f}%")
                click.echo(f"Accepted: {'Yes' if result['accepted'] else 'No'}")
                
                if 'best_offset_seconds' in result.get('metadata', {}):
                    offset = result['metadata']['best_offset_seconds']
                    click.echo(f"Best match at: {offset:.1f}s")
        
        # Pipeline mode
        else:
            pipeline = Pipeline.from_preset(preset, show_progress=progress)

            # Override global threshold if provided
            if threshold is not None:
                pipeline.global_threshold = threshold

            # Run pipeline
            result = pipeline.compare(
                short_video=short_video,
                long_video=long_video,
                use_cache=cache
            )
            
            # Format output
            if output == 'json':
                click.echo(json.dumps(result, indent=2))
            else:
                click.echo(f"Preset: {preset}")
                click.echo(f"Global Score: {result['global_score']:.2f}%")
                click.echo(f"Accepted: {'Yes' if result['accepted'] else 'No'}")
                click.echo(f"Algorithms used: {result['metadata']['algorithms_run']}/{result['metadata']['total_algorithms']}")
                
                if result['metadata'].get('early_exit'):
                    click.echo("Early termination: Yes")
                
                click.echo("\nIndividual Results:")
                for algo_result in result['individual_results']:
                    click.echo(f"  - {algo_result['algorithm']}: {algo_result['similarity']:.2f}% (weight={algo_result['weight']:.2f})")
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command('list-algorithms')
@click.option('--category', '-c', type=str, default=None,
              help='Filter by category')
@click.option('--speed', '-s', type=str, default=None,
              help='Filter by speed (fast/medium/slow)')
@click.option('--output', '-o', type=click.Choice(['text', 'json']), default='text',
              help='Output format')
def list_algorithms(category, speed, output):
    """
    List all available algorithms.
    
    Examples:
        duplicateflow list-algorithms
        duplicateflow list-algorithms --category statistical
        duplicateflow list-algorithms --speed fast
    """
    algos = get_all_algorithms()
    
    # Apply filters
    if category:
        algos = [a for a in algos if a.get('category') == category]
    if speed:
        algos = [a for a in algos if a.get('speed') == speed]
    
    if output == 'json':
        click.echo(json.dumps(algos, indent=2))
    else:
        click.echo(f"Total algorithms: {len(algos)}\n")
        
        for algo in algos:
            click.echo(f"{algo['display_name']}")
            click.echo(f"  Name: {algo['name']}")
            click.echo(f"  Category: {algo['category']}")
            click.echo(f"  Speed: {algo['speed']}")
            click.echo(f"  Threshold: {algo['default_threshold']}")
            click.echo(f"  Use case: {algo['use_case']}")
            click.echo()


@cli.command('list-presets')
@click.option('--output', '-o', type=click.Choice(['text', 'json']), default='text',
              help='Output format')
def list_presets(output):
    """
    List all available pipeline presets.

    Examples:
        duplicateflow list-presets
        duplicateflow list-presets --output json
    """
    presets = get_all_presets()

    if output == 'json':
        preset_data = {}
        for preset_name in presets:
            config = get_preset(preset_name)
            preset_data[preset_name] = {
                'algorithms': [s['algorithm'] for s in config['steps']],
                'num_algorithms': len(config['steps']),
                'global_threshold': config['global_threshold'],
                'early_termination': config['early_termination']
            }
        click.echo(json.dumps(preset_data, indent=2))
    else:
        click.echo(f"Available presets: {len(presets)}\n")

        for preset_name in presets:
            config = get_preset(preset_name)
            click.echo(f"{preset_name}")
            click.echo(f"  Algorithms: {len(config['steps'])}")
            click.echo(f"  Threshold: {config['global_threshold']}")
            click.echo(f"  Early termination: {'Yes' if config['early_termination'] else 'No'}")
            click.echo(f"  Pipeline: {', '.join([s['algorithm'] for s in config['steps']])}")
            click.echo()


@cli.group()
def pipeline():
    """Pipeline management commands."""
    pass


@pipeline.command('list')
@click.option('--output', '-o', type=click.Choice(['text', 'json']), default='text',
              help='Output format')
def pipeline_list(output):
    """
    List all available pipeline presets.

    This is an alias for 'list-presets' command.

    Examples:
        duplicateflow pipeline list
        duplicateflow pipeline list --output json
    """
    presets = get_all_presets()

    if output == 'json':
        preset_data = {}
        for preset_name in presets:
            config = get_preset(preset_name)
            preset_data[preset_name] = {
                'algorithms': [s['algorithm'] for s in config['steps']],
                'num_algorithms': len(config['steps']),
                'global_threshold': config['global_threshold'],
                'early_termination': config['early_termination'],
                'steps': config['steps']
            }
        click.echo(json.dumps(preset_data, indent=2))
    else:
        click.echo("\n" + "=" * 70)
        click.echo("  AVAILABLE PIPELINE PRESETS")
        click.echo("=" * 70)
        click.echo(f"\nTotal presets: {len(presets)}\n")

        for preset_name in presets:
            config = get_preset(preset_name)
            click.echo(f"📋 {preset_name}")
            click.echo(f"   Algorithms: {len(config['steps'])}")
            click.echo(f"   Threshold: {config['global_threshold']}")
            click.echo(f"   Early termination: {'Yes' if config['early_termination'] else 'No'}")
            click.echo(f"   Pipeline: {', '.join([s['algorithm'] for s in config['steps']])}")
            click.echo()


@pipeline.command('show')
@click.argument('preset_name', type=str)
@click.option('--output', '-o', type=click.Choice(['text', 'json']), default='text',
              help='Output format')
def pipeline_show(preset_name, output):
    """
    Show details of a specific pipeline preset.

    Examples:
        duplicateflow pipeline show balanced
        duplicateflow pipeline show thorough --output json
    """
    try:
        config = get_preset(preset_name)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if output == 'json':
        click.echo(json.dumps(config, indent=2))
    else:
        click.echo("\n" + "=" * 70)
        click.echo(f"  PIPELINE PRESET: {preset_name}")
        click.echo("=" * 70)
        click.echo(f"\nGlobal threshold: {config['global_threshold']}")
        click.echo(f"Early termination: {'Enabled' if config['early_termination'] else 'Disabled'}")
        click.echo(f"\nAlgorithms ({len(config['steps'])} total):\n")

        for i, step in enumerate(config['steps'], 1):
            click.echo(f"  {i}. {step['algorithm']}")
            click.echo(f"     Threshold: {step.get('threshold', 'default')}")
            click.echo(f"     Weight: {step.get('weight', 1.0)}")
            if 'params' in step:
                click.echo(f"     Params: {step['params']}")
            click.echo()


@cli.command()
@click.argument('video_path', type=click.Path(exists=True))
@click.option('--method', '-m', type=click.Choice(['full', 'fast']), default='fast',
              help='Hash method (default: fast)')
def hash(video_path, method):
    """
    Compute MD5 hash of a video file.
    
    Examples:
        duplicateflow hash video.mp4
        duplicateflow hash video.mp4 --method full
    """
    try:
        storage = StorageManager()
        file_hash = storage.get_file_hash(video_path, method=method)
        
        click.echo(f"File: {video_path}")
        click.echo(f"Method: {method}")
        click.echo(f"Hash: {file_hash}")
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.group()
def cache():
    """Cache management commands."""
    pass


@cache.command()
@click.option('--output', '-o', type=click.Choice(['text', 'json']), default='text',
              help='Output format')
def stats(output):
    """
    Show cache statistics.
    
    Examples:
        duplicateflow cache stats
        duplicateflow cache stats --output json
    """
    try:
        storage = StorageManager()
        stats_data = storage.get_stats()
        
        if output == 'json':
            click.echo(json.dumps(stats_data, indent=2))
        else:
            click.echo("Cache Statistics:\n")
            
            click.echo("Hash Cache:")
            click.echo(f"  Hits: {stats_data['hash_cache']['hits']}")
            click.echo(f"  Misses: {stats_data['hash_cache']['misses']}")
            click.echo(f"  Hit rate: {stats_data['hash_cache']['hit_rate']:.2f}%")
            
            click.echo("\nResult Cache:")
            click.echo(f"  Hits: {stats_data['result_cache']['hits']}")
            click.echo(f"  Misses: {stats_data['result_cache']['misses']}")
            click.echo(f"  Hit rate: {stats_data['result_cache']['hit_rate']:.2f}%")
            click.echo(f"  Total entries: {stats_data['result_cache']['total_entries']}")
            click.echo(f"  Memory cache size: {stats_data['result_cache']['memory_cache_size']}")
            
            click.echo(f"\nCache directory: {stats_data['cache_dir']}")
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cache.command()
@click.option('--algorithm', '-a', type=str, default=None,
              help='Clear results for specific algorithm')
@click.option('--days', '-d', type=int, default=None,
              help='Clear results older than N days')
@click.option('--all', 'clear_all', is_flag=True,
              help='Clear all cached results')
@click.confirmation_option(prompt='Are you sure you want to clear the cache?')
def clear(algorithm, days, clear_all):
    """
    Clear cached results.
    
    Examples:
        duplicateflow cache clear --all
        duplicateflow cache clear --algorithm frame_hash
        duplicateflow cache clear --days 30
    """
    try:
        storage = StorageManager()
        
        if clear_all:
            storage.clear_results()
            click.echo("All cached results cleared")
        elif algorithm:
            count = storage.clear_results(algorithm)
            click.echo(f"Cleared {count} results for algorithm '{algorithm}'")
        elif days:
            count = storage.clear_old_results(days)
            click.echo(f"Cleared {count} results older than {days} days")
        else:
            click.echo("Please specify --all, --algorithm, or --days", err=True)
            sys.exit(1)
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('short_video', type=click.Path(exists=True))
@click.argument('long_video', type=click.Path(exists=True))
@click.option('--algorithm', '-a', type=str, default='frame_hash',
              help='Algorithm to use for search (default: frame_hash)')
@click.option('--threshold', '-t', type=float, default=None,
              help='Detection threshold')
@click.option('--strategy', type=click.Choice(['linear', 'parallel', 'cascade', 'adaptive']),
              default='cascade', help='Search strategy (default: cascade)')
@click.option('--workers', '-w', type=int, default=None,
              help='Number of parallel workers (default: CPU count)')
@click.option('--step', type=float, default=5.0,
              help='Step size between windows in seconds (default: 5.0)')
@click.option('--output', '-o', type=click.Choice(['text', 'json']), default='text',
              help='Output format')
def search(short_video, long_video, algorithm, threshold, strategy, workers, step, output):
    """
    Optimized search for finding scenes in long videos using sliding windows.

    This is much faster than 'compare' for multi-hour videos. Uses parallel
    processing and cascade filtering for 50-100x speedup.

    Examples:
        duplicateflow search scene.mp4 movie.mp4
        duplicateflow search clip.mp4 stream.mp4 --strategy cascade --workers 8
        duplicateflow search scene.mp4 movie.mp4 --algorithm color_histogram
    """
    try:
        import time

        # Get algorithm instance
        AlgoClass = get_algorithm(algorithm)
        algo = AlgoClass()

        # Configure with threshold if provided
        config = {}
        if threshold is not None:
            config['threshold'] = threshold
        algo.configure(**config)

        click.echo(f"Strategy: {strategy}")
        click.echo(f"Algorithm: {algorithm}")
        click.echo(f"Workers: {workers or 'auto'}")
        click.echo()

        start = time.time()

        if strategy == 'parallel':
            from duplicateflow.processing import ParallelWindowSearch

            searcher = ParallelWindowSearch(num_workers=workers)
            result = searcher.search(
                short_video, long_video, algorithm, algo,
                step_size=step, show_progress=True
            )

        elif strategy == 'cascade':
            from duplicateflow.processing.parallel_search import ParallelWindowSearch
            from duplicateflow.processing.cascade_filter import CascadeFilter
            from duplicateflow.algorithms.base.video_loader import get_video_duration

            # Get duration
            short_duration = get_video_duration(short_video)
            long_duration = get_video_duration(long_video)

            # Generate all windows
            num_windows = int((long_duration - short_duration) / step)
            windows = [i * step for i in range(num_windows)]

            click.echo(f"Total windows to search: {len(windows)}")
            click.echo()

            # Stage 1 & 2: Cascade filter
            cascade = CascadeFilter()
            candidates = cascade.filter_windows(
                windows, short_video, long_video, short_duration,
                stage1_threshold=40.0, stage2_threshold=55.0,
                show_progress=True
            )

            click.echo()
            click.echo(f"Cascade filtering complete: {len(candidates)} candidates")
            click.echo()

            # Stage 3: Full algorithm on candidates
            if candidates:
                click.echo(f"Running full {algorithm} algorithm on {len(candidates)} candidates")
                searcher = ParallelWindowSearch(num_workers=workers)

                # Override windows to only test candidates
                best_score = 0.0
                best_offset = 0.0

                from tqdm import tqdm as tqdm_std
                for candidate in tqdm_std(candidates, desc=f"Full {algorithm} analysis"):
                    single_result = algo.compare(
                        short_video=short_video,
                        long_video=long_video,
                        start_time=candidate,
                        duration=short_duration
                    )

                    similarity = single_result['similarity']
                    if similarity <= 1.0:
                        similarity *= 100.0

                    if similarity > best_score:
                        best_score = similarity
                        best_offset = candidate

                result = {
                    'offset': best_offset,
                    'score': best_score,
                    'accepted': best_score >= algo.threshold,
                    'windows_tested': len(candidates),
                    'total_windows': len(windows),
                    'algorithm': algorithm,
                    'cascade_stats': cascade.get_stats()
                }
            else:
                result = {
                    'offset': 0.0,
                    'score': 0.0,
                    'accepted': False,
                    'windows_tested': 0,
                    'total_windows': len(windows),
                    'algorithm': algorithm
                }

        elif strategy == 'adaptive':
            from duplicateflow.processing.parallel_search import AdaptiveStepSearch

            searcher = AdaptiveStepSearch(num_workers=workers)
            result = searcher.search(
                short_video, long_video, algorithm, algo,
                initial_step=30.0, fine_step=2.0,
                show_progress=True
            )

        else:  # linear
            from duplicateflow.processing import ParallelWindowSearch

            searcher = ParallelWindowSearch(num_workers=1)
            result = searcher.search(
                short_video, long_video, algorithm, algo,
                step_size=step, show_progress=True
            )

        elapsed = time.time() - start
        result['duration'] = elapsed

        # Output results
        if output == 'json':
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo()
            click.echo("=" * 60)
            click.echo("SEARCH RESULTS")
            click.echo("=" * 60)
            click.echo(f"Best match at: {result['offset']:.1f}s")
            click.echo(f"Similarity score: {result['score']:.2f}%")
            click.echo(f"Accepted: {'Yes' if result['accepted'] else 'No'}")
            click.echo(f"Windows tested: {result['windows_tested']}")
            if 'total_windows' in result:
                elimination = (1 - result['windows_tested'] / result['total_windows']) * 100
                click.echo(f"Total windows: {result['total_windows']} ({elimination:.1f}% eliminated)")
            click.echo(f"Time elapsed: {elapsed:.2f}s")

            if 'cascade_stats' in result:
                click.echo()
                click.echo("Cascade Filter Stats:")
                stats = result['cascade_stats']
                click.echo(f"  Stage 1 elimination: {stats['stage1_elimination_rate']:.1f}%")
                click.echo(f"  Stage 2 elimination: {stats['stage2_elimination_rate']:.1f}%")
                click.echo(f"  Total elimination: {stats['total_elimination_rate']:.1f}%")
                click.echo(f"  Stage 1 avg time: {stats['avg_stage1_time_per_window_ms']:.2f}ms/window")
                click.echo(f"  Stage 2 avg time: {stats['avg_stage2_time_per_window_ms']:.2f}ms/window")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.argument('input_dir', type=click.Path(exists=True))
@click.argument('reference_video', type=click.Path(exists=True))
@click.option('--algorithm', '-a', type=str, default='frame_hash',
              help='Algorithm to use (default: frame_hash)')
@click.option('--threshold', '-t', type=float, default=None,
              help='Detection threshold')
@click.option('--strategy', type=click.Choice(['parallel', 'standard']),
              default='parallel', help='Search strategy (default: parallel)')
@click.option('--workers', '-w', type=int, default=4,
              help='Number of parallel workers (default: 4)')
@click.option('--step', type=float, default=5.0,
              help='Step size for window search (default: 5.0)')
@click.option('--output', '-o', type=click.Path(), required=True,
              help='Output file (.csv or .json)')
@click.option('--checkpoint', type=click.Path(), default=None,
              help='Checkpoint file for resume')
@click.option('--pattern', type=str, default='*.mp4',
              help='File pattern to match (default: *.mp4)')
def batch(input_dir, reference_video, algorithm, threshold, strategy, workers, step, output, checkpoint, pattern):
    """
    Batch process multiple videos against a reference video.

    Compares all videos in INPUT_DIR against REFERENCE_VIDEO and exports
    results to CSV or JSON. Supports resume from checkpoint.

    Examples:
        duplicateflow batch ./videos reference.mp4 --output results.csv
        duplicateflow batch ./clips movie.mp4 -w 8 -o matches.json
        duplicateflow batch ./test ref.mp4 -o out.csv --checkpoint chk.pkl
    """
    try:
        import time
        from pathlib import Path
        from duplicateflow.processing.batch_processor import BatchProcessor

        # Find all videos
        input_path = Path(input_dir)
        video_files = sorted(input_path.glob(pattern))

        if not video_files:
            click.echo(f"No videos found matching pattern: {pattern}", err=True)
            sys.exit(1)

        click.echo(f"Found {len(video_files)} videos to process")
        click.echo(f"Reference: {reference_video}")
        click.echo(f"Algorithm: {algorithm}")
        click.echo(f"Workers: {workers}")
        click.echo(f"Output: {output}")
        click.echo()

        # Configure algorithm
        algo_params = {}
        if threshold is not None:
            algo_params['threshold'] = threshold

        # Process batch
        processor = BatchProcessor(
            num_workers=workers,
            checkpoint_interval=10,
            max_retries=2
        )

        start = time.time()

        results = processor.process_batch(
            short_videos=[str(f) for f in video_files],
            long_video=reference_video,
            algorithm=algorithm,
            algorithm_params=algo_params,
            strategy=strategy,
            step_size=step,
            output_file=output,
            checkpoint_file=checkpoint,
            show_progress=True
        )

        elapsed = time.time() - start

        # Display statistics
        stats = processor.get_stats(results)

        click.echo()
        click.echo("=" * 60)
        click.echo("BATCH PROCESSING COMPLETE")
        click.echo("=" * 60)
        click.echo(f"Total videos: {stats['total_videos']}")
        click.echo(f"Successful: {stats['successful']}")
        click.echo(f"Failed: {stats['failed']}")
        click.echo(f"Accepted: {stats['accepted']} ({stats['acceptance_rate']:.1f}%)")
        click.echo(f"Average score: {stats['avg_score']:.2f}%")
        click.echo(f"Score range: {stats['min_score']:.2f}% - {stats['max_score']:.2f}%")
        click.echo(f"Total time: {elapsed:.2f}s")
        click.echo(f"Average time per video: {stats['avg_duration']:.2f}s")
        click.echo()
        click.echo(f"Results saved to: {output}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.argument('input_dir', type=click.Path(exists=True))
@click.option('--algorithm', '-a', type=str, default='frame_hash',
              help='Algorithm to use (default: frame_hash)')
@click.option('--threshold', '-t', type=float, default=None,
              help='Detection threshold')
@click.option('--workers', '-w', type=int, default=4,
              help='Number of parallel workers (default: 4)')
@click.option('--output', '-o', type=click.Path(), required=True,
              help='Output CSV file for matrix')
@click.option('--pattern', type=str, default='*.mp4',
              help='File pattern to match (default: *.mp4)')
def matrix(input_dir, algorithm, threshold, workers, output, pattern):
    """
    Compute N-to-N similarity matrix for all videos in a directory.

    Compares each video against all others and exports results as CSV matrix.

    Examples:
        duplicateflow matrix ./videos --output similarity.csv
        duplicateflow matrix ./clips -a color_histogram -o matrix.csv
    """
    try:
        import time
        from pathlib import Path
        from duplicateflow.processing.batch_processor import BatchProcessor

        # Find all videos
        input_path = Path(input_dir)
        video_files = sorted(input_path.glob(pattern))

        if not video_files:
            click.echo(f"No videos found matching pattern: {pattern}", err=True)
            sys.exit(1)

        n = len(video_files)
        total_comparisons = n * (n - 1) // 2

        click.echo(f"Found {n} videos")
        click.echo(f"Total comparisons: {total_comparisons}")
        click.echo(f"Algorithm: {algorithm}")
        click.echo(f"Workers: {workers}")
        click.echo()

        if n > 100:
            click.confirm(
                f"Computing {total_comparisons} comparisons may take a long time. Continue?",
                abort=True
            )

        # Configure algorithm
        algo_params = {}
        if threshold is not None:
            algo_params['threshold'] = threshold

        # Process matrix
        processor = BatchProcessor(num_workers=workers)

        start = time.time()

        matrix_data = processor.process_matrix(
            video_list=[str(f) for f in video_files],
            algorithm=algorithm,
            algorithm_params=algo_params,
            output_file=output,
            show_progress=True
        )

        elapsed = time.time() - start

        click.echo()
        click.echo("=" * 60)
        click.echo("MATRIX COMPUTATION COMPLETE")
        click.echo("=" * 60)
        click.echo(f"Videos: {n}x{n}")
        click.echo(f"Comparisons: {total_comparisons}")
        click.echo(f"Time: {elapsed:.2f}s")
        click.echo(f"Average time per comparison: {elapsed/total_comparisons:.2f}s")
        click.echo()
        click.echo(f"Matrix saved to: {output}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


@cli.command()
def info():
    """
    Show DuplicateFlow information.

    Examples:
        duplicateflow info
    """
    algos = get_all_algorithms()
    presets = get_all_presets()

    # Count by category
    by_category = {}
    for algo in algos:
        cat = algo.get('category', 'unknown')
        by_category[cat] = by_category.get(cat, 0) + 1

    click.echo(f"DuplicateFlow v{__version__}")
    click.echo()
    click.echo("Algorithms:")
    click.echo(f"  Total: {len(algos)}")
    for cat, count in sorted(by_category.items()):
        click.echo(f"  - {cat}: {count}")

    click.echo()
    click.echo("Pipeline Presets:")
    click.echo(f"  Total: {len(presets)}")
    click.echo(f"  Available: {', '.join(presets)}")

    click.echo()
    click.echo("Features:")
    click.echo("  - 100% free and open-source")
    click.echo("  - MD5-based caching")
    click.echo("  - SQLite result cache")
    click.echo("  - Weighted scoring")
    click.echo("  - Early termination")
    click.echo("  - Parallel window search")
    click.echo("  - Cascade filtering")


if __name__ == '__main__':
    cli()
