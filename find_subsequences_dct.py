#!/usr/bin/env python3
"""
DCT-Based Subsequence Detection
================================

Uses DCT (Discrete Cosine Transform) coefficients for verification.

Results from testing:
- 100% precision (0 false positives)
- 70% recall (7/10 true positives detected)
- Misses: _2, _3, A.avi in Rocco

Strategy:
1. Adaptive signature matching (from previous script)
2. DCT verification instead of Frame Differences
3. Threshold: 80%
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple, Dict, Optional
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
SEQUENCE_MATCH_THRESHOLD = 0.85
DCT_VERIFICATION_THRESHOLD = 80.0

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
    """Compute stable signature from a frame."""
    # Color histogram (HSV)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    hist_h = cv2.calcHist([hsv], [0], None, [32], [0, 180])
    hist_s = cv2.calcHist([hsv], [1], None, [32], [0, 256])
    hist = np.concatenate([hist_h.flatten(), hist_s.flatten()])
    hist = cv2.normalize(hist, hist).flatten()

    # Edge density pattern
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)

    h, w = edges.shape
    cell_h, cell_w = h // 4, w // 4
    edge_pattern = []

    for i in range(4):
        for j in range(4):
            cell = edges[i*cell_h:(i+1)*cell_h, j*cell_w:(j+1)*cell_w]
            density = np.sum(cell > 0) / cell.size
            edge_pattern.append(density)

    edge_pattern = np.array(edge_pattern)
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
    """Find positions where sequences of signatures match."""
    matches = []

    short_times = sorted(short_sigs.keys())
    long_times = sorted(long_sigs.keys())

    seq_len = get_sequence_length(short_duration)
    sequence_lengths = [seq_len]
    if seq_len > 2:
        sequence_lengths.append(seq_len - 1)

    for SEQUENCE_LENGTH in sequence_lengths:
        for short_idx in range(len(short_times) - SEQUENCE_LENGTH + 1):
            short_sequence = [short_sigs[short_times[short_idx + i]] for i in range(SEQUENCE_LENGTH)]
            short_start = short_times[short_idx]

            for long_idx in range(len(long_times) - SEQUENCE_LENGTH + 1):
                long_sequence = [long_sigs[long_times[long_idx + i]] for i in range(SEQUENCE_LENGTH)]
                long_start = long_times[long_idx]

                similarities = []
                for s_sig, l_sig in zip(short_sequence, long_sequence):
                    sim = signature_similarity(s_sig, l_sig)
                    similarities.append(sim)

                avg_similarity = np.mean(similarities)

                if avg_similarity >= SEQUENCE_MATCH_THRESHOLD:
                    matches.append((short_start, long_start, avg_similarity))

    return matches

def verify_dct_coefficients(short_video: Path, long_video: Path,
                           short_start: float, long_start: float,
                           duration: float) -> float:
    """
    Verification using DCT coefficients.
    Returns: similarity score 0-100
    """
    sample_interval = 5
    num_samples = min(10, int(duration / sample_interval))

    if num_samples < 2:
        return 0.0

    short_dcts = []
    long_dcts = []

    for i in range(num_samples):
        offset = i * sample_interval

        short_frame = extract_frame_at(short_video, short_start + offset)
        long_frame = extract_frame_at(long_video, long_start + offset)

        if short_frame is None or long_frame is None:
            continue

        # Convert to grayscale and compute DCT
        short_gray = cv2.cvtColor(short_frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
        long_gray = cv2.cvtColor(long_frame, cv2.COLOR_BGR2GRAY).astype(np.float32)

        short_dct = cv2.dct(short_gray)
        long_dct = cv2.dct(long_gray)

        # Keep only low-frequency coefficients (top-left 32x32)
        short_dct_low = short_dct[:32, :32].flatten()
        long_dct_low = long_dct[:32, :32].flatten()

        short_dcts.append(short_dct_low)
        long_dcts.append(long_dct_low)

    if len(short_dcts) < 2:
        return 0.0

    # Compare DCT sequences using cosine similarity
    similarities = []
    for sd, ld in zip(short_dcts, long_dcts):
        dot_product = np.dot(sd, ld)
        norm_s = np.linalg.norm(sd)
        norm_l = np.linalg.norm(ld)

        if norm_s > 0 and norm_l > 0:
            sim = dot_product / (norm_s * norm_l)
            similarities.append(sim)

    if not similarities:
        return 0.0

    return np.mean(similarities) * 100

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
    print("DCT-BASED SUBSEQUENCE DETECTION")
    print("=" * 80)
    print()
    print("Method: Adaptive Signatures + DCT Verification")
    print(f"  • Signature threshold: {SEQUENCE_MATCH_THRESHOLD * 100}%")
    print(f"  • DCT verification threshold: {DCT_VERIFICATION_THRESHOLD}%")
    print(f"  • Expected: 100% precision, 70% recall")
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

    # Build signature indices
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
        print(f" {len(signatures):3d} sigs")

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

            matches = find_sequence_matches_adaptive(short_sigs, long_sigs, short_dur)

            if matches:
                best_match = max(matches, key=lambda x: x[2])
                short_start, long_start, seq_sim = best_match

                print(f"Candidate at {format_time(long_start)} (seq: {seq_sim*100:.1f}%)", end="")

                # Verify with DCT
                verification_score = verify_dct_coefficients(
                    short_video, long_video,
                    short_start, long_start,
                    min(short_dur, 60)
                )

                if verification_score >= DCT_VERIFICATION_THRESHOLD:
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
