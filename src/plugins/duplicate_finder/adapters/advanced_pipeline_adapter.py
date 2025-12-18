"""
Advanced Pipeline Adapter for DuplicateFlow.

This adapter replaces the legacy 3-level pipeline (LSH audio, long audio, pHash visual)
with DuplicateFlow's equivalent algorithms while maintaining the same interface.

Mapping:
- Level 1 (LSH audio) → audio_fingerprint algorithm
- Level 2 (Long audio) → audio_spectrum algorithm
- Level 3 (pHash visual) → frame_hash algorithm (pHash mode)
"""

import time
from typing import List, Dict, Optional, Callable
from pathlib import Path

from duplicateflow import Pipeline
from duplicateflow.core import get_algorithm
from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.AdvancedPipelineAdapter')


class AdvancedDuplicatePipelineAdapter:
    """
    Adapter that provides the same interface as AdvancedDuplicatePipeline
    but uses DuplicateFlow algorithms internally.

    This allows seamless replacement of the legacy 3-level system while
    maintaining compatibility with existing UI code (run_advanced_mode).
    """

    def __init__(
        self,
        config: Dict,
        db_manager,
        progress_callback: Optional[Callable] = None
    ):
        """
        Initialize the advanced pipeline adapter.

        Args:
            config: Configuration dictionary with keys:
                - 'level1_threshold': Audio fingerprint threshold (default: 200 votes)
                - 'level2_threshold': Audio spectrum threshold (default: 70.0)
                - 'level3_phash_threshold': pHash similarity threshold (default: 80.0)
            db_manager: Database manager instance
            progress_callback: Optional callback(phase, current, total, message)
        """
        self.config = config
        self.db = db_manager
        self.progress_callback = progress_callback
        self.stopped = False

        # Extract configuration with defaults
        self.level1_threshold = config.get('level1_threshold', 200)
        self.level2_threshold = config.get('level2_threshold', 70.0)
        self.level3_threshold = config.get('level3_phash_threshold', 80.0)

        logger.info(
            f"AdvancedPipelineAdapter initialized with thresholds: "
            f"L1={self.level1_threshold}, L2={self.level2_threshold}, L3={self.level3_threshold}"
        )

        # Initialize DuplicateFlow algorithms
        try:
            self.audio_fingerprint = get_algorithm('audio_fingerprint')
            self.audio_fingerprint.configure(threshold=self.level1_threshold)
            logger.info("✓ Level 1 (audio_fingerprint) initialized")
        except Exception as e:
            logger.error(f"✗ Level 1 (audio_fingerprint) unavailable: {e}")
            self.audio_fingerprint = None

        try:
            self.audio_spectrum = get_algorithm('audio_spectrum')
            self.audio_spectrum.configure(threshold=self.level2_threshold)
            logger.info("✓ Level 2 (audio_spectrum) initialized")
        except Exception as e:
            logger.error(f"✗ Level 2 (audio_spectrum) unavailable: {e}")
            self.audio_spectrum = None

        try:
            self.frame_hash = get_algorithm('frame_hash')
            self.frame_hash.configure(
                threshold=self.level3_threshold,
                hash_method='pHash'
            )
            logger.info("✓ Level 3 (frame_hash pHash) initialized")
        except Exception as e:
            logger.error(f"✗ Level 3 (frame_hash) unavailable: {e}")
            self.frame_hash = None

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
        Run the complete 3-level analysis pipeline using DuplicateFlow.

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
        logger.info(f"🔬 Starting Advanced 3-Level Analysis (DuplicateFlow) on {total_videos} videos")
        logger.info("=" * 70)

        # Initialize results
        level_times = {}
        candidates_l1 = []
        candidates_l2 = []
        confirmed = []

        # ═══════════════════════════════════════════════════════════════
        # LEVEL 1: Audio Fingerprint (Fast Initial Filtering)
        # ═══════════════════════════════════════════════════════════════
        logger.info("\n" + "─" * 70)
        logger.info("📊 LEVEL 1: Audio Fingerprinting (DuplicateFlow)")
        logger.info("─" * 70)

        level1_start = time.time()

        if self.audio_fingerprint is None:
            logger.warning("Audio fingerprint not available - skipping Level 1")
            candidates_l1 = []
        else:
            try:
                self._update_progress("Level 1", 0, total_videos, "Starting audio fingerprint analysis...")

                # Compare all pairs with audio_fingerprint
                n = len(video_paths)
                for i in range(n):
                    for j in range(i + 1, n):
                        if self.stopped:
                            logger.warning("Pipeline stopped at Level 1")
                            return None

                        self._update_progress(
                            "Level 1",
                            i * n + j,
                            n * (n - 1) // 2,
                            f"Comparing {Path(video_paths[i]).name} vs {Path(video_paths[j]).name}"
                        )

                        try:
                            result = self.audio_fingerprint.compare(video_paths[i], video_paths[j])
                            if result.is_match:
                                candidates_l1.append({
                                    'video1': video_paths[i],
                                    'video2': video_paths[j],
                                    'similarity': result.similarity,
                                    'metadata': result.metadata
                                })
                        except Exception as e:
                            logger.debug(f"Error comparing {video_paths[i]} vs {video_paths[j]}: {e}")

                level_times['level1'] = time.time() - level1_start
                logger.info(
                    f"✓ Level 1 complete: {len(candidates_l1)} candidate pairs found "
                    f"in {level_times['level1']:.1f}s"
                )

            except Exception as e:
                logger.error(f"✗ Level 1 failed: {e}", exc_info=True)
                candidates_l1 = []
                level_times['level1'] = time.time() - level1_start

        # ═══════════════════════════════════════════════════════════════
        # LEVEL 2: Audio Spectrum (Refined Filtering)
        # ═══════════════════════════════════════════════════════════════
        logger.info("\n" + "─" * 70)
        logger.info("🎵 LEVEL 2: Audio Spectrum Comparison (DuplicateFlow)")
        logger.info("─" * 70)

        level2_start = time.time()

        if len(candidates_l1) == 0:
            logger.warning("No candidates from Level 1 - skipping Level 2")
            candidates_l2 = []
        elif self.audio_spectrum is None:
            logger.warning("Audio spectrum not available - passing all Level 1 candidates to Level 3")
            candidates_l2 = candidates_l1
        else:
            try:
                self._update_progress(
                    "Level 2", 0, len(candidates_l1),
                    "Starting audio spectrum analysis..."
                )

                for idx, candidate in enumerate(candidates_l1):
                    if self.stopped:
                        logger.warning("Pipeline stopped at Level 2")
                        return None

                    self._update_progress(
                        "Level 2",
                        idx + 1,
                        len(candidates_l1),
                        f"Analyzing {Path(candidate['video1']).name} vs {Path(candidate['video2']).name}"
                    )

                    try:
                        result = self.audio_spectrum.compare(candidate['video1'], candidate['video2'])
                        if result.is_match:
                            candidates_l2.append({
                                'video1': candidate['video1'],
                                'video2': candidate['video2'],
                                'similarity': result.similarity,
                                'metadata': result.metadata
                            })
                    except Exception as e:
                        logger.debug(f"Error in Level 2 for pair: {e}")

                level_times['level2'] = time.time() - level2_start

                reduction_l1_l2 = (
                    (1 - len(candidates_l2) / len(candidates_l1)) * 100
                    if len(candidates_l1) > 0 else 0
                )

                logger.info(
                    f"✓ Level 2 complete: {len(candidates_l2)} refined candidates "
                    f"({reduction_l1_l2:.1f}% reduction) in {level_times['level2']:.1f}s"
                )

            except Exception as e:
                logger.error(f"✗ Level 2 failed: {e}", exc_info=True)
                candidates_l2 = candidates_l1
                level_times['level2'] = time.time() - level2_start

        # ═══════════════════════════════════════════════════════════════
        # LEVEL 3: pHash Visual (Final Confirmation)
        # ═══════════════════════════════════════════════════════════════
        logger.info("\n" + "─" * 70)
        logger.info("👁️  LEVEL 3: pHash Visual Confirmation (DuplicateFlow)")
        logger.info("─" * 70)

        level3_start = time.time()

        if len(candidates_l2) == 0:
            logger.warning("No candidates from Level 2 - no duplicates confirmed")
            confirmed = []
        elif self.frame_hash is None:
            logger.warning("Frame hash not available - passing all Level 2 candidates as confirmed")
            confirmed = candidates_l2
        else:
            try:
                self._update_progress(
                    "Level 3", 0, len(candidates_l2),
                    "Starting pHash visual confirmation..."
                )

                for idx, candidate in enumerate(candidates_l2):
                    if self.stopped:
                        logger.warning("Pipeline stopped at Level 3")
                        return None

                    self._update_progress(
                        "Level 3",
                        idx + 1,
                        len(candidates_l2),
                        f"Confirming {Path(candidate['video1']).name} vs {Path(candidate['video2']).name}"
                    )

                    try:
                        result = self.frame_hash.compare(candidate['video1'], candidate['video2'])
                        if result.is_match:
                            # Store in database
                            self.db.store_advanced_duplicate(
                                candidate['video1'],
                                candidate['video2'],
                                result.similarity,
                                {
                                    'algorithm': 'frame_hash',
                                    'method': 'pHash',
                                    'confidence': 'high' if result.similarity > 90 else 'medium'
                                }
                            )
                            confirmed.append({
                                'video1': candidate['video1'],
                                'video2': candidate['video2'],
                                'similarity': result.similarity,
                                'confidence': 'high' if result.similarity > 90 else 'medium',
                                'metadata': result.metadata
                            })
                    except Exception as e:
                        logger.debug(f"Error in Level 3 for pair: {e}")

                level_times['level3'] = time.time() - level3_start

                reduction_l2_l3 = (
                    (1 - len(confirmed) / len(candidates_l2)) * 100
                    if len(candidates_l2) > 0 else 0
                )

                logger.info(
                    f"✓ Level 3 complete: {len(confirmed)} confirmed duplicates "
                    f"({reduction_l2_l3:.1f}% reduction) in {level_times['level3']:.1f}s"
                )

            except Exception as e:
                logger.error(f"✗ Level 3 failed: {e}", exc_info=True)
                confirmed = candidates_l2
                level_times['level3'] = time.time() - level3_start

        # ═══════════════════════════════════════════════════════════════
        # Generate Report
        # ═══════════════════════════════════════════════════════════════
        total_time = time.time() - start_time

        report = {
            'total_videos': total_videos,
            'candidates_level1': len(candidates_l1),
            'candidates_level2': len(candidates_l2),
            'confirmed_duplicates': len(confirmed),
            'duplicates': confirmed,
            'reduction_rate_l1_l2': (
                (1 - len(candidates_l2) / len(candidates_l1)) * 100
                if len(candidates_l1) > 0 else 0
            ),
            'reduction_rate_l2_l3': (
                (1 - len(confirmed) / len(candidates_l2)) * 100
                if len(candidates_l2) > 0 else 0
            ),
            'total_time': total_time,
            'level_times': level_times,
            'level1_time': level_times.get('level1', 0),
            'level2_time': level_times.get('level2', 0),
            'level3_time': level_times.get('level3', 0),
            'avg_time_per_video': total_time / total_videos if total_videos > 0 else 0,
            'overall_reduction': (
                (1 - len(confirmed) / len(candidates_l1)) * 100
                if len(candidates_l1) > 0 else 0
            ),
            'confidence_high': sum(1 for d in confirmed if d.get('confidence') == 'high'),
            'confidence_medium': sum(1 for d in confirmed if d.get('confidence') == 'medium'),
            'confidence_low': sum(1 for d in confirmed if d.get('confidence') == 'low'),
        }

        self._print_summary(report)

        return report

    def _print_summary(self, report: Dict):
        """
        Print formatted summary report.

        Args:
            report: Report dictionary from run_complete_analysis
        """
        logger.info("\n" + "═" * 70)
        logger.info("📊 ANALYSIS COMPLETE - SUMMARY REPORT (DuplicateFlow)")
        logger.info("═" * 70)

        # Input
        logger.info(f"\n📹 Videos Analyzed: {report['total_videos']}")

        # Level 1
        logger.info(f"\n🔍 Level 1 (Audio Fingerprint):")
        logger.info(f"   Candidates Found: {report['candidates_level1']}")
        logger.info(f"   Time: {report['level1_time']:.1f}s")

        # Level 2
        logger.info(f"\n🎵 Level 2 (Audio Spectrum):")
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
            'level1_available': self.audio_fingerprint is not None,
            'level2_available': self.audio_spectrum is not None,
            'level3_available': self.frame_hash is not None,
            'pipeline_ready': all([
                self.audio_fingerprint is not None,
                self.audio_spectrum is not None,
                self.frame_hash is not None
            ])
        }
