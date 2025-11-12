"""Enhanced rename engine with redo support and transaction logging."""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional, Dict
from src.core.logger import Logger

logger = Logger.get_logger('BatchRenamer.EnhancedRenamer')


class RenameTransaction:
    """Represents a single rename transaction with full history."""

    def __init__(self, old_path: str, new_path: str, timestamp: str = None):
        """
        Initialize rename transaction.

        Args:
            old_path: Original file path
            new_path: New file path after rename
            timestamp: Transaction timestamp (auto-generated if None)
        """
        self.old_path = old_path
        self.new_path = new_path
        self.timestamp = timestamp or datetime.now().isoformat()
        self.success = True
        self.error_message = None

    def to_dict(self) -> Dict:
        """Convert transaction to dictionary for logging."""
        return {
            'timestamp': self.timestamp,
            'old_path': self.old_path,
            'new_path': self.new_path,
            'old_name': Path(self.old_path).name,
            'new_name': Path(self.new_path).name,
            'success': self.success,
            'error': self.error_message
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'RenameTransaction':
        """Create transaction from dictionary."""
        trans = cls(data['old_path'], data['new_path'], data['timestamp'])
        trans.success = data.get('success', True)
        trans.error_message = data.get('error')
        return trans


class EnhancedRenameEngine:
    """
    Advanced rename engine with:
    - Full undo/redo support
    - Transaction logging to file
    - Batch operation management
    - Dry-run mode (simulation)
    - Detailed history tracking
    """

    def __init__(self, log_dir: str = None):
        """
        Initialize enhanced rename engine.

        Args:
            log_dir: Directory for transaction logs (default: ~/.videoflow/batch_renamer/logs)
        """
        if log_dir is None:
            log_dir = Path.home() / '.videoflow' / 'batch_renamer' / 'logs'

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Undo/redo stacks
        self.undo_stack: List[List[RenameTransaction]] = []
        self.redo_stack: List[List[RenameTransaction]] = []

        # Current session log file
        self.session_log_file = self.log_dir / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.session_transactions: List[RenameTransaction] = []

    def rename_file(self, old_path: str, new_filename: str, dry_run: bool = False) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Rename a single file.

        Args:
            old_path: Original file path
            new_filename: New filename (without path)
            dry_run: If True, simulate without actually renaming

        Returns:
            tuple: (success: bool, new_path: str or None, error_msg: str or None)
        """
        try:
            old_path_obj = Path(old_path)
            new_path = old_path_obj.parent / new_filename

            # Validation
            if new_path.exists() and new_path != old_path_obj:
                return False, None, f"File already exists: {new_filename}"

            if not self._is_valid_filename(new_filename):
                return False, None, f"Invalid filename: {new_filename}"

            if dry_run:
                # Simulation mode - don't actually rename
                logger.info(f"[DRY RUN] Would rename: {old_path_obj.name} → {new_filename}")
                return True, str(new_path), None

            # Perform actual rename
            old_path_obj.rename(new_path)

            # Create transaction record
            transaction = RenameTransaction(str(old_path), str(new_path))
            self.session_transactions.append(transaction)

            logger.info(f"Renamed: {old_path_obj.name} → {new_filename}")
            return True, str(new_path), None

        except Exception as e:
            logger.error(f"Error renaming {old_path}: {e}")
            transaction = RenameTransaction(old_path, "")
            transaction.success = False
            transaction.error_message = str(e)
            self.session_transactions.append(transaction)
            return False, None, str(e)

    def rename_batch(self, rename_list: List[Tuple[str, str]], dry_run: bool = False) -> Tuple[int, List[Tuple[str, str]]]:
        """
        Rename multiple files as a single transaction.

        Args:
            rename_list: List of (old_path, new_filename) tuples
            dry_run: If True, simulate without actually renaming

        Returns:
            tuple: (successful_count, failed_list)
        """
        successful = 0
        failed = []
        batch_transactions = []

        if dry_run:
            logger.info(f"[DRY RUN] Simulating rename of {len(rename_list)} files")

        # Detect duplicate target filenames
        target_names = {}
        for old_path, new_filename in rename_list:
            old_path_obj = Path(old_path)
            new_path = old_path_obj.parent / new_filename
            new_path_str = str(new_path).lower()

            if new_path_str in target_names:
                failed.append((old_path, f"Duplicate target name in batch: {new_filename}"))
            else:
                target_names[new_path_str] = old_path

        # Filter out failed files
        failed_paths = {old_path for old_path, _ in failed}
        rename_list = [(old, new) for old, new in rename_list if old not in failed_paths]

        if dry_run:
            # Dry run - just validate and log
            for old_path, new_filename in rename_list:
                success, new_path, error = self.rename_file(old_path, new_filename, dry_run=True)
                if success:
                    successful += 1
                    batch_transactions.append(RenameTransaction(old_path, new_path))
                else:
                    failed.append((old_path, error))
        else:
            # Actual rename with two-phase commit
            # Phase 1: Rename to temporary names
            temp_renames = []
            for old_path, new_filename in rename_list:
                old_path_obj = Path(old_path)
                temp_name = f".tmp_{os.getpid()}_{len(temp_renames)}_{old_path_obj.name}"
                temp_path = old_path_obj.parent / temp_name

                try:
                    old_path_obj.rename(temp_path)
                    temp_renames.append((str(temp_path), new_filename, str(old_path)))
                except Exception as e:
                    logger.error(f"Error in temp rename for {old_path}: {e}")
                    failed.append((old_path, str(e)))

            # Phase 2: Rename from temp to final names
            for temp_path, new_filename, original_path in temp_renames:
                temp_path_obj = Path(temp_path)
                new_path = temp_path_obj.parent / new_filename

                try:
                    if new_path.exists():
                        # Rollback
                        temp_path_obj.rename(original_path)
                        failed.append((original_path, f"File already exists: {new_filename}"))
                    else:
                        temp_path_obj.rename(new_path)

                        # Create transaction
                        transaction = RenameTransaction(original_path, str(new_path))
                        batch_transactions.append(transaction)
                        self.session_transactions.append(transaction)

                        successful += 1
                        logger.info(f"Renamed: {Path(original_path).name} → {new_filename}")
                except Exception as e:
                    logger.error(f"Error in final rename for {temp_path}: {e}")
                    # Try to rollback
                    try:
                        temp_path_obj.rename(original_path)
                    except Exception:
                        pass
                    failed.append((original_path, str(e)))

        # Add batch to undo stack (only if not dry run and successful)
        if not dry_run and batch_transactions:
            self.undo_stack.append(batch_transactions)
            # Clear redo stack when new operation performed
            self.redo_stack.clear()
            # Save transaction log
            self._save_transaction_log()

        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Batch rename: {successful} successful, {len(failed)} failed")
        return successful, failed

    def undo(self) -> Tuple[bool, str]:
        """
        Undo the last batch operation.

        Returns:
            tuple: (success: bool, message: str)
        """
        if not self.undo_stack:
            return False, "No operations to undo"

        try:
            # Get last batch
            batch = self.undo_stack.pop()
            undone_count = 0

            # Undo all transactions in reverse order
            for transaction in reversed(batch):
                try:
                    Path(transaction.new_path).rename(transaction.old_path)
                    undone_count += 1
                except Exception as e:
                    logger.error(f"Error undoing rename: {e}")

            # Add to redo stack
            self.redo_stack.append(batch)

            message = f"Undone {undone_count} rename(s)"
            logger.info(message)
            return True, message

        except Exception as e:
            logger.error(f"Error during undo: {e}")
            return False, str(e)

    def redo(self) -> Tuple[bool, str]:
        """
        Redo the last undone operation.

        Returns:
            tuple: (success: bool, message: str)
        """
        if not self.redo_stack:
            return False, "No operations to redo"

        try:
            # Get last undone batch
            batch = self.redo_stack.pop()
            redone_count = 0

            # Redo all transactions
            for transaction in batch:
                try:
                    Path(transaction.old_path).rename(transaction.new_path)
                    redone_count += 1
                except Exception as e:
                    logger.error(f"Error redoing rename: {e}")

            # Add back to undo stack
            self.undo_stack.append(batch)

            message = f"Redone {redone_count} rename(s)"
            logger.info(message)
            return True, message

        except Exception as e:
            logger.error(f"Error during redo: {e}")
            return False, str(e)

    def can_undo(self) -> bool:
        """Check if undo is available."""
        return len(self.undo_stack) > 0

    def can_redo(self) -> bool:
        """Check if redo is available."""
        return len(self.redo_stack) > 0

    def get_history(self, limit: int = 50) -> List[Dict]:
        """
        Get recent transaction history.

        Args:
            limit: Maximum number of transactions to return

        Returns:
            List of transaction dictionaries
        """
        return [t.to_dict() for t in self.session_transactions[-limit:]]

    def clear_history(self):
        """Clear undo/redo stacks and session transactions."""
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.session_transactions.clear()
        logger.info("History cleared")

    def _save_transaction_log(self):
        """Save transaction log to file."""
        try:
            log_data = {
                'session_start': self.session_log_file.stem,
                'transactions': [t.to_dict() for t in self.session_transactions]
            }

            with open(self.session_log_file, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)

            logger.debug(f"Transaction log saved: {self.session_log_file}")
        except Exception as e:
            logger.error(f"Error saving transaction log: {e}")

    def load_transaction_log(self, log_file: str) -> List[RenameTransaction]:
        """
        Load transaction log from file.

        Args:
            log_file: Path to log file

        Returns:
            List of transactions
        """
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                log_data = json.load(f)

            transactions = [
                RenameTransaction.from_dict(t) for t in log_data.get('transactions', [])
            ]

            logger.info(f"Loaded {len(transactions)} transactions from {log_file}")
            return transactions
        except Exception as e:
            logger.error(f"Error loading transaction log: {e}")
            return []

    def get_log_files(self) -> List[Path]:
        """
        Get all transaction log files.

        Returns:
            List of log file paths, sorted by date (newest first)
        """
        try:
            log_files = sorted(
                self.log_dir.glob('session_*.json'),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            return log_files
        except Exception as e:
            logger.error(f"Error getting log files: {e}")
            return []

    def _is_valid_filename(self, filename: str) -> bool:
        """Check if filename is valid."""
        if not filename:
            return False

        # Invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            if char in filename:
                return False

        # Reserved names (Windows)
        reserved = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4',
                   'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2',
                   'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']

        name_without_ext = Path(filename).stem.upper()
        if name_without_ext in reserved:
            return False

        return True
