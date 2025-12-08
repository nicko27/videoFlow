"""
Cluster View Dialog for Duplicate Finder plugin.

Displays detected clusters of similar videos and allows management operations.
"""

from typing import Optional, List
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QGroupBox, QTextEdit, QSplitter,
    QMessageBox, QProgressDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from ..analysis.cluster_detector import ClusterDetector, Cluster
from src.core.logger import Logger

logger = Logger.get_logger(__name__)


class ClusterViewDialog(QDialog):
    """
    Dialog for viewing and managing duplicate clusters.

    Displays clusters detected by ClusterDetector with:
    - Cluster table with statistics
    - Video details for selected cluster
    - Actions to manage clusters (keep representative, delete others, etc.)
    """

    # Signals
    files_deleted = pyqtSignal(list)  # List of deleted file paths

    def __init__(self, detector: ClusterDetector, parent=None):
        super().__init__(parent)

        self.detector = detector
        self.selected_cluster: Optional[Cluster] = None

        self.setWindowTitle("Duplicate Clusters")
        self.resize(1000, 700)

        self._setup_ui()
        self._load_clusters()

        logger.info("ClusterViewDialog initialized")

    def _setup_ui(self):
        """Create the UI layout."""
        layout = QVBoxLayout(self)

        # ===== Header with Statistics =====
        header_layout = QHBoxLayout()
        header_label = QLabel("🔗 Duplicate Clusters")
        header_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()

        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("font-size: 11px; color: #666;")
        header_layout.addWidget(self.stats_label)

        layout.addLayout(header_layout)

        # ===== Splitter for Clusters and Details =====
        splitter = QSplitter(Qt.Orientation.Vertical)

        # ===== Clusters Table =====
        cluster_group = QGroupBox("Clusters")
        cluster_layout = QVBoxLayout(cluster_group)

        self.clusters_table = QTableWidget()
        self.clusters_table.setColumnCount(6)
        self.clusters_table.setHorizontalHeaderLabels([
            "ID", "Videos", "Total Size", "Avg Similarity", "Representative", "Potential Savings"
        ])

        # Column sizing
        header = self.clusters_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Videos
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Total Size
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Avg Similarity
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)  # Representative
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Savings

        self.clusters_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.clusters_table.setAlternatingRowColors(True)
        self.clusters_table.itemSelectionChanged.connect(self._on_cluster_selected)

        cluster_layout.addWidget(self.clusters_table)
        splitter.addWidget(cluster_group)

        # ===== Cluster Details =====
        details_group = QGroupBox("Cluster Details")
        details_layout = QVBoxLayout(details_group)

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(200)
        details_layout.addWidget(self.details_text)

        splitter.addWidget(details_group)
        layout.addWidget(splitter)

        # ===== Actions =====
        actions_layout = QHBoxLayout()

        self.refresh_btn = QPushButton("🔄 Refresh Clusters")
        self.refresh_btn.clicked.connect(self._refresh_clusters)
        actions_layout.addWidget(self.refresh_btn)

        self.view_btn = QPushButton("👁 View Videos")
        self.view_btn.clicked.connect(self._view_cluster_videos)
        self.view_btn.setEnabled(False)
        actions_layout.addWidget(self.view_btn)

        self.keep_best_btn = QPushButton("✅ Keep Representative Only")
        self.keep_best_btn.clicked.connect(self._keep_representative_only)
        self.keep_best_btn.setEnabled(False)
        self.keep_best_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        actions_layout.addWidget(self.keep_best_btn)

        actions_layout.addStretch()

        self.export_btn = QPushButton("💾 Export Clusters")
        self.export_btn.clicked.connect(self._export_clusters)
        actions_layout.addWidget(self.export_btn)

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        actions_layout.addWidget(self.close_btn)

        layout.addLayout(actions_layout)

    def _load_clusters(self):
        """Load clusters into the table."""
        # Get cluster statistics
        stats = self.detector.get_stats()
        self.stats_label.setText(
            f"Total: {stats['total_videos']} videos | "
            f"Clusters: {stats['total_clusters']} | "
            f"Clustered: {stats['clustered_videos']} videos | "
            f"Potential savings: {self._format_size(stats['total_duplicate_size_bytes'])}"
        )

        # Clear table
        self.clusters_table.setRowCount(0)

        # Add clusters
        for row, cluster in enumerate(self.detector.clusters):
            self.clusters_table.insertRow(row)

            # ID
            id_item = QTableWidgetItem(str(cluster.cluster_id))
            id_item.setData(Qt.ItemDataRole.UserRole, cluster.cluster_id)
            self.clusters_table.setItem(row, 0, id_item)

            # Videos count
            videos_item = QTableWidgetItem(str(cluster.size))
            self.clusters_table.setItem(row, 1, videos_item)

            # Total size
            size_item = QTableWidgetItem(self._format_size(cluster.total_size))
            self.clusters_table.setItem(row, 2, size_item)

            # Average similarity
            sim_item = QTableWidgetItem(f"{cluster.avg_similarity:.1%}")
            self.clusters_table.setItem(row, 3, sim_item)

            # Representative video
            rep_path = "N/A"
            if cluster.representative_id and cluster.representative_id in self.detector.nodes:
                rep_node = self.detector.nodes[cluster.representative_id]
                rep_path = Path(rep_node.path).name
            rep_item = QTableWidgetItem(rep_path)
            self.clusters_table.setItem(row, 4, rep_item)

            # Potential savings (size of all non-representative videos)
            if cluster.representative_id:
                rep_size = self.detector.nodes[cluster.representative_id].size if cluster.representative_id in self.detector.nodes else 0
                savings = cluster.total_size - rep_size
            else:
                savings = 0
            savings_item = QTableWidgetItem(self._format_size(savings))
            self.clusters_table.setItem(row, 5, savings_item)

            # Color code by cluster size
            color = self._get_cluster_color(cluster.size)
            for col in range(6):
                item = self.clusters_table.item(row, col)
                if item:
                    item.setBackground(QColor(color))

        logger.info(f"Loaded {len(self.detector.clusters)} clusters")

    def _on_cluster_selected(self):
        """Handle cluster selection."""
        selected_rows = self.clusters_table.selectionModel().selectedRows()
        if not selected_rows:
            self.selected_cluster = None
            self.details_text.clear()
            self.view_btn.setEnabled(False)
            self.keep_best_btn.setEnabled(False)
            return

        row = selected_rows[0].row()
        cluster_id = self.clusters_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self.selected_cluster = self.detector.get_cluster_by_id(cluster_id)

        if self.selected_cluster:
            self._show_cluster_details()
            self.view_btn.setEnabled(True)
            self.keep_best_btn.setEnabled(True)

    def _show_cluster_details(self):
        """Display details of the selected cluster."""
        if not self.selected_cluster:
            return

        cluster = self.selected_cluster
        videos = self.detector.get_cluster_videos(cluster.cluster_id)

        # Build details text
        details = f"<h3>Cluster {cluster.cluster_id}</h3>"
        details += f"<p><b>Videos:</b> {cluster.size} | "
        details += f"<b>Total Size:</b> {self._format_size(cluster.total_size)} | "
        details += f"<b>Avg Similarity:</b> {cluster.avg_similarity:.1%}</p>"

        details += "<h4>Videos in Cluster:</h4>"
        details += "<table border='1' cellpadding='3' cellspacing='0' style='width:100%'>"
        details += "<tr style='background-color:#E0E0E0'><th>ID</th><th>File</th><th>Size</th><th>Duration</th><th>Connections</th></tr>"

        for video in videos:
            is_rep = video.video_id == cluster.representative_id
            row_style = "background-color:#C8E6C9;" if is_rep else ""
            rep_marker = " ⭐" if is_rep else ""

            details += f"<tr style='{row_style}'>"
            details += f"<td>{video.video_id}</td>"
            details += f"<td>{Path(video.path).name}{rep_marker}</td>"
            details += f"<td>{self._format_size(video.size)}</td>"
            details += f"<td>{video.duration:.1f}s</td>"
            details += f"<td>{video.degree}</td>"
            details += "</tr>"

        details += "</table>"

        if cluster.representative_id:
            to_delete = self.detector.get_videos_to_delete(cluster.cluster_id)
            if to_delete:
                rep_size = self.detector.nodes[cluster.representative_id].size
                savings = cluster.total_size - rep_size
                details += f"<p><b>💡 Suggestion:</b> Keep video {cluster.representative_id} (representative), "
                details += f"delete {len(to_delete)} other(s) to save {self._format_size(savings)}</p>"

        self.details_text.setHtml(details)

    def _view_cluster_videos(self):
        """View videos in the selected cluster."""
        if not self.selected_cluster:
            return

        videos = self.detector.get_cluster_videos(self.selected_cluster.cluster_id)
        video_list = "\n".join(f"- {Path(v.path).name}" for v in videos)

        QMessageBox.information(
            self, "Cluster Videos",
            f"Cluster {self.selected_cluster.cluster_id} contains {len(videos)} videos:\n\n{video_list}"
        )

    def _keep_representative_only(self):
        """Delete all videos except the representative."""
        if not self.selected_cluster:
            return

        cluster = self.selected_cluster
        to_delete = self.detector.get_videos_to_delete(cluster.cluster_id)

        if not to_delete:
            QMessageBox.information(
                self, "No Action Needed",
                "No videos to delete in this cluster."
            )
            return

        # Build confirmation message
        delete_paths = []
        for vid in to_delete:
            if vid in self.detector.nodes:
                delete_paths.append(self.detector.nodes[vid].path)

        rep_name = "N/A"
        if cluster.representative_id and cluster.representative_id in self.detector.nodes:
            rep_name = Path(self.detector.nodes[cluster.representative_id].path).name

        message = (
            f"This will delete {len(to_delete)} video(s) from cluster {cluster.cluster_id}.\n\n"
            f"Kept: {rep_name} (representative)\n\n"
            f"Deleted:\n" + "\n".join(f"- {Path(p).name}" for p in delete_paths[:10])
        )

        if len(delete_paths) > 10:
            message += f"\n... and {len(delete_paths) - 10} more"

        reply = QMessageBox.question(
            self, "Confirm Deletion",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._delete_videos(delete_paths)

    def _delete_videos(self, paths: List[str]):
        """Delete videos and emit signal."""
        progress = QProgressDialog("Deleting videos...", "Cancel", 0, len(paths), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)

        deleted = []
        for i, path in enumerate(paths):
            if progress.wasCanceled():
                break

            try:
                Path(path).unlink()
                deleted.append(path)
                logger.info(f"Deleted: {path}")
            except Exception as e:
                logger.error(f"Failed to delete {path}: {e}")

            progress.setValue(i + 1)

        progress.close()

        QMessageBox.information(
            self, "Deletion Complete",
            f"Deleted {len(deleted)} of {len(paths)} videos."
        )

        # Emit signal
        self.files_deleted.emit(deleted)

        # Refresh display
        self._refresh_clusters()

    def _refresh_clusters(self):
        """Refresh cluster detection."""
        # Note: In a real implementation, you'd reload from database
        # For now, just reload the existing clusters
        self._load_clusters()
        self.details_text.clear()
        self.selected_cluster = None
        self.view_btn.setEnabled(False)
        self.keep_best_btn.setEnabled(False)

        QMessageBox.information(
            self, "Refreshed",
            "Clusters refreshed from current data."
        )

    def _export_clusters(self):
        """Export clusters to JSON."""
        from PyQt6.QtWidgets import QFileDialog
        import json

        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Clusters",
            "clusters.json",
            "JSON Files (*.json)"
        )

        if not filename:
            return

        try:
            data = self.detector.export_clusters()
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            QMessageBox.information(
                self, "Export Complete",
                f"Exported {len(data)} clusters to {filename}"
            )
            logger.info(f"Exported clusters to {filename}")

        except Exception as e:
            QMessageBox.critical(
                self, "Export Failed",
                f"Failed to export clusters:\n{e}"
            )
            logger.error(f"Failed to export clusters: {e}")

    # ==================== Utilities ====================

    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable form."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

    def _get_cluster_color(self, size: int) -> str:
        """Get background color based on cluster size."""
        if size == 2:
            return "#E3F2FD"  # Light blue - pairs
        elif size <= 5:
            return "#FFF9C4"  # Light yellow - small
        elif size <= 10:
            return "#FFE0B2"  # Light orange - medium
        elif size <= 20:
            return "#FFCCBC"  # Light red-orange - large
        else:
            return "#F8BBD0"  # Light pink - xlarge
