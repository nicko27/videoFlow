"""Dialog management for VideoConverter UI.

This module handles creation and display of various dialogs used in
the VideoConverter interface.
"""

from PyQt6.QtWidgets import (
    QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QSpinBox, QCheckBox, QPushButton, QDialogButtonBox, QFileDialog
)
from pathlib import Path
from typing import TYPE_CHECKING, Optional, List, Tuple
import shutil

from ..utils import format_size, format_duration
from src.core.logger import Logger
from src.core.i18n import t

if TYPE_CHECKING:
    from ..window import VideoConverterWindow

logger = Logger.get_logger('VideoConverter.Dialogs')


class DialogManager:
    """Manages dialogs for the VideoConverter UI.

    Handles creation and display of help, statistics, discovery configuration,
    and confirmation dialogs.
    """

    def __init__(self, window: 'VideoConverterWindow'):
        """Initialize the dialog manager.

        Args:
            window: Parent VideoConverterWindow instance.
        """
        self.window = window

    def show_help(self) -> None:
        """Display the help dialog with keyboard shortcuts and tips."""
        help_text = t(
            "video_converter.dialog.help.text",
            """
<h2>🎬 Video Converter Pro - Quick Guide</h2>

<h3>📁 Adding Files:</h3>
• <b>Ctrl+O</b>: Add files
• <b>Ctrl+Shift+O</b>: Add folder
• <b>Drag & Drop</b>: Drop directly into the window

<h3>⌨️ Useful Shortcuts:</h3>
• <b>F5</b>: Start conversion
• <b>Escape</b>: Stop conversion
• <b>Ctrl+A</b>: Select all files
• <b>Delete</b>: Remove selection
• <b>Ctrl+L</b>: Clear list
• <b>Ctrl+,</b>: Open settings

<h3>🎯 Smart Filtering:</h3>
• Configure minimum size in settings
• Already converted files (_cvt suffix) can be ignored
• Use "🔍 Filter" to apply new filters

<h3>⚙️ Conversion:</h3>
• Select files to convert
• Configure settings according to your needs
• Start with F5 or "Start" button
• Follow progress in real-time

<h3>💡 Tips:</h3>
• Time estimation improves with usage
• Conversions are automatically paused if disk space is insufficient
• Use system icon to view notifications
            """
        )

        QMessageBox.information(
            self.window,
            t("video_converter.dialog.help.title", "Help - Video Converter Pro"),
            help_text
        )

    def show_stats(self) -> None:
        """Display conversion statistics dialog."""
        try:
            from ..stats import StatsManager
            stats_manager = StatsManager()
            summary = stats_manager.get_stats_summary()

            stats_text = f"""
Total conversions: {summary['total_conversions']}
Successful: {summary['successful_conversions']}
Failed: {summary['failed_conversions']}
Success rate: {summary['success_rate']:.1f}%

Space saved: {format_size(summary['total_space_saved'])}
Average compression: {summary['average_compression']:.1f}%
Average attempts: {summary['average_attempts']:.1f}
            """

            dialog = QMessageBox(self.window)
            dialog.setWindowTitle(t("video_converter.dialog.stats.title", "📊 Statistics"))
            dialog.setIcon(QMessageBox.Icon.Information)
            dialog.setText(stats_text.strip())
            dialog.exec()

        except Exception as e:
            QMessageBox.warning(
                self.window,
                t("video_converter.dialog.error.title", "Error"),
                t("video_converter.dialog.stats.error", f"Unable to load statistics: {e}", error=e)
            )

    def show_discovery_dialog(self) -> Optional[Tuple[List[Path], int]]:
        """Show file discovery configuration dialog.

        Returns:
            Tuple of (selected_folders, min_size_mb) or None if cancelled.
        """
        dialog = QDialog(self.window)
        dialog.setWindowTitle(t("video_converter.dialog.discovery.title", "🔍 Discovery Configuration"))
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout(dialog)

        # Minimum size selection
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel(t("video_converter.dialog.discovery.min_size", "Minimum size:")))
        size_spin = QSpinBox()
        size_spin.setRange(50, 5000)
        size_spin.setValue(500)  # 500MB default
        size_spin.setSuffix(" MB")
        size_layout.addWidget(size_spin)
        size_layout.addStretch()
        layout.addLayout(size_layout)

        # Folders to scan
        layout.addWidget(QLabel(t("video_converter.dialog.discovery.folders", "Folders to scan:")))

        # Default folders
        default_folders = [
            (Path.home() / "Videos", t("video_converter.dialog.discovery.folder_videos", "Videos Folder")),
            (Path.home() / "Downloads", t("video_converter.dialog.discovery.folder_downloads", "Downloads")),
            (Path.home() / "Desktop", t("video_converter.dialog.discovery.folder_desktop", "Desktop")),
        ]

        checkboxes = []
        for folder_path, description in default_folders:
            if folder_path.exists():
                cb = QCheckBox(f"{description} ({folder_path})")
                cb.setChecked(True)
                cb.folder_path = folder_path
                layout.addWidget(cb)
                checkboxes.append(cb)

        # Custom folder option
        custom_layout = QHBoxLayout()
        custom_cb = QCheckBox(t("video_converter.dialog.discovery.custom_label", "Custom folder:"))
        custom_btn = QPushButton(t("video_converter.dialog.discovery.browse", "Browse..."))
        custom_path = None

        def browse_custom():
            nonlocal custom_path
            folder = QFileDialog.getExistingDirectory(
                dialog,
                t("video_converter.window.dialog.select_folder", "Select Folder")
            )
            if folder:
                custom_path = Path(folder)
                custom_cb.setText(
                    t(
                        "video_converter.dialog.discovery.custom_selected",
                        f"Custom: {custom_path.name}",
                        folder=custom_path.name
                    )
                )
                custom_cb.setChecked(True)

        custom_btn.clicked.connect(browse_custom)
        custom_layout.addWidget(custom_cb)
        custom_layout.addWidget(custom_btn)
        layout.addLayout(custom_layout)

        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Collect selected folders
            selected_folders = []
            for cb in checkboxes:
                if cb.isChecked():
                    selected_folders.append(cb.folder_path)

            if custom_cb.isChecked() and custom_path:
                selected_folders.append(custom_path)

            if selected_folders:
                return selected_folders, size_spin.value()

        return None

    def confirm_disk_space(self, estimated_needed: int, free_space: int) -> bool:
        """Show disk space warning dialog.

        Args:
            estimated_needed: Estimated space needed in bytes.
            free_space: Available free space in bytes.

        Returns:
            True if user wants to continue anyway.
        """
        reply = QMessageBox.warning(
            self.window,
            t("video_converter.dialog.disk_space.title", "⚠️ Insufficient Disk Space"),
            t(
                "video_converter.dialog.disk_space.body",
                f"Free space: {format_size(free_space)}\n"
                f"Estimated space needed: {format_size(estimated_needed)}\n\n"
                f"Do you want to continue anyway?",
                free=format_size(free_space),
                needed=format_size(estimated_needed)
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes

    def confirm_removal(self, count: int) -> bool:
        """Show removal confirmation dialog.

        Args:
            count: Number of files to remove.

        Returns:
            True if user confirms removal.
        """
        reply = QMessageBox.question(
            self.window,
            t("video_converter.dialog.removal.title", "Confirm Removal"),
            t(
                "video_converter.dialog.removal.body",
                f"Remove {count} file(s) from the list?",
                count=count
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes

    def confirm_stop_discovery(self) -> bool:
        """Show stop discovery confirmation dialog.

        Returns:
            True if user wants to stop discovery and close.
        """
        reply = QMessageBox.question(
            self.window,
            t("video_converter.dialog.stop_discovery.title", "Stop Discovery"),
            t("video_converter.dialog.stop_discovery.body", "File discovery is in progress. Stop and close?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes

    def confirm_stop_conversions(self) -> bool:
        """Show stop conversions confirmation dialog.

        Returns:
            True if user wants to stop conversions and close.
        """
        reply = QMessageBox.question(
            self.window,
            t("video_converter.dialog.stop_conversions.title", "Stop Conversions"),
            t("video_converter.dialog.stop_conversions.body", "Conversions are in progress. Stop and close?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes

    def confirm_clear_with_active(self) -> bool:
        """Show clear list confirmation when conversions are active.

        Returns:
            True if user wants to stop and clear.
        """
        reply = QMessageBox.question(
            self.window,
            t("video_converter.dialog.clear_active.title", "Confirm"),
            t("video_converter.dialog.clear_active.body", "Conversions are in progress. Stop and clear the list?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes

    def confirm_apply_filters(self) -> bool:
        """Show apply filters confirmation dialog.

        Returns:
            True if user wants to apply filters.
        """
        reply = QMessageBox.question(
            self.window,
            t("video_converter.dialog.apply_filters.title", "Filter List"),
            t(
                "video_converter.dialog.apply_filters.body",
                "Settings updated. Do you want to apply the new filters to the current list?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes

    def show_completion_summary(
        self,
        successful: int,
        failed: int,
        total_time: str
    ) -> None:
        """Show conversion completion summary dialog.

        Args:
            successful: Number of successful conversions.
            failed: Number of failed conversions.
            total_time: Total time elapsed string.
        """
        if successful + failed == 0:
            return

        success_rate = (
            (successful / (successful + failed) * 100)
            if (successful + failed) > 0 else 0
        )

        QMessageBox.information(
            self.window,
            t("video_converter.dialog.completion.title", "🎬 Conversions Complete"),
            t(
                "video_converter.dialog.completion.body",
                f"All conversions are complete{total_time}!\n\n"
                f"📊 Results:\n"
                f"• Total processed: {successful + failed}\n"
                f"• ✅ Successful: {successful}\n"
                f"• ❌ Failed: {failed}\n"
                f"• 📈 Success rate: {success_rate:.1f}%\n\n"
                f"💡 Check statistics for more details.",
                time=total_time,
                total=successful + failed,
                success=successful,
                failed=failed,
                rate=f"{success_rate:.1f}%"
            )
        )

    def show_discovery_complete(self, count: int, total_size: int) -> None:
        """Show discovery completion dialog.

        Args:
            count: Number of files discovered.
            total_size: Total size of discovered files.
        """
        if count > 0:
            QMessageBox.information(
                self.window,
                t("video_converter.dialog.discovery_complete.title", "Discovery Complete"),
                t(
                    "video_converter.dialog.discovery_complete.body_found",
                    f"Found {count} large files\nTotal size: {format_size(total_size)}\n\nUse settings to adjust conversion criteria.",
                    count=count,
                    size=format_size(total_size)
                )
            )
        else:
            QMessageBox.information(
                self.window,
                t("video_converter.dialog.discovery_complete.title", "Discovery Complete"),
                t(
                    "video_converter.dialog.discovery_complete.body_none",
                    "No large video files found.\n\nTry reducing the minimum size or selecting other folders."
                )
            )

    def show_no_ffmpeg_error(self) -> None:
        """Show FFmpeg not found error dialog."""
        QMessageBox.critical(
            self.window,
            t("video_converter.dialog.ffmpeg_error.title", "❌ Error"),
            t(
                "video_converter.dialog.ffmpeg_error.body",
                "FFmpeg is not installed or accessible.\n\n"
                "💡 Solution: Install FFmpeg from https://ffmpeg.org\n"
                "Or add it to the system PATH."
            )
        )

    def show_no_files_selected_warning(self) -> None:
        """Show no files selected warning."""
        QMessageBox.warning(
            self.window,
            t("video_converter.dialog.no_files_selected.title", "Warning"),
            t("video_converter.dialog.no_files_selected.body", "No files selected for conversion")
        )

    def show_no_files_to_remove_info(self) -> None:
        """Show no files to remove info."""
        QMessageBox.information(
            self.window,
            t("video_converter.dialog.no_files_to_remove.title", "Info"),
            t(
                "video_converter.dialog.no_files_to_remove.body",
                "No files selected to remove\n(Files being converted cannot be removed)"
            )
        )

    def show_discovery_in_progress_info(self) -> None:
        """Show discovery already in progress info."""
        QMessageBox.information(
            self.window,
            t("video_converter.dialog.discovery_in_progress.title", "Info"),
            t("video_converter.dialog.discovery_in_progress.body", "Discovery already in progress...")
        )

    def show_no_folders_selected_info(self) -> None:
        """Show no folders selected info."""
        QMessageBox.information(
            self.window,
            t("video_converter.dialog.no_folders_selected.title", "Info"),
            t("video_converter.dialog.no_folders_selected.body", "No folders selected")
        )
