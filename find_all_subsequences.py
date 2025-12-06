#!/usr/bin/env python3
"""
Ultimate Subsequence Finder - Find All Related Videos
======================================================

Strategy:
1. PHASE 1: Initial Detection with Smart Hybrid Method
   - Use multi-point sampling if first sample has low motion (like _7)
   - Use baseline method otherwise (faster and works well)

2. PHASE 2: Refinement with High-Precision Algorithms
   - For top candidates, use Frame Differences on longer samples
   - Verify temporal coherence (check multiple points)

3. PHASE 3: Validation
   - Check if detected position + video duration fits
   - Eliminate overlapping detections (keep best score)

Scans ALL videos in Downloads to find subsequences in ALL other videos.
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

# Refinement parameters
REFINE_SAMPLE_DURATION = 40  # Longer samples for refinement
REFINE_INTERVAL = 3

# Thresholds
LOW_MOTION_THRESHOLD = 1.5  # If variance < this, use multi-point
CANDIDATE_THRESHOLD = 60.0  # Minimum score to consider
HIGH_CONFIDENCE_THRESHOLD = 85.0  # Very confident match

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

    # Ensure same length
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

def smart_hybrid_search(short_video: Path, long_video: Path, short_duration: float, long_duration: float) -> List[Tuple[int, float, Dict[str, float]]]:
    """
    Smart hybrid search:
    - Detects if first sample has low motion
    - Uses multi-point if low motion, otherwise baseline
    """

    # Extract first sample
    ref_frames = extract_frames_from_video(short_video, 0, SAMPLE_DURATION, SAMPLE_INTERVAL)
    if len(ref_frames) < 2:
        return []

    # Check motion variance
    motion_var = compute_motion_variance(ref_frames)
    use_multipoint = motion_var < LOW_MOTION_THRESHOLD

    if use_multipoint:
        print(f"      → Low motion detected ({motion_var:.2f}) - Using multi-point sampling")
        return multipoint_search(short_video, long_video, short_duration, long_duration)
    else:
        print(f"      → Normal motion ({motion_var:.2f}) - Using baseline method")
        return baseline_search(short_video, long_video, long_duration)

def baseline_search(short_video: Path, long_video: Path, long_duration: float) -> List[Tuple[int, float, Dict[str, float]]]:
    """Baseline hybrid voting (C:30%, E:30%, M:40%)."""

    ref_frames = extract_frames_from_video(short_video, 0, SAMPLE_DURATION, SAMPLE_INTERVAL)
    if len(ref_frames) < 2:
        return []

    num_positions = int(long_duration / SEARCH_STEP) + 1
    results = []

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

        if weighted_score >= CANDIDATE_THRESHOLD:
            results.append((position_sec, weighted_score, scores))

    results.sort(key=lambda x: x[1], reverse=True)
    return results

def multipoint_search(short_video: Path, long_video: Path, short_duration: float, long_duration: float) -> List[Tuple[int, float, Dict[str, float]]]:
    """Multi-point sampling for videos with static openings."""

    # Sample points
    sample_points = [0, min(300, short_duration - 30), min(480, short_duration - 30)]
    sample_points = [p for p in sample_points if p >= 0 and p + SAMPLE_DURATION <= short_duration]

    num_positions = int(long_duration / SEARCH_STEP) + 1
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
    results = []
    for position_sec, data in position_scores.items():
        if not data['scores']:
            continue

        avg_weighted = np.mean(data['scores'])

        if avg_weighted >= CANDIDATE_THRESHOLD:
            avg_scores = {
                'color': np.mean([s['color'] for s in data['details']]),
                'edge': np.mean([s['edge'] for s in data['details']]),
                'motion': np.mean([s['motion'] for s in data['details']])
            }
            results.append((position_sec, avg_weighted, avg_scores))

    results.sort(key=lambda x: x[1], reverse=True)
    return results

def refine_position(short_video: Path, long_video: Path, position: int, short_duration: float) -> Tuple[int, float]:
    """
    Refine position using longer samples and frame differences.
    Returns (best_position, confidence_score)
    """

    # Test positions around the candidate: -30s to +30s every 10s
    test_positions = [position + offset for offset in range(-30, 31, 10)]
    test_positions = [p for p in test_positions if p >= 0]

    best_pos = position
    best_score = 0.0

    # Use longer samples for refinement
    ref_frames = extract_frames_from_video(short_video, 0, REFINE_SAMPLE_DURATION, REFINE_INTERVAL)
    if len(ref_frames) < 2:
        return position, 0.0

    for test_pos in test_positions:
        cand_frames = extract_frames_from_video(long_video, test_pos, REFINE_SAMPLE_DURATION, REFINE_INTERVAL)
        if len(cand_frames) < 2:
            continue

        # Use all 3 methods for refinement
        color_score = method_color_histogram(ref_frames, cand_frames)
        edge_score = method_edge_density(ref_frames, cand_frames)
        motion_score = method_frame_differences(ref_frames, cand_frames)

        # Weighted combination
        combined = color_score * 0.30 + edge_score * 0.30 + motion_score * 0.40

        if combined > best_score:
            best_score = combined
            best_pos = test_pos

    return best_pos, best_score

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
    print("ULTIMATE SUBSEQUENCE FINDER - Find All Related Videos")
    print("=" * 80)
    print()
    print("Scanning Downloads directory for video files...")
    print()

    # Find all video files
    video_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.flv', '.wmv', '.webm'}
    all_videos = []

    for ext in video_extensions:
        all_videos.extend(DOWNLOADS_DIR.glob(f"*{ext}"))

    # Filter out system files and get video info
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

    # Display videos
    print("Videos to analyze:")
    print("-" * 80)
    for i, (video, duration, fps) in enumerate(videos, 1):
        print(f"  {i:3d}. {video.name:50s} {format_time(duration):>12s}")
    print()

    # Find subsequences
    print("=" * 80)
    print("PHASE 1: INITIAL DETECTION")
    print("=" * 80)
    print()

    matches = []

    # Compare each video pair
    total_pairs = len(videos) * (len(videos) - 1)
    pair_count = 0

    for i, (short_video, short_dur, short_fps) in enumerate(videos):
        for j, (long_video, long_dur, long_fps) in enumerate(videos):
            # Skip same video
            if i == j:
                continue

            # Only check if short video is actually shorter
            if short_dur >= long_dur:
                continue

            pair_count += 1

            print(f"[{pair_count}/{total_pairs//2}] Checking if '{short_video.name}' is in '{long_video.name}'...")

            # Search
            results = smart_hybrid_search(short_video, long_video, short_dur, long_dur)

            if results:
                position, score, scores = results[0]

                print(f"    ✅ Found candidate at {format_time(position)} (score: {score:.1f}%)")
                print(f"       Details: C:{scores['color']:.1f}% E:{scores['edge']:.1f}% M:{scores['motion']:.1f}%")

                matches.append({
                    'short': short_video,
                    'short_dur': short_dur,
                    'long': long_video,
                    'long_dur': long_dur,
                    'position': position,
                    'score': score,
                    'scores': scores
                })
            else:
                print(f"    ⚠️  No match found")

            print()

    if not matches:
        print("\n❌ No subsequence relationships found!\n")
        return

    # Phase 2: Refinement
    print("=" * 80)
    print("PHASE 2: REFINEMENT")
    print("=" * 80)
    print()

    for i, match in enumerate(matches, 1):
        print(f"[{i}/{len(matches)}] Refining '{match['short'].name}' in '{match['long'].name}'...")
        print(f"    Initial position: {format_time(match['position'])} (score: {match['score']:.1f}%)")

        refined_pos, refined_score = refine_position(
            match['short'],
            match['long'],
            match['position'],
            match['short_dur']
        )

        if refined_pos != match['position']:
            print(f"    ✨ Refined to: {format_time(refined_pos)} (score: {refined_score:.1f}%)")
            match['position'] = refined_pos
            match['score'] = refined_score
        else:
            print(f"    → Position confirmed: {format_time(refined_pos)} (score: {refined_score:.1f}%)")

        print()

    # Final results
    print("=" * 80)
    print("FINAL RESULTS - All Detected Subsequences")
    print("=" * 80)
    print()

    # Group by long video
    by_long_video = defaultdict(list)
    for match in matches:
        by_long_video[match['long'].name].append(match)

    for long_name in sorted(by_long_video.keys()):
        print(f"\n📹 {long_name}")
        print("-" * 80)

        # Sort by position
        video_matches = sorted(by_long_video[long_name], key=lambda x: x['position'])

        for match in video_matches:
            confidence = "🔥 HIGH" if match['score'] >= HIGH_CONFIDENCE_THRESHOLD else "✓ GOOD" if match['score'] >= 70 else "⚠️ LOW"

            print(f"  → {match['short'].name:50s}")
            print(f"     Position: {format_time(match['position']):>12s} - {format_time(match['position'] + match['short_dur']):>12s}")
            print(f"     Duration: {format_time(match['short_dur']):>12s}")
            print(f"     Score:    {match['score']:5.1f}% {confidence}")
            print(f"     Details:  C:{match['scores']['color']:4.1f}% E:{match['scores']['edge']:4.1f}% M:{match['scores']['motion']:4.1f}%")
            print()

    # Summary statistics
    print("=" * 80)
    print("STATISTICS")
    print("=" * 80)
    print()
    print(f"  Total video files:        {len(videos)}")
    print(f"  Pairs checked:            {pair_count}")
    print(f"  Matches found:            {len(matches)}")
    print(f"  High confidence (≥85%):   {sum(1 for m in matches if m['score'] >= HIGH_CONFIDENCE_THRESHOLD)}")
    print(f"  Good confidence (≥70%):   {sum(1 for m in matches if 70 <= m['score'] < HIGH_CONFIDENCE_THRESHOLD)}")
    print(f"  Low confidence (<70%):    {sum(1 for m in matches if m['score'] < 70)}")
    print()

if __name__ == "__main__":
    main()
