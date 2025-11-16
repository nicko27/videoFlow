"""
Example usage of subsequence detection feature.

This script demonstrates how to use the SubsequenceDetector to find
when a shorter video is contained within a longer video.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from src.plugins.duplicate_finder.video_hasher import VideoHasher
from src.plugins.duplicate_finder.subsequence_detector import SubsequenceDetector


def example_basic_detection():
    """Basic example: Detect if video B is a subsequence of video A."""
    print("=" * 60)
    print("EXAMPLE 1: Basic Subsequence Detection")
    print("=" * 60)

    # Initialize hasher and detector
    hasher = VideoHasher(method='pHash')
    detector = SubsequenceDetector(
        hasher=hasher,
        max_cache_memory_mb=500,        # Limit cache to 500MB
        sample_interval_seconds=3.0,    # Sample every 3 seconds
        min_match_ratio=0.80            # Require 80% match
    )

    # Example video paths (replace with your actual video paths)
    video_long = "/path/to/long_video.mp4"      # Full video with scenes A1, A2, A3
    video_short = "/path/to/short_video.mp4"    # Just scene A2

    print(f"\nChecking if '{os.path.basename(video_short)}' is in '{os.path.basename(video_long)}'...")

    # Detect subsequence
    result = detector.find_subsequence(video_short, video_long)

    if result:
        if result['is_subsequence']:
            print(f"\n✓ SUBSEQUENCE DETECTED!")
            print(f"  Match ratio: {result['match_ratio']*100:.1f}%")
            print(f"  Start position: frame {result['start_frame_idx']}")
            print(f"  Confidence: {result['confidence']*100:.1f}%")
            print(f"  Short video duration: {result['short_duration']:.1f}s")
            print(f"  Long video duration: {result['long_duration']:.1f}s")
        else:
            print(f"\n✗ Not a subsequence (match: {result['match_ratio']*100:.1f}%)")
    else:
        print("\n✗ Error during detection")

    # Show cache stats
    stats = detector.get_cache_stats()
    print(f"\nCache usage: {stats['memory_mb']:.1f}MB / {stats['max_memory_mb']}MB ({stats['usage_percent']:.1f}%)")


def example_batch_detection():
    """Advanced example: Detect all subsequences in a folder."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Batch Subsequence Detection")
    print("=" * 60)

    # Initialize
    hasher = VideoHasher(method='pHash')
    detector = SubsequenceDetector(
        hasher=hasher,
        max_cache_memory_mb=1000,       # 1GB cache for batch processing
        sample_interval_seconds=3.0,
        min_match_ratio=0.85            # Stricter matching
    )

    # Get all videos from a folder
    video_folder = "/path/to/videos"
    video_files = [
        os.path.join(video_folder, f)
        for f in os.listdir(video_folder)
        if f.endswith(('.mp4', '.avi', '.mkv', '.mov'))
    ]

    print(f"\nScanning {len(video_files)} videos for subsequences...")

    # Progress callback
    def progress(current, total, message):
        print(f"[{current}/{total}] {message}")

    # Detect all subsequences
    results = detector.detect_all_subsequences(video_files, progress_callback=progress)

    # Display results
    print(f"\n{'='*60}")
    print(f"RESULTS: Found {len(results)} subsequences")
    print(f"{'='*60}")

    for short_video, long_video, detection in results:
        print(f"\n'{os.path.basename(short_video)}' is in '{os.path.basename(long_video)}'")
        print(f"  Match: {detection['match_ratio']*100:.1f}%")
        print(f"  Position: frame {detection['start_frame_idx']}")

    # Final cache stats
    stats = detector.get_cache_stats()
    print(f"\nFinal cache: {stats['items']} videos, {stats['memory_mb']:.1f}MB")


def example_custom_settings():
    """Example with custom detection settings."""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Custom Settings")
    print("=" * 60)

    hasher = VideoHasher(method='dHash')  # Faster hashing method

    # Custom detector for very short clips
    detector = SubsequenceDetector(
        hasher=hasher,
        max_cache_memory_mb=200,        # Lower memory limit
        sample_interval_seconds=1.0,    # Dense sampling (every second)
        min_match_ratio=0.90            # Very strict matching
    )

    print("\nSettings:")
    print(f"  Hash method: dHash (faster)")
    print(f"  Sampling: every 1.0 seconds (dense)")
    print(f"  Min match: 90% (strict)")
    print(f"  Cache limit: 200MB")

    # The detector will:
    # - Sample frames every second for better precision
    # - Use only 200MB of cache maximum
    # - Require 90% match ratio
    # - Automatically evict old entries when cache is full


def example_memory_monitoring():
    """Example showing memory-safe operation."""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Memory Monitoring")
    print("=" * 60)

    hasher = VideoHasher(method='pHash')
    detector = SubsequenceDetector(
        hasher=hasher,
        max_cache_memory_mb=100  # Very limited cache
    )

    print(f"\nCache limit: 100MB")
    print("Processing videos and monitoring memory...")

    # Simulate processing many videos
    video_paths = [f"/path/to/video{i}.mp4" for i in range(50)]

    for i, video_path in enumerate(video_paths[:5]):  # Just first 5 for demo
        # Compute dense hash (will auto-evict if memory limit reached)
        hash_data, duration = detector.compute_dense_hash(video_path)

        # Check memory after each video
        stats = detector.get_cache_stats()
        print(f"\nVideo {i+1}: {stats['items']} cached, "
              f"{stats['memory_mb']:.1f}MB ({stats['usage_percent']:.1f}%)")

        if stats['usage_percent'] > 80:
            print("  ⚠️  Cache nearly full, old entries being evicted")

    print("\n✓ Memory stayed within limit (automatic eviction)")


def example_with_database():
    """Example showing database integration."""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Database Integration")
    print("=" * 60)

    hasher = VideoHasher(method='pHash')
    detector = SubsequenceDetector(hasher=hasher)

    video_short = "/path/to/short.mp4"
    video_long = "/path/to/long.mp4"

    # Detect subsequence
    result = detector.find_subsequence(video_short, video_long)

    if result and result['is_subsequence']:
        # Store in database for later review
        detector.db.store_subsequence_detection(
            video_short,
            video_long,
            result['match_ratio'],
            result['start_frame_idx'],
            result['confidence']
        )
        print("\n✓ Subsequence detection stored in database")

    # Get pending subsequences from database
    pending = detector.db.get_pending_subsequences()
    print(f"\nPending subsequences in database: {len(pending)}")

    for short, long, match, start, confidence, seq_id in pending:
        print(f"\n  ID {seq_id}:")
        print(f"    Short: {os.path.basename(short)}")
        print(f"    Long:  {os.path.basename(long)}")
        print(f"    Match: {match*100:.1f}%")

    # Get statistics
    stats = detector.db.get_subsequence_statistics()
    print(f"\nDatabase stats:")
    print(f"  Total: {stats['total']}")
    print(f"  Pending: {stats['pending']}")
    print(f"  Avg match: {stats['avg_match_ratio']*100:.1f}%")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("VIDEO SUBSEQUENCE DETECTION - Examples")
    print("=" * 60)
    print("\nThese examples demonstrate different use cases.")
    print("Replace paths with your actual video files.\n")

    # Uncomment the example you want to run:

    # example_basic_detection()
    # example_batch_detection()
    # example_custom_settings()
    # example_memory_monitoring()
    # example_with_database()

    print("\n" + "=" * 60)
    print("To run examples, uncomment them in the __main__ block")
    print("=" * 60)
