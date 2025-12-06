#!/usr/bin/env python3
"""
Test All Verification Methods
==============================

Tests 8 different verification methods to see which ones can correctly
validate the Das Monster subsequences that have high signature similarity
but failed Frame Differences verification.

Test cases (from adaptive script results):
- _2: signature 99.7% but verification 38.0%
- _3: signature 99.4% but verification 0.0%
- _6: signature 99.7% but verification 5.2%
- _7: signature 99.5% but verification 8.2%
- _8: signature 99.7% but verification 14.0%
- _9: signature 97.7% but verification 4.2%

Known good positions:
- _1: 0m00s ✓
- _2: 20m30s (approximately)
- _3: 24m00s (approximately)
- _4: 30m00s ✓
- _5: 40m00s ✓
- _6: 50m00s (approximately)
- _7: 60m00s (approximately)
- _8: 70m00s (approximately)
- _9: 80m00s (approximately)
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Tuple, Optional
import scipy.signal
from scipy.fft import fft
from skimage.feature import local_binary_pattern

# Paths
DOWNLOADS_DIR = Path("/Users/nico/Downloads")

# Test cases: (short_video, long_video, expected_position, should_match)
# should_match: True = should validate (true positive), False = should reject (true negative)
TEST_CASES = [
    # TRUE POSITIVES - Das Monster subsequences (should score >= 80%)
    ("Das Monster und die Schone_1.mp4", "Das Monster und die Schone.mp4", 0, True),      # Known good (0m)
    ("Das Monster und die Schone_2.mp4", "Das Monster und die Schone.mp4", 1230, True),   # 20m30s
    ("Das Monster und die Schone_3.mp4", "Das Monster und die Schone.mp4", 1440, True),   # 24m00s
    ("Das Monster und die Schone_4.mp4", "Das Monster und die Schone.mp4", 1800, True),   # Known good (30m)
    ("Das Monster und die Schone_5.mp4", "Das Monster und die Schone.mp4", 2400, True),   # Known good (40m)
    ("Das Monster und die Schone_6.mp4", "Das Monster und die Schone.mp4", 3000, True),   # 50m00s
    ("Das Monster und die Schone_7.mp4", "Das Monster und die Schone.mp4", 3600, True),   # 60m00s
    ("Das Monster und die Schone_8.mp4", "Das Monster und die Schone.mp4", 4200, True),   # 70m00s
    ("Das Monster und die Schone_9.mp4", "Das Monster und die Schone.mp4", 4800, True),   # 80m00s

    # TRUE POSITIVE - A.avi in Rocco's Initiations (should score >= 80%)
    ("A.avi", "Rocco's Initiations 5 (1).avi", 420, True),  # 7m00s

    # FALSE POSITIVES to reject - Das Monster vs wrong videos (should score < 80%)
    ("Das Monster und die Schone_1.mp4", "A.avi", 0, False),           # Wrong video
    ("Das Monster und die Schone_1.mp4", "Rocco's Initiations 5 (1).avi", 0, False),  # Wrong video
    ("Das Monster und die Schone_4.mp4", "A.avi", 450, False),         # Wrong position

    # FALSE POSITIVES to reject - A.avi vs wrong videos (should score < 80%)
    ("A.avi", "Das Monster und die Schone.mp4", 420, False),           # Wrong video
    ("A.avi", "Das Monster und die Schone.mp4", 2400, False),          # Wrong video, wrong position
]

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

def extract_audio_segment(video_path: Path, start_sec: float, duration_sec: float) -> Optional[np.ndarray]:
    """Extract audio segment (simplified - returns None if no audio or error)."""
    try:
        # This would require ffmpeg or librosa
        # For now, return None to skip audio-based methods
        return None
    except:
        return None

# ============================================================================
# METHOD 1: Color Histogram Temporal
# ============================================================================
def verify_color_histogram_temporal(short_video: Path, long_video: Path,
                                   short_start: float, long_start: float,
                                   duration: float) -> float:
    """
    Compare temporal sequence of color histograms.
    Returns: similarity score 0-100
    """
    # Sample every 5 seconds
    sample_interval = 5
    num_samples = min(10, int(duration / sample_interval))

    if num_samples < 2:
        return 0.0

    short_hists = []
    long_hists = []

    for i in range(num_samples):
        offset = i * sample_interval

        short_frame = extract_frame_at(short_video, short_start + offset)
        long_frame = extract_frame_at(long_video, long_start + offset)

        if short_frame is None or long_frame is None:
            continue

        # Compute HSV histograms
        short_hsv = cv2.cvtColor(short_frame, cv2.COLOR_BGR2HSV)
        long_hsv = cv2.cvtColor(long_frame, cv2.COLOR_BGR2HSV)

        short_hist = cv2.calcHist([short_hsv], [0, 1], None, [32, 32], [0, 180, 0, 256])
        long_hist = cv2.calcHist([long_hsv], [0, 1], None, [32, 32], [0, 180, 0, 256])

        short_hist = cv2.normalize(short_hist, short_hist).flatten()
        long_hist = cv2.normalize(long_hist, long_hist).flatten()

        short_hists.append(short_hist)
        long_hists.append(long_hist)

    if len(short_hists) < 2:
        return 0.0

    # Compare sequences using Bhattacharyya distance
    similarities = []
    for sh, lh in zip(short_hists, long_hists):
        # Bhattacharyya coefficient
        bc = np.sum(np.sqrt(sh * lh))
        similarities.append(bc)

    return np.mean(similarities) * 100

# ============================================================================
# METHOD 2: Scene Cuts Alignment
# ============================================================================
def detect_scene_cuts(video_path: Path, start_sec: float, duration_sec: float) -> list:
    """
    Detect scene cuts in a video segment.
    Returns: list of timestamps (relative to start_sec)
    """
    cuts = []

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return cuts

    fps = cap.get(cv2.CAP_PROP_FPS)
    start_frame = int(start_sec * fps)
    end_frame = int((start_sec + duration_sec) * fps)

    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    prev_frame = None
    threshold = 30.0  # Scene cut threshold

    for frame_idx in range(start_frame, min(end_frame, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)))):
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (160, 90))

        if prev_frame is not None:
            diff = cv2.absdiff(gray, prev_frame)
            mean_diff = np.mean(diff)

            if mean_diff > threshold:
                timestamp = (frame_idx - start_frame) / fps
                cuts.append(timestamp)

        prev_frame = gray

    cap.release()
    return cuts

def verify_scene_cuts_alignment(short_video: Path, long_video: Path,
                                short_start: float, long_start: float,
                                duration: float) -> float:
    """
    Compare scene cut patterns.
    Returns: similarity score 0-100
    """
    short_cuts = detect_scene_cuts(short_video, short_start, duration)
    long_cuts = detect_scene_cuts(long_video, long_start, duration)

    if len(short_cuts) == 0 and len(long_cuts) == 0:
        return 100.0  # No cuts in either = perfect match

    if len(short_cuts) == 0 or len(long_cuts) == 0:
        return 0.0

    # Find matching cuts (within 2 seconds tolerance)
    matches = 0
    for sc in short_cuts:
        for lc in long_cuts:
            if abs(sc - lc) < 2.0:
                matches += 1
                break

    # Score based on matched cuts
    max_cuts = max(len(short_cuts), len(long_cuts))
    return (matches / max_cuts) * 100

# ============================================================================
# METHOD 3: Audio Fingerprint (SKIPPED - requires librosa)
# ============================================================================
def verify_audio_fingerprint(short_video: Path, long_video: Path,
                             short_start: float, long_start: float,
                             duration: float) -> float:
    """Audio fingerprint verification - SKIPPED (requires additional libraries)"""
    return -1.0  # Return -1 to indicate "not tested"

# ============================================================================
# METHOD 4: DCT (Discrete Cosine Transform)
# ============================================================================
def verify_dct_coefficients(short_video: Path, long_video: Path,
                           short_start: float, long_start: float,
                           duration: float) -> float:
    """
    Compare DCT coefficients of frames.
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
        # Cosine similarity
        dot_product = np.dot(sd, ld)
        norm_s = np.linalg.norm(sd)
        norm_l = np.linalg.norm(ld)

        if norm_s > 0 and norm_l > 0:
            sim = dot_product / (norm_s * norm_l)
            similarities.append(sim)

    if not similarities:
        return 0.0

    return np.mean(similarities) * 100

# ============================================================================
# METHOD 5: Optical Flow Pattern
# ============================================================================
def verify_optical_flow_pattern(short_video: Path, long_video: Path,
                                short_start: float, long_start: float,
                                duration: float) -> float:
    """
    Compare optical flow patterns (direction, not magnitude).
    Returns: similarity score 0-100
    """
    sample_interval = 3
    num_samples = min(15, int(duration / sample_interval) - 1)

    if num_samples < 2:
        return 0.0

    short_flows = []
    long_flows = []

    for i in range(num_samples):
        offset = i * sample_interval

        short_f1 = extract_frame_at(short_video, short_start + offset)
        short_f2 = extract_frame_at(short_video, short_start + offset + 1)
        long_f1 = extract_frame_at(long_video, long_start + offset)
        long_f2 = extract_frame_at(long_video, long_start + offset + 1)

        if None in [short_f1, short_f2, long_f1, long_f2]:
            continue

        # Convert to grayscale
        short_g1 = cv2.cvtColor(short_f1, cv2.COLOR_BGR2GRAY)
        short_g2 = cv2.cvtColor(short_f2, cv2.COLOR_BGR2GRAY)
        long_g1 = cv2.cvtColor(long_f1, cv2.COLOR_BGR2GRAY)
        long_g2 = cv2.cvtColor(long_f2, cv2.COLOR_BGR2GRAY)

        # Compute optical flow
        short_flow = cv2.calcOpticalFlowFarneback(short_g1, short_g2, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        long_flow = cv2.calcOpticalFlowFarneback(long_g1, long_g2, None, 0.5, 3, 15, 3, 5, 1.2, 0)

        # Extract flow direction (angle) - ignore magnitude
        short_angle = np.arctan2(short_flow[..., 1], short_flow[..., 0])
        long_angle = np.arctan2(long_flow[..., 1], long_flow[..., 0])

        # Histogram of flow directions
        short_hist, _ = np.histogram(short_angle, bins=36, range=(-np.pi, np.pi))
        long_hist, _ = np.histogram(long_angle, bins=36, range=(-np.pi, np.pi))

        # Normalize
        short_hist = short_hist / (short_hist.sum() + 1e-7)
        long_hist = long_hist / (long_hist.sum() + 1e-7)

        short_flows.append(short_hist)
        long_flows.append(long_hist)

    if len(short_flows) < 2:
        return 0.0

    # Compare flow histograms
    similarities = []
    for sf, lf in zip(short_flows, long_flows):
        # Chi-square distance - use element-wise operations carefully
        denominator = sf + lf + 1e-7
        chi2 = float(np.sum((sf - lf) ** 2 / denominator))
        sim = 1.0 / (1.0 + chi2)
        similarities.append(sim)

    if not similarities:
        return 0.0

    return float(np.mean(similarities)) * 100

# ============================================================================
# METHOD 6: Multi-Scale Pyramid
# ============================================================================
def verify_multiscale_pyramid(short_video: Path, long_video: Path,
                              short_start: float, long_start: float,
                              duration: float) -> float:
    """
    Compare at multiple scales (resolutions).
    Returns: similarity score 0-100
    """
    sample_interval = 5
    num_samples = min(10, int(duration / sample_interval))

    if num_samples < 2:
        return 0.0

    scales = [1.0, 0.5, 0.25]  # Full, half, quarter
    scale_scores = []

    for scale in scales:
        similarities = []

        for i in range(num_samples):
            offset = i * sample_interval

            short_frame = extract_frame_at(short_video, short_start + offset)
            long_frame = extract_frame_at(long_video, long_start + offset)

            if short_frame is None or long_frame is None:
                continue

            # Resize to scale
            h, w = short_frame.shape[:2]
            new_h, new_w = int(h * scale), int(w * scale)

            short_scaled = cv2.resize(short_frame, (new_w, new_h))
            long_scaled = cv2.resize(long_frame, (new_w, new_h))

            # Compute color histogram at this scale
            short_hsv = cv2.cvtColor(short_scaled, cv2.COLOR_BGR2HSV)
            long_hsv = cv2.cvtColor(long_scaled, cv2.COLOR_BGR2HSV)

            short_hist = cv2.calcHist([short_hsv], [0, 1], None, [16, 16], [0, 180, 0, 256])
            long_hist = cv2.calcHist([long_hsv], [0, 1], None, [16, 16], [0, 180, 0, 256])

            short_hist = cv2.normalize(short_hist, short_hist).flatten()
            long_hist = cv2.normalize(long_hist, long_hist).flatten()

            # Bhattacharyya
            bc = np.sum(np.sqrt(short_hist * long_hist))
            similarities.append(bc)

        if similarities:
            scale_scores.append(np.mean(similarities))

    if not scale_scores:
        return 0.0

    # Weighted average (higher weight for larger scales)
    weights = [0.5, 0.3, 0.2]
    return np.average(scale_scores, weights=weights[:len(scale_scores)]) * 100

# ============================================================================
# METHOD 7: Keyframe Matching
# ============================================================================
def verify_keyframe_matching(short_video: Path, long_video: Path,
                            short_start: float, long_start: float,
                            duration: float) -> float:
    """
    Extract and match keyframes (high variance frames).
    Returns: similarity score 0-100
    """
    # Extract frames every 2 seconds
    sample_interval = 2
    num_samples = int(duration / sample_interval)

    if num_samples < 3:
        return 0.0

    short_frames = []
    long_frames = []

    for i in range(num_samples):
        offset = i * sample_interval

        short_frame = extract_frame_at(short_video, short_start + offset)
        long_frame = extract_frame_at(long_video, long_start + offset)

        if short_frame is not None:
            short_frames.append(short_frame)
        if long_frame is not None:
            long_frames.append(long_frame)

    if len(short_frames) < 3 or len(long_frames) < 3:
        return 0.0

    # Compute variance for each frame to find keyframes
    def frame_variance(frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return np.var(gray)

    short_vars = [frame_variance(f) for f in short_frames]
    long_vars = [frame_variance(f) for f in long_frames]

    # Select top 5 keyframes
    num_keyframes = min(5, len(short_frames))
    short_key_indices = np.argsort(short_vars)[-num_keyframes:]
    long_key_indices = np.argsort(long_vars)[-num_keyframes:]

    # Match keyframes by position
    matches = 0
    for idx in range(num_keyframes):
        if idx >= len(short_key_indices) or idx >= len(long_key_indices):
            break

        s_idx = short_key_indices[idx]
        l_idx = long_key_indices[idx]

        if s_idx >= len(short_frames) or l_idx >= len(long_frames):
            continue

        s_frame = short_frames[s_idx]
        l_frame = long_frames[l_idx]

        # Compare using histogram
        s_hist = cv2.calcHist([s_frame], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        l_hist = cv2.calcHist([l_frame], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])

        s_hist = cv2.normalize(s_hist, s_hist).flatten()
        l_hist = cv2.normalize(l_hist, l_hist).flatten()

        similarity = np.sum(np.sqrt(s_hist * l_hist))

        if similarity > 0.8:
            matches += 1

    return (matches / num_keyframes) * 100

# ============================================================================
# METHOD 8: Texture Pattern (LBP)
# ============================================================================
def verify_texture_lbp(short_video: Path, long_video: Path,
                      short_start: float, long_start: float,
                      duration: float) -> float:
    """
    Compare Local Binary Pattern (texture) histograms.
    Returns: similarity score 0-100
    """
    sample_interval = 5
    num_samples = min(10, int(duration / sample_interval))

    if num_samples < 2:
        return 0.0

    similarities = []

    # LBP parameters
    radius = 3
    n_points = 8 * radius

    for i in range(num_samples):
        offset = i * sample_interval

        short_frame = extract_frame_at(short_video, short_start + offset)
        long_frame = extract_frame_at(long_video, long_start + offset)

        if short_frame is None or long_frame is None:
            continue

        # Convert to grayscale
        short_gray = cv2.cvtColor(short_frame, cv2.COLOR_BGR2GRAY)
        long_gray = cv2.cvtColor(long_frame, cv2.COLOR_BGR2GRAY)

        # Compute LBP
        short_lbp = local_binary_pattern(short_gray, n_points, radius, method='uniform')
        long_lbp = local_binary_pattern(long_gray, n_points, radius, method='uniform')

        # Compute histograms
        short_hist, _ = np.histogram(short_lbp, bins=n_points + 2, range=(0, n_points + 2))
        long_hist, _ = np.histogram(long_lbp, bins=n_points + 2, range=(0, n_points + 2))

        # Normalize
        short_hist = short_hist / (short_hist.sum() + 1e-7)
        long_hist = long_hist / (long_hist.sum() + 1e-7)

        # Bhattacharyya coefficient
        bc = np.sum(np.sqrt(short_hist * long_hist))
        similarities.append(bc)

    if not similarities:
        return 0.0

    return np.mean(similarities) * 100

# ============================================================================
# Main Test Runner
# ============================================================================
def format_time(seconds: float) -> str:
    """Format seconds as MM:SS."""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}m{secs:02d}s"

def main():
    print("=" * 80)
    print("VERIFICATION METHODS COMPARISON TEST")
    print("=" * 80)
    print()
    print("Testing 8 verification methods on:")
    print("  - 10 TRUE POSITIVES (should score >= 80%)")
    print("  - 5 FALSE POSITIVES (should score < 80%)")
    print()

    # Verification methods
    methods = [
        ("Color Histogram Temporal", verify_color_histogram_temporal),
        ("Scene Cuts Alignment", verify_scene_cuts_alignment),
        ("Audio Fingerprint", verify_audio_fingerprint),
        ("DCT Coefficients", verify_dct_coefficients),
        ("Optical Flow Pattern", verify_optical_flow_pattern),
        ("Multi-Scale Pyramid", verify_multiscale_pyramid),
        ("Keyframe Matching", verify_keyframe_matching),
        ("Texture LBP", verify_texture_lbp),
    ]

    # Results storage
    results = []

    for short_name, long_name, expected_pos, should_match in TEST_CASES:
        short_path = DOWNLOADS_DIR / short_name
        long_path = DOWNLOADS_DIR / long_name

        if not short_path.exists():
            print(f"WARNING: {short_name} not found, skipping")
            continue

        if not long_path.exists():
            print(f"WARNING: {long_name} not found, skipping")
            continue

        # Get video duration
        cap = cv2.VideoCapture(str(short_path))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        cap.release()

        match_type = "TRUE POSITIVE" if should_match else "FALSE POSITIVE (reject)"

        print(f"\n{'=' * 80}")
        print(f"Testing: {short_name} vs {long_name}")
        print(f"Type: {match_type}")
        print(f"Position: {format_time(expected_pos)}")
        print(f"Duration: {format_time(duration)}")
        print(f"{'=' * 80}")

        test_result = {
            'short': short_name,
            'long': long_name,
            'expected_pos': expected_pos,
            'should_match': should_match,
            'scores': {}
        }

        for method_name, method_func in methods:
            print(f"\n  {method_name}...", end=" ", flush=True)

            try:
                score = method_func(
                    short_path, long_path,
                    0, expected_pos,  # Compare from start of short to expected pos in long
                    min(duration, 60)  # Use up to 60 seconds for verification
                )

                if score < 0:
                    print("SKIPPED")
                    test_result['scores'][method_name] = None
                else:
                    # Determine if this is correct
                    is_correct = (score >= 80 and should_match) or (score < 80 and not should_match)
                    status = "✅ CORRECT" if is_correct else "❌ WRONG"
                    print(f"{score:5.1f}% {status}")
                    test_result['scores'][method_name] = score

            except Exception as e:
                print(f"ERROR: {str(e)}")
                test_result['scores'][method_name] = None

        results.append(test_result)

    # Summary table
    print("\n" + "=" * 80)
    print("SUMMARY - Verification Method Performance")
    print("=" * 80)
    print()

    # Header
    print(f"{'Test Case':<40s} {'Type':<10s}", end="")
    for method_name, _ in methods:
        if method_name == "Audio Fingerprint":
            continue  # Skip audio (not implemented)
        print(f"{method_name[:10]:>10s}", end="")
    print()
    print("-" * 120)

    # Rows
    for result in results:
        short_name = result['short'].replace('Das Monster und die Schone_', '_').replace('.mp4', '').replace('.avi', '')
        long_name = result['long'].replace('Das Monster und die Schone.mp4', 'Monster').replace('Rocco\'s Initiations 5 (1).avi', 'Rocco').replace('A.avi', 'A')
        test_name = f"{short_name} vs {long_name}"
        test_type = "MATCH" if result['should_match'] else "REJECT"

        print(f"{test_name:<40s} {test_type:<10s}", end="")

        for method_name, _ in methods:
            if method_name == "Audio Fingerprint":
                continue

            score = result['scores'].get(method_name)
            should_match = result['should_match']

            if score is None:
                print(f"{'N/A':>10s}", end="")
            else:
                # Check if method gave correct answer
                is_correct = (score >= 80 and should_match) or (score < 80 and not should_match)
                marker = "✓" if is_correct else "✗"
                print(f"{score:5.1f}% {marker:>2s}", end="")
        print()

    print()

    # Method accuracy rates
    print("=" * 80)
    print("METHOD ACCURACY (correct predictions / total tests)")
    print("=" * 80)
    print()

    for method_name, _ in methods:
        if method_name == "Audio Fingerprint":
            continue

        correct = 0
        total = 0
        tp = 0  # True positives
        tn = 0  # True negatives
        fp = 0  # False positives
        fn = 0  # False negatives

        for result in results:
            score = result['scores'].get(method_name)
            should_match = result['should_match']

            if score is not None:
                total += 1
                predicted_match = score >= 80

                if predicted_match and should_match:
                    tp += 1
                    correct += 1
                elif not predicted_match and not should_match:
                    tn += 1
                    correct += 1
                elif predicted_match and not should_match:
                    fp += 1
                elif not predicted_match and should_match:
                    fn += 1

        if total > 0:
            accuracy = (correct / total) * 100
            precision = (tp / (tp + fp) * 100) if (tp + fp) > 0 else 0
            recall = (tp / (tp + fn) * 100) if (tp + fn) > 0 else 0

            print(f"  {method_name:<30s}")
            print(f"    Accuracy:  {correct}/{total} = {accuracy:5.1f}%")
            print(f"    Precision: {precision:5.1f}% (TP={tp}, FP={fp})")
            print(f"    Recall:    {recall:5.1f}% (TP={tp}, FN={fn})")
            print()

    print()

if __name__ == "__main__":
    main()
