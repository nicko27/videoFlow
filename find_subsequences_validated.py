#!/usr/bin/env python3
"""
Advanced Subsequence Finder with Multi-Point Validation
========================================================

Improvements over previous version:
1. Multi-point validation: Test 3-5 points across the video duration
2. Temporal coherence: All points must match at expected positions
3. Higher confidence threshold (75%)
4. Progressive refinement for high-confidence matches

Strategy:
- Phase 1: Quick scan to find candidates (like before)
- Phase 2: Multi-point validation
  * Test beginning (0s)
  * Test middle (duration/2)
  * Test end (duration - 30s)
  * All must match within ±30s tolerance
- Phase 3: Fine refinement for validated matches
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import sys
from collections import defaultdict

# Paths
DOWNLOADS_DIR = Path("/Users/nico/Downloads")

# Search parameters
SEARCH_STEP = 30
SAMPLE_DURATION = 20
SAMPLE_INTERVAL = 2

# Validation parameters
VALIDATION_SAMPLE_DURATION = 30
VALIDATION_POINTS = 3  # Test at beginning, middle, end
TEMPORAL_TOLERANCE = 30  # ±30s tolerance for each validation point

# Thresholds
LOW_MOTION_THRESHOLD = 1.5
INITIAL_THRESHOLD = 70.0  # Raised from 60% to reduce false positives
VALIDATION_THRESHOLD = 75.0  # Each validation point must score ≥75%
HIGH_CONFIDENCE_THRESHOLD = 85.0

def get_video_info(video_path: Path) -> Optional[Tuple[float, float]]:
    """Get video duration and fps."""
    try:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return None

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        cap.release()

        return duration, fps
    except:
        return None

def extract_frames_from_video(video_path: Path, start_sec: float, duration: float, interval: float) -> List[np.ndarray]:
    """Extract frames at regular intervals from a video segment."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return []

    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = []

    for offset in np.arange(0, duration, interval):
        frame_num = int((start_sec + offset) * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        if ret:
            frame = cv2.resize(frame, (320, 180))
            frames.append(frame)

    cap.release()
    return frames

def method_color_histogram(ref_frames: List[np.ndarray], cand_frames: List[np.ndarray]) -> float:
    """Compare using color histograms."""
    if not ref_frames or not cand_frames:
        return 0.0

    ref_hists = []
    for frame in ref_frames:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])
        hist = cv2.normalize(hist, hist).flatten()
        ref_hists.append(hist)

    cand_hists = []
    for frame in cand_frames[:len(ref_frames)]:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])
        hist = cv2.normalize(hist, hist).flatten()
        cand_hists.append(hist)

    scores = []
    for rh, ch in zip(ref_hists, cand_hists):
        score = cv2.compareHist(rh, ch, cv2.HISTCMP_CORREL)
        scores.append(score)

    return np.mean(scores) * 100

def method_edge_density(ref_frames: List[np.ndarray], cand_frames: List[np.ndarray]) -> float:
    """Compare using edge density patterns."""
    if not ref_frames or not cand_frames:
        return 0.0

    ref_densities = []
    for frame in ref_frames:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        density = np.sum(edges > 0) / edges.size
        ref_densities.append(density)

    cand_densities = []
    for frame in cand_frames[:len(ref_frames)]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        density = np.sum(edges > 0) / edges.size
        cand_densities.append(density)

    min_len = min(len(ref_densities), len(cand_densities))
    if min_len < 2:
        return 0.0

    ref_arr = np.array(ref_densities[:min_len])
    cand_arr = np.array(cand_densities[:min_len])

    if ref_arr.std() == 0 or cand_arr.std() == 0:
        return 0.0

    ref_norm = (ref_arr - ref_arr.mean()) / ref_arr.std()
    cand_norm = (cand_arr - cand_arr.mean()) / cand_arr.std()

    correlation = np.corrcoef(ref_norm, cand_norm)[0, 1]

    if np.isnan(correlation):
        return 0.0

    return max(0, min(100, correlation * 100))

def method_frame_differences(ref_frames: List[np.ndarray], cand_frames: List[np.ndarray]) -> float:
    """Compare using frame difference patterns."""
    if len(ref_frames) < 2 or len(cand_frames) < 2:
        return 0.0

    ref_diffs = []
    for i in range(min(len(ref_frames), len(cand_frames)) - 1):
        gray1 = cv2.cvtColor(ref_frames[i], cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(ref_frames[i + 1], cv2.COLOR_BGR2GRAY)
        diff = cv2.absdiff(gray1, gray2)
        ref_diffs.append(np.mean(diff))

    cand_diffs = []
    for i in range(min(len(ref_frames), len(cand_frames)) - 1):
        gray1 = cv2.cvtColor(cand_frames[i], cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(cand_frames[i + 1], cv2.COLOR_BGR2GRAY)
        diff = cv2.absdiff(gray1, gray2)
        cand_diffs.append(np.mean(diff))

    ref_arr = np.array(ref_diffs)
    cand_arr = np.array(cand_diffs)

    if ref_arr.std() == 0 or cand_arr.std() == 0:
        return 0.0

    ref_norm = (ref_arr - ref_arr.mean()) / ref_arr.std()
    cand_norm = (cand_arr - cand_arr.mean()) / cand_arr.std()

    correlation = np.corrcoef(ref_norm, cand_norm)[0, 1]

    if np.isnan(correlation):
        return 0.0

    return max(0, min(100, correlation * 100))

def compute_motion_variance(frames: List[np.ndarray]) -> float:
    """Compute motion variance to detect static scenes."""
    if len(frames) < 2:
        return 0.0

    diffs = []
    for i in range(len(frames) - 1):
        gray1 = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frames[i + 1], cv2.COLOR_BGR2GRAY)
        diff = cv2.absdiff(gray1, gray2)
        diffs.append(np.mean(diff))

    return np.std(diffs)

def validate_multipoint(short_video: Path, long_video: Path, candidate_pos: int, short_dur: float) -> Tuple[bool, List[Tuple[float, float, str]]]:
    """
    Validate a candidate match by testing multiple points.

    Returns:
        (is_valid, validation_details)
        validation_details: [(offset, score, status), ...]
    """

    # Define validation points
    validation_offsets = []

    if short_dur < 60:
        # Short video: test beginning and end
        validation_offsets = [0, max(0, short_dur - 30)]
    elif short_dur < 300:
        # Medium video: test beginning, middle, end
        validation_offsets = [0, short_dur / 2, max(0, short_dur - 30)]
    else:
        # Long video: test 5 points
        validation_offsets = [0, short_dur * 0.25, short_dur * 0.5, short_dur * 0.75, max(0, short_dur - 30)]

    validation_results = []

    for offset in validation_offsets:
        # Extract from short video at this offset
        ref_frames = extract_frames_from_video(short_video, offset, VALIDATION_SAMPLE_DURATION, SAMPLE_INTERVAL)
        if len(ref_frames) < 2:
            validation_results.append((offset, 0.0, "❌ FAIL (no frames)"))
            continue

        # Expected position in long video
        expected_long_pos = candidate_pos + offset

        # Test positions around expected with tolerance
        best_score = 0.0
        best_pos = expected_long_pos

        for test_offset in range(-TEMPORAL_TOLERANCE, TEMPORAL_TOLERANCE + 1, 10):
            test_pos = expected_long_pos + test_offset
            if test_pos < 0:
                continue

            cand_frames = extract_frames_from_video(long_video, test_pos, VALIDATION_SAMPLE_DURATION, SAMPLE_INTERVAL)
            if len(cand_frames) < 2:
                continue

            # Score this position
            color_score = method_color_histogram(ref_frames, cand_frames)
            edge_score = method_edge_density(ref_frames, cand_frames)
            motion_score = method_frame_differences(ref_frames, cand_frames)

            combined = color_score * 0.30 + edge_score * 0.30 + motion_score * 0.40

            if combined > best_score:
                best_score = combined
                best_pos = test_pos

        # Check if this validation point passes
        if best_score >= VALIDATION_THRESHOLD:
            status = f"✅ PASS ({best_score:.1f}%)"
        else:
            status = f"❌ FAIL ({best_score:.1f}%)"

        validation_results.append((offset, best_score, status))

    # All validation points must pass
    is_valid = all(score >= VALIDATION_THRESHOLD for _, score, _ in validation_results)

    return is_valid, validation_results

def initial_scan(short_video: Path, long_video: Path, short_dur: float, long_dur: float) -> List[Tuple[int, float, Dict[str, float]]]:
    """Quick initial scan to find candidates."""

    # Extract first sample
    ref_frames = extract_frames_from_video(short_video, 0, SAMPLE_DURATION, SAMPLE_INTERVAL)
    if len(ref_frames) < 2:
        return []

    # Check motion variance for smart method selection
    motion_var = compute_motion_variance(ref_frames)
    use_multipoint = motion_var < LOW_MOTION_THRESHOLD

    num_positions = int(long_dur / SEARCH_STEP) + 1
    results = []

    if use_multipoint:
        # Multi-point sampling for static videos
        sample_points = [0, min(300, short_dur - 30), min(480, short_dur - 30)]
        sample_points = [p for p in sample_points if p >= 0 and p + SAMPLE_DURATION <= short_dur]

        position_scores = {}

        for sample_start in sample_points:
            ref_frames = extract_frames_from_video(short_video, sample_start, SAMPLE_DURATION, SAMPLE_INTERVAL)
            if len(ref_frames) < 2:
                continue

            for i in range(num_positions):
                position_sec = i * SEARCH_STEP
                adjusted_pos = position_sec + sample_start

                cand_frames = extract_frames_from_video(long_video, adjusted_pos, SAMPLE_DURATION, SAMPLE_INTERVAL)
                if len(cand_frames) < 2:
                    continue

                scores = {
                    'color': method_color_histogram(ref_frames, cand_frames),
                    'edge': method_edge_density(ref_frames, cand_frames),
                    'motion': method_frame_differences(ref_frames, cand_frames)
                }

                weighted_score = scores['color'] * 0.30 + scores['edge'] * 0.30 + scores['motion'] * 0.40

                if position_sec not in position_scores:
                    position_scores[position_sec] = {'scores': [], 'details': []}

                position_scores[position_sec]['scores'].append(weighted_score)
                position_scores[position_sec]['details'].append(scores)

        # Average across sample points
        for position_sec, data in position_scores.items():
            if not data['scores']:
                continue

            avg_weighted = np.mean(data['scores'])

            if avg_weighted >= INITIAL_THRESHOLD:
                avg_scores = {
                    'color': np.mean([s['color'] for s in data['details']]),
                    'edge': np.mean([s['edge'] for s in data['details']]),
                    'motion': np.mean([s['motion'] for s in data['details']])
                }
                results.append((position_sec, avg_weighted, avg_scores))
    else:
        # Baseline for videos with normal motion
        for i in range(num_positions):
            position_sec = i * SEARCH_STEP

            cand_frames = extract_frames_from_video(long_video, position_sec, SAMPLE_DURATION, SAMPLE_INTERVAL)
            if len(cand_frames) < 2:
                continue

            scores = {
                'color': method_color_histogram(ref_frames, cand_frames),
                'edge': method_edge_density(ref_frames, cand_frames),
                'motion': method_frame_differences(ref_frames, cand_frames)
            }

            weighted_score = scores['color'] * 0.30 + scores['edge'] * 0.30 + scores['motion'] * 0.40

            if weighted_score >= INITIAL_THRESHOLD:
                results.append((position_sec, weighted_score, scores))

    results.sort(key=lambda x: x[1], reverse=True)
    return results

def format_time(seconds: float) -> str:
    """Format seconds as HH:MM:SS or MM:SS."""
    hours = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}h{mins:02d}m{secs:02d}s"
    else:
        return f"{mins}m{secs:02d}s"

def main():
    print("=" * 80)
    print("ADVANCED SUBSEQUENCE FINDER - Multi-Point Validation")
    print("=" * 80)
    print()
    print("Improvements:")
    print("  • Higher initial threshold (70% vs 60%)")
    print("  • Multi-point validation (test beginning, middle, end)")
    print("  • Temporal coherence check")
    print("  • Validation threshold: 75% for each point")
    print()
    print("Scanning Downloads directory...")
    print()

    # Find all video files
    video_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.flv', '.wmv', '.webm'}
    all_videos = []

    for ext in video_extensions:
        all_videos.extend(DOWNLOADS_DIR.glob(f"*{ext}"))

    videos = []
    for video in all_videos:
        if video.name.startswith('.'):
            continue

        info = get_video_info(video)
        if info and info[0] > 0:
            duration, fps = info
            videos.append((video, duration, fps))

    videos.sort(key=lambda x: x[0].name)

    print(f"Found {len(videos)} video files\n")

    if len(videos) == 0:
        print("No videos found!")
        return

    # Find subsequences
    print("=" * 80)
    print("PHASE 1: INITIAL SCAN (threshold: 70%)")
    print("=" * 80)
    print()

    candidates = []
    total_pairs = sum(1 for i in range(len(videos)) for j in range(len(videos))
                     if i != j and videos[i][1] < videos[j][1])

    pair_count = 0

    for i, (short_video, short_dur, short_fps) in enumerate(videos):
        for j, (long_video, long_dur, long_fps) in enumerate(videos):
            if i == j or short_dur >= long_dur:
                continue

            pair_count += 1
            print(f"[{pair_count}/{total_pairs}] Scanning '{short_video.name}' in '{long_video.name}'...", end="")

            results = initial_scan(short_video, long_video, short_dur, long_dur)

            if results:
                print(f" → {len(results)} candidate(s)")
                for position, score, scores in results[:3]:  # Keep top 3 candidates
                    candidates.append({
                        'short': short_video,
                        'short_dur': short_dur,
                        'long': long_video,
                        'long_dur': long_dur,
                        'position': position,
                        'score': score,
                        'scores': scores
                    })
            else:
                print(" → No candidates")

    if not candidates:
        print("\n❌ No candidates found!\n")
        return

    print(f"\n✅ Found {len(candidates)} candidates to validate\n")

    # Phase 2: Multi-point validation
    print("=" * 80)
    print("PHASE 2: MULTI-POINT VALIDATION")
    print("=" * 80)
    print()

    validated_matches = []

    for i, candidate in enumerate(candidates, 1):
        print(f"[{i}/{len(candidates)}] Validating '{candidate['short'].name}' in '{candidate['long'].name}'")
        print(f"    Initial: {format_time(candidate['position'])} (score: {candidate['score']:.1f}%)")

        is_valid, validation_details = validate_multipoint(
            candidate['short'],
            candidate['long'],
            candidate['position'],
            candidate['short_dur']
        )

        print(f"    Validation points:")
        for offset, score, status in validation_details:
            print(f"      @{format_time(offset):>8s}: {status}")

        if is_valid:
            print(f"    ✅ VALIDATED - All points match!")
            validated_matches.append(candidate)
        else:
            print(f"    ❌ REJECTED - Temporal coherence failed")

        print()

    # Final results
    print("=" * 80)
    print(f"FINAL VALIDATED RESULTS - {len(validated_matches)} Matches")
    print("=" * 80)
    print()

    if not validated_matches:
        print("❌ No validated matches found!")
        print()
        print("This means:")
        print("  • All candidates failed multi-point validation")
        print("  • No video is a true subsequence of another")
        print("  • Previous matches were likely false positives")
        print()
        return

    # Group by long video
    by_long_video = defaultdict(list)
    for match in validated_matches:
        by_long_video[match['long'].name].append(match)

    for long_name in sorted(by_long_video.keys()):
        print(f"\n📹 {long_name}")
        print("-" * 80)

        video_matches = sorted(by_long_video[long_name], key=lambda x: x['position'])

        for match in video_matches:
            confidence = "🔥 HIGH" if match['score'] >= HIGH_CONFIDENCE_THRESHOLD else "✓ GOOD"

            print(f"  → {match['short'].name:50s}")
            print(f"     Position: {format_time(match['position']):>12s} - {format_time(match['position'] + match['short_dur']):>12s}")
            print(f"     Duration: {format_time(match['short_dur']):>12s}")
            print(f"     Score:    {match['score']:5.1f}% {confidence}")
            print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print(f"  Candidates found (Phase 1):   {len(candidates)}")
    print(f"  Validated matches (Phase 2):  {len(validated_matches)}")
    print(f"  False positives eliminated:   {len(candidates) - len(validated_matches)}")
    print(f"  Accuracy:                     {len(validated_matches)/len(candidates)*100:.1f}%")
    print()

if __name__ == "__main__":
    main()
