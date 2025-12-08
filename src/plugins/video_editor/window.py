"""Main window module for the video editor"""

import os
import subprocess  # CRITICAL FIX: Missing import for export_segments()
import cv2
import numpy as np
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                           QPushButton, QLabel, QSlider, QFileDialog, QTableWidget,
                           QProgressBar, QTableWidgetItem, QMenu, QInputDialog,
                           QMessageBox, QApplication, QGroupBox, QDialog, QTextEdit,
                           QMenuBar, QHeaderView, QComboBox, QLineEdit, QSplitter,
                           QTabWidget, QStackedWidget, QScrollArea, QFrame)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QColor, QShortcut, QKeySequence, QAction
from src.core.logger import Logger
from src.core.i18n import t
# Timeline imports - using EnhancedTimeline for all modes now
from .data_manager import DataManager
from .history_manager import HistoryManager, HistoryAction
from .widgets.preview_widget import PreviewWidget
from .widgets.segments_panel import SegmentsPanel
from .widgets.detection_panel import DetectionPanel
from .widgets.audio_panel import AudioPanel
from .widgets.dashboard import DashboardWidget
from .widgets.modern_toolbar import ModernToolbar, StatusBar
from .widgets.media_browser import MediaBrowser
from .widgets.inspector_panel import InspectorPanel
from .enhanced_timeline import EnhancedTimeline
from .segment_manager import VideoSegment, SegmentManager
from .dialogs.transition_dialog import TransitionDialog
from .dialogs.preferences_dialog import PreferencesDialog
from .dialogs.export_dialog import ExportDialog
from .transition_export import TransitionExportWorker
from .theme_manager import ThemeManager
from .utils.time_utils import TimeCode
from .services import VideoPlayerService, SegmentEditorService, ExportService
import copy

logger = Logger.get_logger('VideoEditor.Window')

class VideoEditorWindow(QMainWindow):
    """Main window for the video editor"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle(t("video_editor.window.title", "Video Editor"))
        self.setMinimumSize(1200, 800)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        # Theme Manager - Initialize and apply theme FIRST
        self.theme_manager = ThemeManager()
        self.theme_manager.apply_theme(app=QApplication.instance())

        # State variables
        self.video_path = None
        self.cap = None
        self.current_frame = 0
        self.total_frames = 0
        self.fps = 0
        self.playing = False
        self.data_manager = None
        self._updating_frame = False

        # TimeCode utility (will be updated when video is loaded)
        self.timecode = TimeCode(30.0)  # Default 30 fps

        # Segment Manager (centralized)
        self.segment_manager = SegmentManager()

        # History manager for Undo/Redo
        self.history = HistoryManager(max_history=50)

        # Services
        self.export_service = ExportService()
        self.segment_editor_service = SegmentEditorService(self.segment_manager, self.history)

        # Connect segment service signals
        self.segment_editor_service.segment_created.connect(self.on_segment_service_created)
        self.segment_editor_service.segment_deleted.connect(self.on_segment_service_deleted)
        self.segment_editor_service.segment_updated.connect(self.on_segment_service_updated)
        self.segment_editor_service.in_point_set.connect(self.on_service_in_point_set)
        self.segment_editor_service.out_point_set.connect(self.on_service_out_point_set)
        self.segment_editor_service.error_occurred.connect(self.on_segment_service_error)

        # IN/OUT points for editing (deprecated - will use service properties)
        self.in_point = None
        self.out_point = None

        # Clipboard for Copy/Paste
        self.clipboard = []

        # Timeline zoom level
        self.zoom_level = 1.0

        # Worker references (to prevent garbage collection)
        self.scene_detection_worker = None

        # Selected segment index (for Inspector Panel actions)
        self.selected_segment_index = -1

        # Multi-source video management
        self.source_videos = []  # List of {path, cap, timeline, fps, frames}
        self.active_source_index = 0  # Currently selected source

        # Panel layout preferences - no longer needed with tabs

        # Timer for playback
        self.play_timer = QTimer()
        self.play_timer.timeout.connect(self.next_frame)

        # Show dashboard on start
        self.show_dashboard_on_start = False  # Disabled - go straight to editor
        self.dashboard_widget = None
        self.editor_widget = None  # Will hold the editor UI

        # Layout mode: 'classic' or 'davinci'
        self.layout_mode = 'davinci'  # NEW DAVINCI LAYOUT BY DEFAULT

        # Create stacked widget to switch between dashboard and editor
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # Create editor UI
        self.editor_widget = QWidget()
        self.stacked_widget.addWidget(self.editor_widget)

        # Initialize UI based on mode
        if self.layout_mode == 'davinci':
            self.init_davinci_ui()
        else:
            self.init_ui()

        self.setup_shortcuts()
        self.setup_menus()

        # Show dashboard if no video loaded
        if self.show_dashboard_on_start and not self.video_path:
            self.show_dashboard()
        else:
            # Show editor by default
            self.stacked_widget.setCurrentWidget(self.editor_widget)

        logger.debug("VideoEditor Window initialized")

    def init_davinci_ui(self):
        """Initialize DaVinci-style simplified UI.

        Layout:
        - Top: Simple toolbar (fixed height)
        - Middle: Tabbed Side Panel (30%) | Preview (70%) - 65% of height
          - Tab 1: 📁 Médias (Media Browser)
          - Tab 2: ⚙️ Propriétés (Inspector Panel)
        - Bottom: Dual Timeline System - 35% of height
          - Timeline 1: 📹 Vidéo Source (read-only, for reference)
          - Timeline 2: ✂️ Timeline de Montage (for editing segments)
        """
        # Use self.editor_widget as the container with modern styling
        self.editor_widget.setStyleSheet("""
            QWidget {
                background-color: #f8f8f8;
            }
        """)
        main_layout = QVBoxLayout(self.editor_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ===== TOP TOOLBAR (Simple) =====
        toolbar = self._create_simple_toolbar()
        main_layout.addWidget(toolbar)

        # ===== MIDDLE AREA: 2-column splitter with tabs =====
        self.middle_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.middle_splitter.setChildrenCollapsible(False)
        self.middle_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #e0e0e0;
                width: 1px;
            }
            QSplitter::handle:hover {
                background-color: #0066cc;
            }
        """)

        # LEFT: Tabbed panel with Media Browser and Inspector
        self.side_tabs = QTabWidget()
        self.side_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #e0e0e0;
                background-color: #ffffff;
                border-radius: 0px;
            }
            QTabBar::tab {
                background-color: #f5f5f5;
                color: #333;
                padding: 10px 20px;
                margin-right: 2px;
                border: 1px solid #e0e0e0;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: 600;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                color: #0066cc;
                border-bottom: 2px solid #0066cc;
            }
            QTabBar::tab:hover {
                background-color: #e8f4fd;
            }
        """)

        # Media Browser tab
        self.media_browser = MediaBrowser()
        self.media_browser.import_clicked.connect(self.open_video_dialog)
        self.media_browser.file_selected.connect(self.open_video)
        self.side_tabs.addTab(self.media_browser, t("video_editor.window.tab_media", "📁 Media"))

        # Inspector Panel tab
        self.inspector_panel = InspectorPanel()
        self.inspector_panel.transition_clicked.connect(self.on_inspector_transition_clicked)
        self.inspector_panel.text_overlay_clicked.connect(self.on_inspector_text_overlay_clicked)
        self.inspector_panel.audio_clicked.connect(self.on_inspector_audio_clicked)
        self.inspector_panel.delete_clicked.connect(self.delete_selected_segments)
        self.side_tabs.addTab(self.inspector_panel, t("video_editor.window.tab_properties", "⚙️ Properties"))

        self.middle_splitter.addWidget(self.side_tabs)

        # RIGHT: Preview (now takes more space)
        self.preview_widget = PreviewWidget()
        self.preview_widget.play_clicked.connect(self.toggle_play)
        self.preview_widget.pause_clicked.connect(self.toggle_play)
        self.preview_widget.prev_frame_clicked.connect(self.prev_frame)
        self.preview_widget.next_frame_clicked.connect(self.next_frame)
        self.middle_splitter.addWidget(self.preview_widget)

        # Keep compatibility references
        self.preview = self.preview_widget.preview_label
        self.time_label = self.preview_widget.timecode_label

        # Set proportions: 30% tabs | 70% preview
        self.middle_splitter.setStretchFactor(0, 30)
        self.middle_splitter.setStretchFactor(1, 70)

        main_layout.addWidget(self.middle_splitter, stretch=65)  # 65% of height

        # ===== HIDDEN SEGMENTS TABLE (for compatibility) =====
        # Many methods depend on segments_table, so we create it but hide it
        self.segments_table = QTableWidget()
        self.segments_table.setColumnCount(6)
        self.segments_table.setHorizontalHeaderLabels([
            t("video_editor.window.table_start", "Start"),
            t("video_editor.window.table_end", "End"),
            t("video_editor.window.table_duration", "Duration"),
            t("video_editor.window.table_name", "Name"),
            t("video_editor.window.table_transition", "Transition"),
            t("video_editor.window.table_text", "Text")
        ])
        self.segments_table.setVisible(False)  # Hidden in DaVinci mode

        # ===== BOTTOM: Dual Timeline System (35% of height) =====
        timeline_container = QWidget()
        timeline_container.setStyleSheet("QWidget { background-color: #f8f8f8; }")
        timeline_layout = QVBoxLayout(timeline_container)
        timeline_layout.setContentsMargins(0, 0, 0, 0)
        timeline_layout.setSpacing(2)

        # Source Timelines Header with Add button
        source_header_widget = QWidget()
        source_header_widget.setStyleSheet("QWidget { background-color: #ffffff; border-bottom: 1px solid #e0e0e0; }")
        source_header_layout = QHBoxLayout(source_header_widget)
        source_header_layout.setContentsMargins(10, 5, 10, 5)
        source_header_layout.setSpacing(10)

        source_title = QLabel(t("video_editor.window.source_videos_title", "📹 Source Videos"))
        source_title.setStyleSheet("QLabel { font-size: 12px; font-weight: bold; color: #333; border: none; }")
        source_header_layout.addWidget(source_title)

        source_header_layout.addStretch()

        add_source_btn = QPushButton(t("video_editor.window.add_source_btn", "+ Add Source"))
        add_source_btn.setStyleSheet("""
            QPushButton {
                background-color: #0066cc;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0052a3;
            }
        """)
        add_source_btn.setMaximumHeight(25)
        add_source_btn.clicked.connect(self.add_source_video)
        source_header_layout.addWidget(add_source_btn)

        timeline_layout.addWidget(source_header_widget)

        # Scrollable area for source timelines
        sources_scroll = QScrollArea()
        sources_scroll.setWidgetResizable(True)
        sources_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sources_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        sources_scroll.setFrameShape(QFrame.Shape.NoFrame)
        sources_scroll.setStyleSheet("QScrollArea { background-color: #f8f8f8; border: none; }")
        sources_scroll.setMaximumHeight(150)  # Max height for sources area

        # Container for source timelines
        self.sources_container = QWidget()
        self.sources_layout = QVBoxLayout(self.sources_container)
        self.sources_layout.setContentsMargins(0, 0, 0, 0)
        self.sources_layout.setSpacing(5)
        self.sources_layout.addStretch()  # Push timelines to top

        sources_scroll.setWidget(self.sources_container)
        timeline_layout.addWidget(sources_scroll)

        # Editing Timeline (for segments)
        edit_header = QLabel(t("video_editor.window.editing_timeline_title", "✂️ Editing Timeline"))
        edit_header.setStyleSheet("""
            QLabel {
                background-color: #ffffff;
                color: #333;
                font-size: 12px;
                font-weight: bold;
                padding: 5px 10px;
                border-bottom: 1px solid #e0e0e0;
            }
        """)
        edit_header.setMaximumHeight(30)
        timeline_layout.addWidget(edit_header)

        self.timeline = EnhancedTimeline(segment_manager=self.segment_manager)  # Main editing timeline
        self.timeline.setMaximumHeight(150)  # Slightly taller for editing
        self.timeline.position_changed.connect(self.on_timeline_position_changed)
        self.timeline.segment_created.connect(self.on_segment_created)
        self.timeline.segment_deleted.connect(self.on_segment_deleted)
        self.timeline.segment_selected.connect(self.on_segment_selected)
        timeline_layout.addWidget(self.timeline)

        main_layout.addWidget(timeline_container, stretch=35)  # 35% of height

        # ===== STATUS BAR =====
        self.statusBar().showMessage(t("video_editor.window.status_davinci", "✅ Video Editor Pro - DaVinci Layout"))

        logger.info("DaVinci interface initialized")

    def _create_simple_toolbar(self) -> QWidget:
        """Create modern, professional toolbar with light theme.

        Returns:
            Toolbar widget
        """
        toolbar_widget = QWidget()
        toolbar_widget.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border-bottom: 1px solid #e0e0e0;
            }
        """)
        toolbar_widget.setMaximumHeight(65)
        toolbar_widget.setMinimumHeight(65)

        toolbar = QHBoxLayout(toolbar_widget)
        toolbar.setContentsMargins(15, 8, 15, 8)
        toolbar.setSpacing(15)

        # Logo/Title with modern styling
        title = QLabel("🎬 VideoFlow Editor")
        title.setStyleSheet("""
            QLabel {
                color: #1a1a1a;
                font-size: 18px;
                font-weight: 700;
                letter-spacing: -0.5px;
                padding: 0px;
                border: none;
            }
        """)
        toolbar.addWidget(title)

        toolbar.addStretch()

        # File group
        file_group = QWidget()
        file_layout = QHBoxLayout(file_group)
        file_layout.setContentsMargins(0, 0, 0, 0)
        file_layout.setSpacing(5)

        self.open_btn = QPushButton(t("video_editor.window.open_btn", "📁 Open"))
        self.open_btn.setMinimumHeight(35)
        self.open_btn.setStyleSheet(self._get_button_style('#0078d4', '#005a9e'))
        self.open_btn.setToolTip(t("video_editor.window.tooltip_open", "Open a video (Ctrl+O)"))
        self.open_btn.clicked.connect(self.open_video_dialog)
        file_layout.addWidget(self.open_btn)

        save_btn = QPushButton(t("video_editor.window.save_btn", "💾 Save"))
        save_btn.setMinimumHeight(35)
        save_btn.setStyleSheet(self._get_button_style('#2a2a2a', '#353535'))
        save_btn.setToolTip(t("video_editor.window.tooltip_save", "Save project (Ctrl+S)"))
        file_layout.addWidget(save_btn)

        toolbar.addWidget(file_group)

        # Edit group with modern icon buttons
        edit_group = QWidget()
        edit_group.setStyleSheet("QWidget { background: transparent; border: none; }")
        edit_layout = QHBoxLayout(edit_group)
        edit_layout.setContentsMargins(0, 0, 0, 0)
        edit_layout.setSpacing(4)

        undo_btn = QPushButton("↶")
        undo_btn.setStyleSheet(self._get_icon_button_style())
        undo_btn.setToolTip(t("video_editor.window.tooltip_undo", "Undo (Ctrl+Z)"))
        undo_btn.clicked.connect(self.undo)
        edit_layout.addWidget(undo_btn)

        redo_btn = QPushButton("↷")
        redo_btn.setStyleSheet(self._get_icon_button_style())
        redo_btn.setToolTip(t("video_editor.window.tooltip_redo", "Redo (Ctrl+Y)"))
        redo_btn.clicked.connect(self.redo)
        edit_layout.addWidget(redo_btn)

        toolbar.addWidget(edit_group)

        # Marking group
        mark_group = QWidget()
        mark_layout = QHBoxLayout(mark_group)
        mark_layout.setContentsMargins(0, 0, 0, 0)
        mark_layout.setSpacing(5)

        self.start_cut_btn = QPushButton(t("video_editor.window.start_point_btn", "📍 Start Point"))
        self.start_cut_btn.setMinimumHeight(35)
        self.start_cut_btn.setStyleSheet(self._get_button_style('#28a745', '#218838'))
        self.start_cut_btn.setToolTip(t("video_editor.window.tooltip_mark_in", "Mark segment start point (I key)"))
        self.start_cut_btn.clicked.connect(self.mark_in)
        self.start_cut_btn.setEnabled(False)
        mark_layout.addWidget(self.start_cut_btn)

        self.end_cut_btn = QPushButton(t("video_editor.window.end_point_btn", "🏁 End Point"))
        self.end_cut_btn.setMinimumHeight(35)
        self.end_cut_btn.setStyleSheet(self._get_button_style('#dc3545', '#c82333'))
        self.end_cut_btn.setToolTip(t("video_editor.window.tooltip_mark_out", "Mark segment end point (O key)"))
        self.end_cut_btn.clicked.connect(self.mark_out)
        self.end_cut_btn.setEnabled(False)
        mark_layout.addWidget(self.end_cut_btn)

        self.create_segment_btn = QPushButton(t("video_editor.window.create_segment_btn", "✂️ Create Segment"))
        self.create_segment_btn.setMinimumHeight(35)
        self.create_segment_btn.setStyleSheet(self._get_button_style('#6c63ff', '#5a52d5'))
        self.create_segment_btn.setToolTip(t("video_editor.window.tooltip_create_segment", "Create segment between start and end points (C key)"))
        self.create_segment_btn.clicked.connect(self.create_segment_from_io)
        self.create_segment_btn.setEnabled(False)
        mark_layout.addWidget(self.create_segment_btn)

        toolbar.addWidget(mark_group)

        toolbar.addStretch()

        # Export group with modern styling
        export_group = QWidget()
        export_group.setStyleSheet("QWidget { background: transparent; border: none; }")
        export_layout = QHBoxLayout(export_group)
        export_layout.setContentsMargins(0, 0, 0, 0)
        export_layout.setSpacing(8)

        self.export_btn = QPushButton(t("video_editor.window.export_btn", "💾 Export"))
        self.export_btn.setStyleSheet(self._get_button_style('#ffc107', '#e0a800', text_color='#000'))
        self.export_btn.setToolTip(t("video_editor.window.tooltip_export", "Export segments (Ctrl+E)"))
        self.export_btn.clicked.connect(self.export_segments)
        self.export_btn.setEnabled(False)
        export_layout.addWidget(self.export_btn)

        # Separator
        separator = QLabel("|")
        separator.setStyleSheet("color: #ddd; padding: 0 4px; border: none;")
        export_layout.addWidget(separator)

        prefs_btn = QPushButton("⚙")
        prefs_btn.setStyleSheet(self._get_icon_button_style())
        prefs_btn.setToolTip(t("video_editor.window.tooltip_preferences", "Preferences (Ctrl+,)"))
        prefs_btn.clicked.connect(self.open_preferences)
        export_layout.addWidget(prefs_btn)

        help_btn = QPushButton("❓")
        help_btn.setStyleSheet(self._get_icon_button_style())
        help_btn.setToolTip(t("video_editor.window.tooltip_help", "Help (F1)"))
        help_btn.clicked.connect(self.show_shortcuts_help)
        export_layout.addWidget(help_btn)

        toolbar.addWidget(export_group)

        return toolbar_widget

    def _get_button_style(self, bg_color: str, hover_color: str, text_color: str = '#fff') -> str:
        """Get modern button stylesheet with light theme.

        Args:
            bg_color: Background color
            hover_color: Hover background color
            text_color: Text color

        Returns:
            Stylesheet string
        """
        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                border: 1px solid {bg_color};
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: 600;
                font-size: 13px;
                min-height: 36px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
                border-color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {bg_color};
            }}
            QPushButton:disabled {{
                background-color: #f5f5f5;
                color: #bbb;
                border-color: #e0e0e0;
            }}
            QPushButton:checked {{
                background-color: {hover_color};
                border-color: {bg_color};
            }}
        """

    def _get_icon_button_style(self) -> str:
        """Get style for icon-only buttons in toolbar.

        Returns:
            Icon button stylesheet
        """
        return """
            QPushButton {
                background-color: transparent;
                color: #444;
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 6px;
                font-size: 16px;
                min-width: 38px;
                min-height: 38px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border-color: #e0e0e0;
            }
            QPushButton:pressed {
                background-color: #e5e5e5;
            }
            QPushButton:checked {
                background-color: #e8f4fd;
                border-color: #0066cc;
                color: #0066cc;
            }
            QPushButton:disabled {
                color: #ccc;
            }
        """

    def on_segment_selected(self, index: int):
        """Handle segment selection from timeline.

        Args:
            index: Selected segment index
        """
        # Store selected segment index for Inspector Panel actions
        self.selected_segment_index = index

        if 0 <= index < len(self.timeline.segments):
            segment = self.timeline.segments[index]

            # Update Inspector Panel in DaVinci mode
            if self.layout_mode == 'davinci' and hasattr(self, 'inspector_panel'):
                self.inspector_panel.set_segment(segment)

            logger.debug(f"Segment {index} selected")

    def on_inspector_transition_clicked(self):
        """Handle transition button click from Inspector Panel.

        Wrapper method that calls the existing on_transition_clicked with the selected segment index.
        """
        if self.selected_segment_index >= 0:
            self.on_transition_clicked(self.selected_segment_index)
        else:
            QMessageBox.warning(
                self,
                t("video_editor.window.dialog_no_segment", "No Segment"),
                t("video_editor.window.msg_select_segment", "Please select a segment in the timeline.")
            )

    def on_inspector_text_overlay_clicked(self):
        """Handle text overlay button click from Inspector Panel.

        Wrapper method that calls the existing on_text_overlay_clicked with the selected segment index.
        """
        if self.selected_segment_index >= 0:
            self.on_text_overlay_clicked(self.selected_segment_index)
        else:
            QMessageBox.warning(
                self,
                t("video_editor.window.dialog_no_segment", "No Segment"),
                t("video_editor.window.msg_select_segment", "Please select a segment in the timeline.")
            )

    def on_inspector_audio_clicked(self):
        """Handle audio button click from Inspector Panel.

        Opens audio panel or settings for the selected segment.
        """
        if self.selected_segment_index >= 0:
            # For now, show a message. Could open AudioPanel dialog in future
            QMessageBox.information(
                self,
                t("video_editor.window.dialog_audio_settings", "Audio Settings"),
                t("video_editor.window.msg_audio_future", "Audio settings for segment {index}.\n\nThis feature will be available in a future update.", index=self.selected_segment_index + 1)
            )
        else:
            QMessageBox.warning(
                self,
                t("video_editor.window.dialog_no_segment", "No Segment"),
                t("video_editor.window.msg_select_segment", "Please select a segment in the timeline.")
            )

    def init_ui(self):
        """Initialize user interface - Pro version with improved layout"""
        # Use self.editor_widget as the container
        main_layout = QVBoxLayout(self.editor_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # ===== TOP TOOLBAR =====
        toolbar = QHBoxLayout()
        toolbar.setSpacing(5)

        # File operations
        self.open_btn = QPushButton("📁 Ouvrir Vidéo")
        self.open_btn.setToolTip("Ouvrir une vidéo pour édition (Ctrl+O)")
        self.open_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 15px;
                font-weight: bold;
                background-color: #007bff;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        self.open_btn.clicked.connect(self.open_video_dialog)
        toolbar.addWidget(self.open_btn)

        toolbar.addWidget(QLabel("  "))  # Spacing

        # IN/OUT/Create controls
        in_out_widget = QWidget()
        in_out_layout = QHBoxLayout(in_out_widget)
        in_out_layout.setContentsMargins(0, 0, 0, 0)
        in_out_layout.setSpacing(3)

        self.start_cut_btn = QPushButton("⬇️ Début")
        self.start_cut_btn.setToolTip("Marquer point de DÉBUT (Touche I)")
        self.start_cut_btn.clicked.connect(self.mark_in)
        self.start_cut_btn.setEnabled(False)
        self.start_cut_btn.setStyleSheet("QPushButton { padding: 5px 10px; }")
        in_out_layout.addWidget(self.start_cut_btn)

        self.end_cut_btn = QPushButton("⬆️ Fin")
        self.end_cut_btn.setToolTip("Marquer point de FIN (Touche O)")
        self.end_cut_btn.clicked.connect(self.mark_out)
        self.end_cut_btn.setEnabled(False)
        self.end_cut_btn.setStyleSheet("QPushButton { padding: 5px 10px; }")
        in_out_layout.addWidget(self.end_cut_btn)

        create_segment_btn = QPushButton("✂️ Créer")
        create_segment_btn.setToolTip("Créer un segment entre Début et Fin (Touche C)")
        create_segment_btn.clicked.connect(self.create_segment_from_io)
        create_segment_btn.setEnabled(False)
        create_segment_btn.setStyleSheet("""
            QPushButton {
                padding: 5px 10px;
                background-color: #28a745;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        in_out_layout.addWidget(create_segment_btn)
        self.create_segment_btn = create_segment_btn

        toolbar.addWidget(in_out_widget)

        toolbar.addStretch()

        # Export
        self.export_btn = QPushButton("💾 Exporter Segments")
        self.export_btn.setToolTip("Exporter tous les segments créés (Ctrl+E)")
        self.export_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 15px;
                font-weight: bold;
                background-color: #ffc107;
                color: #000;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #e0a800;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.export_btn.clicked.connect(self.export_segments)
        self.export_btn.setEnabled(False)
        toolbar.addWidget(self.export_btn)

        toolbar.addWidget(QLabel("  "))  # Spacing

        # Help
        help_btn = QPushButton("❓ Aide")
        help_btn.setToolTip("Afficher tous les raccourcis clavier (F1)")
        help_btn.setStyleSheet("QPushButton { padding: 5px 10px; }")
        help_btn.clicked.connect(self.show_shortcuts_help)
        toolbar.addWidget(help_btn)

        main_layout.addLayout(toolbar)

        # ===== MAIN CONTENT AREA with Splitter =====
        content_splitter = QSplitter(Qt.Orientation.Horizontal)

        # LEFT: Preview Widget (NEW)
        self.preview_widget = PreviewWidget()
        self.preview_widget.play_clicked.connect(self.toggle_play)
        self.preview_widget.pause_clicked.connect(self.toggle_play)
        self.preview_widget.prev_frame_clicked.connect(self.prev_frame)
        self.preview_widget.next_frame_clicked.connect(self.next_frame)
        content_splitter.addWidget(self.preview_widget)

        # Keep reference to old preview label for compatibility
        self.preview = self.preview_widget.preview_label
        self.time_label = self.preview_widget.timecode_label

        # RIGHT: Tabs Panel (NEW)
        self.tabs_widget = QTabWidget()

        # Tab 1: Segments Panel (NEW)
        self.segments_panel = SegmentsPanel()
        self.segments_panel.add_segment_clicked.connect(self.mark_in)  # Start segment creation
        self.segments_panel.delete_segments_clicked.connect(self.delete_selected_segments)
        self.segments_panel.cut_at_cursor_clicked.connect(self.split_at_cursor)
        self.segments_panel.merge_segments_clicked.connect(self.merge_segments)
        self.segments_panel.copy_segments_clicked.connect(self.copy_segments)
        self.segments_panel.paste_segments_clicked.connect(self.paste_segments)
        self.segments_panel.transition_clicked.connect(self.on_transition_clicked)
        self.segments_panel.text_overlay_clicked.connect(self.on_text_overlay_clicked)
        self.tabs_widget.addTab(self.segments_panel, "📋 Segments")

        # Keep reference to old table for compatibility
        self.segments_table = self.segments_panel.segments_table

        # Tab 2: Detection Panel (NEW)
        self.detection_panel = DetectionPanel()
        self.detection_panel.detect_black_frames_clicked.connect(self.detect_black_frames_from_panel)
        self.detection_panel.detect_scenes_clicked.connect(self.detect_scenes_from_panel)
        self.detection_panel.stop_scene_detection_clicked.connect(self.stop_scene_detection)
        self.detection_panel.split_n_parts_clicked.connect(self.split_into_n_parts)
        self.detection_panel.split_by_duration_clicked.connect(self.split_by_duration)
        self.detection_panel.merge_all_clicked.connect(self.merge_all_segments)
        self.tabs_widget.addTab(self.detection_panel, "🔍 Détection")

        # Tab 3: Audio Panel (NEW)
        self.audio_panel = AudioPanel()
        self.audio_panel.extract_full_audio_clicked.connect(self.extract_full_audio)
        self.audio_panel.extract_segment_audio_clicked.connect(self.extract_segment_audio)
        self.audio_panel.extract_all_segments_audio_clicked.connect(self.extract_all_segments_audio)
        self.tabs_widget.addTab(self.audio_panel, "🎵 Audio")

        # Tab 4: Info Panel (Simple for now)
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.addWidget(QLabel("📹 Informations Vidéo"))
        self.info_label = QLabel("Aucune vidéo chargée")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("padding: 10px;")
        info_layout.addWidget(self.info_label)
        info_layout.addStretch()
        self.tabs_widget.addTab(info_widget, "ℹ️ Info")

        content_splitter.addWidget(self.tabs_widget)

        # Set splitter proportions (60% preview, 40% panels)
        content_splitter.setStretchFactor(0, 60)
        content_splitter.setStretchFactor(1, 40)

        main_layout.addWidget(content_splitter, stretch=1)

        # ===== TIMELINE (Bottom) =====
        # Using EnhancedTimeline for both modes now (unified)
        self.timeline = EnhancedTimeline(segment_manager=self.segment_manager)
        self.timeline.position_changed.connect(self.on_timeline_position_changed)
        self.timeline.segment_created.connect(self.on_segment_created)
        self.timeline.segment_deleted.connect(self.on_segment_deleted)
        if hasattr(self.timeline, 'segment_selected'):
            self.timeline.segment_selected.connect(self.on_segment_selected)
        main_layout.addWidget(self.timeline)

        # ===== STATUS BAR =====
        self.statusBar().showMessage("✅ Video Editor Pro chargé - Appuyez sur F1 pour aide")

        logger.info("VideoEditor Pro interface initialized with new layout")
    
    def show_dashboard(self):
        """Show the welcome dashboard."""
        if self.dashboard_widget is None:
            # Create dashboard
            self.dashboard_widget = DashboardWidget(self)
            self.dashboard_widget.open_video_clicked.connect(self.open_video_dialog)
            self.dashboard_widget.new_project_clicked.connect(self.open_video_dialog)
            self.dashboard_widget.open_project_clicked.connect(self.open_video)

            # Add to stacked widget
            self.stacked_widget.addWidget(self.dashboard_widget)

        # Switch to dashboard
        self.stacked_widget.setCurrentWidget(self.dashboard_widget)

        # Update window title
        self.setWindowTitle("Video Editor Pro")

        logger.debug("Dashboard shown")

    def hide_dashboard(self):
        """Hide the dashboard and show editor."""
        # Switch to editor widget
        self.stacked_widget.setCurrentWidget(self.editor_widget)
        logger.debug("Dashboard hidden, editor restored")

    def open_video_dialog(self):
        """Open a dialog to select a video"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open une vidéo",
            "",
            "Vidéos (*.mp4 *.avi *.mkv *.mov);;Tous les files (*.*)"
        )

        if file_path:
            self.open_video(file_path)
    
    def open_video(self, file_path):
        """Open a video"""
        # Hide dashboard if showing
        self.hide_dashboard()

        # Release old video capture if exists
        if self.cap is not None:
            self.cap.release()
            self.cap = None

        try:
            self.video_path = file_path
            self.cap = cv2.VideoCapture(file_path)

            if not self.cap.isOpened():
                raise Exception("Could not open video file")

            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

            # Update timecode utility with actual FPS
            self.timecode = TimeCode(self.fps)

            # Update segment editor service with total frames
            self.segment_editor_service.set_total_frames(self.total_frames)

            # Update inspector panel with FPS
            if hasattr(self, 'inspector_panel'):
                self.inspector_panel.set_fps(self.fps)

            # Add as first source if no sources exist
            if len(self.source_videos) == 0:
                self._add_source_to_list(file_path, self.cap, self.fps, self.total_frames)

            # Configure main editing timeline
            self.timeline.set_total_frames(self.total_frames)

            # Load les données existantes
            self.data_manager = DataManager(file_path)
            self.load_segments()

            # Activer les contrôles
            if hasattr(self, 'play_btn'):
                self.play_btn.setEnabled(True)
            self.start_cut_btn.setEnabled(True)
            self.end_cut_btn.setEnabled(True)
            self.create_segment_btn.setEnabled(True)
            if hasattr(self, 'prev_frame_btn'):
                self.prev_frame_btn.setEnabled(True)
            if hasattr(self, 'next_frame_btn'):
                self.next_frame_btn.setEnabled(True)

            # Activer les nouveaux widgets
            self.preview_widget.set_enabled_state(True)

            # Update Media Browser recent files in DaVinci mode
            if self.layout_mode == 'davinci' and hasattr(self, 'media_browser'):
                self.media_browser.add_recent_file(file_path)

            # Only enable these panels if they exist (classic mode)
            if hasattr(self, 'detection_panel'):
                self.detection_panel.set_enabled_state(True)

            if hasattr(self, 'audio_panel'):
                self.audio_panel.set_enabled_state(True)
                # Update audio panel mode availability
                self.audio_panel.update_mode_availability(
                    has_segments=len(self.timeline.segments) > 0,
                    has_selection=False
                )

            # Update info panel (only in classic mode)
            video_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration_sec = self.total_frames / self.fps if self.fps > 0 else 0
            duration_str = self.timecode.seconds_to_timecode(duration_sec)

            if hasattr(self, 'info_label'):
                info_text = f"""
                <b>📹 Fichier</b><br>
                Nom: {video_name}<br>
                Chemin: {file_path}<br>
                Taille: {file_size:.1f} MB<br>
                <br>
                <b>🎞️ Format</b><br>
                Résolution: {width}x{height}<br>
                FPS: {self.fps:.2f}<br>
                Durée: {duration_str}<br>
                Frames totales: {self.total_frames}<br>
                <br>
                <b>📊 Statistiques</b><br>
                Segments: 0<br>
                """

                self.info_label.setText(info_text)

            # Update window title
            self.setWindowTitle(f"Video Editor Pro - {video_name}")

            # Show la première frame
            self.show_frame(0)

            logger.info(f"Video opened: {video_name} ({width}x{height}, {self.fps:.2f} fps)")

        except Exception as e:
            logger.error(f"Error opening video : {str(e)}")
            self.video_path = None
            # Release the failed capture
            if self.cap is not None:
                self.cap.release()
            self.cap = None

    def add_source_video(self):
        """Add an additional source video."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Ajouter une vidéo source",
            "",
            "Vidéos (*.mp4 *.avi *.mkv *.mov);;Tous les fichiers (*.*)"
        )

        if file_path:
            try:
                # Open video
                cap = cv2.VideoCapture(file_path)
                if not cap.isOpened():
                    QMessageBox.warning(self, "Erreur", "Impossible d'ouvrir la vidéo source")
                    return

                fps = cap.get(cv2.CAP_PROP_FPS)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

                # Add to sources list
                self._add_source_to_list(file_path, cap, fps, total_frames)

                logger.info(f"Video source added: {os.path.basename(file_path)}")
                self.statusBar().showMessage(f"✅ Source ajoutée: {os.path.basename(file_path)}", 3000)

            except Exception as e:
                logger.error(f"Error adding source video: {str(e)}")
                QMessageBox.critical(self, "Erreur", f"Erreur lors de l'ajout de la source:\n{str(e)}")

    def _add_source_to_list(self, file_path, cap, fps, total_frames):
        """Create and add a source timeline widget."""
        # Create container for this source
        source_widget = QWidget()
        source_widget.setStyleSheet("QWidget { background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 4px; }")
        source_layout = QVBoxLayout(source_widget)
        source_layout.setContentsMargins(5, 5, 5, 5)
        source_layout.setSpacing(2)

        # Header with filename and controls
        header_widget = QWidget()
        header_widget.setStyleSheet("QWidget { background-color: transparent; border: none; }")
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(5)

        filename = os.path.basename(file_path)
        name_label = QLabel(f"📹 {filename}")
        name_label.setStyleSheet("QLabel { font-size: 11px; font-weight: bold; color: #333; }")
        header_layout.addWidget(name_label)

        header_layout.addStretch()

        # Info label
        duration_sec = total_frames / fps if fps > 0 else 0
        info_label = QLabel(f"{self.timecode.seconds_to_timecode(duration_sec)} • {fps:.0f} FPS")
        info_label.setStyleSheet("QLabel { font-size: 10px; color: #666; }")
        header_layout.addWidget(info_label)

        # Remove button
        remove_btn = QPushButton("✕")
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ff4444;
                border: none;
                font-size: 14px;
                font-weight: bold;
                padding: 2px;
                max-width: 20px;
                max-height: 20px;
            }
            QPushButton:hover {
                background-color: #ffeeee;
                border-radius: 3px;
            }
        """)
        remove_btn.setToolTip("Retirer cette source")
        source_index = len(self.source_videos)
        remove_btn.clicked.connect(lambda: self._remove_source(source_index))
        header_layout.addWidget(remove_btn)

        source_layout.addWidget(header_widget)

        # Timeline
        timeline = EnhancedTimeline()
        timeline.setMaximumHeight(100)
        timeline.set_total_frames(total_frames)
        timeline.position_changed.connect(self._on_source_timeline_seek)
        timeline.setToolTip(f"Timeline source: {filename}")
        source_layout.addWidget(timeline)

        # Store source data
        source_data = {
            'path': file_path,
            'cap': cap,
            'fps': fps,
            'total_frames': total_frames,
            'timeline': timeline,
            'widget': source_widget,
            'index': len(self.source_videos)
        }

        self.source_videos.append(source_data)

        # Add widget to sources container (before the stretch)
        self.sources_layout.insertWidget(self.sources_layout.count() - 1, source_widget)

        logger.info(f"Source timeline created for: {filename}")

    def _remove_source(self, index):
        """Remove a source video."""
        if 0 <= index < len(self.source_videos):
            source = self.source_videos[index]

            # Release video capture
            if source['cap']:
                source['cap'].release()

            # Remove widget
            source['widget'].deleteLater()

            # Remove from list
            self.source_videos.pop(index)

            # Update indices of remaining sources
            for i, src in enumerate(self.source_videos):
                src['index'] = i

            logger.info(f"Source removed: {os.path.basename(source['path'])}")
            self.statusBar().showMessage("Source retirée", 2000)

    def _on_source_timeline_seek(self, frame):
        """Handle seeking from a source timeline."""
        # This could be enhanced to show the frame from the specific source
        # For now, we just update the active video if it exists
        if self.cap:
            self.show_frame(frame)

    def show_frame(self, frame_num):
        """Display a specific frame"""
        if not self.cap or self._updating_frame:
            return

        try:
            self._updating_frame = True

            # Read the frame
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = self.cap.read()
            if not ret:
                return

            # Convert to QImage for display
            height, width = frame.shape[:2]
            bytes_per_line = 3 * width
            qt_image = QImage(
                frame.data,
                width,
                height,
                bytes_per_line,
                QImage.Format.Format_BGR888
            )

            # Resize for display
            scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
                self.preview.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

            # Show the image
            self.preview.setPixmap(scaled_pixmap)

            # Update all source timelines and main timeline
            for source in self.source_videos:
                if 'timeline' in source:
                    source['timeline'].set_current_frame(frame_num)
            self.timeline.set_current_frame(frame_num)

            # Update the time
            if self.fps > 0:
                current_time = frame_num / self.fps
                total_time = self.total_frames / self.fps
                self.time_label.setText(f"{self.timecode.seconds_to_timecode(current_time)} / {self.timecode.seconds_to_timecode(total_time)}")
            else:
                self.time_label.setText("--:-- / --:--")

            self.current_frame = frame_num
            
        finally:
            self._updating_frame = False
    
    def load_segments(self):
        """Load the segments in the table"""
        if not self.data_manager:
            return
            
        segments = self.data_manager.get_segments()
        self.segments_table.setRowCount(len(segments))
        
        for i, segment in enumerate(segments):
            # Name
            self.segments_table.setItem(
                i, 0,
                QTableWidgetItem(segment['name'])
            )
            
            # Début
            self.segments_table.setItem(
                i, 1,
                QTableWidgetItem(self.timecode.seconds_to_timecode(segment['start']))
            )
            
            # Fin
            self.segments_table.setItem(
                i, 2,
                QTableWidgetItem(self.timecode.seconds_to_timecode(segment['end']))
            )
            
            # Boutons d'action
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            
            preview_btn = QPushButton("👁️")
            preview_btn.clicked.connect(lambda x, s=i: self.preview_segment(s))
            actions_layout.addWidget(preview_btn)
            
            delete_btn = QPushButton("🗑️")
            delete_btn.clicked.connect(lambda x, s=i: self.delete_segment(s))
            actions_layout.addWidget(delete_btn)
            
            self.segments_table.setCellWidget(i, 3, actions_widget)
        
        self.segments_table.resizeColumnsToContents()
    
    def preview_segment(self, segment_index):
        """Preview a segment"""
        if not self.data_manager:
            return
            
        segments = self.data_manager.get_segments()
        if 0 <= segment_index < len(segments):
            segment = segments[segment_index]
            start_frame = int(segment['start'] * self.fps)
            self.current_frame = start_frame
            self.time_slider.setValue(start_frame)
            self.show_frame(start_frame)
    
    def delete_segment(self, segment_index):
        """Removes un segment"""
        if not self.data_manager:
            return
            
        reply = QMessageBox.question(
            self,
            "Remove the segment",
            "Are you one you want remove ce segment ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.data_manager.remove_segment(segment_index)
            self.load_segments()
            logger.debug(f"Segment {segment_index} removed")
    
    def save_video(self):
        """Save the edited video"""
        if not self.data_manager or not self.video_path:
            return
            
        segments = self.data_manager.get_segments()
        if not segments:
            QMessageBox.warning(
                self,
                "Error",
                "Aucun segment à save"
            )
            return
            
        output_file, _ = QFileDialog.getSaveFileName(
            self,
            "Save the video",
            "",
            "Vidéo MP4 (*.mp4)"
        )
        
        if output_file:
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, len(segments))
            self.progress_bar.setValue(0)
            
            try:
                # Créer un folder temporaire pour the segments
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Extraire chaque segment
                    segment_files = []
                    video = VideoFileClip(self.video_path)
                    
                    for i, segment in enumerate(segments):
                        start_time = segment['start']
                        end_time = segment['end']
                        
                        # Extraire the segment
                        segment_clip = video.subclip(start_time, end_time)
                        segment_file = os.path.join(temp_dir, f"segment_{i}.mp4")
                        segment_clip.write_videofile(
                            segment_file,
                            codec='libx264',
                            audio_codec='aac'
                        )
                        segment_files.append(segment_file)
                        
                        self.progress_bar.setValue(i + 1)
                    
                    # Concaténer tous the segments
                    final_clip = VideoFileClip(segment_files[0])
                    clips = [VideoFileClip(f) for f in segment_files[1:]]
                    final_clip = final_clip.concatenate_videoclips(clips)
                    
                    # Save the video finale
                    final_clip.write_videofile(
                        output_file,
                        codec='libx264',
                        audio_codec='aac'
                    )
                    
                    # Close tous les clips
                    final_clip.close()
                    for clip in clips:
                        clip.close()
                    video.close()
                
                QMessageBox.information(
                    self,
                    "Success",
                    "Vidéo sauvegardée with success !"
                )
                logger.debug(f"Video saved: {output_file}")
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Error saving : {str(e)}"
                )
                logger.error(f"Error saving : {str(e)}")
            
            finally:
                self.progress_bar.setVisible(False)
    
    def toggle_play(self):
        """Start or stop playback"""
        if self.playing:
            self.play_timer.stop()
            if hasattr(self, 'play_btn'):
                self.play_btn.setText("▶️ Lecture")
            self.preview_widget.set_playing(False)
        else:
            self.play_timer.start(int(1000 / self.fps))
            if hasattr(self, 'play_btn'):
                self.play_btn.setText("⏸️ Pause")
            self.preview_widget.set_playing(True)
        self.playing = not self.playing
    
    def next_frame(self):
        """Go to the next frame"""
        if self.cap is None:
            return
        
        current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if current_frame < total_frames - 1:
            self.show_frame(current_frame + 1)
        else:
            self.play_timer.stop()
            self.playing = False
            self.play_btn.setText("▶️ Lecture")
    
    def prev_frame(self):
        """Go back to the previous frame"""
        if self.cap is None:
            return
        
        current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        if current_frame > 0:
            self.show_frame(current_frame - 1)
    
    def on_timeline_position_changed(self, frame):
        """Called when the position in the timeline changes"""
        self.show_frame(frame)
    
    def start_cut(self):
        """Start a cut"""
        if not self.cap:
            return
        
        current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        self.timeline.start_segment(current_frame)
        
        # Add une ligne in le tableau
        row = self.segments_table.rowCount()
        self.segments_table.insertRow(row)
        
        # Calculatesr le timestamp
        start_time = current_frame / self.fps
        
        # Add les information
        status_item = QTableWidgetItem("🔴 In progress")
        status_item.setBackground(QColor("#ffebee"))  # Red très clair
        self.segments_table.setItem(row, 0, status_item)
        self.segments_table.setItem(row, 1, QTableWidgetItem(self.timecode.seconds_to_timecode(start_time)))
        self.segments_table.setItem(row, 2, QTableWidgetItem("--:--"))
        
        # Désactiver les boutons pendant la découpe
        self.start_cut_btn.setEnabled(False)
        self.end_cut_btn.setEnabled(True)
        self.cancel_cut_btn.setEnabled(True)
        self.export_btn.setEnabled(False)

    def end_cut(self):
        """Finish a cut"""
        if not self.cap:
            return
        
        current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        segment = self.timeline.end_segment(current_frame)
        
        if segment:
            row = self.segments_table.rowCount() - 1
            
            # Calculatesr les timestamps
            start_time = segment.start_frame / self.fps
            end_time = segment.end_frame / self.fps
            duration = end_time - start_time
            
            # Mettre à jour les information
            status_item = QTableWidgetItem("✅ Completed")
            status_item.setBackground(QColor("#e8f5e9"))  # Green très clair
            self.segments_table.setItem(row, 0, status_item)
            self.segments_table.setItem(row, 2, QTableWidgetItem(self.timecode.seconds_to_timecode(end_time)))
            
            # Add le bouton de suppression
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            
            delete_btn = QPushButton("🗑️")
            delete_btn.setToolTip("Remove the segment")
            delete_btn.clicked.connect(lambda: self.delete_segment(row))
            actions_layout.addWidget(delete_btn)
            
            self.segments_table.setCellWidget(row, 3, actions_widget)
            
            # Réactiver les boutons
            self.start_cut_btn.setEnabled(True)
            self.end_cut_btn.setEnabled(False)
            self.cancel_cut_btn.setEnabled(False)
            self.export_btn.setEnabled(True)
    
    def cancel_cut(self):
        """Cancel the cut in progress"""
        self.timeline.cancel_current_segment()
        
        # Remove la dernière ligne du tableau
        row = self.segments_table.rowCount() - 1
        if row >= 0:
            self.segments_table.removeRow(row)
        
        # Réactiver les boutons
        self.start_cut_btn.setEnabled(True)
        self.end_cut_btn.setEnabled(False)
        self.cancel_cut_btn.setEnabled(False)
        self.export_btn.setEnabled(self.segments_table.rowCount() > 0)
    
    def export_segments(self):
        """Export the segments as separate video files using ffmpeg"""
        if not self.video_path or self.segments_table.rowCount() == 0:
            return

        # Show export dialog with templates
        dialog = ExportDialog(self, self.video_path, self.timeline.get_segments(), self.fps)
        dialog.exec()

    def delete_segment(self, row):
        """Removes un segment"""
        self.segments_table.removeRow(row)
        self.timeline.segment_manager.remove_segment(row)
        
        # Désactiver le bouton d'export s'il n'y a plus de segments
        if self.segments_table.rowCount() == 0:
            self.export_btn.setEnabled(False)

    # ===== Segment Service Signal Handlers =====

    def on_segment_service_created(self, segment):
        """Handle segment created by service."""
        # Add to table
        self.add_segment_to_table(segment)
        # Update UI
        self.export_btn.setEnabled(True)
        self.statusBar().showMessage("Segment créé", 2000)
        # Refresh timeline
        self.timeline.update()
        logger.info(f"Segment created via service: {segment.start_frame} to {segment.end_frame}")

    def on_segment_service_deleted(self, index):
        """Handle segment deleted by service."""
        # Refresh table
        self.refresh_segments_table()
        self.statusBar().showMessage("Segment supprimé", 2000)
        logger.info(f"Segment deleted via service at index {index}")

    def on_segment_service_updated(self, index, segment):
        """Handle segment updated by service."""
        # Refresh table
        self.refresh_segments_table()
        self.statusBar().showMessage("Segment mis à jour", 2000)
        logger.info(f"Segment updated via service at index {index}")

    def on_service_in_point_set(self, frame):
        """Handle IN point set by service."""
        self.in_point = frame
        self.timeline.set_in_point(frame)
        self.statusBar().showMessage(
            f"IN marqué: {self.timecode.seconds_to_timecode(frame / self.fps)}",
            2000
        )

    def on_service_out_point_set(self, frame):
        """Handle OUT point set by service."""
        self.out_point = frame
        self.timeline.set_out_point(frame)
        self.statusBar().showMessage(
            f"OUT marqué: {self.timecode.seconds_to_timecode(frame / self.fps)}",
            2000
        )

    def on_segment_service_error(self, error_message):
        """Handle error from segment service."""
        QMessageBox.warning(self, "Erreur", error_message)
        logger.warning(f"Segment service error: {error_message}")

    # ===== Close Event =====

    def closeEvent(self, event):
        """Called when the window is closed"""
        # Stop playback timer
        if hasattr(self, 'play_timer') and self.play_timer is not None:
            self.play_timer.stop()

        # Stop any active worker threads
        if hasattr(self, 'current_batch_worker') and self.current_batch_worker is not None:
            try:
                if hasattr(self.current_batch_worker, 'stop'):
                    self.current_batch_worker.stop()
                if hasattr(self.current_batch_worker, 'wait'):
                    self.current_batch_worker.wait(1000)  # Wait max 1 second
            except Exception as e:
                logger.warning(f"Could not stop worker thread: {str(e)}")

        # Release main video capture
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception as e:
                logger.warning(f"Could not release main video capture: {str(e)}")
            self.cap = None

        # Release all source video captures
        if hasattr(self, 'source_videos'):
            for source in self.source_videos:
                if 'cap' in source and source['cap'] is not None:
                    try:
                        source['cap'].release()
                    except Exception as e:
                        logger.warning(f"Could not release source video capture: {str(e)}")
            self.source_videos.clear()

        # Save any pending data
        if hasattr(self, 'data_manager') and self.data_manager is not None:
            try:
                self.data_manager.save_data()
            except Exception as e:
                logger.warning(f"Could not save data: {str(e)}")

        logger.info("Video Editor window closed, resources released")
        super().closeEvent(event)
    
    def on_segment_created(self, segment):
        """Called when a segment is created"""
        row = self.segments_table.rowCount()
        self.segments_table.insertRow(row)
        
        # Convertir the frames en time
        start_time = self.timecode.seconds_to_timecode(segment.start_frame / self.fps)
        end_time = self.timecode.seconds_to_timecode(segment.end_frame / self.fps) if segment.end_frame else "--:--"
        
        # Add les information in la table
        self.segments_table.setItem(row, 0, QTableWidgetItem(start_time))
        self.segments_table.setItem(row, 1, QTableWidgetItem(end_time))
        self.segments_table.setItem(row, 2, QTableWidgetItem(f"Segment {row + 1}"))
    
    def on_segment_deleted(self, index):
        """Called when a segment is deleted from the timeline"""
        # Remove la ligne correspondante in le tableau
        self.segments_table.removeRow(index)
        
        # Désactiver le bouton d'export s'il n'y a plus de segments
        if self.segments_table.rowCount() == 0:
            self.export_btn.setEnabled(False)


    def add_segment_to_table(self, segment):
        """Add a segment to the table"""
        if not hasattr(self, 'segments_table'):
            return
            
        row = self.segments_table.rowCount()
        self.segments_table.insertRow(row)
        
        # Convertir the frames en time
        start_time = self.timecode.seconds_to_timecode(segment.start_frame / self.fps)
        end_time = self.timecode.seconds_to_timecode(segment.end_frame / self.fps) if segment.end_frame else "--:--"
        
        # Add les information in la table
        self.segments_table.setItem(row, 0, QTableWidgetItem(start_time))
        self.segments_table.setItem(row, 1, QTableWidgetItem(end_time))
        self.segments_table.setItem(row, 2, QTableWidgetItem(f"Segment {row + 1}"))

    # ==================== NEW FEATURES ====================

    def setup_menus(self):
        """Setup menu bar with new actions."""
        menubar = self.menuBar()

        # Menu Découpe
        cut_menu = menubar.addMenu("✂️ Découpe")

        mark_in_action = QAction("📍 Marquer Point de Début", self)
        mark_in_action.setShortcut("I")
        mark_in_action.triggered.connect(self.mark_in)
        cut_menu.addAction(mark_in_action)

        mark_out_action = QAction("🏁 Marquer Point de Fin", self)
        mark_out_action.setShortcut("O")
        mark_out_action.triggered.connect(self.mark_out)
        cut_menu.addAction(mark_out_action)

        create_segment_action = QAction("✂️ Créer Segment", self)
        create_segment_action.setShortcut("C")
        create_segment_action.triggered.connect(self.create_segment_from_io)
        cut_menu.addAction(create_segment_action)

        cut_menu.addSeparator()

        split_action = QAction("Couper à la position (S)", self)
        split_action.setShortcut("S")
        split_action.triggered.connect(self.split_at_cursor)
        cut_menu.addAction(split_action)

        # Menu Automatique
        auto_menu = menubar.addMenu("Automatique")

        detect_black_action = QAction("🖤 Détecter fenêtres noires...", self)
        detect_black_action.triggered.connect(self.detect_black_frames)
        auto_menu.addAction(detect_black_action)

        auto_menu.addSeparator()

        split_n_action = QAction("Diviser en N parties...", self)
        split_n_action.triggered.connect(self.split_into_n_parts)
        auto_menu.addAction(split_n_action)

        split_duration_action = QAction("Diviser par durée...", self)
        split_duration_action.triggered.connect(self.split_by_duration)
        auto_menu.addAction(split_duration_action)

        # Menu Segments
        segments_menu = menubar.addMenu("Segments")

        merge_action = QAction("Fusionner sélection", self)
        merge_action.setShortcut("Ctrl+M")
        merge_action.triggered.connect(self.merge_segments)
        segments_menu.addAction(merge_action)

        merge_all_action = QAction("Fusionner TOUT", self)
        merge_all_action.triggered.connect(self.merge_all_segments)
        segments_menu.addAction(merge_all_action)

        segments_menu.addSeparator()

        export_transitions_action = QAction("⚡ Exporter avec transitions...", self)
        export_transitions_action.setShortcut("Ctrl+Shift+E")
        export_transitions_action.triggered.connect(self.export_with_transitions)
        segments_menu.addAction(export_transitions_action)

        # Menu Vidéo
        video_menu = menubar.addMenu("Vidéo")

        merge_videos_action = QAction("🔗 Fusionner plusieurs vidéos...", self)
        merge_videos_action.triggered.connect(self.merge_multiple_videos)
        video_menu.addAction(merge_videos_action)

        # Menu Préférences
        prefs_menu = menubar.addMenu("Préférences")

        theme_action = QAction("🎨 Thèmes et apparence...", self)
        theme_action.setShortcut("Ctrl+,")
        theme_action.triggered.connect(self.open_preferences)
        prefs_menu.addAction(theme_action)

    def setup_shortcuts(self):
        """Configure keyboard shortcuts (Premiere Pro style)."""
        # === PLAYBACK ===
        QShortcut(QKeySequence("Space"), self, self.toggle_play)
        QShortcut(QKeySequence("K"), self, self.toggle_play)

        # === FRAME NAVIGATION ===
        QShortcut(QKeySequence("Left"), self, self.prev_frame)
        QShortcut(QKeySequence("Right"), self, self.next_frame)
        QShortcut(QKeySequence("Shift+Left"), self, lambda: self.skip_frames(-10))
        QShortcut(QKeySequence("Shift+Right"), self, lambda: self.skip_frames(10))
        QShortcut(QKeySequence("Home"), self, self.goto_start)
        QShortcut(QKeySequence("End"), self, self.goto_end)

        # === CUTTING ===
        QShortcut(QKeySequence("I"), self, self.mark_in)
        QShortcut(QKeySequence("O"), self, self.mark_out)
        QShortcut(QKeySequence("X"), self, self.mark_clip)
        QShortcut(QKeySequence("S"), self, self.split_at_cursor)
        QShortcut(QKeySequence("C"), self, self.create_segment_from_io)

        # === DELETION ===
        QShortcut(QKeySequence("Delete"), self, self.delete_selected_segments)
        QShortcut(QKeySequence("Backspace"), self, self.ripple_delete)

        # === MARKERS ===
        QShortcut(QKeySequence("M"), self, self.add_marker)

        # === FILE ===
        QShortcut(QKeySequence("Ctrl+O"), self, self.open_video_dialog)
        QShortcut(QKeySequence("Ctrl+E"), self, self.export_segments)

        # === UNDO/REDO ===
        QShortcut(QKeySequence("Ctrl+Z"), self, self.undo)
        QShortcut(QKeySequence("Ctrl+Shift+Z"), self, self.redo)
        QShortcut(QKeySequence("Ctrl+Y"), self, self.redo)  # Alternative

        # === COPY/PASTE ===
        QShortcut(QKeySequence("Ctrl+C"), self, self.copy_segments)
        QShortcut(QKeySequence("Ctrl+V"), self, self.paste_segments)

        # === ZOOM ===
        QShortcut(QKeySequence("Ctrl++"), self, self.zoom_in)
        QShortcut(QKeySequence("Ctrl+="), self, self.zoom_in)  # Alternative (no shift)
        QShortcut(QKeySequence("Ctrl+-"), self, self.zoom_out)
        QShortcut(QKeySequence("Ctrl+0"), self, self.zoom_reset)

        # === HELP ===
        QShortcut(QKeySequence("F1"), self, self.show_shortcuts_help)
        QShortcut(QKeySequence("Ctrl+?"), self, self.show_shortcuts_help)

        logger.info("Keyboard shortcuts configured")

    def mark_in(self):
        """Mark IN point (start of selection)."""
        if not self.video_path:
            return

        self.in_point = self.current_frame
        self.timeline.set_in_point(self.in_point)
        self.statusBar().showMessage(f"IN marqué: {self.timecode.seconds_to_timecode(self.in_point / self.fps)}", 2000)
        logger.info(f"IN point set at frame {self.in_point}")

    def mark_out(self):
        """Mark OUT point (end of selection)."""
        if not self.video_path:
            return

        self.out_point = self.current_frame
        self.timeline.set_out_point(self.out_point)
        self.statusBar().showMessage(f"OUT marqué: {self.timecode.seconds_to_timecode(self.out_point / self.fps)}", 2000)
        logger.info(f"OUT point set at frame {self.out_point}")

    def mark_clip(self):
        """Mark IN and OUT automatically around cursor."""
        if not self.video_path:
            return

        default_duration = int(self.fps * 5)  # 5 seconds
        self.in_point = max(0, self.current_frame - default_duration // 2)
        self.out_point = min(self.total_frames - 1, self.current_frame + default_duration // 2)
        self.timeline.set_in_out_points(self.in_point, self.out_point)
        self.statusBar().showMessage(
            f"Clip marqué: {self.timecode.seconds_to_timecode(self.in_point / self.fps)} → {self.timecode.seconds_to_timecode(self.out_point / self.fps)}",
            2000
        )

    def create_segment_from_io(self):
        """Create segment between IN and OUT points."""
        if not self.video_path:
            return

        if self.in_point is None or self.out_point is None:
            QMessageBox.warning(self, "Points manquants",
                              "Marquez d'abord IN (I) et OUT (O)")
            return

        if self.in_point >= self.out_point:
            QMessageBox.warning(self, "Intervalle invalide",
                              "Le point OUT doit être après le point IN")
            return

        # Create segment
        segment = VideoSegment(start_frame=self.in_point, end_frame=self.out_point)
        self.timeline.segments.append(segment)

        # Add to table
        self.add_segment_to_table(segment)

        # Clear IN/OUT
        self.in_point = None
        self.out_point = None
        self.timeline.clear_in_out_points()

        self.export_btn.setEnabled(True)
        self.statusBar().showMessage("Segment créé", 2000)
        logger.info(f"Segment created from IN/OUT")

    def split_at_cursor(self):
        """Split segment at current cursor position."""
        if not self.video_path:
            return

        # Find segment containing cursor
        for i, segment in enumerate(self.timeline.segments):
            if segment.start_frame <= self.current_frame <= segment.end_frame:
                if self.current_frame == segment.start_frame or self.current_frame == segment.end_frame:
                    QMessageBox.information(self, "Position invalide",
                                          "Le curseur est déjà sur un bord de segment")
                    return

                # Create two new segments
                segment1 = VideoSegment(start_frame=segment.start_frame, end_frame=self.current_frame)
                segment2 = VideoSegment(start_frame=self.current_frame + 1, end_frame=segment.end_frame)

                # Replace old segment
                self.timeline.segments.pop(i)
                self.timeline.segments.insert(i, segment1)
                self.timeline.segments.insert(i + 1, segment2)

                # Refresh table
                self.refresh_segments_table()
                self.statusBar().showMessage("Segment divisé", 2000)
                logger.info(f"Segment split at frame {self.current_frame}")
                return

        QMessageBox.information(self, "Aucun segment",
                              "Pas de segment à la position du curseur")

    def refresh_segments_table(self):
        """Refresh segments table from timeline."""
        self.segments_table.setRowCount(0)
        for segment in self.timeline.segments:
            self.add_segment_to_table(segment)
        self.export_btn.setEnabled(len(self.timeline.segments) > 0)

    def ripple_delete(self):
        """Delete segment and shift all following segments."""
        selected_rows = self.get_selected_segments()
        if not selected_rows:
            self.statusBar().showMessage("Aucun segment sélectionné", 2000)
            return

        # Sort in reverse to delete from end
        for row in sorted(selected_rows, reverse=True):
            if row < len(self.timeline.segments):
                segment = self.timeline.segments[row]
                duration = segment.end_frame - segment.start_frame + 1

                # Delete segment
                self.timeline.segments.pop(row)

                # Shift all following segments
                for i in range(row, len(self.timeline.segments)):
                    self.timeline.segments[i].start_frame -= duration
                    self.timeline.segments[i].end_frame -= duration

        self.refresh_segments_table()
        self.statusBar().showMessage("Ripple delete effectué", 2000)
        logger.info(f"Ripple delete performed on {len(selected_rows)} segment(s)")

    def skip_frames(self, count):
        """Skip N frames forward or backward."""
        if not self.video_path:
            return

        new_frame = max(0, min(self.total_frames - 1, self.current_frame + count))
        self.show_frame(new_frame)

    def goto_start(self):
        """Go to start of video."""
        if not self.video_path:
            return
        self.show_frame(0)

    def goto_end(self):
        """Go to end of video."""
        if not self.video_path:
            return
        self.show_frame(self.total_frames - 1)

    def add_marker(self):
        """Add marker at current position."""
        if not self.video_path:
            return

        self.timeline.add_marker(self.current_frame, "📍")
        self.statusBar().showMessage(f"Marqueur ajouté à {self.timecode.seconds_to_timecode(self.current_frame / self.fps)}", 2000)

    def detect_black_frames_from_panel(self, threshold, min_duration):
        """Detect black frames from detection panel settings."""
        if not self.video_path:
            QMessageBox.warning(self, "Pas de vidéo", "Ouvrez d'abord une vidéo")
            return

        from .detectors.black_frame_detector import BlackFrameDetectorDialog

        dialog = BlackFrameDetectorDialog(
            self.video_path,
            self.fps,
            self.total_frames,
            threshold=threshold,
            min_duration=min_duration,
            parent=self
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            segments_to_create = dialog.get_segments_between_blacks()

            for start, end in segments_to_create:
                segment = VideoSegment(start_frame=start, end_frame=end)
                self.timeline.segments.append(segment)

            self.refresh_segments_table()
            self.statusBar().showMessage(
                f"✅ {len(segments_to_create)} segments créés depuis détection noire",
                3000
            )
            logger.info(f"Created {len(segments_to_create)} segments from black frame detection")

    def detect_scenes_from_panel(self, threshold, min_scene_length):
        """Detect scenes from detection panel settings."""
        if not self.video_path:
            QMessageBox.warning(self, "Pas de vidéo", "Ouvrez d'abord une vidéo")
            return

        # Stop any existing scene detection
        if self.scene_detection_worker and self.scene_detection_worker.isRunning():
            self.scene_detection_worker.stop()
            self.scene_detection_worker.wait()

        from .detectors.scene_detector import SceneDetectionWorker

        # Save current state for undo
        old_segments = copy.deepcopy(self.timeline.segments)

        # Create worker and store reference to prevent garbage collection
        self.scene_detection_worker = SceneDetectionWorker(
            self.video_path,
            threshold=threshold,
            min_scene_length=min_scene_length
        )

        # Show progress bar and stop button
        self.detection_panel.show_scene_progress()
        self.statusBar().showMessage("🔍 Détection de scènes en cours...")

        def on_progress(percentage):
            """Update progress bar."""
            self.detection_panel.update_scene_progress(percentage)

        def on_finished(scenes):
            """Handle scene detection completion."""
            # Create segments from detected scenes
            for start_frame, end_frame, timestamp in scenes:
                segment = VideoSegment(start_frame=start_frame, end_frame=end_frame)
                self.timeline.segments.append(segment)

            self.refresh_segments_table()

            # Hide progress bar and show detect button
            self.detection_panel.hide_scene_progress()

            self.statusBar().showMessage(
                f"✅ {len(scenes)} scènes détectées et segments créés",
                3000
            )
            logger.info(f"Created {len(scenes)} segments from scene detection")

            # Clean up worker reference
            self.scene_detection_worker = None

        def on_error(error_msg):
            """Handle scene detection error."""
            self.detection_panel.hide_scene_progress()
            self.statusBar().showMessage(f"❌ Erreur: {error_msg}", 5000)
            QMessageBox.critical(self, "Erreur", f"Erreur lors de la détection:\n{error_msg}")

            # Clean up worker reference
            self.scene_detection_worker = None

        # Connect signals
        self.scene_detection_worker.progress.connect(on_progress)
        self.scene_detection_worker.finished.connect(on_finished)
        self.scene_detection_worker.error.connect(on_error)
        self.scene_detection_worker.start()

    def stop_scene_detection(self):
        """Stop the scene detection worker."""
        if self.scene_detection_worker and self.scene_detection_worker.isRunning():
            logger.info("Stopping scene detection...")
            self.scene_detection_worker.stop()
            self.scene_detection_worker.wait()

            # Hide progress bar and show detect button
            self.detection_panel.hide_scene_progress()
            self.statusBar().showMessage("⏹️ Détection de scènes arrêtée", 3000)

            # Clean up worker reference
            self.scene_detection_worker = None

    def detect_black_frames(self):
        """Open black frame detection dialog."""
        if not self.video_path:
            QMessageBox.warning(self, "Pas de vidéo",
                              "Ouvrez d'abord une vidéo")
            return

        from .detectors.black_frame_detector import BlackFrameDetectorDialog

        dialog = BlackFrameDetectorDialog(
            self.video_path,
            self.fps,
            self.total_frames,
            parent=self
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Create segments automatically
            segments_to_create = dialog.get_segments_between_blacks()

            for start, end in segments_to_create:
                segment = VideoSegment(start_frame=start, end_frame=end)
                self.timeline.segments.append(segment)

            self.refresh_segments_table()
            self.statusBar().showMessage(
                f"{len(segments_to_create)} segments créés",
                3000
            )
            logger.info(f"Created {len(segments_to_create)} segments from black frame detection")

    def split_into_n_parts(self):
        """Divide video into N equal parts."""
        if not self.video_path:
            return

        n, ok = QInputDialog.getInt(
            self,
            "Division en N parties",
            "Nombre de parties égales:",
            value=4,
            min=2,
            max=100
        )

        if not ok:
            return

        # Calculate duration of each part
        part_duration = self.total_frames // n

        # Create segments
        self.timeline.segments.clear()
        for i in range(n):
            start = i * part_duration
            end = (i + 1) * part_duration - 1 if i < n - 1 else self.total_frames - 1

            segment = VideoSegment(start_frame=start, end_frame=end)
            self.timeline.segments.append(segment)

        self.refresh_segments_table()
        self.statusBar().showMessage(f"Vidéo divisée en {n} parties", 3000)
        logger.info(f"Video split into {n} equal parts")

    def split_by_duration(self):
        """Divide video by fixed duration."""
        if not self.video_path:
            return

        duration_sec, ok = QInputDialog.getInt(
            self,
            "Division par durée",
            "Durée de chaque segment (secondes):",
            value=30,
            min=1,
            max=3600
        )

        if not ok:
            return

        duration_frames = int(duration_sec * self.fps)

        # Create segments
        self.timeline.segments.clear()
        current_frame = 0
        part_num = 1

        while current_frame < self.total_frames:
            end_frame = min(current_frame + duration_frames - 1, self.total_frames - 1)

            segment = VideoSegment(start_frame=current_frame, end_frame=end_frame)
            self.timeline.segments.append(segment)

            current_frame = end_frame + 1
            part_num += 1

        self.refresh_segments_table()
        self.statusBar().showMessage(
            f"Créé {part_num - 1} segments de {duration_sec}s",
            3000
        )
        logger.info(f"Video split into {part_num - 1} segments of {duration_sec}s each")

    def merge_segments(self):
        """Merge selected segments."""
        selected_rows = self.get_selected_segments()

        if len(selected_rows) < 2:
            QMessageBox.warning(
                self,
                "Sélection insuffisante",
                "Sélectionnez au moins 2 segments à fusionner\n"
                "(Ctrl+Clic ou Shift+Clic)"
            )
            return

        # Get and sort segments by start frame
        segments_to_merge = [self.timeline.segments[row] for row in selected_rows]
        segments_to_merge.sort(key=lambda s: s.start_frame)

        # Check if contiguous
        has_gaps = False
        for i in range(len(segments_to_merge) - 1):
            if segments_to_merge[i].end_frame + 1 != segments_to_merge[i+1].start_frame:
                has_gaps = True
                break

        if has_gaps:
            reply = QMessageBox.question(
                self,
                "Segments non contigus",
                "Les segments ne sont pas adjacents.\n"
                "Voulez-vous fusionner quand même?\n\n"
                "⚠️ Cela créera un segment incluant les parties entre eux.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        # Create merged segment
        merged = VideoSegment(
            start_frame=segments_to_merge[0].start_frame,
            end_frame=segments_to_merge[-1].end_frame
        )

        # Remove old segments
        for segment in segments_to_merge:
            self.timeline.segments.remove(segment)

        # Add new segment
        self.timeline.segments.append(merged)

        self.refresh_segments_table()
        self.statusBar().showMessage(
            f"{len(segments_to_merge)} segments fusionnés",
            3000
        )
        logger.info(f"Merged {len(segments_to_merge)} segments")

    def merge_all_segments(self):
        """Merge ALL segments into one."""
        if len(self.timeline.segments) < 2:
            QMessageBox.information(
                self,
                "Pas assez de segments",
                "Il faut au moins 2 segments pour fusionner"
            )
            return

        reply = QMessageBox.question(
            self,
            "Tout fusionner",
            f"Fusionner les {len(self.timeline.segments)} segments en un seul?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Find global start and end
        start = min(s.start_frame for s in self.timeline.segments)
        end = max(s.end_frame for s in self.timeline.segments)

        # Create global segment
        merged = VideoSegment(start_frame=start, end_frame=end)

        # Replace all
        self.timeline.segments.clear()
        self.timeline.segments.append(merged)

        self.refresh_segments_table()
        self.statusBar().showMessage("Tous les segments fusionnés", 3000)
        logger.info("All segments merged into one")

    def merge_multiple_videos(self):
        """Merge multiple videos into timeline."""
        from .video_merger import VideoMergerDialog

        dialog = VideoMergerDialog(parent=self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            merged_video = dialog.get_merged_video_path()
            if merged_video:
                # Open merged video in editor
                self.open_video(merged_video)
                self.statusBar().showMessage("Vidéo fusionnée chargée", 3000)

    def get_selected_segments(self):
        """Return indices of selected segments."""
        selected_indexes = self.segments_table.selectedIndexes()
        return sorted(set(index.row() for index in selected_indexes))

    def delete_selected_segments(self):
        """Delete selected segments."""
        selected_rows = self.get_selected_segments()
        if not selected_rows:
            self.statusBar().showMessage("Aucun segment sélectionné", 2000)
            return

        # Save for undo
        deleted_segments = []
        for row in selected_rows:
            if row < len(self.timeline.segments):
                deleted_segments.append((row, copy.deepcopy(self.timeline.segments[row])))

        old_segments = copy.deepcopy(self.timeline.segments)

        def undo_delete():
            self.timeline.segments = old_segments
            self.refresh_segments_table()

        def redo_delete():
            # Sort in reverse to delete from end
            for row in sorted(selected_rows, reverse=True):
                if row < len(self.timeline.segments):
                    self.timeline.segments.pop(row)
            self.refresh_segments_table()

        redo_delete()

        # Add to history
        action = HistoryAction(
            name=f"Supprimer {len(selected_rows)} segment(s)",
            undo_callback=undo_delete,
            redo_callback=redo_delete
        )
        self.history.push(action)

        self.statusBar().showMessage(f"{len(selected_rows)} segment(s) supprimé(s)", 2000)

    def show_segments_context_menu(self, position):
        """Show context menu on segments table."""
        menu = QMenu()

        # Actions on single segment
        if len(self.get_selected_segments()) == 1:
            rename_action = menu.addAction("✏️ Renommer")
            rename_action.triggered.connect(self.rename_selected_segment)

            duplicate_action = menu.addAction("📋 Dupliquer")
            duplicate_action.triggered.connect(self.duplicate_selected_segment)

            menu.addSeparator()

        # Actions on multiple segments
        if len(self.get_selected_segments()) >= 2:
            merge_action = menu.addAction("🔗 Fusionner")
            merge_action.triggered.connect(self.merge_segments)

            menu.addSeparator()

        # Common actions
        delete_action = menu.addAction("🗑️ Supprimer")
        delete_action.triggered.connect(self.delete_selected_segments)

        ripple_action = menu.addAction("⚡ Ripple Delete")
        ripple_action.triggered.connect(self.ripple_delete)

        menu.addSeparator()

        export_action = menu.addAction("💾 Exporter segment(s)")
        export_action.triggered.connect(self.export_segments)

        # Show menu
        menu.exec(self.segments_table.mapToGlobal(position))

    def rename_selected_segment(self):
        """Rename selected segment."""
        rows = self.get_selected_segments()
        if not rows:
            return

        row = rows[0]
        current_name = f"Segment {row + 1}"
        if row < self.segments_table.rowCount():
            item = self.segments_table.item(row, 2)
            if item:
                current_name = item.text()

        new_name, ok = QInputDialog.getText(
            self,
            "Renommer segment",
            "Nouveau nom:",
            text=current_name
        )

        if ok and new_name:
            self.segments_table.setItem(row, 2, QTableWidgetItem(new_name))
            self.statusBar().showMessage("Segment renommé", 2000)

    def duplicate_selected_segment(self):
        """Duplicate selected segment."""
        rows = self.get_selected_segments()
        if not rows:
            return

        row = rows[0]
        if row < len(self.timeline.segments):
            segment = self.timeline.segments[row]

            # Create copy shifted
            duration = segment.end_frame - segment.start_frame
            new_start = segment.end_frame + 10  # 10 frames gap
            new_end = new_start + duration

            if new_end < self.total_frames:
                duplicate = VideoSegment(start_frame=new_start, end_frame=new_end)
                self.timeline.segments.append(duplicate)
                self.refresh_segments_table()
                self.statusBar().showMessage("Segment dupliqué", 2000)
            else:
                QMessageBox.warning(self, "Impossible",
                                  "Pas assez d'espace pour dupliquer le segment")

    # ==================== UNDO/REDO ====================

    def undo(self):
        """Undo last action."""
        if self.history.can_undo():
            if self.history.undo():
                self.refresh_segments_table()
                desc = self.history.get_undo_description()
                self.statusBar().showMessage(f"Annulé: {desc if desc else 'action précédente'}", 2000)
        else:
            self.statusBar().showMessage("Rien à annuler", 2000)

    def redo(self):
        """Redo last undone action."""
        if self.history.can_redo():
            if self.history.redo():
                self.refresh_segments_table()
                desc = self.history.get_redo_description()
                self.statusBar().showMessage(f"Rétabli: {desc if desc else 'action annulée'}", 2000)
        else:
            self.statusBar().showMessage("Rien à rétablir", 2000)

    # ==================== COPY/PASTE ====================

    def copy_segments(self):
        """Copy selected segments to clipboard."""
        rows = self.get_selected_segments()
        if not rows:
            self.statusBar().showMessage("Aucun segment sélectionné", 2000)
            return

        self.clipboard = []
        for row in rows:
            if row < len(self.timeline.segments):
                segment = self.timeline.segments[row]
                # Deep copy to avoid reference issues
                self.clipboard.append(copy.deepcopy(segment))

        self.statusBar().showMessage(f"{len(self.clipboard)} segment(s) copié(s)", 2000)
        logger.info(f"Copied {len(self.clipboard)} segments")

    def paste_segments(self):
        """Paste segments from clipboard."""
        if not self.clipboard:
            self.statusBar().showMessage("Presse-papier vide", 2000)
            return

        if not self.video_path:
            self.statusBar().showMessage("Ouvrez d'abord une vidéo", 2000)
            return

        # Save state for undo
        old_segments = copy.deepcopy(self.timeline.segments)

        def undo_paste():
            self.timeline.segments = old_segments
            self.refresh_segments_table()

        def redo_paste():
            for segment in self.clipboard:
                # Calculate offset from current frame
                duration = segment.end_frame - segment.start_frame
                new_start = self.current_frame
                new_end = min(new_start + duration, self.total_frames - 1)

                if new_end > new_start:
                    new_segment = VideoSegment(start_frame=new_start, end_frame=new_end)
                    self.timeline.segments.append(new_segment)
                    self.current_frame = new_end + 10  # Move cursor forward

            self.refresh_segments_table()

        redo_paste()

        # Add to history
        action = HistoryAction(
            name=f"Coller {len(self.clipboard)} segment(s)",
            undo_callback=undo_paste,
            redo_callback=redo_paste
        )
        self.history.push(action)

        self.export_btn.setEnabled(True)
        self.statusBar().showMessage(f"{len(self.clipboard)} segment(s) collé(s)", 2000)
        logger.info(f"Pasted {len(self.clipboard)} segments")

    # ==================== ZOOM ====================

    def zoom_in(self):
        """Zoom in on timeline."""
        self.zoom_level = min(self.zoom_level * 1.2, 10.0)
        self.timeline.setFixedHeight(int(50 * self.zoom_level))
        self.statusBar().showMessage(f"Zoom: {int(self.zoom_level * 100)}%", 2000)
        logger.debug(f"Zoom in: {self.zoom_level}")

    def zoom_out(self):
        """Zoom out on timeline."""
        self.zoom_level = max(self.zoom_level / 1.2, 0.5)
        self.timeline.setFixedHeight(int(50 * self.zoom_level))
        self.statusBar().showMessage(f"Zoom: {int(self.zoom_level * 100)}%", 2000)
        logger.debug(f"Zoom out: {self.zoom_level}")

    def zoom_reset(self):
        """Reset timeline zoom to 100%."""
        self.zoom_level = 1.0
        self.timeline.setMinimumHeight(50)
        self.timeline.setMaximumHeight(16777215)  # Reset to no max
        self.statusBar().showMessage("Zoom réinitialisé: 100%", 2000)
        logger.debug("Zoom reset")

    # ==================== HELP ====================

    def show_shortcuts_help(self):
        """Show keyboard shortcuts help dialog."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Raccourcis Clavier")
        dialog.setMinimumSize(700, 600)

        layout = QVBoxLayout(dialog)

        # Title
        title = QLabel("📋 Guide des Raccourcis Clavier")
        title.setStyleSheet("font-weight: bold; font-size: 16px; margin-bottom: 10px;")
        layout.addWidget(title)

        # Create text editor with shortcuts
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)

        shortcuts_html = """
        <style>
            body { font-family: Arial; }
            h3 { color: #0066cc; margin-top: 15px; }
            table { width: 100%; border-collapse: collapse; }
            td { padding: 8px; border-bottom: 1px solid #ddd; }
            td:first-child { font-weight: bold; width: 30%; }
            .category { background-color: #f0f0f0; font-weight: bold; padding: 10px; margin-top: 10px; }
        </style>

        <div class="category">🎬 LECTURE</div>
        <table>
            <tr><td>Space / K</td><td>Lecture / Pause</td></tr>
            <tr><td>Left / Right</td><td>Frame précédente / suivante</td></tr>
            <tr><td>Shift+Left / Shift+Right</td><td>-10 / +10 frames</td></tr>
            <tr><td>Home / End</td><td>Début / Fin de vidéo</td></tr>
        </table>

        <div class="category">✂️ DÉCOUPE</div>
        <table>
            <tr><td>I</td><td>Marquer IN point (début)</td></tr>
            <tr><td>O</td><td>Marquer OUT point (fin)</td></tr>
            <tr><td>X</td><td>Marquer IN+OUT automatiquement (5 sec)</td></tr>
            <tr><td>C</td><td>Créer segment entre IN et OUT</td></tr>
            <tr><td>S</td><td>Couper à la position du curseur</td></tr>
        </table>

        <div class="category">🗑️ GESTION</div>
        <table>
            <tr><td>Delete</td><td>Supprimer segments sélectionnés</td></tr>
            <tr><td>Backspace</td><td>Ripple delete (supprimer + décaler)</td></tr>
            <tr><td>M</td><td>Ajouter marqueur</td></tr>
        </table>

        <div class="category">↩️ UNDO/REDO</div>
        <table>
            <tr><td>Ctrl+Z</td><td>Annuler</td></tr>
            <tr><td>Ctrl+Shift+Z / Ctrl+Y</td><td>Rétablir</td></tr>
        </table>

        <div class="category">📋 COPIER/COLLER</div>
        <table>
            <tr><td>Ctrl+C</td><td>Copier segments sélectionnés</td></tr>
            <tr><td>Ctrl+V</td><td>Coller segments</td></tr>
        </table>

        <div class="category">🔍 ZOOM</div>
        <table>
            <tr><td>Ctrl++ / Ctrl+=</td><td>Zoom avant sur timeline</td></tr>
            <tr><td>Ctrl+-</td><td>Zoom arrière sur timeline</td></tr>
            <tr><td>Ctrl+0</td><td>Réinitialiser zoom (100%)</td></tr>
        </table>

        <div class="category">📁 FICHIER</div>
        <table>
            <tr><td>Ctrl+O</td><td>Ouvrir vidéo</td></tr>
            <tr><td>Ctrl+E</td><td>Exporter segments</td></tr>
            <tr><td>Ctrl+M</td><td>Fusionner segments sélectionnés</td></tr>
        </table>

        <div class="category">❓ AIDE</div>
        <table>
            <tr><td>F1</td><td>Afficher cette aide</td></tr>
        </table>
        """

        text_edit.setHtml(shortcuts_html)
        layout.addWidget(text_edit)

        # Close button
        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.exec()
        logger.info("Shortcuts help displayed")

    # ==================== AUDIO EXTRACTION ====================

    def extract_full_audio(self, audio_format, bitrate, normalize):
        """Extract audio from full video."""
        if not self.video_path:
            QMessageBox.warning(self, "Pas de vidéo", "Ouvrez d'abord une vidéo")
            return

        from .detectors.audio_extractor import AudioExtractionWorker

        # Ask for output location
        output_folder = QFileDialog.getExistingDirectory(
            self,
            "Sélectionner le dossier de sortie",
            os.path.dirname(self.video_path)
        )

        if not output_folder:
            return

        # Create worker
        self.audio_panel.setEnabled(False)
        self.statusBar().showMessage("🎵 Extraction audio en cours...")

        worker = AudioExtractionWorker(
            [self.video_path],
            output_format=audio_format,
            bitrate=bitrate,
            normalize=normalize,
            output_folder=output_folder
        )

        def on_finished():
            self.audio_panel.setEnabled(True)
            self.statusBar().showMessage("✅ Audio extrait avec succès!", 3000)
            QMessageBox.information(
                self,
                "Extraction réussie",
                f"Audio extrait dans:\n{output_folder}"
            )

        def on_error(error_msg):
            self.audio_panel.setEnabled(True)
            self.statusBar().showMessage(f"❌ Erreur: {error_msg}", 5000)
            QMessageBox.critical(self, "Erreur", f"Erreur lors de l'extraction:\n{error_msg}")

        worker.finished.connect(on_finished)
        worker.error.connect(on_error)
        worker.start()

    def extract_segment_audio(self, segment_index, audio_format, bitrate, normalize):
        """Extract audio from selected segment."""
        if not self.video_path:
            QMessageBox.warning(self, "Pas de vidéo", "Ouvrez d'abord une vidéo")
            return

        # Get selected segments
        selected_rows = self.segments_panel.get_selected_rows()
        if not selected_rows:
            QMessageBox.warning(self, "Pas de sélection", "Sélectionnez un segment d'abord")
            return

        segment_index = selected_rows[0]
        if segment_index >= len(self.timeline.segments):
            return

        segment = self.timeline.segments[segment_index]

        from .detectors.audio_extractor import AudioExtractionWorker

        # Ask for output location
        output_folder = QFileDialog.getExistingDirectory(
            self,
            "Sélectionner le dossier de sortie",
            os.path.dirname(self.video_path)
        )

        if not output_folder:
            return

        # Calculate times
        start_time = segment.start_frame / self.fps if self.fps > 0 else 0
        end_time = segment.end_frame / self.fps if self.fps > 0 else 0

        # Create worker
        self.audio_panel.setEnabled(False)
        self.statusBar().showMessage("🎵 Extraction audio du segment en cours...")

        worker = AudioExtractionWorker(
            [self.video_path],
            output_format=audio_format,
            bitrate=bitrate,
            normalize=normalize,
            output_folder=output_folder,
            start_time=start_time,
            end_time=end_time
        )

        def on_finished():
            self.audio_panel.setEnabled(True)
            self.statusBar().showMessage("✅ Audio du segment extrait avec succès!", 3000)
            QMessageBox.information(
                self,
                "Extraction réussie",
                f"Audio du segment extrait dans:\n{output_folder}"
            )

        def on_error(error_msg):
            self.audio_panel.setEnabled(True)
            self.statusBar().showMessage(f"❌ Erreur: {error_msg}", 5000)
            QMessageBox.critical(self, "Erreur", f"Erreur lors de l'extraction:\n{error_msg}")

        worker.finished.connect(on_finished)
        worker.error.connect(on_error)
        worker.start()

    def extract_all_segments_audio(self, audio_format, bitrate, normalize):
        """Extract audio from all segments."""
        if not self.video_path:
            QMessageBox.warning(self, "Pas de vidéo", "Ouvrez d'abord une vidéo")
            return

        if not self.timeline.segments:
            QMessageBox.warning(self, "Pas de segments", "Créez des segments d'abord")
            return

        # Ask for output location
        output_folder = QFileDialog.getExistingDirectory(
            self,
            "Sélectionner le dossier de sortie",
            os.path.dirname(self.video_path)
        )

        if not output_folder:
            return

        # Confirm batch extraction
        reply = QMessageBox.question(
            self,
            "Extraction batch",
            f"Extraire l'audio de {len(self.timeline.segments)} segments?\n\n"
            f"Format: {audio_format}\n"
            f"Qualité: {bitrate} kbps\n"
            f"Normalisation: {'Oui' if normalize else 'Non'}\n\n"
            f"Dossier de sortie: {output_folder}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        from .detectors.audio_extractor import AudioExtractionWorker
        from pathlib import Path

        # Prepare segment data
        video_name = Path(self.video_path).stem
        segments_data = []

        for i, segment in enumerate(self.timeline.segments, 1):
            start_time = segment.start_frame / self.fps if self.fps > 0 else 0
            end_time = segment.end_frame / self.fps if self.fps > 0 else 0
            segments_data.append({
                'index': i,
                'start_time': start_time,
                'end_time': end_time,
                'segment': segment
            })

        # Create progress dialog
        from PyQt6.QtWidgets import QProgressDialog
        progress_dialog = QProgressDialog(
            f"Extraction de l'audio des segments...",
            "Annuler",
            0,
            len(segments_data),
            self
        )
        progress_dialog.setWindowTitle("Extraction Audio")
        progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        progress_dialog.setMinimumDuration(0)
        progress_dialog.setValue(0)

        # Track results
        self.batch_extraction_results = {
            'total': len(segments_data),
            'completed': 0,
            'failed': 0,
            'current_index': 0,
            'segments_data': segments_data,
            'output_folder': output_folder,
            'video_name': video_name,
            'audio_format': audio_format,
            'bitrate': bitrate,
            'normalize': normalize,
            'progress_dialog': progress_dialog,
            'output_files': []
        }

        # Disable panel during extraction
        self.audio_panel.setEnabled(False)

        # Start first extraction
        self._extract_next_segment_audio()

    def _extract_next_segment_audio(self):
        """Extract audio from next segment in batch."""
        results = self.batch_extraction_results

        # Check if cancelled
        if results['progress_dialog'].wasCanceled():
            self._finish_batch_extraction()
            return

        # Check if all segments processed
        if results['current_index'] >= results['total']:
            self._finish_batch_extraction()
            return

        # Get current segment data
        segment_data = results['segments_data'][results['current_index']]
        segment_index = segment_data['index']

        # Update progress dialog
        results['progress_dialog'].setLabelText(
            f"Extraction du segment {segment_index}/{results['total']}...\n"
            f"Temps: {segment_data['start_time']:.1f}s - {segment_data['end_time']:.1f}s"
        )
        results['progress_dialog'].setValue(results['current_index'])

        # Create custom filename for this segment
        from .detectors.audio_extractor import AudioExtractionWorker
        format_info = AudioExtractionWorker.FORMATS[results['audio_format']]
        custom_filename = f"{results['video_name']}_segment_{segment_index:03d}"
        output_filename = f"{custom_filename}{format_info['ext']}"
        output_path = Path(results['output_folder']) / output_filename

        # Create temporary worker for this segment
        # We use a list with single video but specify start/end times and custom filename
        worker = AudioExtractionWorker(
            [self.video_path],
            output_format=results['audio_format'],
            bitrate=results['bitrate'],
            normalize=results['normalize'],
            output_folder=results['output_folder'],
            start_time=segment_data['start_time'],
            end_time=segment_data['end_time'],
            custom_filename=custom_filename
        )

        # Store worker reference
        self.current_batch_worker = worker

        # Connect signals
        def on_finished():
            results['completed'] += 1
            results['output_files'].append(str(output_path))
            results['current_index'] += 1
            logger.info(f"Segment {segment_index} audio extracted successfully")
            # Process next segment
            self._extract_next_segment_audio()

        def on_error(error_msg):
            results['failed'] += 1
            results['current_index'] += 1
            logger.error(f"Failed to extract audio from segment {segment_index}: {error_msg}")
            # Continue with next segment despite error
            self._extract_next_segment_audio()

        worker.finished.connect(on_finished)
        worker.error.connect(on_error)

        # Start extraction
        worker.start()

    def _finish_batch_extraction(self):
        """Finish batch audio extraction and show results."""
        results = self.batch_extraction_results

        # Close progress dialog
        results['progress_dialog'].close()

        # Re-enable panel
        self.audio_panel.setEnabled(True)

        # Show results
        if results['completed'] > 0:
            message = f"✅ Extraction terminée!\n\n"
            message += f"Segments traités: {results['completed']}/{results['total']}\n"

            if results['failed'] > 0:
                message += f"Échecs: {results['failed']}\n"

            message += f"\nFichiers créés dans:\n{results['output_folder']}"

            QMessageBox.information(
                self,
                "Extraction réussie",
                message
            )

            self.statusBar().showMessage(
                f"✅ {results['completed']} segments audio extraits avec succès!",
                5000
            )
        else:
            QMessageBox.warning(
                self,
                "Extraction annulée",
                "Aucun segment n'a été extrait."
            )
            self.statusBar().showMessage("⚠️ Extraction annulée", 3000)

        # Clean up
        self.batch_extraction_results = None
        self.current_batch_worker = None

    # ==================== TRANSITIONS ====================

    def on_transition_clicked(self, row_index):
        """Handle transition configuration for a segment.

        Args:
            row_index: Index of the segment in the segments table
        """
        if not self.video_path:
            QMessageBox.warning(
                self,
                "Aucune vidéo",
                "Veuillez ouvrir une vidéo avant de configurer les transitions."
            )
            return

        # Get segments from timeline
        segments = self.timeline.segment_manager.segments

        if not segments or row_index >= len(segments):
            QMessageBox.warning(
                self,
                "Segment invalide",
                "Le segment sélectionné n'existe pas."
            )
            return

        segment = segments[row_index]

        # Open transition dialog
        dialog = TransitionDialog(self, segment.transition_out)

        if dialog.exec():
            # Apply the selected transition
            transition = dialog.get_current_transition()
            segment.transition_out = transition

            # Update status
            from .transitions import TransitionType
            if transition.type == TransitionType.NONE:
                self.statusBar().showMessage(f"✂️ Transition supprimée pour le segment {row_index + 1}", 3000)
            else:
                self.statusBar().showMessage(
                    f"⚡ Transition '{transition.type.value}' appliquée au segment {row_index + 1}",
                    3000
                )

            logger.info(f"Transition configured for segment {row_index}: {transition}")

    def on_text_overlay_clicked(self, row_index):
        """Handle text overlay configuration for a segment.

        Args:
            row_index: Index of the segment in the segments table
        """
        if not self.video_path:
            QMessageBox.warning(
                self,
                "Aucune vidéo",
                "Veuillez ouvrir une vidéo avant d'ajouter du texte."
            )
            return

        # Get segments from timeline
        segments = self.timeline.segment_manager.segments

        if not segments or row_index >= len(segments):
            QMessageBox.warning(
                self,
                "Segment invalide",
                "Le segment sélectionné n'existe pas."
            )
            return

        segment = segments[row_index]

        # Prepare video info for the dialog
        video_info = {
            'width': self.video_width,
            'height': self.video_height,
            'fps': self.fps,
            'duration_frames': segment.end_frame - segment.start_frame if segment.end_frame else 100
        }

        # Open text editor dialog
        from .dialogs.text_editor_dialog import TextEditorDialog
        dialog = TextEditorDialog(self, video_info=video_info)

        # Connect the signal
        dialog.text_overlay_created.connect(lambda overlay: self._add_text_to_segment(segment, overlay, row_index))

        dialog.exec()

    def _add_text_to_segment(self, segment, overlay, row_index):
        """Add a text overlay to a segment.

        Args:
            segment: VideoSegment to add text to
            overlay: TextOverlay to add
            row_index: Index of segment for status message
        """
        # Add overlay to segment
        segment.add_text_overlay(overlay)

        # Update timeline to show text marker
        self.timeline.update()

        # Update status
        self.statusBar().showMessage(
            f"📝 Texte '{overlay.name}' ajouté au segment {row_index + 1}",
            3000
        )

        logger.info(f"Text overlay added to segment {row_index}: {overlay.text[:30]}...")

    def export_with_transitions(self):
        """Export all segments with transitions to a single video file."""
        if not self.video_path:
            QMessageBox.warning(
                self,
                "Aucune vidéo",
                "Veuillez ouvrir une vidéo avant d'exporter."
            )
            return

        segments = self.timeline.segment_manager.segments

        if not segments:
            QMessageBox.warning(
                self,
                "Aucun segment",
                "Veuillez créer au moins un segment avant d'exporter."
            )
            return

        # Ask for output file
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter la vidéo avec transitions",
            "",
            "Vidéo MP4 (*.mp4);;Tous les fichiers (*)"
        )

        if not output_path:
            return

        # Check if any segments have transitions
        has_transitions = any(seg.has_transition_out() for seg in segments[:-1])

        if not has_transitions:
            reply = QMessageBox.question(
                self,
                "Aucune transition",
                "Aucun segment n'a de transition configurée.\n\n"
                "Voulez-vous continuer avec un export simple (plus rapide) ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.No:
                return

        # Create progress dialog
        progress_dialog = QDialog(self)
        progress_dialog.setWindowTitle("Export en cours...")
        progress_dialog.setMinimumWidth(400)
        progress_dialog.setModal(True)

        layout = QVBoxLayout(progress_dialog)

        status_label = QLabel("Initialisation de l'export...")
        layout.addWidget(status_label)

        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        layout.addWidget(progress_bar)

        cancel_btn = QPushButton("Annuler")
        layout.addWidget(cancel_btn)

        # Create export worker
        worker = TransitionExportWorker(
            self.video_path,
            segments,
            output_path,
            self.fps
        )

        # Connect signals
        worker.progress.connect(progress_bar.setValue)
        worker.status_message.connect(status_label.setText)

        def on_finished(path):
            progress_dialog.accept()
            QMessageBox.information(
                self,
                "Export réussi",
                f"Vidéo exportée avec succès:\n{path}"
            )
            self.statusBar().showMessage("✅ Export terminé avec succès", 5000)

        def on_error(error_msg):
            progress_dialog.reject()
            QMessageBox.critical(
                self,
                "Erreur d'export",
                f"Une erreur est survenue lors de l'export:\n\n{error_msg}"
            )
            self.statusBar().showMessage("❌ Erreur lors de l'export", 5000)

        worker.finished.connect(on_finished)
        worker.error.connect(on_error)
        cancel_btn.clicked.connect(worker.stop)
        cancel_btn.clicked.connect(progress_dialog.reject)

        # Start export
        worker.start()
        progress_dialog.exec()

        logger.info(f"Export with transitions to: {output_path}")

    # ==================== PREFERENCES ====================

    def open_preferences(self):
        """Open preferences dialog for theme and settings configuration."""
        dialog = PreferencesDialog(self.theme_manager, self)

        # Connect signals
        dialog.theme_changed.connect(self.on_theme_changed)
        dialog.timeline_height_changed.connect(self.on_timeline_height_changed)

        dialog.exec()

    def on_theme_changed(self, theme):
        """Handle theme change from preferences.

        Args:
            theme: New Theme to apply
        """
        self.theme_manager.apply_theme(theme, app=QApplication.instance())
        self.statusBar().showMessage(f"🎨 Thème '{theme.name}' appliqué", 3000)
        logger.info(f"Theme changed to: {theme.name}")

    def on_timeline_height_changed(self, height: int):
        """Handle timeline height change from preferences.

        Args:
            height: New timeline height in pixels
        """
        if hasattr(self, 'timeline'):
            self.timeline.setMinimumHeight(height)
            self.timeline.setMaximumHeight(height)
            self.statusBar().showMessage(f"📏 Hauteur timeline: {height}px", 3000)
            logger.info(f"Timeline height changed to: {height}px")

    # ===== PANEL LAYOUT CONTROLS =====
    # No longer needed with tabbed layout

# ==================== EXPORT DIALOG ====================

class ExportDialog(QDialog):
    """Dialog for exporting segments with templates and progress."""

    # Export templates with presets
    TEMPLATES = {
        "Original (Copy)": {
            "description": "Copie rapide sans réencodage",
            "params": ["-c", "copy"]
        },
        "YouTube (H.264)": {
            "description": "Optimisé pour YouTube (1080p)",
            "params": [
                "-c:v", "libx264", "-preset", "medium",
                "-crf", "23", "-c:a", "aac", "-b:a", "192k",
                "-vf", "scale=-2:1080"
            ]
        },
        "Instagram (H.264)": {
            "description": "Optimisé pour Instagram (720p, 30fps)",
            "params": [
                "-c:v", "libx264", "-preset", "medium",
                "-crf", "23", "-c:a", "aac", "-b:a", "128k",
                "-vf", "scale=-2:720", "-r", "30"
            ]
        },
        "Web (H.264)": {
            "description": "Léger pour le web (720p)",
            "params": [
                "-c:v", "libx264", "-preset", "fast",
                "-crf", "28", "-c:a", "aac", "-b:a", "128k",
                "-vf", "scale=-2:720"
            ]
        },
        "High Quality (H.265)": {
            "description": "Haute qualité avec compression (H.265)",
            "params": [
                "-c:v", "libx265", "-preset", "medium",
                "-crf", "20", "-c:a", "aac", "-b:a", "192k"
            ]
        }
    }

    def __init__(self, parent, video_path, segments, fps):
        """Initialize export dialog."""
        super().__init__(parent)
        self.video_path = video_path
        self.segments = segments
        self.fps = fps
        self.is_exporting = False

        self.setWindowTitle("Exporter les Segments")
        self.setMinimumSize(600, 400)
        self.setup_ui()

    def setup_ui(self):
        """Setup user interface."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel(f"📤 Exporter {len(self.segments)} segment(s)")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        # Template selection
        template_group = QGroupBox("Template d'export")
        template_layout = QVBoxLayout(template_group)

        self.template_combo = QComboBox()
        for name, info in self.TEMPLATES.items():
            self.template_combo.addItem(f"{name} - {info['description']}")

        template_layout.addWidget(self.template_combo)
        layout.addWidget(template_group)

        # Output directory
        output_group = QGroupBox("Dossier de sortie")
        output_layout = QHBoxLayout(output_group)

        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setText(os.path.dirname(self.video_path))
        output_layout.addWidget(self.output_dir_edit)

        browse_btn = QPushButton("📁")
        browse_btn.clicked.connect(self.browse_output_dir)
        output_layout.addWidget(browse_btn)

        layout.addWidget(output_group)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        # Buttons
        buttons_layout = QHBoxLayout()

        self.export_btn = QPushButton("✂️ Exporter")
        self.export_btn.clicked.connect(self.start_export)
        buttons_layout.addWidget(self.export_btn)

        cancel_btn = QPushButton("Annuler")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        layout.addLayout(buttons_layout)

    def browse_output_dir(self):
        """Browse for output directory."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Sélectionner le dossier de sortie",
            self.output_dir_edit.text()
        )
        if directory:
            self.output_dir_edit.setText(directory)

    def start_export(self):
        """Start exporting segments."""
        if self.is_exporting:
            return

        output_dir = self.output_dir_edit.text()
        if not output_dir or not os.path.exists(output_dir):
            QMessageBox.warning(self, "Erreur", "Dossier de sortie invalide")
            return

        self.is_exporting = True
        self.export_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(self.segments))
        self.progress_bar.setValue(0)

        # Get selected template
        template_name = list(self.TEMPLATES.keys())[self.template_combo.currentIndex()]
        template_params = self.TEMPLATES[template_name]["params"]

        # Export each segment
        video_name = os.path.splitext(os.path.basename(self.video_path))[0]
        success_count = 0

        for i, segment in enumerate(self.segments):
            self.status_label.setText(f"Export segment {i+1}/{len(self.segments)}...")
            QApplication.processEvents()

            try:
                # Calculate times
                start_time = segment.start_frame / self.fps
                duration = (segment.end_frame - segment.start_frame) / self.fps

                # Output path
                output_path = os.path.join(output_dir, f"{video_name}_segment_{i+1}.mp4")

                # FFmpeg command
                command = [
                    "ffmpeg", "-y",
                    "-i", self.video_path,
                    "-ss", str(start_time),
                    "-t", str(duration)
                ] + template_params + [output_path]

                # Execute FFmpeg
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                process.wait()

                if process.returncode == 0:
                    success_count += 1
                else:
                    logger.error(f"FFmpeg error for segment {i+1}: {process.stderr.read().decode()}")

            except Exception as e:
                logger.error(f"Error exporting segment {i+1}: {e}")

            self.progress_bar.setValue(i + 1)

        # Done
        self.is_exporting = False
        self.export_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

        if success_count == len(self.segments):
            self.status_label.setText(f"✅ {success_count} segment(s) exporté(s) avec succès!")
            QMessageBox.information(
                self,
                "Export réussi",
                f"{success_count} segment(s) exporté(s) dans:\n{output_dir}"
            )
            self.accept()
        else:
            self.status_label.setText(f"⚠️ {success_count}/{len(self.segments)} segment(s) exporté(s)")
            QMessageBox.warning(
                self,
                "Export partiel",
                f"Seulement {success_count}/{len(self.segments)} segment(s) exporté(s)"
            )
