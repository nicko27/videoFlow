"""Text editor dialog for creating and editing text overlays.

This dialog provides a comprehensive interface for creating titles,
subtitles, and other text overlays with live preview.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QGridLayout, QComboBox, QSpinBox,
    QDoubleSpinBox, QCheckBox, QColorDialog, QTextEdit, QTabWidget,
    QWidget, QSlider, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from ..text_overlay import (
    TextOverlay, TextStyle, TextPosition,
    AnimationType, TextAlignment
)
from ..text_templates import TextTemplates
from src.core.i18n import t


class TextEditorDialog(QDialog):
    """Dialog for creating and editing text overlays.

    Provides controls for:
    - Text content input
    - Style customization (font, size, colors)
    - Position selection
    - Animation configuration
    - Template selection
    - Live preview

    Signals:
        text_overlay_created: Emitted when text overlay is created (TextOverlay)
    """

    text_overlay_created = pyqtSignal(object)  # TextOverlay

    def __init__(self, parent=None, existing_overlay: TextOverlay = None, video_info: dict = None):
        """Initialize text editor dialog.

        Args:
            parent: Parent widget
            existing_overlay: Existing text overlay to edit (None = create new)
            video_info: Dict with video info (width, height, fps, duration_frames)
        """
        super().__init__(parent)

        self.existing_overlay = existing_overlay
        self.video_info = video_info or {
            'width': 1920,
            'height': 1080,
            'fps': 30,
            'duration_frames': 3000
        }

        # Current overlay being edited
        if existing_overlay:
            self.overlay = existing_overlay
        else:
            self.overlay = TextOverlay(
                text="Sample Text",
                style=TextStyle(),
                position=TextPosition.CENTER
            )

        self.setup_ui()
        self.load_overlay_data()

    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle(t("video_editor.dialog.text_editor.title", "Text Editor"))
        self.setMinimumWidth(900)
        self.setMinimumHeight(700)

        layout = QVBoxLayout(self)

        # Main content with tabs
        tabs = QTabWidget()

        # Template tab
        template_tab = self._create_template_tab()
        tabs.addTab(template_tab, t("video_editor.dialog.text_editor.tab_templates", "📋 Templates"))

        # Text tab
        text_tab = self._create_text_tab()
        tabs.addTab(text_tab, t("video_editor.dialog.text_editor.tab_text", "📝 Text"))

        # Style tab
        style_tab = self._create_style_tab()
        tabs.addTab(style_tab, t("video_editor.dialog.text_editor.tab_style", "🎨 Style"))

        # Position tab
        position_tab = self._create_position_tab()
        tabs.addTab(position_tab, t("video_editor.dialog.text_editor.tab_position", "📍 Position"))

        # Animation tab
        animation_tab = self._create_animation_tab()
        tabs.addTab(animation_tab, t("video_editor.dialog.text_editor.tab_animation", "⚡ Animation"))

        layout.addWidget(tabs)

        # Preview section
        preview_group = QGroupBox(t("video_editor.dialog.text_editor.preview", "Preview"))
        preview_layout = QVBoxLayout()

        self.preview_label = QLabel()
        self.preview_label.setMinimumHeight(150)
        self.preview_label.setStyleSheet("""
            QLabel {
                background-color: #1a1a1a;
                color: white;
                border: 2px solid #555;
                border-radius: 4px;
                padding: 20px;
                font-size: 16px;
            }
        """)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setWordWrap(True)
        preview_layout.addWidget(self.preview_label)

        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton(t("video_editor.dialog.text_editor.cancel", "Cancel"))
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        create_btn = QPushButton(
            t("video_editor.dialog.text_editor.create", "Create") if not self.existing_overlay
            else t("video_editor.dialog.text_editor.update", "Update")
        )
        create_btn.setDefault(True)
        create_btn.clicked.connect(self.create_overlay)
        button_layout.addWidget(create_btn)

        layout.addLayout(button_layout)

        # Update preview
        self.update_preview()

    def _create_template_tab(self) -> QWidget:
        """Create template selection tab.

        Returns:
            Widget with template controls
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel(t("video_editor.dialog.text_editor.choose_template", "<b>Choose a preset template</b>")))

        # Template list
        self.template_list = QListWidget()
        categories = TextTemplates.get_template_categories()

        for category, templates in categories.items():
            # Category header
            header_item = QListWidgetItem(f"━━━ {category} ━━━")
            header_item.setFlags(Qt.ItemFlag.NoItemFlags)
            header_font = QFont()
            header_font.setBold(True)
            header_item.setFont(header_font)
            self.template_list.addItem(header_item)

            # Templates in category
            for template_name in templates:
                item = QListWidgetItem(f"  {template_name}")
                item.setData(Qt.ItemDataRole.UserRole, template_name)
                desc = TextTemplates.get_template_description(template_name)
                item.setToolTip(desc)
                self.template_list.addItem(item)

        self.template_list.itemClicked.connect(self.on_template_selected)
        layout.addWidget(self.template_list)

        # Template description
        self.template_desc = QLabel()
        self.template_desc.setWordWrap(True)
        self.template_desc.setStyleSheet("padding: 10px; background-color: #2a2a2a; border-radius: 4px;")
        layout.addWidget(self.template_desc)

        return widget

    def _create_text_tab(self) -> QWidget:
        """Create text input tab.

        Returns:
            Widget with text controls
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Text input
        layout.addWidget(QLabel(t("video_editor.dialog.text_editor.text_content", "<b>Text Content</b>")))

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText(t("video_editor.dialog.text_editor.text_placeholder", "Enter your text here...\n(Use Enter for line breaks)"))
        self.text_edit.setMaximumHeight(150)
        self.text_edit.textChanged.connect(self.on_text_changed)
        layout.addWidget(self.text_edit)

        # Timing group
        timing_group = QGroupBox(t("video_editor.dialog.text_editor.timing", "Timing"))
        timing_layout = QGridLayout()

        timing_layout.addWidget(QLabel(t("video_editor.dialog.text_editor.start_frame", "Start Frame:")), 0, 0)
        self.start_frame_spin = QSpinBox()
        self.start_frame_spin.setRange(0, self.video_info['duration_frames'])
        self.start_frame_spin.setValue(0)
        timing_layout.addWidget(self.start_frame_spin, 0, 1)

        timing_layout.addWidget(QLabel(t("video_editor.dialog.text_editor.end_frame", "End Frame:")), 1, 0)
        self.end_frame_spin = QSpinBox()
        self.end_frame_spin.setRange(0, self.video_info['duration_frames'])
        self.end_frame_spin.setValue(150)
        timing_layout.addWidget(self.end_frame_spin, 1, 1)

        # Duration display
        self.duration_label = QLabel()
        self.update_duration_label()
        self.start_frame_spin.valueChanged.connect(self.update_duration_label)
        self.end_frame_spin.valueChanged.connect(self.update_duration_label)
        timing_layout.addWidget(self.duration_label, 2, 0, 1, 2)

        timing_group.setLayout(timing_layout)
        layout.addWidget(timing_group)

        layout.addStretch()

        return widget

    def _create_style_tab(self) -> QWidget:
        """Create style customization tab.

        Returns:
            Widget with style controls
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Font group
        font_group = QGroupBox("Police")
        font_layout = QGridLayout()

        font_layout.addWidget(QLabel("Famille:"), 0, 0)
        self.font_combo = QComboBox()
        self.font_combo.addItems([
            "Arial", "Times New Roman", "Courier New", "Verdana",
            "Georgia", "Comic Sans MS", "Impact", "Trebuchet MS"
        ])
        self.font_combo.currentTextChanged.connect(self.on_style_changed)
        font_layout.addWidget(self.font_combo, 0, 1)

        font_layout.addWidget(QLabel("Taille:"), 1, 0)
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 200)
        self.font_size_spin.setValue(48)
        self.font_size_spin.setSuffix(" pt")
        self.font_size_spin.valueChanged.connect(self.on_style_changed)
        font_layout.addWidget(self.font_size_spin, 1, 1)

        # Font style checkboxes
        self.bold_check = QCheckBox("Gras")
        self.bold_check.stateChanged.connect(self.on_style_changed)
        font_layout.addWidget(self.bold_check, 2, 0)

        self.italic_check = QCheckBox("Italique")
        self.italic_check.stateChanged.connect(self.on_style_changed)
        font_layout.addWidget(self.italic_check, 2, 1)

        font_group.setLayout(font_layout)
        layout.addWidget(font_group)

        # Colors group
        colors_group = QGroupBox("Couleurs")
        colors_layout = QGridLayout()

        colors_layout.addWidget(QLabel("Couleur du texte:"), 0, 0)
        self.text_color_btn = QPushButton("Choisir")
        self.text_color_btn.clicked.connect(self.choose_text_color)
        colors_layout.addWidget(self.text_color_btn, 0, 1)

        self.text_color_preview = QLabel("  ")
        self.text_color_preview.setFixedSize(50, 30)
        self.text_color_preview.setStyleSheet("background-color: #FFFFFF; border: 1px solid #555;")
        colors_layout.addWidget(self.text_color_preview, 0, 2)

        colors_layout.addWidget(QLabel("Opacité:"), 1, 0)
        self.alpha_slider = QSlider(Qt.Orientation.Horizontal)
        self.alpha_slider.setRange(0, 100)
        self.alpha_slider.setValue(100)
        self.alpha_slider.valueChanged.connect(self.on_style_changed)
        colors_layout.addWidget(self.alpha_slider, 1, 1, 1, 2)

        colors_group.setLayout(colors_layout)
        layout.addWidget(colors_group)

        # Outline group
        outline_group = QGroupBox("Contour")
        outline_layout = QGridLayout()

        outline_layout.addWidget(QLabel("Épaisseur:"), 0, 0)
        self.outline_width_spin = QSpinBox()
        self.outline_width_spin.setRange(0, 20)
        self.outline_width_spin.setValue(0)
        self.outline_width_spin.setSuffix(" px")
        self.outline_width_spin.valueChanged.connect(self.on_style_changed)
        outline_layout.addWidget(self.outline_width_spin, 0, 1)

        outline_layout.addWidget(QLabel("Couleur:"), 1, 0)
        self.outline_color_btn = QPushButton("Choisir")
        self.outline_color_btn.clicked.connect(self.choose_outline_color)
        outline_layout.addWidget(self.outline_color_btn, 1, 1)

        self.outline_color_preview = QLabel("  ")
        self.outline_color_preview.setFixedSize(50, 30)
        self.outline_color_preview.setStyleSheet("background-color: #000000; border: 1px solid #555;")
        outline_layout.addWidget(self.outline_color_preview, 1, 2)

        outline_group.setLayout(outline_layout)
        layout.addWidget(outline_group)

        # Background group
        bg_group = QGroupBox("Fond")
        bg_layout = QGridLayout()

        self.bg_enabled_check = QCheckBox("Activer le fond")
        self.bg_enabled_check.stateChanged.connect(self.on_background_toggled)
        bg_layout.addWidget(self.bg_enabled_check, 0, 0, 1, 3)

        bg_layout.addWidget(QLabel("Couleur:"), 1, 0)
        self.bg_color_btn = QPushButton("Choisir")
        self.bg_color_btn.clicked.connect(self.choose_bg_color)
        self.bg_color_btn.setEnabled(False)
        bg_layout.addWidget(self.bg_color_btn, 1, 1)

        self.bg_color_preview = QLabel("  ")
        self.bg_color_preview.setFixedSize(50, 30)
        self.bg_color_preview.setStyleSheet("background-color: #000000; border: 1px solid #555;")
        bg_layout.addWidget(self.bg_color_preview, 1, 2)

        bg_layout.addWidget(QLabel("Opacité:"), 2, 0)
        self.bg_alpha_slider = QSlider(Qt.Orientation.Horizontal)
        self.bg_alpha_slider.setRange(0, 100)
        self.bg_alpha_slider.setValue(80)
        self.bg_alpha_slider.setEnabled(False)
        self.bg_alpha_slider.valueChanged.connect(self.on_style_changed)
        bg_layout.addWidget(self.bg_alpha_slider, 2, 1, 1, 2)

        bg_group.setLayout(bg_layout)
        layout.addWidget(bg_group)

        layout.addStretch()

        return widget

    def _create_position_tab(self) -> QWidget:
        """Create position selection tab.

        Returns:
            Widget with position controls
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel("<b>Position du texte sur la vidéo</b>"))

        # Position preset
        self.position_combo = QComboBox()
        for pos in TextPosition:
            self.position_combo.addItem(pos.value.replace('_', ' ').title(), pos)
        self.position_combo.currentIndexChanged.connect(self.on_position_changed)
        layout.addWidget(self.position_combo)

        # Visual position selector (grid of 9 positions)
        position_grid_group = QGroupBox("Sélection Visuelle")
        grid = QGridLayout()

        positions_grid = [
            (TextPosition.TOP_LEFT, 0, 0),
            (TextPosition.TOP, 0, 1),
            (TextPosition.TOP_RIGHT, 0, 2),
            (TextPosition.CUSTOM, 1, 0),  # Left
            (TextPosition.CENTER, 1, 1),
            (TextPosition.CUSTOM, 1, 2),  # Right
            (TextPosition.BOTTOM_LEFT, 2, 0),
            (TextPosition.BOTTOM, 2, 1),
            (TextPosition.BOTTOM_RIGHT, 2, 2),
        ]

        for pos, row, col in positions_grid:
            btn = QPushButton("")
            btn.setFixedSize(60, 60)
            btn.setProperty("position", pos)
            btn.clicked.connect(lambda checked, p=pos: self.set_position_from_grid(p))
            grid.addWidget(btn, row, col)

        position_grid_group.setLayout(grid)
        layout.addWidget(position_grid_group)

        # Custom position (if needed)
        custom_group = QGroupBox("Position Personnalisée")
        custom_layout = QGridLayout()

        custom_layout.addWidget(QLabel("X:"), 0, 0)
        self.custom_x_spin = QSpinBox()
        self.custom_x_spin.setRange(0, self.video_info['width'])
        self.custom_x_spin.setValue(0)
        self.custom_x_spin.setEnabled(False)
        custom_layout.addWidget(self.custom_x_spin, 0, 1)

        custom_layout.addWidget(QLabel("Y:"), 1, 0)
        self.custom_y_spin = QSpinBox()
        self.custom_y_spin.setRange(0, self.video_info['height'])
        self.custom_y_spin.setValue(0)
        self.custom_y_spin.setEnabled(False)
        custom_layout.addWidget(self.custom_y_spin, 1, 1)

        custom_group.setLayout(custom_layout)
        layout.addWidget(custom_group)

        # Text alignment
        align_group = QGroupBox("Alignement du Texte")
        align_layout = QHBoxLayout()

        self.align_combo = QComboBox()
        for align in TextAlignment:
            self.align_combo.addItem(align.value.title(), align)
        self.align_combo.currentIndexChanged.connect(self.on_style_changed)
        align_layout.addWidget(self.align_combo)

        align_group.setLayout(align_layout)
        layout.addWidget(align_group)

        layout.addStretch()

        return widget

    def _create_animation_tab(self) -> QWidget:
        """Create animation configuration tab.

        Returns:
            Widget with animation controls
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel("<b>Animation du texte</b>"))

        # Animation type
        layout.addWidget(QLabel("Type d'animation:"))
        self.animation_combo = QComboBox()
        for anim in AnimationType:
            self.animation_combo.addItem(anim.value.replace('_', ' ').title(), anim)
        self.animation_combo.currentIndexChanged.connect(self.on_animation_changed)
        layout.addWidget(self.animation_combo)

        # Animation duration
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Durée:"))

        self.anim_duration_spin = QDoubleSpinBox()
        self.anim_duration_spin.setRange(0.1, 5.0)
        self.anim_duration_spin.setValue(1.0)
        self.anim_duration_spin.setSingleStep(0.1)
        self.anim_duration_spin.setSuffix(" s")
        duration_layout.addWidget(self.anim_duration_spin)
        duration_layout.addStretch()

        layout.addLayout(duration_layout)

        # Animation descriptions
        anim_desc = QLabel()
        anim_desc.setWordWrap(True)
        anim_desc.setText(self._get_animation_description(AnimationType.NONE))
        anim_desc.setStyleSheet("padding: 10px; background-color: #2a2a2a; border-radius: 4px;")
        layout.addWidget(anim_desc)
        self.anim_desc_label = anim_desc

        layout.addStretch()

        return widget

    def on_template_selected(self, item: QListWidgetItem):
        """Handle template selection.

        Args:
            item: Selected list item
        """
        template_name = item.data(Qt.ItemDataRole.UserRole)
        if not template_name:
            return

        # Get template description
        desc = TextTemplates.get_template_description(template_name)
        self.template_desc.setText(f"<b>{template_name}</b><br>{desc}")

        # Apply template (basic implementation - create from template)
        templates = TextTemplates.get_all_templates()
        if template_name in templates:
            # For now, just show that template is selected
            # Full implementation would create the template overlay
            self.template_desc.setText(
                f"<b>{template_name}</b><br>{desc}<br>"
                f"<i>Modifiez les autres onglets pour personnaliser.</i>"
            )

    def on_text_changed(self):
        """Handle text content changes."""
        self.update_preview()

    def on_style_changed(self):
        """Handle style changes."""
        self.update_preview()

    def on_position_changed(self):
        """Handle position changes."""
        pos = self.position_combo.currentData()
        is_custom = (pos == TextPosition.CUSTOM)
        self.custom_x_spin.setEnabled(is_custom)
        self.custom_y_spin.setEnabled(is_custom)
        self.update_preview()

    def on_animation_changed(self):
        """Handle animation type changes."""
        anim_type = self.animation_combo.currentData()
        desc = self._get_animation_description(anim_type)
        self.anim_desc_label.setText(desc)

    def on_background_toggled(self, state):
        """Handle background toggle.

        Args:
            state: Checkbox state
        """
        enabled = (state == Qt.CheckState.Checked.value)
        self.bg_color_btn.setEnabled(enabled)
        self.bg_alpha_slider.setEnabled(enabled)
        self.on_style_changed()

    def set_position_from_grid(self, position: TextPosition):
        """Set position from grid button.

        Args:
            position: Selected position
        """
        for i in range(self.position_combo.count()):
            if self.position_combo.itemData(i) == position:
                self.position_combo.setCurrentIndex(i)
                break

    def choose_text_color(self):
        """Open color picker for text color."""
        color = QColorDialog.getColor()
        if color.isValid():
            self.text_color_preview.setStyleSheet(
                f"background-color: {color.name()}; border: 1px solid #555;"
            )
            self.on_style_changed()

    def choose_outline_color(self):
        """Open color picker for outline color."""
        color = QColorDialog.getColor()
        if color.isValid():
            self.outline_color_preview.setStyleSheet(
                f"background-color: {color.name()}; border: 1px solid #555;"
            )
            self.on_style_changed()

    def choose_bg_color(self):
        """Open color picker for background color."""
        color = QColorDialog.getColor()
        if color.isValid():
            self.bg_color_preview.setStyleSheet(
                f"background-color: {color.name()}; border: 1px solid #555;"
            )
            self.on_style_changed()

    def update_duration_label(self):
        """Update duration label with calculated duration."""
        start = self.start_frame_spin.value()
        end = self.end_frame_spin.value()
        duration_frames = max(0, end - start)
        duration_seconds = duration_frames / self.video_info['fps']

        self.duration_label.setText(
            f"Durée: {duration_frames} frames ({duration_seconds:.2f}s)"
        )

    def update_preview(self):
        """Update the live preview."""
        # Get current text
        text = self.text_edit.toPlainText() or "Sample Text"

        # Build preview style
        font_family = self.font_combo.currentText()
        font_size = self.font_size_spin.value()
        is_bold = self.bold_check.isChecked()
        is_italic = self.italic_check.isChecked()

        # Get colors from preview widgets
        text_color = self.text_color_preview.styleSheet().split("background-color: ")[1].split(";")[0]

        # Build Qt stylesheet for preview
        font_weight = "bold" if is_bold else "normal"
        font_style = "italic" if is_italic else "normal"

        style = f"""
            QLabel {{
                background-color: #1a1a1a;
                color: {text_color};
                border: 2px solid #555;
                border-radius: 4px;
                padding: 20px;
                font-family: {font_family};
                font-size: {font_size}pt;
                font-weight: {font_weight};
                font-style: {font_style};
            }}
        """

        self.preview_label.setStyleSheet(style)
        self.preview_label.setText(text)

    def _get_animation_description(self, anim_type: AnimationType) -> str:
        """Get description for animation type.

        Args:
            anim_type: Animation type

        Returns:
            Description string
        """
        descriptions = {
            AnimationType.NONE: "Pas d'animation - le texte apparaît directement",
            AnimationType.FADE_IN: "Fondu d'entrée - le texte apparaît progressivement",
            AnimationType.FADE_OUT: "Fondu de sortie - le texte disparaît progressivement",
            AnimationType.FADE_IN_OUT: "Fondu entrée/sortie - transitions douces",
            AnimationType.SLIDE_IN_LEFT: "Glisse depuis la gauche",
            AnimationType.SLIDE_IN_RIGHT: "Glisse depuis la droite",
            AnimationType.SLIDE_IN_TOP: "Glisse depuis le haut",
            AnimationType.SLIDE_IN_BOTTOM: "Glisse depuis le bas",
            AnimationType.ZOOM_IN: "Zoom avant - le texte grandit",
            AnimationType.ZOOM_OUT: "Zoom arrière - le texte rétrécit",
        }
        return descriptions.get(anim_type, "Animation personnalisée")

    def load_overlay_data(self):
        """Load data from existing overlay."""
        if not self.existing_overlay:
            return

        overlay = self.existing_overlay

        # Load text
        self.text_edit.setPlainText(overlay.text)

        # Load timing
        self.start_frame_spin.setValue(overlay.start_frame)
        if overlay.end_frame:
            self.end_frame_spin.setValue(overlay.end_frame)

        # Load style
        style = overlay.style
        self.font_combo.setCurrentText(style.font_family)
        self.font_size_spin.setValue(style.font_size)
        self.bold_check.setChecked(style.bold)
        self.italic_check.setChecked(style.italic)
        self.alpha_slider.setValue(int(style.alpha * 100))

        # Load colors
        self.text_color_preview.setStyleSheet(f"background-color: {style.color}; border: 1px solid #555;")
        self.outline_color_preview.setStyleSheet(f"background-color: {style.outline_color}; border: 1px solid #555;")
        self.outline_width_spin.setValue(style.outline_width)

        # Load background
        if style.background_color:
            self.bg_enabled_check.setChecked(True)
            self.bg_color_preview.setStyleSheet(f"background-color: {style.background_color}; border: 1px solid #555;")
            self.bg_alpha_slider.setValue(int(style.background_alpha * 100))

        # Load position
        for i in range(self.position_combo.count()):
            if self.position_combo.itemData(i) == overlay.position:
                self.position_combo.setCurrentIndex(i)
                break

        if overlay.custom_position:
            self.custom_x_spin.setValue(overlay.custom_position[0])
            self.custom_y_spin.setValue(overlay.custom_position[1])

        # Load alignment
        for i in range(self.align_combo.count()):
            if self.align_combo.itemData(i) == style.alignment:
                self.align_combo.setCurrentIndex(i)
                break

        # Load animation
        for i in range(self.animation_combo.count()):
            if self.animation_combo.itemData(i) == overlay.animation:
                self.animation_combo.setCurrentIndex(i)
                break
        self.anim_duration_spin.setValue(overlay.animation_duration)

        self.update_preview()

    def create_overlay(self):
        """Create/update text overlay from current settings."""
        # Build style
        text_color = self.text_color_preview.styleSheet().split("background-color: ")[1].split(";")[0]
        outline_color = self.outline_color_preview.styleSheet().split("background-color: ")[1].split(";")[0]

        bg_color = None
        if self.bg_enabled_check.isChecked():
            bg_color = self.bg_color_preview.styleSheet().split("background-color: ")[1].split(";")[0]

        style = TextStyle(
            font_family=self.font_combo.currentText(),
            font_size=self.font_size_spin.value(),
            color=text_color,
            alpha=self.alpha_slider.value() / 100.0,
            bold=self.bold_check.isChecked(),
            italic=self.italic_check.isChecked(),
            outline_width=self.outline_width_spin.value(),
            outline_color=outline_color,
            background_color=bg_color,
            background_alpha=self.bg_alpha_slider.value() / 100.0,
            alignment=self.align_combo.currentData()
        )

        # Build overlay
        position = self.position_combo.currentData()
        custom_pos = None
        if position == TextPosition.CUSTOM:
            custom_pos = (self.custom_x_spin.value(), self.custom_y_spin.value())

        overlay = TextOverlay(
            text=self.text_edit.toPlainText(),
            style=style,
            position=position,
            custom_position=custom_pos,
            start_frame=self.start_frame_spin.value(),
            end_frame=self.end_frame_spin.value(),
            animation=self.animation_combo.currentData(),
            animation_duration=self.anim_duration_spin.value(),
            name=f"Text: {self.text_edit.toPlainText()[:20]}..."
        )

        self.text_overlay_created.emit(overlay)
        self.accept()
