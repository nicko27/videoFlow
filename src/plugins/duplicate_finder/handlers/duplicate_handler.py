"""
Duplicate management handler for the duplicate finder.

This module handles duplicate detection results, user decisions,
and file operations for duplicate management.
"""
import os
from typing import List, Tuple, Optional
from send2trash import send2trash

from PyQt6.QtWidgets import QDialog, QMessageBox
from PyQt6.QtCore import QObject, pyqtSignal

from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.DuplicateHandler')


class DuplicateHandler(QObject):
    """
    Handler for managing duplicate detection results.

    This class manages the list of detected duplicates, coordinates user
    decisions about duplicates, and executes file operations (deletion,
    ignoring) based on user choices.

    Attributes:
        duplicate_processed (pyqtSignal): Signal emitted after processing a duplicate.
        all_duplicates_processed (pyqtSignal): Signal emitted when all duplicates are handled.

    Example:
        ```python
        handler = DuplicateHandler(video_hasher, file_handler)
        handler.add_duplicate(file1, file2, 95.5)
        handler.process_duplicates(parent_window, comparison_dialog_class)
        ```
    """

    duplicate_processed = pyqtSignal(str, str, str)  # file1, file2, action
    all_duplicates_processed = pyqtSignal()
    subsequence_processed = pyqtSignal(str, str, str)  # short_video, long_video, action
    all_subsequences_processed = pyqtSignal()

    def __init__(self, video_hasher, file_handler) -> None:
        """
        Initialize the duplicate handler.

        Args:
            video_hasher: VideoHasher instance for managing duplicate data.
            file_handler: FileHandler instance for file operations.
        """
        super().__init__()
        self.video_hasher = video_hasher
        self.file_handler = file_handler
        self.potential_duplicates: List[Tuple[str, str, float]] = []
        self.pending_subsequences: List[Tuple[str, str, dict]] = []
        self.processing_stopped = False
        logger.info("Duplicate handler initialized")

    def add_duplicate(self, file1: str, file2: str, similarity: float) -> None:
        """
        Add a detected duplicate to the list.

        Args:
            file1: Path to first file.
            file2: Path to second file.
            similarity: Similarity percentage (0-100).
        """
        self.potential_duplicates.append((file1, file2, similarity))
        self.video_hasher.db.store_found_duplicate(file1, file2, similarity)
        logger.info(
            f"Duplicate added: {os.path.basename(file1)} <-> "
            f"{os.path.basename(file2)} ({similarity:.1f}%)"
        )

    def get_duplicate_count(self) -> int:
        """
        Get the number of pending duplicates.

        Returns:
            Number of duplicates in the queue.
        """
        return len(self.potential_duplicates)

    def clear_duplicates(self) -> None:
        """
        Clear all pending duplicates.
        """
        self.potential_duplicates.clear()
        logger.info("Duplicate list cleared")

    def sort_duplicates_by_similarity(self, descending: bool = True) -> None:
        """
        Sort duplicates by similarity score.

        Args:
            descending: If True, sort from highest to lowest similarity.
        """
        self.potential_duplicates.sort(
            key=lambda x: x[2],
            reverse=descending
        )
        logger.debug(f"Duplicates sorted by similarity (descending={descending})")

    def process_duplicates(
        self,
        parent_window,
        comparison_dialog_class
    ) -> None:
        """
        Start processing duplicates interactively.

        This method shows comparison dialogs for each duplicate and handles
        user decisions.

        Args:
            parent_window: Parent window for dialogs.
            comparison_dialog_class: Class to instantiate for comparison dialogs.
        """
        self.processing_stopped = False

        if not self.potential_duplicates:
            logger.info("No duplicates to process")
            self.all_duplicates_processed.emit()
            return

        # Sort by similarity (highest first)
        self.sort_duplicates_by_similarity(descending=True)

        logger.info(f"Starting duplicate processing: {len(self.potential_duplicates)} duplicates")
        self._process_next_duplicate(parent_window, comparison_dialog_class)

    def _process_next_duplicate(
        self,
        parent_window,
        comparison_dialog_class
    ) -> None:
        """
        Process the next duplicate in the queue.

        Args:
            parent_window: Parent window for dialogs.
            comparison_dialog_class: Class for comparison dialogs.
        """
        if not self.potential_duplicates or self.processing_stopped:
            if not self.processing_stopped:
                logger.info("All duplicates processed")
                self.all_duplicates_processed.emit()
            return

        # Get next duplicate
        duplicate_data = self.potential_duplicates[0]

        # Handle different tuple formats (with or without ID)
        if len(duplicate_data) == 4:
            file1, file2, similarity, dup_id = duplicate_data
        else:
            file1, file2, similarity = duplicate_data
            dup_id = None

        # Validate files still exist
        if not os.path.exists(file1) or not os.path.exists(file2):
            logger.warning(f"Files no longer exist, skipping: {file1} or {file2}")
            self.potential_duplicates.pop(0)
            self._process_next_duplicate(parent_window, comparison_dialog_class)
            return

        # Show comparison dialog
        dialog = comparison_dialog_class(file1, file2, similarity, parent_window)
        result = dialog.exec()

        # Handle user decision
        if result == QDialog.DialogCode.Accepted and dialog.result:
            self.handle_duplicate_choice(
                dialog.result,
                file1,
                file2,
                dup_id
            )
        elif result == QDialog.DialogCode.Rejected or dialog.result == "quit":
            # User chose to quit
            self.processing_stopped = True
            logger.info("Duplicate processing stopped by user")
            return

        # Remove processed duplicate
        self.potential_duplicates.pop(0)

        # Process next duplicate
        if not self.processing_stopped:
            self._process_next_duplicate(parent_window, comparison_dialog_class)

    def handle_duplicate_choice(
        self,
        choice: str,
        file1: str,
        file2: str,
        dup_id: Optional[int] = None
    ) -> None:
        """
        Handle user's choice for a duplicate pair.

        Args:
            choice: User choice ('keep_left', 'keep_right', 'ignore_perm', 'ignore_temp').
            file1: Path to first file.
            file2: Path to second file.
            dup_id: Optional database ID for the duplicate.
        """
        try:
            if choice == "keep_left":
                # Delete second file
                send2trash(file2)
                self.file_handler.update_file_status(file2, "🗑️ Deleted")
                logger.info(f"File deleted: {os.path.basename(file2)}")

            elif choice == "keep_right":
                # Delete first file
                send2trash(file1)
                self.file_handler.update_file_status(file1, "🗑️ Deleted")
                logger.info(f"File deleted: {os.path.basename(file1)}")

            elif choice == "ignore_perm":
                # Permanently ignore this pair
                self.video_hasher.add_ignored_pair(file1, file2)
                logger.info(
                    f"Pair permanently ignored: {os.path.basename(file1)} <-> "
                    f"{os.path.basename(file2)}"
                )

            elif choice == "ignore_temp":
                # Temporarily ignore (just skip)
                logger.info(
                    f"Pair temporarily ignored: {os.path.basename(file1)} <-> "
                    f"{os.path.basename(file2)}"
                )

            # Update database status if ID exists
            if dup_id:
                action_map = {
                    "keep_left": "kept_left",
                    "keep_right": "kept_right",
                    "ignore_perm": "ignored_permanently",
                    "ignore_temp": "ignored_temporarily"
                }
                self.video_hasher.db.update_duplicate_status(
                    dup_id,
                    "processed",
                    action_map.get(choice, choice)
                )

            # Emit signal
            self.duplicate_processed.emit(file1, file2, choice)

        except Exception as e:
            logger.error(f"Error handling duplicate choice: {e}")
            raise

    def stop_processing(self) -> None:
        """
        Stop processing duplicates.
        """
        self.processing_stopped = True
        logger.info("Duplicate processing stopped")

    def resume_processing(
        self,
        parent_window,
        comparison_dialog_class
    ) -> bool:
        """
        Resume processing duplicates.

        Args:
            parent_window: Parent window for dialogs.
            comparison_dialog_class: Class for comparison dialogs.

        Returns:
            True if resumed successfully, False otherwise.
        """
        if not self.potential_duplicates:
            logger.info("No duplicates to resume")
            return False

        self.processing_stopped = False
        logger.info(f"Resuming duplicate processing: {len(self.potential_duplicates)} remaining")
        self._process_next_duplicate(parent_window, comparison_dialog_class)
        return True

    def load_pending_duplicates(self) -> int:
        """
        Load pending duplicates from the database.

        Returns:
            Number of duplicates loaded.
        """
        try:
            pending = self.video_hasher.db.get_pending_duplicates()
            self.potential_duplicates = list(pending)
            count = len(self.potential_duplicates)
            logger.info(f"Loaded {count} pending duplicates from database")
            return count
        except Exception as e:
            logger.error(f"Error loading pending duplicates: {e}")
            return 0

    def get_statistics(self) -> dict:
        """
        Get statistics about duplicates.

        Returns:
            Dictionary with statistics.
        """
        return {
            'pending_count': len(self.potential_duplicates),
            'processing_stopped': self.processing_stopped
        }

    # ========== Subsequence Processing Methods ==========

    def add_subsequence(self, short_video: str, long_video: str, match_info: dict) -> None:
        """
        Add a detected subsequence to the list.

        Args:
            short_video: Path to shorter video (extracted).
            long_video: Path to longer video (source).
            match_info: Dictionary with match details (match_ratio, start_frame_idx, etc.).
        """
        self.pending_subsequences.append((short_video, long_video, match_info))
        logger.info(
            f"Subsequence added: {os.path.basename(short_video)} in "
            f"{os.path.basename(long_video)} ({match_info.get('match_ratio', 0)*100:.1f}%)"
        )

    def get_subsequence_count(self) -> int:
        """
        Get the number of pending subsequences.

        Returns:
            Number of subsequences in the queue.
        """
        return len(self.pending_subsequences)

    def clear_subsequences(self) -> None:
        """
        Clear all pending subsequences.
        """
        self.pending_subsequences.clear()
        logger.info("Subsequence list cleared")

    def process_subsequences(
        self,
        parent_window,
        comparison_dialog_class
    ) -> None:
        """
        Start processing subsequences interactively.

        This method shows comparison dialogs for each subsequence and handles
        user decisions.

        Args:
            parent_window: Parent window for dialogs.
            comparison_dialog_class: Class to instantiate for comparison dialogs.
        """
        self.processing_stopped = False

        if not self.pending_subsequences:
            logger.info("No subsequences to process")
            self.all_subsequences_processed.emit()
            return

        logger.info(f"Starting subsequence processing: {len(self.pending_subsequences)} subsequences")
        self._process_next_subsequence(parent_window, comparison_dialog_class)

    def _process_next_subsequence(
        self,
        parent_window,
        comparison_dialog_class
    ) -> None:
        """
        Process the next subsequence in the queue.

        Args:
            parent_window: Parent window for dialogs.
            comparison_dialog_class: Class for comparison dialogs.
        """
        if not self.pending_subsequences or self.processing_stopped:
            if not self.processing_stopped:
                logger.info("All subsequences processed")
                self.all_subsequences_processed.emit()
            return

        # Get next subsequence
        short_video, long_video, match_info = self.pending_subsequences[0]

        # Validate files still exist
        if not os.path.exists(short_video) or not os.path.exists(long_video):
            logger.warning(f"Files no longer exist, skipping: {short_video} or {long_video}")
            self.pending_subsequences.pop(0)
            self._process_next_subsequence(parent_window, comparison_dialog_class)
            return

        # Show comparison dialog
        dialog = comparison_dialog_class(short_video, long_video, match_info, parent_window)
        result = dialog.exec()

        # Handle user decision
        if result == QDialog.DialogCode.Accepted and dialog.result:
            self.handle_subsequence_choice(
                dialog.result,
                short_video,
                long_video
            )
        elif result == QDialog.DialogCode.Rejected or dialog.result == "skip":
            # User chose to skip
            logger.info(f"Subsequence skipped: {os.path.basename(short_video)}")

        # Remove processed subsequence
        self.pending_subsequences.pop(0)

        # Process next subsequence
        if not self.processing_stopped:
            self._process_next_subsequence(parent_window, comparison_dialog_class)

    def handle_subsequence_choice(
        self,
        choice: str,
        short_video: str,
        long_video: str
    ) -> None:
        """
        Handle user's choice for a subsequence pair.

        Args:
            choice: User choice ('keep_short', 'keep_long', 'keep_both', 'skip').
            short_video: Path to shorter video.
            long_video: Path to longer video.
        """
        try:
            if choice == "keep_short":
                # Delete long video
                send2trash(long_video)
                self.file_handler.update_file_status(long_video, "🗑️ Deleted")
                logger.info(f"Long video deleted: {os.path.basename(long_video)}")

                # Update database
                self.video_hasher.db.update_subsequence_status(
                    short_video,
                    long_video,
                    "processed",
                    "kept_short"
                )

            elif choice == "keep_long":
                # Delete short video
                send2trash(short_video)
                self.file_handler.update_file_status(short_video, "🗑️ Deleted")
                logger.info(f"Short video deleted: {os.path.basename(short_video)}")

                # Update database
                self.video_hasher.db.update_subsequence_status(
                    short_video,
                    long_video,
                    "processed",
                    "kept_long"
                )

            elif choice == "keep_both":
                # Keep both files
                logger.info(
                    f"Both videos kept: {os.path.basename(short_video)} & "
                    f"{os.path.basename(long_video)}"
                )

                # Update database
                self.video_hasher.db.update_subsequence_status(
                    short_video,
                    long_video,
                    "processed",
                    "kept_both"
                )

            # Emit signal
            self.subsequence_processed.emit(short_video, long_video, choice)

        except Exception as e:
            logger.error(f"Error handling subsequence choice: {e}")
            raise

    def load_pending_subsequences(self) -> int:
        """
        Load pending subsequences from the database.

        Returns:
            Number of subsequences loaded.
        """
        try:
            pending = self.video_hasher.db.get_pending_subsequences()
            self.pending_subsequences = []

            for row in pending:
                short_video, long_video, match_ratio, start_frame_idx, confidence = row[:5]
                match_info = {
                    'match_ratio': match_ratio,
                    'start_frame_idx': start_frame_idx,
                    'confidence': confidence
                }
                self.pending_subsequences.append((short_video, long_video, match_info))

            count = len(self.pending_subsequences)
            logger.info(f"Loaded {count} pending subsequences from database")
            return count
        except Exception as e:
            logger.error(f"Error loading pending subsequences: {e}")
            return 0
