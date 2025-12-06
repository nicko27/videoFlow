"""
Worker thread for subsequence verification with caching and progress.

This worker handles verification of subsequence matches in the background,
with intelligent caching to avoid re-verification of unchanged files.
"""

import os
from typing import List, Dict
from PyQt6.QtCore import QThread, pyqtSignal

from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.VerificationWorker')


class VerificationWorker(QThread):
    """
    Background worker for verifying subsequence matches.

    Uses Strategy 3 (Scene Cuts Veto + DCT) with intelligent caching:
    - Checks cache first (DB with mtime + file_size)
    - Only re-verifies if files modified
    - Stores results for future runs
    - Provides real-time progress updates

    Signals:
        progress: (current, total, message) - Progress update
        verification_complete: (match_data, result) - Single verification done
        all_complete: (results) - All verifications finished
        error: (error_message) - Error occurred
        finished: () - Worker finished
    """

    # Signals
    progress = pyqtSignal(int, int, str)  # current, total, message
    verification_complete = pyqtSignal(dict, dict)  # match_data, verification_result
    all_complete = pyqtSignal(list)  # list of all results
    error = pyqtSignal(str)  # error message
    finished = pyqtSignal()  # worker finished

    def __init__(self, verifier, matches, db, parent=None):
        """
        Initialize verification worker.

        Args:
            verifier: SubsequenceVerificationMethods instance
            matches: List of match dicts with:
                - short_video: str
                - long_video: str
                - start_time: float
                - duration: float
                - sequence_score: float
            db: VideoDatabase instance for caching
            parent: Parent QObject (optional)
        """
        super().__init__(parent)
        self.verifier = verifier
        self.matches = matches
        self.db = db
        self._stop_requested = False
        self.results = []

        logger.info(f"VerificationWorker initialized with {len(matches)} matches")

    def stop(self):
        """Request worker to stop gracefully."""
        self._stop_requested = True
        logger.info("Verification stop requested")

    def run(self):
        """Run verification process with caching."""
        try:
            total = len(self.matches)
            cache_hits = 0
            verifications = 0

            for i, match in enumerate(self.matches):
                if self._stop_requested:
                    logger.info(f"Verification cancelled at {i}/{total}")
                    break

                short_name = os.path.basename(match['short_video'])
                current = i + 1

                # Check cache first
                self.progress.emit(current, total, f"🔍 Checking cache: {short_name}")

                cached_result = self.db.get_cached_verification(
                    match['short_video'],
                    match['long_video'],
                    match['start_time']
                )

                if cached_result:
                    # Use cached result
                    cache_hits += 1
                    self.progress.emit(
                        current, total,
                        f"✓ Cached ({cache_hits} hits): {short_name}"
                    )

                    logger.debug(f"Using cached verification for {short_name}")

                    # Emit cached result
                    self.verification_complete.emit(match, cached_result)
                    self.results.append({
                        'match': match,
                        'result': cached_result,
                        'from_cache': True
                    })

                else:
                    # Verify from scratch
                    verifications += 1
                    self.progress.emit(
                        current, total,
                        f"🔬 Verifying ({verifications} new): {short_name}"
                    )

                    logger.info(f"Verifying {short_name} @ {match['start_time']:.1f}s")

                    # Run verification
                    verification_result = self.verifier.verify_with_strategy3(
                        short_video=match['short_video'],
                        long_video=match['long_video'],
                        start_time=match['start_time'],
                        duration=match['duration'],
                        sequence_score=match['sequence_score']
                    )

                    # Store in cache for future runs
                    self.db.store_verification_result(
                        match['short_video'],
                        match['long_video'],
                        match['start_time'],
                        match['duration'],
                        match['sequence_score'],
                        verification_result
                    )

                    # Emit result
                    self.verification_complete.emit(match, verification_result)
                    self.results.append({
                        'match': match,
                        'result': verification_result,
                        'from_cache': False
                    })

            # Emit completion summary
            if not self._stop_requested:
                logger.info(
                    f"Verification complete: {total} matches "
                    f"({cache_hits} cached, {verifications} verified)"
                )
                self.all_complete.emit(self.results)

        except Exception as e:
            error_msg = f"Verification error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error.emit(error_msg)

        finally:
            self.finished.emit()
