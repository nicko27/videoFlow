#!/usr/bin/env python3
"""
Adaptive Signature-Based Subsequence Detection
===============================================

Improvements over basic signature method:
1. Adaptive sampling interval based on video duration
   - Short videos (<10min): sample every 15s
   - Medium videos (10-30min): sample every 20s
   - Long videos (>30min): sample every 30s

2. Adaptive sequence matching
   - Very short videos (<5min): match 2 consecutive signatures
   - Short videos (5-15min): match 3 consecutive signatures
   - Long videos (>15min): match 4 consecutive signatures

3. Multi-scale verification
   - Test multiple sequence lengths and take best match
   - Lower sequence threshold to 85% but require higher verification (90%)

4. Sliding window search
   - Instead of fixed intervals, use sliding window with overlap
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import sys
from collections import defaultdict

# Paths
DOWNLOADS_DIR = Path("/Users/nico/Downloads")

# Adaptive parameters
def get_sample_interval(duration: float) -> int:
    """Get sampling interval based on video duration."""
    if duration < 600:  # < 10 min
        return 15
    elif duration < 1800:  # < 30 min
        return 20
    else:
        return 30

def get_sequence_length(duration: float) -> int:
    """Get sequence length based on video duration."""
    if duration < 300:  # < 5 min
        return 2
    elif duration < 900:  # < 15 min
        return 3
    else:
        return 4

# Matching thresholds
SEQUENCE_MATCH_THRESHOLD = 0.85  # Lowered from 0.90
VERIFICATION_THRESHOLD = 90.0    # Increased from 85.0

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

def extract_frame_at(video_path: Path, time_sec: float) -> Optional[np.ndarray]:
    """Extract a single frame at specific time."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return None

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_num = int(time_sec * fps)

    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
    ret, frame = cap.read()
    cap.release()

    if ret:
        return cv2.resize(frame, (320, 180))
    return None

def compute_stable_signature(frame: np.ndarray) -> np.ndarray:
    """
    Compute stable signature from a frame.
    Uses Color Histogram + Edge Density (both stable over 120s).
    """
    # Color histogram (HSV)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    hist_h = cv2.calcHist([hsv], [0], None, [32], [0, 180])
    hist_s = cv2.calcHist([hsv], [1], None, [32], [0, 256])
    hist = np.concatenate([hist_h.flatten(), hist_s.flatten()])
    hist = cv2.normalize(hist, hist).flatten()

    # Edge density pattern
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)

    # Divide into 4x4 grid and compute edge density per cell
    h, w = edges.shape
    cell_h, cell_w = h // 4, w // 4
    edge_pattern = []

    for i in range(4):
        for j in range(4):
            cell = edges[i*cell_h:(i+1)*cell_h, j*cell_w:(j+1)*cell_w]
            density = np.sum(cell > 0) / cell.size
            edge_pattern.append(density)

    edge_pattern = np.array(edge_pattern)

    # Combine: 64 color bins + 16 edge cells = 80-dimensional signature
    signature = np.concatenate([hist, edge_pattern])

    return signature

def build_signature_index(video_path: Path, duration: float, interval: int) -> Dict[float, np.ndarray]:
    """Build index of stable signatures for a video."""
    signatures = {}
    num_samples = int(duration / interval) + 1

    for i in range(num_samples):
        time_sec = i * interval
        if time_sec >= duration:
            break

        frame = extract_frame_at(video_path, time_sec)
        if frame is not None:
            signatures[time_sec] = compute_stable_signature(frame)

    return signatures

def signature_similarity(sig1: np.ndarray, sig2: np.ndarray) -> float:
    """Compute similarity between two signatures using cosine similarity."""
    dot_product = np.dot(sig1, sig2)
    norm1 = np.linalg.norm(sig1)
    norm2 = np.linalg.norm(sig2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)

def find_sequence_matches_adaptive(short_sigs: Dict[float, np.ndarray],
                                   long_sigs: Dict[float, np.ndarray],
                                   short_duration: float) -> List[Tuple[float, float, float]]:
    """
    Find positions where sequences of signatures match.
    Uses adaptive sequence length based on short video duration.
    """
    matches = []

    short_times = sorted(short_sigs.keys())
    long_times = sorted(long_sigs.keys())

    # Adaptive sequence length
    seq_len = get_sequence_length(short_duration)

    # Try multiple sequence lengths for robustness
    sequence_lengths = [seq_len]
    if seq_len > 2:
        sequence_lengths.append(seq_len - 1)

    for SEQUENCE_LENGTH in sequence_lengths:
        # For each possible sequence start in short video
        for short_idx in range(len(short_times) - SEQUENCE_LENGTH + 1):
            # Get sequence from short video
            short_sequence = [short_sigs[short_times[short_idx + i]] for i in range(SEQUENCE_LENGTH)]
            short_start = short_times[short_idx]

            # Try to find this sequence in long video
            for long_idx in range(len(long_times) - SEQUENCE_LENGTH + 1):
                # Get sequence from long video
                long_sequence = [long_sigs[long_times[long_idx + i]] for i in range(SEQUENCE_LENGTH)]
                long_start = long_times[long_idx]

                # Compute average similarity across the sequence
                similarities = []
                for s_sig, l_sig in zip(short_sequence, long_sequence):
                    sim = signature_similarity(s_sig, l_sig)
                    similarities.append(sim)

                avg_similarity = np.mean(similarities)

                # If sequence matches well enough
                if avg_similarity >= SEQUENCE_MATCH_THRESHOLD:
                    matches.append((short_start, long_start, avg_similarity))

    return matches

def verify_with_frame_differences(short_video: Path, long_video: Path,
                                  short_start: float, long_start: float,
                                  duration: float) -> float:
    """
    Final verification using Frame Differences.
    Uses adaptive verification duration based on video length.
    """
    # Adaptive verification duration
    verification_duration = min(60, duration * 0.6)  # Use 60% of video or 60s max

    # Extract frames for verification
    ref_frames = []
    cand_frames = []

    sample_interval = 3  # Sample every 3 seconds
    for offset in range(0, int(verification_duration), sample_interval):
        ref_frame = extract_frame_at(short_video, short_start + offset)
        cand_frame = extract_frame_at(long_video, long_start + offset)

        if ref_frame is not None and cand_frame is not None:
            ref_frames.append(ref_frame)
            cand_frames.append(cand_frame)

    if len(ref_frames) < 3:  # Need at least 3 frames
        return 0.0

    # Compute frame differences
    ref_diffs = []
    for i in range(len(ref_frames) - 1):
        gray1 = cv2.cvtColor(ref_frames[i], cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(ref_frames[i + 1], cv2.COLOR_BGR2GRAY)
        diff = cv2.absdiff(gray1, gray2)
        ref_diffs.append(np.mean(diff))

    cand_diffs = []
    for i in range(len(cand_frames) - 1):
        gray1 = cv2.cvtColor(cand_frames[i], cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(cand_frames[i + 1], cv2.COLOR_BGR2GRAY)
        diff = cv2.absdiff(gray1, gray2)
        cand_diffs.append(np.mean(diff))

    # Normalize and compare
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
    print("ADAPTIVE SIGNATURE-BASED SUBSEQUENCE DETECTION")
    print("=" * 80)
    print()
    print("Improvements:")
    print("  • Adaptive sampling: 15-30s based on video duration")
    print("  • Adaptive sequence length: 2-4 signatures based on duration")
    print("  • Multi-scale matching for robustness")
    print("  • Sequence threshold: 85% (was 90%)")
    print("  • Verification threshold: 90% (was 85%)")
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

    # Build signature indices with adaptive intervals
    print("=" * 80)
    print("BUILDING ADAPTIVE SIGNATURE INDICES")
    print("=" * 80)
    print()

    video_signatures = {}

    for video, duration, fps in videos:
        interval = get_sample_interval(duration)
        seq_len = get_sequence_length(duration)

        print(f"  {video.name:60s}", end="", flush=True)
        signatures = build_signature_index(video, duration, interval)
        video_signatures[video] = (signatures, interval, seq_len)
        print(f" {len(signatures):3d} sigs (interval={interval}s, seq_len={seq_len})")

    print()

    # Search for subsequences
    print("=" * 80)
    print("SEARCHING FOR SEQUENCE MATCHES")
    print("=" * 80)
    print()

    validated_matches = []
    total_pairs = sum(1 for i in range(len(videos)) for j in range(len(videos))
                     if i != j and videos[i][1] < videos[j][1])

    pair_count = 0

    for i, (short_video, short_dur, _) in enumerate(videos):
        for j, (long_video, long_dur, _) in enumerate(videos):
            if i == j or short_dur >= long_dur:
                continue

            pair_count += 1
            print(f"[{pair_count}/{total_pairs}] '{short_video.name}' in '{long_video.name}'...", end=" ")

            short_sigs, _, _ = video_signatures[short_video]
            long_sigs, _, _ = video_signatures[long_video]

            # Find sequence matches with adaptive parameters
            matches = find_sequence_matches_adaptive(short_sigs, long_sigs, short_dur)

            if matches:
                # Get best match
                best_match = max(matches, key=lambda x: x[2])
                short_start, long_start, seq_sim = best_match

                print(f"Candidate at {format_time(long_start)} (seq: {seq_sim*100:.1f}%)", end="")

                # Verify with Frame Differences
                verification_score = verify_with_frame_differences(
                    short_video, long_video,
                    short_start, long_start,
                    short_dur
                )

                if verification_score >= VERIFICATION_THRESHOLD:
                    print(f" → ✅ VERIFIED ({verification_score:.1f}%)")

                    validated_matches.append({
                        'short': short_video,
                        'short_dur': short_dur,
                        'long': long_video,
                        'position': long_start,
                        'sequence_similarity': seq_sim * 100,
                        'verification_score': verification_score
                    })
                else:
                    print(f" → ❌ REJECTED ({verification_score:.1f}%)")
            else:
                print("❌ No sequence match")

    print()

    # Results
    print("=" * 80)
    print(f"VALIDATED RESULTS - {len(validated_matches)} True Subsequences")
    print("=" * 80)
    print()

    if not validated_matches:
        print("❌ No subsequences found!")
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
            confidence = "🔥 HIGH" if match['verification_score'] >= 95 else "✓ GOOD"

            print(f"  → {match['short'].name:50s}")
            print(f"     Position:    {format_time(match['position']):>12s} - {format_time(match['position'] + match['short_dur']):>12s}")
            print(f"     Duration:    {format_time(match['short_dur']):>12s}")
            print(f"     Seq Match:   {match['sequence_similarity']:5.1f}%")
            print(f"     Verified:    {match['verification_score']:5.1f}% {confidence}")
            print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print(f"  Pairs checked:        {total_pairs}")
    print(f"  Validated matches:    {len(validated_matches)}")
    print()

if __name__ == "__main__":
    main()
