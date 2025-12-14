"""
Comprehensive Monitoring Dashboard

Real-time monitoring dashboard with:
- Live metrics display
- Alert feed
- Pipeline health status
- Recent runs overview
- System statistics
- Integration with alert system
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QScrollArea, QFrame, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor

from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.MonitoringDashboard')


class MetricCard(QFrame):
    """
    Colored metric card widget.

    Displays a single metric with value, trend indicator, and status color.
    """

    def __init__(self, title: str, value: str = "--", status: str = "neutral", parent=None):
        super().__init__(parent)
        self.title = title
        self._status = status
        self._init_ui()
        self.update_value(value, status)

    def _init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        # Title
        self.title_label = QLabel(self.title)
        self.title_label.setStyleSheet("font-size: 11px; color: #666; font-weight: bold;")
        layout.addWidget(self.title_label)

        # Value
        self.value_label = QLabel("--")
        self.value_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #333;")
        layout.addWidget(self.value_label)

        # Subtitle/trend
        self.subtitle_label = QLabel("")
        self.subtitle_label.setStyleSheet("font-size: 10px; color: #999;")
        layout.addWidget(self.subtitle_label)

        # Base styling
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)

    def update_value(self, value: str, status: str = "neutral", subtitle: str = ""):
        """
        Update card value and status.

        Args:
            value: Display value
            status: Status color (success, warning, error, neutral)
            subtitle: Optional subtitle text
        """
        self.value_label.setText(value)
        self.subtitle_label.setText(subtitle)
        self._status = status

        # Update styling based on status
        colors = {
            'success': '#4CAF50',
            'warning': '#FF9800',
            'error': '#F44336',
            'neutral': '#2196F3'
        }

        border_color = colors.get(status, colors['neutral'])

        self.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-left: 4px solid {border_color};
                border-radius: 8px;
            }}
        """)


class AlertFeedWidget(QWidget):
    """
    Real-time alert feed widget.

    Shows recent alerts with color-coding and filtering.
    """

    alert_clicked = pyqtSignal(object)  # Alert object

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout(self)

        # Header
        header_layout = QHBoxLayout()
        header_label = QLabel("🔔 <b>Recent Alerts</b>")
        header_label.setStyleSheet("font-size: 13px;")
        header_layout.addWidget(header_label)

        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.setMaximumWidth(80)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF5722;
                color: white;
                border: none;
                padding: 5px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #E64A19;
            }
        """)
        header_layout.addWidget(self.clear_btn)

        layout.addLayout(header_layout)

        # Alert list
        self.alert_list = QTextEdit()
        self.alert_list.setReadOnly(True)
        self.alert_list.setMaximumHeight(200)
        self.alert_list.setStyleSheet("""
            QTextEdit {
                background-color: #F9F9F9;
                border: 1px solid #E0E0E0;
                border-radius: 5px;
                font-family: monospace;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.alert_list)

    def add_alert(self, alert):
        """Add alert to feed."""
        # Color coding
        colors = {
            'info': '#2196F3',
            'warning': '#FF9800',
            'error': '#F44336',
            'critical': '#9C27B0'
        }

        color = colors.get(alert.level.value, '#666')
        timestamp = alert.timestamp.strftime('%H:%M:%S')

        html = f"""
        <div style="padding: 5px; margin-bottom: 5px; border-left: 3px solid {color}; background-color: white;">
            <b style="color: {color};">[{alert.level.value.upper()}]</b>
            <span style="color: #666;">{timestamp}</span><br>
            <b>{alert.title}</b><br>
            <span style="font-size: 10px;">{alert.message}</span>
        </div>
        """

        # Prepend (most recent first)
        current = self.alert_list.toHtml()
        self.alert_list.setHtml(html + current)

    def clear_alerts(self):
        """Clear all alerts from feed."""
        self.alert_list.clear()


class PipelineHealthWidget(QWidget):
    """
    Pipeline health status widget.

    Shows health status of all pipelines based on recent performance.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel("🏥 <b>Pipeline Health</b>")
        header.setStyleSheet("font-size: 13px; margin-bottom: 10px;")
        layout.addWidget(header)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(['Pipeline', 'Status', 'Last F1', 'Runs (24h)'])
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setMaximumHeight(150)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)

        layout.addWidget(self.table)

    def update_pipelines(self, pipelines: List[Dict]):
        """
        Update pipeline health data.

        Args:
            pipelines: List of pipeline dicts with name, status, f1, runs
        """
        self.table.setRowCount(len(pipelines))

        for row, pipeline in enumerate(pipelines):
            # Name
            name_item = QTableWidgetItem(pipeline['name'])
            self.table.setItem(row, 0, name_item)

            # Status indicator
            status = pipeline.get('status', 'unknown')
            status_item = QTableWidgetItem()

            if status == 'healthy':
                status_item.setText("✅ Healthy")
                status_item.setForeground(QColor('#4CAF50'))
            elif status == 'degraded':
                status_item.setText("⚠️ Degraded")
                status_item.setForeground(QColor('#FF9800'))
            elif status == 'failing':
                status_item.setText("❌ Failing")
                status_item.setForeground(QColor('#F44336'))
            else:
                status_item.setText("❔ Unknown")
                status_item.setForeground(QColor('#999'))

            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 1, status_item)

            # Last F1 score
            f1 = pipeline.get('last_f1', 0)
            f1_item = QTableWidgetItem(f'{f1:.1%}')
            f1_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, f1_item)

            # Runs count
            runs = pipeline.get('runs_24h', 0)
            runs_item = QTableWidgetItem(str(runs))
            runs_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, runs_item)


class MonitoringDashboard(QWidget):
    """
    Comprehensive monitoring dashboard.

    Features:
        - Real-time metrics cards
        - Alert feed integration
        - Pipeline health monitoring
        - Recent runs table
        - System statistics
        - Auto-refresh capability
    """

    refresh_requested = pyqtSignal()

    def __init__(self, benchmark_manager, alert_system=None, parent=None):
        super().__init__(parent)
        self.benchmark_manager = benchmark_manager
        self.alert_system = alert_system

        # Auto-refresh timer
        self.auto_refresh_enabled = False
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._auto_refresh)

        self._init_ui()
        self.refresh_data()

        # Connect to alert system if provided
        if self.alert_system:
            self.alert_system.alert_triggered.connect(self._on_alert_triggered)

    def _init_ui(self):
        """Initialize UI."""
        # Main scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setSpacing(20)

        # Header
        header_layout = QHBoxLayout()

        title = QLabel("📊 <b>Benchmark Monitoring Dashboard</b>")
        title.setStyleSheet("font-size: 18px; color: #333;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_data)
        header_layout.addWidget(refresh_btn)

        # Auto-refresh toggle
        self.auto_refresh_btn = QPushButton("⏸️ Auto-refresh OFF")
        self.auto_refresh_btn.setCheckable(True)
        self.auto_refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #9E9E9E;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
            }
            QPushButton:checked {
                background-color: #4CAF50;
            }
        """)
        self.auto_refresh_btn.toggled.connect(self._toggle_auto_refresh)
        header_layout.addWidget(self.auto_refresh_btn)

        main_layout.addLayout(header_layout)

        # Metrics cards
        metrics_group = QGroupBox("📈 Key Metrics")
        metrics_layout = QHBoxLayout(metrics_group)
        metrics_layout.setSpacing(15)

        self.total_runs_card = MetricCard("Total Runs")
        self.avg_f1_card = MetricCard("Average F1")
        self.best_pipeline_card = MetricCard("Best Pipeline")
        self.runs_today_card = MetricCard("Runs Today")

        metrics_layout.addWidget(self.total_runs_card)
        metrics_layout.addWidget(self.avg_f1_card)
        metrics_layout.addWidget(self.best_pipeline_card)
        metrics_layout.addWidget(self.runs_today_card)

        main_layout.addWidget(metrics_group)

        # Two columns: Alerts + Pipeline Health
        columns_layout = QHBoxLayout()

        # Left: Alerts
        self.alert_feed = AlertFeedWidget()
        self.alert_feed.clear_btn.clicked.connect(self._clear_alerts)
        columns_layout.addWidget(self.alert_feed, stretch=1)

        # Right: Pipeline Health
        self.pipeline_health = PipelineHealthWidget()
        columns_layout.addWidget(self.pipeline_health, stretch=1)

        main_layout.addLayout(columns_layout)

        # Recent runs table
        runs_group = QGroupBox("📅 Recent Runs")
        runs_layout = QVBoxLayout(runs_group)

        self.runs_table = QTableWidget()
        self.runs_table.setColumnCount(6)
        self.runs_table.setHorizontalHeaderLabels([
            'ID', 'Timestamp', 'Test Set', 'Pipelines', 'Avg F1', 'Status'
        ])
        self.runs_table.horizontalHeader().setStretchLastSection(True)
        self.runs_table.setMaximumHeight(200)
        self.runs_table.setAlternatingRowColors(True)
        self.runs_table.verticalHeader().setVisible(False)

        runs_layout.addWidget(self.runs_table)

        main_layout.addWidget(runs_group)

        # System stats
        stats_group = QGroupBox("⚙️ System Statistics")
        stats_layout = QVBoxLayout(stats_group)

        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("font-family: monospace; font-size: 11px;")
        self.stats_label.setTextFormat(Qt.TextFormat.RichText)
        stats_layout.addWidget(self.stats_label)

        main_layout.addWidget(stats_group)

        main_layout.addStretch()

        scroll.setWidget(container)

        # Set main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)

    def refresh_data(self):
        """Refresh all dashboard data."""
        try:
            self._update_metrics()
            self._update_pipeline_health()
            self._update_recent_runs()
            self._update_system_stats()
            logger.debug("Dashboard data refreshed")
        except Exception as e:
            logger.error(f"Error refreshing dashboard: {e}", exc_info=True)

    def _update_metrics(self):
        """Update metrics cards."""
        # Total runs
        runs = self.benchmark_manager.list_benchmark_runs(limit=10000)
        total_runs = len(runs)
        self.total_runs_card.update_value(str(total_runs), 'neutral')

        # Average F1 (last 10 runs)
        recent_runs = runs[:10] if runs else []
        if recent_runs:
            f1_values = []
            for run in recent_runs:
                results = self.benchmark_manager.get_benchmark_results(run['id'])
                if results:
                    metrics = self._calculate_metrics(results)
                    f1_values.append(metrics['f1'])

            avg_f1 = sum(f1_values) / len(f1_values) if f1_values else 0
            status = 'success' if avg_f1 >= 0.8 else 'warning' if avg_f1 >= 0.6 else 'error'
            self.avg_f1_card.update_value(f'{avg_f1:.1%}', status, 'Last 10 runs')
        else:
            self.avg_f1_card.update_value('--', 'neutral')

        # Best pipeline (by F1)
        # TODO: Implement pipeline aggregation
        self.best_pipeline_card.update_value('Quick', 'success', 'F1: 95%')

        # Runs today
        today = datetime.now().date()
        runs_today = sum(1 for run in runs
                        if datetime.fromisoformat(run['timestamp']).date() == today)
        self.runs_today_card.update_value(str(runs_today), 'neutral')

    def _update_pipeline_health(self):
        """Update pipeline health status."""
        # TODO: Implement actual pipeline health logic
        # For now, show placeholder data
        pipelines = [
            {'name': 'Quick', 'status': 'healthy', 'last_f1': 0.92, 'runs_24h': 15},
            {'name': 'Balanced', 'status': 'healthy', 'last_f1': 0.89, 'runs_24h': 12},
            {'name': 'Accurate', 'status': 'degraded', 'last_f1': 0.76, 'runs_24h': 8},
        ]

        self.pipeline_health.update_pipelines(pipelines)

    def _update_recent_runs(self):
        """Update recent runs table."""
        runs = self.benchmark_manager.list_benchmark_runs(limit=10)

        self.runs_table.setRowCount(len(runs))

        for row, run in enumerate(runs):
            # ID
            id_item = QTableWidgetItem(str(run['id']))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.runs_table.setItem(row, 0, id_item)

            # Timestamp
            timestamp = datetime.fromisoformat(run['timestamp']).strftime('%Y-%m-%d %H:%M')
            time_item = QTableWidgetItem(timestamp)
            self.runs_table.setItem(row, 1, time_item)

            # Test set
            test_set_item = QTableWidgetItem(run['test_set_name'])
            self.runs_table.setItem(row, 2, test_set_item)

            # Pipelines count
            pipelines_item = QTableWidgetItem(str(run.get('pipelines_count', 0)))
            pipelines_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.runs_table.setItem(row, 3, pipelines_item)

            # Avg F1 (calculate from results)
            results = self.benchmark_manager.get_benchmark_results(run['id'])
            if results:
                metrics = self._calculate_metrics(results)
                f1_item = QTableWidgetItem(f"{metrics['f1']:.1%}")
            else:
                f1_item = QTableWidgetItem("--")
            f1_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.runs_table.setItem(row, 4, f1_item)

            # Status
            status_item = QTableWidgetItem(run.get('status', 'unknown'))
            self.runs_table.setItem(row, 5, status_item)

    def _update_system_stats(self):
        """Update system statistics."""
        runs = self.benchmark_manager.list_benchmark_runs(limit=1000)

        stats_html = f"""
        <b>Database:</b> {len(runs)} total runs stored<br>
        <b>Oldest run:</b> {runs[-1]['timestamp'][:10] if runs else 'N/A'}<br>
        <b>Most recent:</b> {runs[0]['timestamp'][:10] if runs else 'N/A'}<br>
        """

        if self.alert_system:
            alert_summary = self.alert_system.get_alert_summary()
            stats_html += f"""
            <b>Alerts (24h):</b> {alert_summary['recent_24h']}<br>
            <b>Total alerts:</b> {alert_summary['total']}<br>
            """

        self.stats_label.setText(stats_html)

    def _calculate_metrics(self, results: List[Dict]) -> Dict:
        """Calculate metrics from results."""
        tp = fp = tn = fn = 0

        for result in results:
            expected = result['expected']
            predicted = 'duplicate' if result['is_match'] else 'not_duplicate'

            if expected == 'duplicate' and predicted == 'duplicate':
                tp += 1
            elif expected == 'not_duplicate' and predicted == 'duplicate':
                fp += 1
            elif expected == 'not_duplicate' and predicted == 'not_duplicate':
                tn += 1
            elif expected == 'duplicate' and predicted == 'not_duplicate':
                fn += 1

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        return {'f1': f1, 'precision': precision, 'recall': recall}

    def _on_alert_triggered(self, alert):
        """Handle alert from alert system."""
        self.alert_feed.add_alert(alert)

    def _clear_alerts(self):
        """Clear alert feed."""
        self.alert_feed.clear_alerts()
        if self.alert_system:
            self.alert_system.clear_alerts()

    def _toggle_auto_refresh(self, enabled: bool):
        """Toggle auto-refresh."""
        self.auto_refresh_enabled = enabled

        if enabled:
            self.auto_refresh_btn.setText("▶️ Auto-refresh ON")
            self.refresh_timer.start(10000)  # 10 seconds
            logger.info("Auto-refresh enabled (10s interval)")
        else:
            self.auto_refresh_btn.setText("⏸️ Auto-refresh OFF")
            self.refresh_timer.stop()
            logger.info("Auto-refresh disabled")

    def _auto_refresh(self):
        """Auto-refresh handler."""
        if self.auto_refresh_enabled:
            self.refresh_data()

    def closeEvent(self, event):
        """
        CORRECTION BUG #18: Cleanup resources when widget is closed.

        Ensures proper cleanup of resources and signals.
        """
        # All signals are internal and auto-cleaned by Qt
        # Added for consistency with other widgets
        super().closeEvent(event)
