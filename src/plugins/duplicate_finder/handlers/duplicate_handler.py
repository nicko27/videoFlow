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
