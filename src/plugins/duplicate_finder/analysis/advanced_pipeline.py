"""
Advanced 3-level duplicate detection pipeline orchestrator.

This module coordinates the execution of the 3-level analysis:
- Level 1: LSH audio fingerprinting (fast, loose filtering)
- Level 2: Long-period audio comparison (medium, refined filtering)
- Level 3: pHash visual confirmation (slow, final validation)

The pipeline progressively filters candidates at each level, reducing
false positives while maintaining high recall.
"""

import time
import os
from typing import List, Dict, Optional, Callable
from src.core.logger import Logger

from .lsh_audio import LSHAudioAnalyzer
from .long_audio import LongAudioComparator
from .phash_visual import PHashComparator

logger = Logger.get_logger('DuplicateFinder.AdvancedPipeline')


class AdvancedDuplicatePipeline:
    """
    Orchestrates the 3-level advanced duplicate detection pipeline.

    This class manages the complete workflow:
    1. Level 1 (LSH): Fast filtering on large video corpus
    2. Level 2 (Long Audio): Refined filtering on candidates
    3. Level 3 (pHash): Final visual confirmation

    Each level reduces the number of candidates while increasing precision.

    Attributes:
        config: Configuration dictionary with parameters for each level
        db_manager: Database manager for caching and storage
        progress_callback: Optional callback for progress updates
        stopped: Flag to stop pipeline execution
    """

    def __init__(
        self,
        config: Dict,
        db_manager,
        progress_callback: Optional[Callable] = None
    ):
        """
        Initialize the advanced pipeline.

        Args:
            config: Configuration dictionary with keys:
                - 'level1_threshold': LSH Jaccard threshold (default: 0.7)
                - 'level2_duration': Long audio window duration (default: 120)
                - 'level2_threshold': Long audio similarity threshold (default: 0.8)
                - 'level3_phash_threshold': pHash Hamming distance max (default: 10)
                - 'level3_frame_rate': pHash frame similarity rate (default: 0.8)
            db_manager: Database manager instance
            progress_callback: Optional callback(phase, current, total, message)
        """
        self.config = config
        self.db = db_manager
        self.progress_callback = progress_callback
        self.stopped = False

        # Extract configuration with defaults
        level1_threshold = config.get('level1_threshold', 0.7)
        level2_duration = config.get('level2_duration', 120)
        level2_threshold = config.get('level2_threshold', 0.8)
        level3_phash_threshold = config.get('level3_phash_threshold', 10)
        level3_frame_rate = config.get('level3_frame_rate', 0.8)

        # Initialize analyzers for each level
        try:
            self.lsh_analyzer = LSHAudioAnalyzer(
                threshold=level1_threshold,
                audio_duration=30
            )
            logger.info("✓ Level 1 (LSH) analyzer initialized")
        except ImportError as e:
            logger.error(f"✗ Level 1 (LSH) unavailable: {e}")
            self.lsh_analyzer = None

        self.long_audio = LongAudioComparator(
            window_duration=level2_duration,
            threshold=level2_threshold
        )
        logger.info("✓ Level 2 (Long Audio) analyzer initialized")

        self.phash_comparator = PHashComparator(
            phash_threshold=level3_phash_threshold,
            frame_rate_threshold=level3_frame_rate
        )
        logger.info("✓ Level 3 (pHash) analyzer initialized")

        logger.info(
            f"Pipeline configured: L1_threshold={level1_threshold:.2f}, "
            f"L2_duration={level2_duration}s, L2_threshold={level2_threshold:.2f}, "
            f"L3_phash={level3_phash_threshold}bits, L3_framerate={level3_frame_rate:.0%}"
        )

    def stop(self):
        """Stop the pipeline execution."""
        self.stopped = True
        logger.warning("Pipeline stop requested")

    def _update_progress(
        self,
        phase: str,
        current: int,
        total: int,
        message: str
    ):
        """
        Update progress through callback if available.

        Args:
            phase: Current phase ('Level 1', 'Level 2', 'Level 3')
            current: Current item number
            total: Total items
            message: Status message
        """
        if self.progress_callback:
            try:
                self.progress_callback(phase, current, total, message)
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")

    def run_complete_analysis(
        self,
        video_paths: List[str]
    ) -> Optional[Dict]:
        """
        Run the complete 3-level analysis pipeline.

        This is the main entry point for the advanced duplicate detection.

        Args:
            video_paths: List of video file paths to analyze

        Returns:
            Dictionary with analysis results and statistics, or None if stopped
            Contains:
            - 'candidates_level1': Number of candidates from Level 1
            - 'candidates_level2': Number of candidates from Level 2
            - 'confirmed_duplicates': Number of confirmed duplicates
            - 'duplicates': List of confirmed duplicate dicts
            - 'reduction_rate_l1_l2': Reduction rate Level 1→2
            - 'reduction_rate_l2_l3': Reduction rate Level 2→3
            - 'total_time': Total execution time in seconds
            - 'level_times': Dict with time for each level
        """
        start_time = time.time()
        total_videos = len(video_paths)

        logger.info("=" * 70)
        logger.info(f"🔬 Starting Advanced 3-Level Analysis on {total_videos} videos")
        logger.info("=" * 70)

        # Initialize results
        level_times = {}
        candidates_l1 = []
        candidates_l2 = []
        confirmed = []

        # ═══════════════════════════════════════════════════════════════
        # LEVEL 1: LSH Audio Fingerprinting (Fast Initial Filtering)
        # ═══════════════════════════════════════════════════════════════
        logger.info("\n" + "─" * 70)
        logger.info("📊 LEVEL 1: LSH Audio Fingerprinting")
        logger.info("─" * 70)

        level1_start = time.time()

        if self.lsh_analyzer is None:
            logger.warning("LSH analyzer not available - skipping Level 1")
            logger.warning("All videos will be passed to Level 2")
            # Create dummy candidates (all pairs) - NOT RECOMMENDED FOR LARGE CORPUS
            # For now, just pass empty list to avoid O(n²) explosion
            candidates_l1 = []
        else:
            try:
                self._update_progress("Level 1", 0, total_videos, "Starting LSH analysis...")

                candidates_l1 = self.lsh_analyzer.find_candidates(
                    video_paths,
                    self.db,
                    progress_callback=lambda cur, tot, msg: self._update_progress(
                        "Level 1", cur, tot, msg
                    )
                )

                if self.stopped:
                    logger.warning("Pipeline stopped at Level 1")
                    return None

                level_times['level1'] = time.time() - level1_start

                logger.info(
                    f"✓ Level 1 complete: {len(candidates_l1)} candidate pairs found "
                    f"in {level_times['level1']:.1f}s"
                )

            except Exception as e:
                logger.error(f"✗ Level 1 failed: {e}")
                logger.warning("Skipping to Level 2 with empty candidates")
                candidates_l1 = []
                level_times['level1'] = time.time() - level1_start

        # ═══════════════════════════════════════════════════════════════
        # LEVEL 2: Long-Period Audio Comparison (Refined Filtering)
        # ═══════════════════════════════════════════════════════════════
        logger.info("\n" + "─" * 70)
        logger.info("🎵 LEVEL 2: Long-Period Audio Comparison")
        logger.info("─" * 70)

        level2_start = time.time()

        if len(candidates_l1) == 0:
            logger.warning("No candidates from Level 1 - skipping Level 2")
            candidates_l2 = []
        else:
            try:
                self._update_progress(
                    "Level 2", 0, len(candidates_l1),
                    "Starting long-period audio analysis..."
                )

                candidates_l2 = self.long_audio.filter_candidates(
                    candidates_l1,
                    self.db,
                    progress_callback=lambda cur, tot, msg: self._update_progress(
                        "Level 2", cur, tot, msg
                    )
                )

                if self.stopped:
                    logger.warning("Pipeline stopped at Level 2")
                    return None

                level_times['level2'] = time.time() - level2_start

                # Calculate reduction rate
                reduction_l1_l2 = (
                    (1 - len(candidates_l2) / len(candidates_l1)) * 100
                    if len(candidates_l1) > 0 else 0
                )

                logger.info(
                    f"✓ Level 2 complete: {len(candidates_l2)} refined pairs "
                    f"({reduction_l1_l2:.1f}% reduction) in {level_times['level2']:.1f}s"
                )

            except Exception as e:
                logger.error(f"✗ Level 2 failed: {e}")
                logger.warning("Passing Level 1 candidates to Level 3")
                candidates_l2 = candidates_l1  # Pass through on error
                level_times['level2'] = time.time() - level2_start

        # ═══════════════════════════════════════════════════════════════
        # LEVEL 3: pHash Visual Confirmation (Final Validation)
        # ═══════════════════════════════════════════════════════════════
        logger.info("\n" + "─" * 70)
        logger.info("👁️  LEVEL 3: pHash Visual Confirmation")
        logger.info("─" * 70)

        level3_start = time.time()

        if len(candidates_l2) == 0:
            logger.warning("No candidates from Level 2 - skipping Level 3")
            confirmed = []
        else:
            try:
                self._update_progress(
                    "Level 3", 0, len(candidates_l2),
                    "Starting visual confirmation..."
                )

                confirmed = self.phash_comparator.confirm_duplicates(
                    candidates_l2,
                    self.db,
                    progress_callback=lambda cur, tot, msg: self._update_progress(
                        "Level 3", cur, tot, msg
                    )
                )

                if self.stopped:
                    logger.warning("Pipeline stopped at Level 3")
                    return None

                level_times['level3'] = time.time() - level3_start

                # Calculate reduction rate
                reduction_l2_l3 = (
                    (1 - len(confirmed) / len(candidates_l2)) * 100
                    if len(candidates_l2) > 0 else 0
                )

                logger.info(
                    f"✓ Level 3 complete: {len(confirmed)} duplicates confirmed "
                    f"({reduction_l2_l3:.1f}% reduction) in {level_times['level3']:.1f}s"
                )

            except Exception as e:
                logger.error(f"✗ Level 3 failed: {e}")
                confirmed = []
                level_times['level3'] = time.time() - level3_start

        # ═══════════════════════════════════════════════════════════════
        # FINALIZATION: Save Results & Generate Report
        # ═══════════════════════════════════════════════════════════════
        logger.info("\n" + "─" * 70)
        logger.info("💾 Saving Results to Database")
        logger.info("─" * 70)

        saved_count = self._save_results(confirmed)

        total_time = time.time() - start_time

        # Generate final report
        report = self._generate_report(
            total_videos,
            candidates_l1,
            candidates_l2,
            confirmed,
            level_times,
            total_time
        )

        # Print summary
        self._print_summary(report)

        return report

    def _save_results(self, confirmed_duplicates: List[Dict]) -> int:
        """
        Save confirmed duplicates to database.

        Args:
            confirmed_duplicates: List of confirmed duplicate dictionaries

        Returns:
            Number of duplicates successfully saved
        """
        saved_count = 0

        for duplicate in confirmed_duplicates:
            try:
                success = self.db.store_advanced_duplicate(
                    duplicate['file1'],
                    duplicate['file2'],
                    duplicate['level1_score'],
                    duplicate['level2_score'],
                    duplicate['level3_score'],
                    duplicate['confidence']
                )

                if success:
                    saved_count += 1

            except Exception as e:
                logger.error(
                    f"Error saving duplicate {duplicate['file1']} <-> "
                    f"{duplicate['file2']}: {e}"
                )

        logger.info(f"Saved {saved_count}/{len(confirmed_duplicates)} duplicates to database")

        return saved_count

    def _generate_report(
        self,
        total_videos: int,
        candidates_l1: List,
        candidates_l2: List,
        confirmed: List,
        level_times: Dict,
        total_time: float
    ) -> Dict:
        """
        Generate comprehensive analysis report.

        Args:
            total_videos: Total number of videos analyzed
            candidates_l1: Level 1 candidates
            candidates_l2: Level 2 candidates
            confirmed: Confirmed duplicates
            level_times: Execution time for each level
            total_time: Total execution time

        Returns:
            Report dictionary with all statistics
        """
        # Calculate reduction rates
        reduction_l1_l2 = (
            (1 - len(candidates_l2) / len(candidates_l1)) * 100
            if len(candidates_l1) > 0 else 0
        )
        reduction_l2_l3 = (
            (1 - len(confirmed) / len(candidates_l2)) * 100
            if len(candidates_l2) > 0 else 0
        )
        overall_reduction = (
            (1 - len(confirmed) / len(candidates_l1)) * 100
            if len(candidates_l1) > 0 else 0
        )

        # Count by confidence
        confidence_counts = {
            'high': sum(1 for d in confirmed if d['confidence'] == 'high'),
            'medium': sum(1 for d in confirmed if d['confidence'] == 'medium'),
            'low': sum(1 for d in confirmed if d['confidence'] == 'low')
        }

        report = {
            # Input
            'total_videos': total_videos,

            # Level 1 results
            'candidates_level1': len(candidates_l1),
            'level1_time': level_times.get('level1', 0),

            # Level 2 results
            'candidates_level2': len(candidates_l2),
            'level2_time': level_times.get('level2', 0),
            'reduction_rate_l1_l2': reduction_l1_l2,

            # Level 3 results
            'confirmed_duplicates': len(confirmed),
            'level3_time': level_times.get('level3', 0),
            'reduction_rate_l2_l3': reduction_l2_l3,
            'overall_reduction': overall_reduction,

            # Confidence distribution
            'confidence_high': confidence_counts['high'],
            'confidence_medium': confidence_counts['medium'],
            'confidence_low': confidence_counts['low'],

            # Timing
            'total_time': total_time,
            'avg_time_per_video': total_time / total_videos if total_videos > 0 else 0,

            # Data
            'duplicates': confirmed
        }

        return report

    def _print_summary(self, report: Dict):
        """
        Print formatted summary report.

        Args:
            report: Report dictionary from _generate_report
        """
        logger.info("\n" + "═" * 70)
        logger.info("📊 ANALYSIS COMPLETE - SUMMARY REPORT")
        logger.info("═" * 70)

        # Input
        logger.info(f"\n📹 Videos Analyzed: {report['total_videos']}")

        # Level 1
        logger.info(f"\n🔍 Level 1 (LSH Audio):")
        logger.info(f"   Candidates Found: {report['candidates_level1']}")
        logger.info(f"   Time: {report['level1_time']:.1f}s")

        # Level 2
        logger.info(f"\n🎵 Level 2 (Long Audio):")
        logger.info(f"   Refined Candidates: {report['candidates_level2']}")
        logger.info(f"   Reduction: {report['reduction_rate_l1_l2']:.1f}%")
        logger.info(f"   Time: {report['level2_time']:.1f}s")

        # Level 3
        logger.info(f"\n👁️  Level 3 (pHash Visual):")
        logger.info(f"   Confirmed Duplicates: {report['confirmed_duplicates']}")
        logger.info(f"   Reduction: {report['reduction_rate_l2_l3']:.1f}%")
        logger.info(f"   Time: {report['level3_time']:.1f}s")

        # Confidence breakdown
        if report['confirmed_duplicates'] > 0:
            logger.info(f"\n🎯 Confidence Distribution:")
            logger.info(f"   High:   {report['confidence_high']} ({report['confidence_high']/report['confirmed_duplicates']*100:.1f}%)")
            logger.info(f"   Medium: {report['confidence_medium']} ({report['confidence_medium']/report['confirmed_duplicates']*100:.1f}%)")
            logger.info(f"   Low:    {report['confidence_low']} ({report['confidence_low']/report['confirmed_duplicates']*100:.1f}%)")

        # Overall stats
        logger.info(f"\n⏱️  Total Time: {report['total_time']:.1f}s ({report['total_time']/60:.1f} minutes)")
        logger.info(f"   Avg per Video: {report['avg_time_per_video']:.2f}s")

        if report['candidates_level1'] > 0:
            logger.info(f"\n📉 Overall Reduction: {report['overall_reduction']:.1f}%")
            logger.info(f"   ({report['candidates_level1']} → {report['confirmed_duplicates']} pairs)")

        logger.info("\n" + "═" * 70)

    def get_pipeline_status(self) -> Dict:
        """
        Get current status of the pipeline components.

        Returns:
            Dictionary with availability status of each level
        """
        return {
            'level1_available': self.lsh_analyzer is not None,
            'level2_available': self.long_audio is not None,
            'level3_available': self.phash_comparator is not None,
            'pipeline_ready': all([
                self.lsh_analyzer is not None,
                self.long_audio is not None,
                self.phash_comparator is not None
            ])
        }
