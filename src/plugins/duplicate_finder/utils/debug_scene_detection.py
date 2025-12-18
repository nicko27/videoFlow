"""
Debug script for scene detection - diagnose why scenes in the middle are not found.

This script tests fingerprint extraction and comparison to identify issues.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.logger import Logger
from src.plugins.duplicate_finder.detection.audio.audio_fingerprinting import AudioFingerprintDetector, PrecisionMode

logger = Logger.get_logger('SceneDebug')


def test_fingerprint_extraction(video_path: str):
    """Test fingerprint extraction for a single video."""
    print(f"\n{'='*80}")
    print(f"Testing fingerprint extraction: {os.path.basename(video_path)}")
    print(f"{'='*80}")

    detector = AudioFingerprintDetector(
        precision_mode=PrecisionMode.BALANCED,
        min_match_ratio=0.85
    )

    # Check if pyacoustid is available
    print(f"\n1. pyacoustid available: {detector.has_acoustid}")
    print(f"   fpcalc available: {detector.fpcalc_available}")

    # Extract fingerprint
    print(f"\n2. Extracting fingerprint...")
    fp, duration, raw_fp = detector._extract_audio_fingerprint(video_path)

    if fp:
        print(f"   ✓ Fingerprint extracted successfully")
        print(f"   - Duration: {duration:.1f}s")
        print(f"   - Fingerprint length: {len(fp)} chars")
        print(f"   - Raw fingerprint: {len(raw_fp) if raw_fp else 'None'} samples")
        if raw_fp:
            print(f"   - First 5 samples: {raw_fp[:5]}")
            print(f"   - Samples per second: {len(raw_fp)/duration:.2f}")
    else:
        print(f"   ✗ Failed to extract fingerprint")

    return detector, fp, duration, raw_fp


def test_hash_index_method(detector, short_video: str, long_video: str):
    """Test hash index method in detail."""
    print(f"\n{'='*80}")
    print(f"Testing HASH INDEX method")
    print(f"{'='*80}")

    print(f"\nShort: {os.path.basename(short_video)}")
    print(f"Long:  {os.path.basename(long_video)}")

    # Extract fingerprints
    print(f"\n1. Extracting fingerprints...")
    fp_short, dur_short, raw_short = detector._extract_audio_fingerprint(short_video)
    fp_long, dur_long, raw_long = detector._extract_audio_fingerprint(long_video)

    if not fp_short or not fp_long:
        print("   ✗ Failed to extract fingerprints")
        return

    if not raw_short or not raw_long:
        print("   ✗ No raw fingerprints (pyacoustid not available)")
        return

    print(f"   ✓ Short: {dur_short:.1f}s, {len(raw_short)} samples")
    print(f"   ✓ Long:  {dur_long:.1f}s, {len(raw_long)} samples")

    # Create index
    print(f"\n2. Creating hash index...")
    segment_size = 16
    long_index = detector._create_fingerprint_index(raw_long, segment_size=segment_size)
    print(f"   ✓ Index created: {len(long_index)} unique hashes")

    # Query index
    print(f"\n3. Querying index with short video...")
    matches = []

    for i in range(0, len(raw_short) - segment_size + 1):
        segment = raw_short[i:i + segment_size]

        segment_hash = (
            (segment[0] & 0xFFFFFFFF) ^
            (segment[segment_size // 2] << 8) ^
            (segment[-1] << 16)
        )

        if segment_hash in long_index:
            for long_pos in long_index[segment_hash]:
                matches.append((i, long_pos))

    print(f"   ✓ Found {len(matches)} hash matches")

    if len(matches) == 0:
        print("\n   ⚠️  PROBLEM: No hash matches found!")
        print("   This means the hash function is not finding common segments.")
        print("\n   Possible causes:")
        print("   - Hash too simple (only uses 3 values)")
        print("   - Videos re-encoded with different settings")
        print("   - Audio fingerprints too different")

        # Test with direct comparison
        print(f"\n4. Testing direct sample-by-sample comparison...")
        test_direct_comparison(raw_short, raw_long, segment_size)
        return

    # Find cluster
    print(f"\n4. Finding best cluster...")
    cluster_result = detector._find_best_cluster(matches, min_cluster_size=5)

    if cluster_result:
        start_pos, confidence = cluster_result
        start_time = start_pos * 0.128
        print(f"   ✓ Cluster found at position {start_pos} ({start_time:.1f}s)")
        print(f"   - Confidence: {confidence*100:.1f}%")
    else:
        print(f"   ✗ No consistent cluster found")
        print(f"   - Matches are too scattered (not from same scene)")


def test_direct_comparison(raw_short, raw_long, window_size=16):
    """Test direct sample-by-sample comparison to see if there's ANY match."""
    print(f"\n   Testing if ANY window matches...")

    best_match_count = 0
    best_position = -1
    samples_tested = 0

    # Test every 100th position (sampling to save time)
    step = 100

    for pos in range(0, len(raw_long) - len(raw_short) + 1, step):
        samples_tested += 1
        window = raw_long[pos:pos + len(raw_short)]

        # Count exact matches
        matches = sum(1 for i in range(len(raw_short)) if raw_short[i] == window[i])
        match_ratio = matches / len(raw_short)

        if match_ratio > best_match_count / len(raw_short):
            best_match_count = matches
            best_position = pos

    if best_match_count > 0:
        best_ratio = best_match_count / len(raw_short)
        best_time = best_position * 0.128
        print(f"   ✓ Best match: {best_ratio*100:.1f}% at position {best_position} ({best_time:.1f}s)")
        print(f"   - Tested {samples_tested} positions (every {step} samples)")

        if best_ratio < 0.5:
            print(f"\n   ⚠️  PROBLEM: Best match is only {best_ratio*100:.1f}%!")
            print(f"   This suggests:")
            print(f"   - Videos are very different (different encoding, quality, etc.)")
            print(f"   - OR they are not actually the same scene")
    else:
        print(f"   ✗ No matches found at all in {samples_tested} positions tested")


def test_sliding_window_method(detector, short_video: str, long_video: str):
    """Test improved sliding window method."""
    print(f"\n{'='*80}")
    print(f"Testing SLIDING WINDOW method (improved)")
    print(f"{'='*80}")

    result = detector.find_scene(short_video, long_video)

    if result:
        print(f"\n✓ Result: {result}")
        if result['is_scene']:
            print(f"  FOUND at {result['start_time_seconds']:.1f}s")
            print(f"  Match ratio: {result['match_ratio']*100:.1f}%")
        else:
            print(f"  NOT FOUND (ratio {result['match_ratio']*100:.1f}% < threshold)")
    else:
        print(f"\n✗ No result returned")


def main():
    """Main debug function."""
    import argparse

    parser = argparse.ArgumentParser(description='Debug scene detection')
    parser.add_argument('short_video', help='Path to short video (scene)')
    parser.add_argument('long_video', help='Path to long video')

    args = parser.parse_args()

    print("\n" + "="*80)
    print("SCENE DETECTION DEBUG TOOL")
    print("="*80)

    # Test extraction for both videos
    print("\n[STEP 1] Testing fingerprint extraction")
    detector1, fp1, dur1, raw1 = test_fingerprint_extraction(args.short_video)
    detector2, fp2, dur2, raw2 = test_fingerprint_extraction(args.long_video)

    if not fp1 or not fp2:
        print("\n✗ Cannot proceed - fingerprint extraction failed")
        return

    # Test hash index method
    print("\n[STEP 2] Testing Hash Index method")
    test_hash_index_method(detector1, args.short_video, args.long_video)

    # Test sliding window
    print("\n[STEP 3] Testing Sliding Window method")
    test_sliding_window_method(detector1, args.short_video, args.long_video)

    print("\n" + "="*80)
    print("DEBUG COMPLETE")
    print("="*80)


if __name__ == '__main__':
    main()
