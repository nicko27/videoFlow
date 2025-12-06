#!/usr/bin/env python3
"""
Quick utility to compare two specific videos and see their similarity scores.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.logger import Logger
from src.plugins.duplicate_finder.database_manager import VideoDatabase
from src.plugins.duplicate_finder.analysis import LSHAudioAnalyzer, PHashComparator

logger = Logger.get_logger('CompareVideos')


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 compare_two_videos.py <video1> <video2>")
        print("\nExample:")
        print('  python3 compare_two_videos.py "~/Downloads/video1.mp4" "~/Downloads/video2.mp4"')
        return 1

    video1 = Path(sys.argv[1]).expanduser()
    video2 = Path(sys.argv[2]).expanduser()

    if not video1.exists():
        print(f"❌ Video 1 not found: {video1}")
        return 1

    if not video2.exists():
        print(f"❌ Video 2 not found: {video2}")
        return 1

    print("=" * 80)
    print("🔍 DIRECT VIDEO COMPARISON")
    print("=" * 80)
    print(f"\n📹 Video 1: {video1.name}")
    print(f"📹 Video 2: {video2.name}")
    print()

    # Initialize database
    db_path = Path(__file__).parent / "src" / "plugins" / "duplicate_finder" / "video_duplicates.db"
    db_manager = VideoDatabase(str(db_path))

    # Test LSH Audio similarity
    print("🎵 Testing LSH Audio Similarity...")
    print("  Extracting audio from 10% position (30s duration)...")
    try:
        lsh_analyzer = LSHAudioAnalyzer(threshold=0.5)
        similarity = lsh_analyzer.estimate_similarity(str(video1), str(video2), db_manager)

        if similarity is not None:
            print(f"  ✅ LSH Jaccard Similarity: {similarity:.4f}")
            if similarity >= 0.7:
                print(f"     → HIGH similarity (threshold 0.7)")
            elif similarity >= 0.5:
                print(f"     → MEDIUM similarity (threshold 0.5)")
            elif similarity >= 0.3:
                print(f"     → LOW similarity (threshold 0.3)")
            else:
                print(f"     → NO similarity (< 0.3)")
        else:
            print(f"  ❌ Could not compute LSH similarity")
    except Exception as e:
        print(f"  ❌ LSH Error: {e}")

    print()

    # Test pHash Visual similarity
    print("👁️  Testing pHash Visual Similarity...")
    print("  Extracting 10 frames from each video...")
    try:
        phash_comparator = PHashComparator(phash_threshold=15, frame_rate_threshold=0.7)
        result = phash_comparator.verify_visual_similarity(str(video1), str(video2))

        print(f"  ✅ Frames compared: {result['frames_compared']}")
        print(f"  ✅ Frames similar: {result['frames_similar']}")
        print(f"  ✅ Similarity rate: {result['similarity_rate']:.1%}")
        print(f"  ✅ Average distance: {result['avg_distance']:.1f} bits")

        if result['is_similar']:
            print(f"     → VISUALLY SIMILAR (≥70% frames match)")
        else:
            print(f"     → NOT visually similar")
    except Exception as e:
        print(f"  ❌ pHash Error: {e}")

    print()
    print("=" * 80)

    db_manager.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
