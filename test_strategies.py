#!/usr/bin/env python3
"""
Test 3 detection strategies on existing results
"""

import re
from pathlib import Path
from typing import List, Dict, Tuple

# Ground truth - TRUE POSITIVES (extracts that ARE in source videos)
TRUE_POSITIVES = {
    # Das Monster und die Schone extracts
    ("Das Monster und die Schone_1.mp4", "Das Monster und die Schone.mp4"),
    ("Das Monster und die Schone_2.mp4", "Das Monster und die Schone.mp4"),
    ("Das Monster und die Schone_3.mp4", "Das Monster und die Schone.mp4"),
    ("Das Monster und die Schone_3.mkv", "Das Monster und die Schone.mp4"),  # REENCODED VERSION
    ("Das Monster und die Schone_4.mp4", "Das Monster und die Schone.mp4"),
    ("Das Monster und die Schone_4-mac.mp4", "Das Monster und die Schone.mp4"),
    ("Das Monster und die Schone_5.mp4", "Das Monster und die Schone.mp4"),
    ("Das Monster und die Schone_6.mp4", "Das Monster und die Schone.mp4"),
    ("Das Monster und die Schone_7.mp4", "Das Monster und die Schone.mp4"),
    ("Das Monster und die Schone_8.mp4", "Das Monster und die Schone.mp4"),
    ("Das Monster und die Schone_9.mp4", "Das Monster und die Schone.mp4"),

    # Rocco's Initiations extracts
    ("A.avi", "Rocco's Initiations 5 (1).avi"),
    ("DSSDDFDS.avi", "Rocco's Initiations 5 (1).avi"),
    ("gsdgdsgsdgsdsggds.avi", "Rocco's Initiations 5 (1).avi"),
}

# Accepted pairs - segments that match each other (not false positives, but not source matches either)
SEGMENT_TO_SEGMENT_MATCHES = {
    # These are real matches between segments, but we're looking for source detection
    # So we don't count them as TP or FP - just ignore them
}

# FALSE POSITIVES - similar content but NOT actual extracts
FALSE_POSITIVE_PATTERNS = [
    "Aur_Flo",
    "JacquieEtMichelTV",
    "Aisling Franciosi",
]

class Match:
    def __init__(self, short_file: str, long_file: str, position: str,
                 seq_score: float, dct_score: float, color_score: float = 0.0,
                 scene_cuts: float = 0.0, texture_lbp: float = 0.0):
        self.short_file = short_file
        self.long_file = long_file
        self.position = position
        self.seq_score = seq_score
        self.dct_score = dct_score
        self.color_score = color_score
        self.scene_cuts = scene_cuts
        self.texture_lbp = texture_lbp

    def is_true_positive(self) -> bool:
        """Check if this is a known true positive"""
        return (self.short_file, self.long_file) in TRUE_POSITIVES

    def is_false_positive(self) -> bool:
        """Check if this matches false positive patterns"""
        for pattern in FALSE_POSITIVE_PATTERNS:
            if pattern in self.short_file or pattern in self.long_file:
                return True
        return False

    def should_ignore(self) -> bool:
        """Check if this is a segment-to-segment match we should ignore"""
        # Ignore matches between segments (not testing segment-to-segment detection)
        if ("Das Monster und die Schone_" in self.short_file and
            "Das Monster und die Schone_" in self.long_file):
            return True
        if (self.short_file in ["A.avi", "DSSDDFDS.avi", "gsdgdsgsdgsdsggds.avi"] and
            self.long_file in ["A.avi", "DSSDDFDS.avi", "gsdgdsgsdgsdsggds.avi"]):
            return True
        return False

    def __repr__(self):
        return f"{self.short_file} → {self.long_file} @ {self.position} (seq:{self.seq_score:.1f}% dct:{self.dct_score:.1f}%)"


def parse_dct_results(file_path: str) -> List[Match]:
    """Parse results_dct_with_reencoded.txt"""
    matches = []

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern: [X/Y] 'short' in 'long'... Candidate at XXmXXs (seq: XX.X%) → ✅ VERIFIED (XX.X%)
    pattern = r"\[\d+/\d+\] '([^']+)' in '([^']+)'.*?Candidate at ([^(]+) \(seq: ([\d.]+)%\) → ✅ VERIFIED \(([\d.]+)%\)"

    for match in re.finditer(pattern, content):
        short_file = match.group(1)
        long_file = match.group(2)
        position = match.group(3).strip()
        seq_score = float(match.group(4))
        dct_score = float(match.group(5))

        matches.append(Match(short_file, long_file, position, seq_score, dct_score))

    return matches


def parse_dual_results(file_path: str) -> List[Match]:
    """Parse results_dual_with_reencoded.txt"""
    matches = []

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern: [X/Y] 'short' in 'long'... Candidate at XXmXXs (seq: XX.X%) → ✅ VERIFIED (DCT:XX.X%, Color:XX.X%, Best:...)
    pattern = r"\[\d+/\d+\] '([^']+)' in '([^']+)'.*?Candidate at ([^(]+) \(seq: ([\d.]+)%\) → ✅ VERIFIED \(DCT:([\d.]+)%, Color:([\d.]+)%"

    for match in re.finditer(pattern, content):
        short_file = match.group(1)
        long_file = match.group(2)
        position = match.group(3).strip()
        seq_score = float(match.group(4))
        dct_score = float(match.group(5))
        color_score = float(match.group(6))

        matches.append(Match(short_file, long_file, position, seq_score, dct_score, color_score))

    return matches


def parse_verification_results(file_path: str) -> List[Match]:
    """Parse results_verification_with_reencoded.txt for Scene Cuts and Texture LBP scores"""
    matches = []

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by test case
    test_cases = re.split(r'={80,}\nTesting:', content)[1:]  # Skip header

    for case in test_cases:
        # Extract file names
        file_match = re.search(r'([^\s]+\.(?:mp4|avi|mkv)) vs ([^\s]+\.(?:mp4|avi|mkv))', case)
        if not file_match:
            continue

        short_file = file_match.group(1)
        long_file = file_match.group(2)

        # Check type (TRUE POSITIVE or FALSE POSITIVE)
        type_match = re.search(r'Type:\s+(TRUE POSITIVE|FALSE POSITIVE)', case)
        if not type_match:
            continue

        # Extract position
        pos_match = re.search(r'Position:\s+(\d+h)?(\d+m\d+s)', case)
        if not pos_match:
            continue
        position = pos_match.group(0).replace('Position:', '').strip()

        # Extract scores
        dct_match = re.search(r'DCT Coefficients\.\.\.\s+([\d.]+)%', case)
        scene_match = re.search(r'Scene Cuts Alignment\.\.\.\s+([\d.]+)%', case)
        texture_match = re.search(r'Texture LBP\.\.\.\s+([\d.]+)%', case)
        color_match = re.search(r'Color Histogram Temporal\.\.\.\s+([\d.]+)%', case)

        if not (dct_match and scene_match and texture_match):
            continue

        # For sequence score, we'll use 95% as default (not in verification file)
        seq_score = 95.0
        dct_score = float(dct_match.group(1))
        scene_cuts = float(scene_match.group(1))
        texture_lbp = float(texture_match.group(1))
        color_score = float(color_match.group(1)) if color_match else 0.0

        matches.append(Match(short_file, long_file, position, seq_score, dct_score,
                           color_score, scene_cuts, texture_lbp))

    return matches


def strategy_1_adaptive_dct(match: Match) -> bool:
    """
    Strategy 1: Adaptive DCT thresholds based on sequence score
    IF seq ≥ 99% AND dct ≥ 75%: ACCEPT
    IF seq ≥ 95% AND dct ≥ 80%: ACCEPT
    IF seq ≥ 90% AND dct ≥ 85%: ACCEPT
    ELSE: REJECT
    """
    if match.seq_score >= 99.0 and match.dct_score >= 75.0:
        return True
    if match.seq_score >= 95.0 and match.dct_score >= 80.0:
        return True
    if match.seq_score >= 90.0 and match.dct_score >= 85.0:
        return True
    return False


def strategy_2_weighted_vote(match: Match) -> bool:
    """
    Strategy 2: Weighted voting with DCT, Scene Cuts, Texture LBP
    Score = (DCT × 2) + Scene Cuts + Texture LBP
    IF Score ≥ 240: ACCEPT

    Note: Scene Cuts and Texture need to be normalized to 0-100 scale
    """
    # Normalize scene cuts (already 0-100)
    scene_normalized = match.scene_cuts

    # Normalize texture (already 0-100)
    texture_normalized = match.texture_lbp

    # Calculate weighted score
    score = (match.dct_score * 2.0) + scene_normalized + texture_normalized

    return score >= 240.0


def strategy_3_scene_veto(match: Match) -> bool:
    """
    Strategy 3: Scene Cuts as veto for false positives
    IF Scene Cuts = 0%: REJECT (likely false positive)
    ELSE IF dct ≥ 75% AND seq ≥ 95%: ACCEPT
    """
    # Scene cuts veto
    if match.scene_cuts == 0.0:
        return False

    # Otherwise check DCT and sequence
    return match.dct_score >= 75.0 and match.seq_score >= 95.0


def evaluate_strategy(matches: List[Match], strategy_func, strategy_name: str,
                      has_extended_data: bool = False):
    """Evaluate a strategy and print results"""

    # Skip strategies that need extended data if not available
    if not has_extended_data and strategy_func in [strategy_2_weighted_vote, strategy_3_scene_veto]:
        print(f"\n⚠️  {strategy_name}: SKIPPED (needs Scene Cuts/Texture data)")
        return None

    true_positives = 0
    false_positives = 0
    false_negatives = 0
    true_negatives = 0

    accepted_matches = []
    rejected_matches = []

    critical_reencoded_found = False
    critical_2_found = False
    critical_9_found = False

    for match in matches:
        # Skip segment-to-segment matches
        if match.should_ignore():
            continue

        accepted = strategy_func(match)

        is_true = match.is_true_positive()
        is_false = match.is_false_positive()

        # Track critical cases
        if "Das Monster und die Schone_3.mkv" in match.short_file and "Das Monster und die Schone.mp4" in match.long_file:
            if accepted:
                critical_reencoded_found = True
        if "Das Monster und die Schone_2.mp4" in match.short_file and "Das Monster und die Schone.mp4" in match.long_file:
            if accepted:
                critical_2_found = True
        if "Das Monster und die Schone_9.mp4" in match.short_file and "Das Monster und die Schone.mp4" in match.long_file:
            if accepted:
                critical_9_found = True

        if accepted:
            accepted_matches.append(match)
            if is_true:
                true_positives += 1
            elif is_false:
                false_positives += 1
        else:
            rejected_matches.append(match)
            if is_true:
                false_negatives += 1
            elif is_false:
                true_negatives += 1

    # Calculate metrics
    total_accepted = len(accepted_matches)
    precision = (true_positives / total_accepted * 100) if total_accepted > 0 else 0
    recall = (true_positives / (true_positives + false_negatives) * 100) if (true_positives + false_negatives) > 0 else 0
    f1_score = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0

    print(f"\n{'='*80}")
    print(f"{strategy_name}")
    print(f"{'='*80}")
    print(f"Total matches accepted: {total_accepted}")
    print(f"  ✅ True Positives:  {true_positives}")
    print(f"  ❌ False Positives: {false_positives}")
    print(f"  ❌ False Negatives: {false_negatives}")
    print(f"  ✅ True Negatives:  {true_negatives}")
    print(f"\n📊 Metrics:")
    print(f"  Precision: {precision:.1f}%")
    print(f"  Recall:    {recall:.1f}%")
    print(f"  F1 Score:  {f1_score:.1f}%")

    print(f"\n🎯 Critical Cases:")
    print(f"  Reencoded .mkv detected: {'✅ YES' if critical_reencoded_found else '❌ NO'}")
    print(f"  Das Monster _2 detected: {'✅ YES' if critical_2_found else '❌ NO'}")
    print(f"  Das Monster _9 detected: {'✅ YES' if critical_9_found else '❌ NO'}")

    if false_positives > 0:
        print(f"\n❌ False Positives ({false_positives}):")
        fp_matches = [m for m in accepted_matches if m.is_false_positive()]
        for m in fp_matches[:5]:  # Show first 5
            print(f"  {m}")
        if len(fp_matches) > 5:
            print(f"  ... and {len(fp_matches) - 5} more")

    if false_negatives > 0:
        print(f"\n❌ False Negatives ({false_negatives}):")
        fn_matches = [m for m in rejected_matches if m.is_true_positive()]
        for m in fn_matches[:5]:  # Show first 5
            print(f"  {m}")
        if len(fn_matches) > 5:
            print(f"  ... and {len(fn_matches) - 5} more")

    return {
        'precision': precision,
        'recall': recall,
        'f1': f1_score,
        'tp': true_positives,
        'fp': false_positives,
        'fn': false_negatives,
        'tn': true_negatives,
        'critical_reencoded': critical_reencoded_found,
        'critical_2': critical_2_found,
        'critical_9': critical_9_found,
    }


def main():
    print("="*80)
    print("TESTING 3 DETECTION STRATEGIES")
    print("="*80)

    # Test on DCT results
    print("\n" + "="*80)
    print("DATASET 1: DCT Results (results_dct_with_reencoded.txt)")
    print("="*80)

    dct_matches = parse_dct_results("results_dct_with_reencoded.txt")
    print(f"Loaded {len(dct_matches)} matches")

    results_dct = {}
    results_dct['strategy1'] = evaluate_strategy(dct_matches, strategy_1_adaptive_dct,
                                                  "Strategy 1: Adaptive DCT")

    # Test on Dual Vote results
    print("\n" + "="*80)
    print("DATASET 2: Dual Vote Results (results_dual_with_reencoded.txt)")
    print("="*80)

    dual_matches = parse_dual_results("results_dual_with_reencoded.txt")
    print(f"Loaded {len(dual_matches)} matches")

    results_dual = {}
    results_dual['strategy1'] = evaluate_strategy(dual_matches, strategy_1_adaptive_dct,
                                                   "Strategy 1: Adaptive DCT")

    # Test on Verification results (has Scene Cuts and Texture data)
    print("\n" + "="*80)
    print("DATASET 3: Verification Results (results_verification_with_reencoded.txt)")
    print("="*80)

    verif_matches = parse_verification_results("results_verification_with_reencoded.txt")
    print(f"Loaded {len(verif_matches)} matches")

    results_verif = {}
    results_verif['strategy1'] = evaluate_strategy(verif_matches, strategy_1_adaptive_dct,
                                                    "Strategy 1: Adaptive DCT",
                                                    has_extended_data=True)
    results_verif['strategy2'] = evaluate_strategy(verif_matches, strategy_2_weighted_vote,
                                                    "Strategy 2: Weighted Vote (DCT×2 + Scene + Texture)",
                                                    has_extended_data=True)
    results_verif['strategy3'] = evaluate_strategy(verif_matches, strategy_3_scene_veto,
                                                    "Strategy 3: Scene Cuts Veto",
                                                    has_extended_data=True)

    # Final comparison
    print("\n" + "="*80)
    print("FINAL COMPARISON")
    print("="*80)

    print("\nOn DCT Dataset:")
    if results_dct['strategy1']:
        print(f"  Strategy 1: P={results_dct['strategy1']['precision']:.1f}% R={results_dct['strategy1']['recall']:.1f}% F1={results_dct['strategy1']['f1']:.1f}%")

    print("\nOn Dual Vote Dataset:")
    if results_dual['strategy1']:
        print(f"  Strategy 1: P={results_dual['strategy1']['precision']:.1f}% R={results_dual['strategy1']['recall']:.1f}% F1={results_dual['strategy1']['f1']:.1f}%")

    print("\nOn Verification Dataset:")
    if results_verif['strategy1']:
        print(f"  Strategy 1: P={results_verif['strategy1']['precision']:.1f}% R={results_verif['strategy1']['recall']:.1f}% F1={results_verif['strategy1']['f1']:.1f}%")
    if results_verif['strategy2']:
        print(f"  Strategy 2: P={results_verif['strategy2']['precision']:.1f}% R={results_verif['strategy2']['recall']:.1f}% F1={results_verif['strategy2']['f1']:.1f}%")
    if results_verif['strategy3']:
        print(f"  Strategy 3: P={results_verif['strategy3']['precision']:.1f}% R={results_verif['strategy3']['recall']:.1f}% F1={results_verif['strategy3']['f1']:.1f}%")


if __name__ == "__main__":
    main()
