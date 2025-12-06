#!/usr/bin/env python3
"""
Test 3 detection strategies with simulated Scene Cuts and Texture data
"""

import re
from typing import List

# Ground truth - TRUE POSITIVES (extracts that ARE in source videos)
TRUE_POSITIVES = {
    ("Das Monster und die Schone_1.mp4", "Das Monster und die Schone.mp4"),
    ("Das Monster und die Schone_2.mp4", "Das Monster und die Schone.mp4"),
    ("Das Monster und die Schone_3.mp4", "Das Monster und die Schone.mp4"),
    ("Das Monster und die Schone_3.mkv", "Das Monster und die Schone.mp4"),
    ("Das Monster und die Schone_4.mp4", "Das Monster und die Schone.mp4"),
    ("Das Monster und die Schone_4-mac.mp4", "Das Monster und die Schone.mp4"),
    ("Das Monster und die Schone_5.mp4", "Das Monster und die Schone.mp4"),
    ("Das Monster und die Schone_6.mp4", "Das Monster und die Schone.mp4"),
    ("Das Monster und die Schone_7.mp4", "Das Monster und die Schone.mp4"),
    ("Das Monster und die Schone_8.mp4", "Das Monster und die Schone.mp4"),
    ("Das Monster und die Schone_9.mp4", "Das Monster und die Schone.mp4"),
    ("A.avi", "Rocco's Initiations 5 (1).avi"),
    ("DSSDDFDS.avi", "Rocco's Initiations 5 (1).avi"),
    ("gsdgdsgsdgsdsggds.avi", "Rocco's Initiations 5 (1).avi"),
}

FALSE_POSITIVE_PATTERNS = ["Aur_Flo", "JacquieEtMichelTV", "Aisling Franciosi"]

class Match:
    def __init__(self, short_file: str, long_file: str, position: str,
                 seq_score: float, dct_score: float, color_score: float = 0.0):
        self.short_file = short_file
        self.long_file = long_file
        self.position = position
        self.seq_score = seq_score
        self.dct_score = dct_score
        self.color_score = color_score

        # Simulate Scene Cuts and Texture scores based on known behavior
        self.scene_cuts = self._estimate_scene_cuts()
        self.texture_lbp = self._estimate_texture()

    def _estimate_scene_cuts(self) -> float:
        """Estimate Scene Cuts score based on DCT and whether it's FP"""
        # Scene Cuts is VERY good at rejecting false positives (0%)
        # But misses some true positives like _2 and _9
        if self.is_false_positive():
            return 0.0  # FPs get 0% scene cuts

        # Special cases from verification results:
        # _2 and _9 have 0% scene cuts (missing transitions/black frames)
        if "Das Monster und die Schone_2.mp4" in self.short_file:
            return 0.0
        if "Das Monster und die Schone_9.mp4" in self.short_file:
            return 100.0  # Actually _9 has 100% scene cuts in verification

        # True positives usually have good scene detection
        if self.is_true_positive():
            # Most have 100% scene cuts
            return 100.0

        # Unknown: conservative
        return 0.0

    def _estimate_texture(self) -> float:
        """Estimate Texture LBP score"""
        # Texture is permissive - high scores for most matches
        if self.is_true_positive():
            return min(98.0 + (self.seq_score - 85) * 0.2, 100.0)
        if self.is_false_positive():
            return min(75.0 + (self.color_score / 10), 95.0)
        return 80.0

    def is_true_positive(self) -> bool:
        return (self.short_file, self.long_file) in TRUE_POSITIVES

    def is_false_positive(self) -> bool:
        for pattern in FALSE_POSITIVE_PATTERNS:
            if pattern in self.short_file or pattern in self.long_file:
                return True
        return False

    def should_ignore(self) -> bool:
        if ("Das Monster und die Schone_" in self.short_file and
            "Das Monster und die Schone_" in self.long_file):
            return True
        if (self.short_file in ["A.avi", "DSSDDFDS.avi", "gsdgdsgsdgsdsggds.avi"] and
            self.long_file in ["A.avi", "DSSDDFDS.avi", "gsdgdsgsdgsdsggds.avi"]):
            return True
        return False

    def __repr__(self):
        return f"{self.short_file} → {self.long_file} @ {self.position} (seq:{self.seq_score:.1f}% dct:{self.dct_score:.1f}% scene:{self.scene_cuts:.1f}% texture:{self.texture_lbp:.1f}%)"


def parse_dual_results(file_path: str) -> List[Match]:
    matches = []
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

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


def strategy_1_adaptive_dct(match: Match) -> bool:
    """Adaptive DCT thresholds based on sequence score"""
    if match.seq_score >= 99.0 and match.dct_score >= 75.0:
        return True
    if match.seq_score >= 95.0 and match.dct_score >= 80.0:
        return True
    if match.seq_score >= 90.0 and match.dct_score >= 85.0:
        return True
    return False


def strategy_2_weighted_vote(match: Match) -> bool:
    """Weighted voting: (DCT × 2) + Scene Cuts + Texture LBP >= 240"""
    score = (match.dct_score * 2.0) + match.scene_cuts + match.texture_lbp
    return score >= 240.0


def strategy_3_scene_veto(match: Match) -> bool:
    """Scene Cuts veto + DCT threshold"""
    if match.scene_cuts == 0.0:
        return False
    return match.dct_score >= 75.0 and match.seq_score >= 95.0


def strategy_4_hybrid(match: Match) -> bool:
    """Hybrid: Scene veto OR very high confidence"""
    # Very high confidence: perfect sequence + good DCT
    if match.seq_score >= 99.0 and match.dct_score >= 75.0:
        return True

    # Scene cuts veto for others
    if match.scene_cuts == 0.0:
        return False

    return match.dct_score >= 75.0 and match.seq_score >= 95.0


def strategy_5_color_backup(match: Match) -> bool:
    """Scene veto + DCT, with Color as backup for difficult cases"""
    # High DCT: trust it
    if match.dct_score >= 80.0 and match.seq_score >= 90.0:
        return True

    # Scene cuts veto
    if match.scene_cuts == 0.0:
        # But allow Color histogram as backup if VERY high
        if match.color_score >= 400.0 and match.seq_score >= 95.0:
            return True
        return False

    # Medium DCT with scene cuts
    if match.dct_score >= 75.0 and match.seq_score >= 95.0:
        return True

    return False


def strategy_6_relaxed_adaptive(match: Match) -> bool:
    """Relaxed adaptive DCT (lower thresholds)"""
    if match.seq_score >= 99.0 and match.dct_score >= 70.0:
        return True
    if match.seq_score >= 95.0 and match.dct_score >= 75.0:
        return True
    if match.seq_score >= 90.0 and match.dct_score >= 80.0:
        return True
    return False


def strategy_7_scene_with_color_fallback(match: Match) -> bool:
    """Scene veto + DCT, but Color can save scene=0 cases if VERY strong"""
    # Normal path: scene cuts veto
    if match.scene_cuts > 0.0:
        return match.dct_score >= 75.0 and match.seq_score >= 95.0

    # Scene cuts = 0: could be FP OR difficult TP like _2
    # Allow if Color is EXTREMELY high AND sequence is perfect
    if match.seq_score >= 99.5 and match.color_score >= 300.0:
        return True

    return False


def strategy_8_very_strict(match: Match) -> bool:
    """Very strict: prioritize precision over recall"""
    # Require BOTH scene cuts AND good DCT
    if match.scene_cuts == 0.0:
        return False
    if match.dct_score < 80.0:
        return False
    if match.seq_score < 95.0:
        return False
    return True


def evaluate_strategy(matches: List[Match], strategy_func, strategy_name: str):
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
        for m in fp_matches[:3]:
            print(f"  {m}")
        if len(fp_matches) > 3:
            print(f"  ... and {len(fp_matches) - 3} more")

    if false_negatives > 0:
        print(f"\n❌ False Negatives ({false_negatives}):")
        fn_matches = [m for m in rejected_matches if m.is_true_positive()]
        for m in fn_matches[:3]:
            print(f"  {m}")

    return {
        'precision': precision,
        'recall': recall,
        'f1': f1_score,
        'tp': true_positives,
        'fp': false_positives,
        'fn': false_negatives,
    }


def main():
    print("="*80)
    print("TESTING 3 DETECTION STRATEGIES (with simulated Scene Cuts & Texture data)")
    print("="*80)

    matches = parse_dual_results("results_dual_with_reencoded.txt")
    print(f"\nLoaded {len(matches)} matches from dual vote results")

    results = {}
    results['s1'] = evaluate_strategy(matches, strategy_1_adaptive_dct,
                                      "Strategy 1: Adaptive DCT Thresholds")
    results['s2'] = evaluate_strategy(matches, strategy_2_weighted_vote,
                                      "Strategy 2: Weighted Vote (DCT×2 + Scene + Texture)")
    results['s3'] = evaluate_strategy(matches, strategy_3_scene_veto,
                                      "Strategy 3: Scene Cuts Veto + DCT")
    results['s4'] = evaluate_strategy(matches, strategy_4_hybrid,
                                      "Strategy 4: Hybrid (Scene Veto OR High Confidence)")
    results['s5'] = evaluate_strategy(matches, strategy_5_color_backup,
                                      "Strategy 5: Scene Veto + Color Backup")
    results['s6'] = evaluate_strategy(matches, strategy_6_relaxed_adaptive,
                                      "Strategy 6: Relaxed Adaptive DCT")
    results['s7'] = evaluate_strategy(matches, strategy_7_scene_with_color_fallback,
                                      "Strategy 7: Scene Veto + Color Fallback")
    results['s8'] = evaluate_strategy(matches, strategy_8_very_strict,
                                      "Strategy 8: Very Strict (Scene AND High DCT)")

    print("\n" + "="*80)
    print("FINAL COMPARISON")
    print("="*80)
    print(f"\n{'Strategy':<45} {'Precision':>10} {'Recall':>10} {'F1':>10}")
    print("-" * 80)
    for i in range(1, 9):
        key = f's{i}'
        name = f"{i}. " + {
            's1': 'Adaptive DCT',
            's2': 'Weighted Vote',
            's3': 'Scene Cuts Veto ⭐',
            's4': 'Hybrid',
            's5': 'Color Backup',
            's6': 'Relaxed Adaptive',
            's7': 'Scene + Color Fallback',
            's8': 'Very Strict'
        }[key]
        r = results[key]
        print(f"{name:<45} {r['precision']:>9.1f}% {r['recall']:>9.1f}% {r['f1']:>9.1f}%")

    # Find best F1
    best = max(results.items(), key=lambda x: x[1]['f1'])
    best_num = int(best[0][1])
    print(f"\n🏆 Best F1 Score: Strategy {best_num} ({best[1]['f1']:.1f}%)")
    print(f"   TP={best[1]['tp']} FP={best[1]['fp']} FN={best[1]['fn']}")


if __name__ == "__main__":
    main()
