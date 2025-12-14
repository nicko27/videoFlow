"""
Pipeline Configuration Widget

Widget for configuring the verification pipeline with reorderable methods.
Includes PipelineConfigDialog for modal popup configuration.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QListWidget,
    QPushButton, QLabel, QCheckBox, QDoubleSpinBox, QSpinBox,
    QComboBox, QListWidgetItem, QGridLayout, QFrame, QDialog, QLineEdit,
    QScrollArea, QDialogButtonBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSettings
from PyQt6.QtGui import QFont
import json

# Import method definitions from pipeline
from ..verification import VerificationPipeline


class PipelineMethodItem(QWidget):
    """Widget for a single pipeline method with enable/disable and parameters."""

    toggled = pyqtSignal(bool)  # Emitted when method is enabled/disabled
    parameters_changed = pyqtSignal(dict)  # Emitted when parameters change
    weight_changed = pyqtSignal(float)  # Emitted when weight changes

    def __init__(self, method_name: str, display_name: str, default_params: dict, weight: float = 1.0, method_info: dict = None, parent=None):
        super().__init__(parent)
        self.method_name = method_name
        self.display_name = display_name
        self.parameters = default_params.copy()
        self.weight = weight
        self.method_info = method_info or {}

        self._init_ui()

    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        intro = QLabel(
            "🧭 Construis ton pipeline en quelques clics :\n"
            "1) Active ou désactive les étapes (cases à cocher).\n"
            "2) Le poids = importance de l’étape dans le calcul final (1 = normal).\n"
            "3) Les réglages ont des explications simples juste en dessous.\n"
            "Mode Filtrage = passe/échoue étape par étape. Mode Pondération = moyenne pondérée des scores. Hybride = les deux."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("""
            QLabel {
                background: #F1F3F5;
                border-radius: 6px;
                padding: 8px;
                color: #343A40;
                font-size: 11px;
            }
        """)
        layout.addWidget(intro)

        # Header with checkbox, method name, and weight
        header_layout = QHBoxLayout()

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(True)
        self.checkbox.toggled.connect(self.toggled.emit)

        name_label = QLabel(self.display_name)
        name_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))

        header_layout.addWidget(self.checkbox)
        header_layout.addWidget(name_label)
        header_layout.addStretch()

        # Weight control
        weight_label = QLabel("Poids:")
        weight_label.setStyleSheet("QLabel { color: #6C757D; font-size: 9px; }")
        self.weight_label = weight_label

        self.weight_spin = QDoubleSpinBox()
        self.weight_spin.setRange(0.1, 10.0)
        self.weight_spin.setValue(self.weight)
        self.weight_spin.setSingleStep(0.1)
        self.weight_spin.setDecimals(1)
        self.weight_spin.setMaximumWidth(60)
        self.weight_spin.setToolTip(
            "Poids de cette méthode pour le calcul du score pondéré\n"
            "(utilisé en mode Pondération et Hybride)\n"
            "1.0 = poids normal, 2.0 = double importance, 0.5 = demi importance"
        )
        self.weight_spin.valueChanged.connect(self._on_weight_changed)

        header_layout.addWidget(weight_label)
        header_layout.addWidget(self.weight_spin)

        layout.addLayout(header_layout)

        # Algorithm explanation
        if self.method_info.get('detailed_explanation'):
            explanation_label = QLabel(f"ℹ️ {self.method_info['detailed_explanation']}")
            explanation_label.setWordWrap(True)
            explanation_label.setStyleSheet("""
                QLabel {
                    background-color: #F8F9FA;
                    color: #495057;
                    padding: 6px;
                    font-size: 9px;
                    border-left: 3px solid #6C757D;
                    margin-left: 20px;
                }
            """)
            layout.addWidget(explanation_label)

            # Speed and use case info
            if self.method_info.get('speed') and self.method_info.get('use_case'):
                info_label = QLabel(f"⚡ Vitesse: {self.method_info['speed']} | 🎯 Usage: {self.method_info['use_case']}")
                info_label.setStyleSheet("""
                    QLabel {
                        color: #6C757D;
                        font-size: 8px;
                        padding: 2px 6px;
                        margin-left: 20px;
                    }
                """)
                layout.addWidget(info_label)

        # Parameters container (collapsible)
        self.params_widget = QWidget()
        params_layout = QGridLayout(self.params_widget)
        params_layout.setContentsMargins(20, 0, 0, 0)
        params_layout.setSpacing(5)

        self._create_parameters(params_layout)

        layout.addWidget(self.params_widget)
        self.params_widget.setVisible(True)  # Always visible for now

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("QFrame { background-color: #DEE2E6; }")
        layout.addWidget(separator)

    def _create_parameters(self, layout):
        """Create parameter widgets based on method."""
        row = 0

        if self.method_name == 'color_histogram':
            layout.addWidget(QLabel("Seuil:"), row, 0)
            self.threshold_spin = QDoubleSpinBox()
            self.threshold_spin.setRange(50.0, 99.0)
            self.threshold_spin.setValue(self.parameters.get('threshold', 85.0))
            self.threshold_spin.setSuffix(" %")
            self.threshold_spin.setToolTip(
                "Seuil de similarité des couleurs (50-99%)\n\n"
                "• Détermine à quel point les distributions de couleurs doivent être similaires\n"
                "• Valeur haute (>85%): Plus strict, moins de faux positifs\n"
                "• Valeur basse (<75%): Plus permissif, détecte plus de variations\n"
                "• Recommandé: 85% pour un bon équilibre précision/rappel"
            )
            self.threshold_spin.valueChanged.connect(lambda v: self._update_param('threshold', v))
            layout.addWidget(self.threshold_spin, row, 1)

        elif self.method_name == 'edge_pattern':
            layout.addWidget(QLabel("Seuil:"), row, 0)
            self.threshold_spin = QDoubleSpinBox()
            self.threshold_spin.setRange(50.0, 99.0)
            self.threshold_spin.setValue(self.parameters.get('threshold', 80.0))
            self.threshold_spin.setSuffix(" %")
            self.threshold_spin.setToolTip(
                "Seuil de similarité des contours (50-99%)\n\n"
                "• Compare les motifs de contours détectés par Canny\n"
                "• Valeur haute (>85%): Contours doivent être très similaires\n"
                "• Valeur basse (<75%): Tolère plus de différences dans les contours\n"
                "• Recommandé: 80% - bon pour détecter même avec variations mineures"
            )
            self.threshold_spin.valueChanged.connect(lambda v: self._update_param('threshold', v))
            layout.addWidget(self.threshold_spin, row, 1)

            row += 1
            layout.addWidget(QLabel("Canny Low:"), row, 0)
            self.canny_low_spin = QSpinBox()
            self.canny_low_spin.setRange(10, 200)
            self.canny_low_spin.setValue(self.parameters.get('canny_low', 50))
            self.canny_low_spin.setToolTip(
                "Seuil bas pour la détection de contours Canny (10-200)\n\n"
                "• Gradient minimum pour commencer à tracer un contour\n"
                "• Valeur basse (30-40): Détecte plus de contours faibles\n"
                "• Valeur haute (60-80): Ne garde que les contours nets\n"
                "• Recommandé: 50 - équilibre entre détection et bruit\n"
                "• Doit être < Canny High (ratio typique: 1:2 ou 1:3)"
            )
            self.canny_low_spin.valueChanged.connect(lambda v: self._update_param('canny_low', v))
            layout.addWidget(self.canny_low_spin, row, 1)

            row += 1
            layout.addWidget(QLabel("Canny High:"), row, 0)
            self.canny_high_spin = QSpinBox()
            self.canny_high_spin.setRange(50, 300)
            self.canny_high_spin.setValue(self.parameters.get('canny_high', 150))
            self.canny_high_spin.setToolTip(
                "Seuil haut pour la détection de contours Canny (50-300)\n\n"
                "• Gradient minimum pour marquer un contour comme fort\n"
                "• Valeur basse (100-120): Plus de contours acceptés\n"
                "• Valeur haute (180-220): Seulement les contours très nets\n"
                "• Recommandé: 150 - contours bien définis sans être trop strict\n"
                "• Doit être > Canny Low (ratio typique: 2:1 ou 3:1)"
            )
            self.canny_high_spin.valueChanged.connect(lambda v: self._update_param('canny_high', v))
            layout.addWidget(self.canny_high_spin, row, 1)

        elif self.method_name == 'motion_analysis':
            layout.addWidget(QLabel("Seuil corrélation:"), row, 0)
            self.correlation_spin = QDoubleSpinBox()
            self.correlation_spin.setRange(50.0, 99.0)
            self.correlation_spin.setValue(self.parameters.get('correlation_threshold', 85.0))
            self.correlation_spin.setSuffix(" %")
            self.correlation_spin.setToolTip(
                "Seuil de corrélation des vecteurs de mouvement (50-99%)\n\n"
                "• Compare les patterns de mouvement optique entre vidéos\n"
                "• Valeur haute (>90%): Mouvements doivent être quasi identiques\n"
                "• Valeur basse (<80%): Tolère des variations de cadrage/vitesse\n"
                "• Recommandé: 85% - détecte contenus similaires même réencodés\n"
                "• Efficace pour détecter duplicatas avec zooms ou recadrages mineurs"
            )
            self.correlation_spin.valueChanged.connect(lambda v: self._update_param('correlation_threshold', v))
            layout.addWidget(self.correlation_spin, row, 1)

            row += 1
            layout.addWidget(QLabel("Intervalle (s):"), row, 0)
            self.interval_spin = QSpinBox()
            self.interval_spin.setRange(1, 10)
            self.interval_spin.setValue(self.parameters.get('sample_interval', 3))
            self.interval_spin.setToolTip(
                "Intervalle entre les échantillons de frames (1-10 secondes)\n\n"
                "• Détermine la fréquence d'analyse du mouvement\n"
                "• Valeur basse (1-2s): Plus précis, détecte changements rapides\n"
                "• Valeur haute (5-8s): Plus rapide, bon pour mouvement uniforme\n"
                "• Recommandé: 3s - bon équilibre vitesse/précision\n"
                "• Impact: valeur haute = traitement plus rapide mais moins précis"
            )
            self.interval_spin.valueChanged.connect(lambda v: self._update_param('sample_interval', v))
            layout.addWidget(self.interval_spin, row, 1)

            row += 1
            layout.addWidget(QLabel("Pas de recherche (s):"), row, 0)
            self.motion_step_spin = QDoubleSpinBox()
            self.motion_step_spin.setRange(0.5, 15.0)
            self.motion_step_spin.setSingleStep(0.5)
            self.motion_step_spin.setValue(self.parameters.get('search_step', 3.0))
            self.motion_step_spin.setToolTip("Décalage de la fenêtre glissante dans la longue vidéo.")
            self.motion_step_spin.valueChanged.connect(lambda v: self._update_param('search_step', v))
            layout.addWidget(self.motion_step_spin, row, 1)

            row += 1
            layout.addWidget(QLabel("Fenêtres max:"), row, 0)
            self.motion_max_win = QSpinBox()
            self.motion_max_win.setRange(20, 2000)
            self.motion_max_win.setValue(self.parameters.get('max_windows', 200))
            self.motion_max_win.setToolTip("Limite de fenêtres testées pour vidéos longues.")
            self.motion_max_win.valueChanged.connect(lambda v: self._update_param('max_windows', v))
            layout.addWidget(self.motion_max_win, row, 1)

        elif self.method_name == 'dct_coefficients':
            layout.addWidget(QLabel("Seuil:"), row, 0)
            self.threshold_spin = QDoubleSpinBox()
            self.threshold_spin.setRange(50.0, 99.0)
            self.threshold_spin.setValue(self.parameters.get('threshold', 75.0))
            self.threshold_spin.setSuffix(" %")
            self.threshold_spin.setToolTip(
                "Seuil de similarité des coefficients DCT (50-99%)\n\n"
                "• Compare les coefficients de transformation cosinus discrète\n"
                "• Capture l'essence fréquentielle de l'image (robuste au bruit)\n"
                "• Valeur haute (>85%): Fréquences doivent être très proches\n"
                "• Valeur basse (<70%): Tolère plus de variations d'encodage\n"
                "• Recommandé: 75% - excellent pour détecter réencodages"
            )
            self.threshold_spin.valueChanged.connect(lambda v: self._update_param('threshold', v))
            layout.addWidget(self.threshold_spin, row, 1)

            row += 1
            layout.addWidget(QLabel("Coefficients:"), row, 0)
            self.coeffs_spin = QSpinBox()
            self.coeffs_spin.setRange(5, 30)
            self.coeffs_spin.setValue(self.parameters.get('num_coeffs', 15))
            self.coeffs_spin.setToolTip(
                "Nombre de coefficients DCT à comparer (5-30)\n\n"
                "💡 POURQUOI DES COEFFICIENTS?\n"
                "La DCT décompose l'image en fréquences (comme un prisme décompose la lumière):\n"
                "• Premiers coeffs = grandes structures (formes, composition globale)\n"
                "• Coeffs suivants = détails moyens (textures, motifs)\n"
                "• Derniers coeffs = détails fins (bruit, grain)\n\n"
                "📊 PARAMÈTRE:\n"
                "• Valeur basse (5-10): Compare uniquement composition globale - RAPIDE\n"
                "• Valeur haute (20-30): Compare jusqu'aux détails fins - PRÉCIS mais LENT\n"
                "• Recommandé: 15 - capture l'essentiel sans le bruit\n\n"
                "🎯 UTILITÉ: Les coefficients DCT sont robustes au réencodage vidéo\n"
                "(car les codecs JPEG/H.264 utilisent aussi la DCT!)"
            )
            self.coeffs_spin.valueChanged.connect(lambda v: self._update_param('num_coeffs', v))
            layout.addWidget(self.coeffs_spin, row, 1)

            row += 1
            layout.addWidget(QLabel("Pas de recherche (s):"), row, 0)
            self.search_step_spin = QDoubleSpinBox()
            self.search_step_spin.setRange(0.5, 15.0)
            self.search_step_spin.setSingleStep(0.5)
            self.search_step_spin.setValue(self.parameters.get('search_step', 3.0))
            self.search_step_spin.setToolTip(
                "Pas de la fenêtre glissante dans la longue vidéo.\n"
                "Petit pas = plus précis mais plus lent. Grand pas = plus rapide mais peut rater un alignement fin."
            )
            self.search_step_spin.valueChanged.connect(lambda v: self._update_param('search_step', v))
            layout.addWidget(self.search_step_spin, row, 1)

            row += 1
            layout.addWidget(QLabel("Fenêtres max:"), row, 0)
            self.max_windows_spin = QSpinBox()
            self.max_windows_spin.setRange(20, 2000)
            self.max_windows_spin.setValue(self.parameters.get('max_windows', 200))
            self.max_windows_spin.setToolTip(
                "Limite le nombre de fenêtres testées dans la longue vidéo.\n"
                "Réduit le temps de calcul sur des vidéos très longues."
            )
            self.max_windows_spin.valueChanged.connect(lambda v: self._update_param('max_windows', v))
            layout.addWidget(self.max_windows_spin, row, 1)

            row += 1
            layout.addWidget(QLabel("Timeout (s):"), row, 0)
            self.dct_timeout_spin = QSpinBox()
            self.dct_timeout_spin.setRange(30, 3600)
            self.dct_timeout_spin.setValue(int(self.parameters.get('timeout_seconds', 600)))
            self.dct_timeout_spin.setToolTip("Temps max pour la comparaison DCT (évite les blocages).")
            self.dct_timeout_spin.valueChanged.connect(lambda v: self._update_param('timeout_seconds', v))
            layout.addWidget(self.dct_timeout_spin, row, 1)

        elif self.method_name == 'ssim':
            layout.addWidget(QLabel("Seuil SSIM:"), row, 0)
            self.ssim_spin = QDoubleSpinBox()
            self.ssim_spin.setRange(0.5, 0.99)
            self.ssim_spin.setValue(self.parameters.get('threshold', 0.85))
            self.ssim_spin.setSingleStep(0.05)
            self.ssim_spin.setToolTip(
                "Seuil de l'indice de similarité structurelle (0.5-0.99)\n\n"
                "• Mesure perceptuelle: compare luminance, contraste, structure\n"
                "• Simule la perception visuelle humaine\n"
                "• Valeur haute (>0.90): Images doivent être quasi identiques\n"
                "• Valeur basse (<0.80): Tolère plus de variations visuelles\n"
                "• Recommandé: 0.85 - correspond bien à la perception humaine\n"
                "• Très précis mais plus lent (analyse pixel par pixel)"
            )
            self.ssim_spin.valueChanged.connect(lambda v: self._update_param('threshold', v))
            layout.addWidget(self.ssim_spin, row, 1)

            row += 1
            layout.addWidget(QLabel("Pas de recherche (s):"), row, 0)
            self.ssim_step_spin = QDoubleSpinBox()
            self.ssim_step_spin.setRange(0.5, 15.0)
            self.ssim_step_spin.setSingleStep(0.5)
            self.ssim_step_spin.setValue(self.parameters.get('search_step', 3.0))
            self.ssim_step_spin.setToolTip("Fenêtre glissante dans la longue vidéo (plus petit = plus précis).")
            self.ssim_step_spin.valueChanged.connect(lambda v: self._update_param('search_step', v))
            layout.addWidget(self.ssim_step_spin, row, 1)

            row += 1
            layout.addWidget(QLabel("Fenêtres max:"), row, 0)
            self.ssim_max_win = QSpinBox()
            self.ssim_max_win.setRange(20, 2000)
            self.ssim_max_win.setValue(self.parameters.get('max_windows', 200))
            self.ssim_max_win.setToolTip("Limite le nombre de positions testées dans la longue vidéo.")
            self.ssim_max_win.valueChanged.connect(lambda v: self._update_param('max_windows', v))
            layout.addWidget(self.ssim_max_win, row, 1)

        elif self.method_name == 'feature_matching':
            layout.addWidget(QLabel("Détecteur:"), row, 0)
            self.detector_combo = QComboBox()
            self.detector_combo.addItems(['ORB', 'AKAZE', 'SIFT'])
            self.detector_combo.setCurrentText(self.parameters.get('detector', 'ORB'))
            self.detector_combo.setToolTip(
                "Algorithme de détection de points clés\n\n"
                "• ORB: Rapide, orienté temps-réel, bon pour duplicatas exacts\n"
                "  - Vitesse: Très rapide\n"
                "  - Robustesse: Moyenne (sensible aux grandes transformations)\n\n"
                "• AKAZE: Équilibre vitesse/qualité, bon pour variations modérées\n"
                "  - Vitesse: Moyenne\n"
                "  - Robustesse: Bonne (tolère rotations et échelle)\n\n"
                "• SIFT: Très précis mais lent, meilleur pour transformations complexes\n"
                "  - Vitesse: Lent\n"
                "  - Robustesse: Excellente (invariant rotation, échelle, lumière)\n\n"
                "Recommandé: ORB pour vitesse, SIFT pour précision maximale"
            )
            self.detector_combo.currentTextChanged.connect(lambda v: self._update_param('detector', v))
            layout.addWidget(self.detector_combo, row, 1)

            row += 1
            layout.addWidget(QLabel("Seuil:"), row, 0)
            self.threshold_spin = QDoubleSpinBox()
            self.threshold_spin.setRange(50.0, 99.0)
            self.threshold_spin.setValue(self.parameters.get('threshold', 70.0))
            self.threshold_spin.setSuffix(" %")
            self.threshold_spin.setToolTip(
                "Seuil de correspondance des points clés (50-99%)\n\n"
                "• Pourcentage de features qui doivent correspondre\n"
                "• Valeur haute (>80%): Nombreux points communs requis\n"
                "• Valeur basse (<65%): Tolère plus de différences de cadrage\n"
                "• Recommandé: 70% - robuste aux recadrages et zooms\n"
                "• Idéal pour détecter duplicatas avec transformations géométriques"
            )
            self.threshold_spin.valueChanged.connect(lambda v: self._update_param('threshold', v))
            layout.addWidget(self.threshold_spin, row, 1)

            row += 1
            layout.addWidget(QLabel("Pas de recherche (s):"), row, 0)
            self.feature_step_spin = QDoubleSpinBox()
            self.feature_step_spin.setRange(0.5, 15.0)
            self.feature_step_spin.setSingleStep(0.5)
            self.feature_step_spin.setValue(self.parameters.get('search_step', 3.0))
            self.feature_step_spin.setToolTip("Fenêtre glissante dans la longue vidéo pour aligner les frames.")
            self.feature_step_spin.valueChanged.connect(lambda v: self._update_param('search_step', v))
            layout.addWidget(self.feature_step_spin, row, 1)

            row += 1
            layout.addWidget(QLabel("Fenêtres max:"), row, 0)
            self.feature_max_win = QSpinBox()
            self.feature_max_win.setRange(20, 2000)
            self.feature_max_win.setValue(self.parameters.get('max_windows', 100))
            self.feature_max_win.setToolTip("Limite du nombre de positions testées dans la longue vidéo.")
            self.feature_max_win.valueChanged.connect(lambda v: self._update_param('max_windows', v))
            layout.addWidget(self.feature_max_win, row, 1)

        elif self.method_name == 'optical_flow':
            layout.addWidget(QLabel("Seuil flux (%):"), row, 0)
            self.optflow_threshold = QDoubleSpinBox()
            self.optflow_threshold.setRange(50.0, 99.0)
            self.optflow_threshold.setValue(self.parameters.get('threshold', 70.0))
            self.optflow_threshold.setSuffix(" %")
            self.optflow_threshold.setToolTip(
                "Seuil de similarité du flux optique (50-99%). Plus haut = mouvements quasi identiques."
            )
            self.optflow_threshold.valueChanged.connect(lambda v: self._update_param('threshold', v))
            layout.addWidget(self.optflow_threshold, row, 1)

            row += 1
            layout.addWidget(QLabel("Frames max:"), row, 0)
            self.optflow_max_frames = QSpinBox()
            self.optflow_max_frames.setRange(5, 200)
            self.optflow_max_frames.setValue(self.parameters.get('max_frames', 30))
            self.optflow_max_frames.setToolTip("Nombre de frames échantillonnées pour calculer le flux.")
            self.optflow_max_frames.valueChanged.connect(lambda v: self._update_param('max_frames', v))
            layout.addWidget(self.optflow_max_frames, row, 1)

            row += 1
            layout.addWidget(QLabel("Pas entre frames:"), row, 0)
            self.optflow_frame_step = QSpinBox()
            self.optflow_frame_step.setRange(1, 20)
            self.optflow_frame_step.setValue(self.parameters.get('frame_step', 3))
            self.optflow_frame_step.setToolTip("Chaque N-ième frame est utilisée pour le flux optique.")
            self.optflow_frame_step.valueChanged.connect(lambda v: self._update_param('frame_step', v))
            layout.addWidget(self.optflow_frame_step, row, 1)

            row += 1
            layout.addWidget(QLabel("Variance mini:"), row, 0)
            self.optflow_min_var = QDoubleSpinBox()
            self.optflow_min_var.setRange(0.0, 5.0)
            self.optflow_min_var.setDecimals(3)
            self.optflow_min_var.setSingleStep(0.05)
            self.optflow_min_var.setValue(self.parameters.get('min_variance', 0.0))
            self.optflow_min_var.setToolTip("Évite les rejets si le mouvement est très faible (caméra fixe).")
            self.optflow_min_var.valueChanged.connect(lambda v: self._update_param('min_variance', v))
            layout.addWidget(self.optflow_min_var, row, 1)

            row += 1
            layout.addWidget(QLabel("Pas de recherche (s):"), row, 0)
            self.optflow_step = QDoubleSpinBox()
            self.optflow_step.setRange(0.5, 15.0)
            self.optflow_step.setSingleStep(0.5)
            self.optflow_step.setValue(self.parameters.get('search_step', 3.0))
            self.optflow_step.setToolTip("Décalage de la fenêtre glissante dans la longue vidéo.")
            self.optflow_step.valueChanged.connect(lambda v: self._update_param('search_step', v))
            layout.addWidget(self.optflow_step, row, 1)

            row += 1
            layout.addWidget(QLabel("Fenêtres max:"), row, 0)
            self.optflow_max_windows = QSpinBox()
            self.optflow_max_windows.setRange(20, 2000)
            self.optflow_max_windows.setValue(self.parameters.get('max_windows', 200))
            self.optflow_max_windows.setToolTip("Limite le nombre de positions testées pour accélérer.")
            self.optflow_max_windows.valueChanged.connect(lambda v: self._update_param('max_windows', v))
            layout.addWidget(self.optflow_max_windows, row, 1)

        elif self.method_name == 'frame_hash':
            layout.addWidget(QLabel("Taille du hash:"), row, 0)
            self.frame_hash_size = QSpinBox()
            self.frame_hash_size.setRange(8, 64)
            self.frame_hash_size.setValue(self.parameters.get('hash_size', 16))
            self.frame_hash_size.setToolTip("Taille du hash moyen (8-64). Plus grand = plus précis mais plus lent.")
            self.frame_hash_size.valueChanged.connect(lambda v: self._update_param('hash_size', v))
            layout.addWidget(self.frame_hash_size, row, 1)

            row += 1
            layout.addWidget(QLabel("Seuil (%):"), row, 0)
            self.frame_hash_threshold = QDoubleSpinBox()
            self.frame_hash_threshold.setRange(50.0, 99.0)
            self.frame_hash_threshold.setValue(self.parameters.get('threshold', 75.0))
            self.frame_hash_threshold.setSuffix(" %")
            self.frame_hash_threshold.setToolTip("Score moyen minimal pour accepter (50-99%).")
            self.frame_hash_threshold.valueChanged.connect(lambda v: self._update_param('threshold', v))
            layout.addWidget(self.frame_hash_threshold, row, 1)

            row += 1
            layout.addWidget(QLabel("Échantillonnage (frames):"), row, 0)
            self.frame_hash_sample = QSpinBox()
            self.frame_hash_sample.setRange(1, 30)
            self.frame_hash_sample.setValue(self.parameters.get('sample_rate', 5))
            self.frame_hash_sample.setToolTip("Un hash toutes les N frames (1 = chaque frame).")
            self.frame_hash_sample.valueChanged.connect(lambda v: self._update_param('sample_rate', v))
            layout.addWidget(self.frame_hash_sample, row, 1)

            row += 1
            layout.addWidget(QLabel("Pas de recherche (s):"), row, 0)
            self.frame_hash_step = QDoubleSpinBox()
            self.frame_hash_step.setRange(0.5, 15.0)
            self.frame_hash_step.setSingleStep(0.5)
            self.frame_hash_step.setValue(self.parameters.get('search_step', 3.0))
            self.frame_hash_step.setToolTip("Fenêtre glissante dans la longue vidéo (plus petit = plus précis).")
            self.frame_hash_step.valueChanged.connect(lambda v: self._update_param('search_step', v))
            layout.addWidget(self.frame_hash_step, row, 1)

            row += 1
            layout.addWidget(QLabel("Fenêtres max:"), row, 0)
            self.frame_hash_max_windows = QSpinBox()
            self.frame_hash_max_windows.setRange(20, 2000)
            self.frame_hash_max_windows.setValue(self.parameters.get('max_windows', 200))
            self.frame_hash_max_windows.setToolTip("Limite le nombre de positions testées (accélère les longues vidéos).")
            self.frame_hash_max_windows.valueChanged.connect(lambda v: self._update_param('max_windows', v))
            layout.addWidget(self.frame_hash_max_windows, row, 1)

        elif self.method_name == 'strategy3':
            layout.addWidget(QLabel("Seuil scènes:"), row, 0)
            self.scene_spin = QDoubleSpinBox()
            self.scene_spin.setRange(10.0, 200.0)
            self.scene_spin.setValue(self.parameters.get('scene_threshold', 50.0))
            self.scene_spin.setSuffix(" Δ")
            self.scene_spin.setToolTip(
                "Détecte les coupures de scènes en mesurant les changements entre frames.\n\n"
                "• Plus haut = nécessite des coupures nettes (moins de faux positifs)\n"
                "• Plus bas = accepte des transitions douces (plus permissif)\n"
                "• Recommandé: 50 par défaut. Monte à 70 si beaucoup de faux positifs, baisse à 40 si clips très doux"
            )
            self.scene_spin.valueChanged.connect(lambda v: self._update_param('scene_threshold', v))
            layout.addWidget(self.scene_spin, row, 1)

            row += 1
            layout.addWidget(QLabel("Seuil DCT:"), row, 0)
            self.dct_spin = QDoubleSpinBox()
            self.dct_spin.setRange(50.0, 99.0)
            self.dct_spin.setValue(self.parameters.get('dct_threshold', 75.0))
            self.dct_spin.setSuffix(" %")
            self.dct_spin.setToolTip(
                "Seuil DCT pour validation frame-par-frame (50-99%)\n\n"
                "• Utilisé dans la phase de validation détaillée\n"
                "• Compare les signatures DCT de frames individuelles\n"
                "• Valeur haute (>85%): Validation très stricte, peu de faux positifs\n"
                "• Valeur basse (<70%): Plus permissif, tolère variations d'encodage\n"
                "• Recommandé: 75% - bon équilibre pour détection robuste\n"
                "• Impact: affecte la précision de la détection finale"
            )
            self.dct_spin.valueChanged.connect(lambda v: self._update_param('dct_threshold', v))
            layout.addWidget(self.dct_spin, row, 1)

            row += 1
            layout.addWidget(QLabel("Seuil séquence:"), row, 0)
            self.seq_spin = QDoubleSpinBox()
            self.seq_spin.setRange(85.0, 99.0)
            self.seq_spin.setValue(self.parameters.get('sequence_threshold', 95.0))
            self.seq_spin.setSuffix(" %")
            self.seq_spin.setToolTip(
                "Seuil global de similarité de séquence (85-99%)\n\n"
                "• Pourcentage minimal de frames similaires pour accepter le match\n"
                "• Validation finale sur toute la séquence détectée\n"
                "• Valeur haute (>95%): Quasi toutes les frames doivent matcher\n"
                "• Valeur basse (<90%): Tolère quelques frames différentes\n"
                "• Recommandé: 95% - assure haute qualité des détections\n"
                "• Impact: seuil de décision final (accept/reject)"
            )
            self.seq_spin.valueChanged.connect(lambda v: self._update_param('sequence_threshold', v))
            layout.addWidget(self.seq_spin, row, 1)

            row += 1
            layout.addWidget(QLabel("Frames DCT:"), row, 0)
            self.samples_spin = QSpinBox()
            self.samples_spin.setRange(3, 30)
            self.samples_spin.setValue(self.parameters.get('num_samples', 10))
            self.samples_spin.setToolTip(
                "Nombre de frames échantillonnées pour la comparaison DCT (3-30).\n\n"
                "• Plus haut = plus précis mais plus lent\n"
                "• Plus bas = plus rapide mais peut rater des différences fines\n"
                "• Recommandé: 10 pour équilibré, 15+ pour validation maximale"
            )
            self.samples_spin.valueChanged.connect(lambda v: self._update_param('num_samples', v))
            layout.addWidget(self.samples_spin, row, 1)

            row += 1
            layout.addWidget(QLabel("Ignorer début (s):"), row, 0)
            self.warmup_spin = QDoubleSpinBox()
            self.warmup_spin.setRange(0.0, 10.0)
            self.warmup_spin.setDecimals(1)
            self.warmup_spin.setSingleStep(0.5)
            self.warmup_spin.setValue(self.parameters.get('warmup_seconds', 0.0))
            self.warmup_spin.setToolTip(
                "Ignore les premières secondes (génériques noirs) avant d'analyser scènes/DCT.\n"
                "Utile si les clips commencent par du noir ou un fondu."
            )
            self.warmup_spin.valueChanged.connect(lambda v: self._update_param('warmup_seconds', v))
            layout.addWidget(self.warmup_spin, row, 1)

            row += 1
            layout.addWidget(QLabel("Workers:"), row, 0)
            self.workers_spin = QSpinBox()
            self.workers_spin.setRange(1, 16)
            self.workers_spin.setValue(self.parameters.get('max_workers', 8))
            self.workers_spin.setToolTip(
                "Nombre de threads de traitement parallèle (1-16)\n\n"
                "• Contrôle le nombre de comparaisons simultanées\n"
                "• Valeur basse (1-4): Moins de charge CPU, plus lent\n"
                "• Valeur haute (12-16): Utilise tous les cœurs, très rapide\n"
                "• Recommandé: 8 - bon équilibre pour la plupart des systèmes\n"
                "• Règle: ne pas dépasser le nombre de cœurs logiques de votre CPU\n"
                "• Impact: vitesse de traitement (linéaire jusqu'au nb de cœurs)"
            )
            self.workers_spin.valueChanged.connect(lambda v: self._update_param('max_workers', v))
            layout.addWidget(self.workers_spin, row, 1)

    def _update_param(self, key, value):
        """Update a parameter and emit signal."""
        self.parameters[key] = value
        self.parameters_changed.emit(self.parameters)

    def is_enabled(self):
        """Check if method is enabled."""
        return self.checkbox.isChecked()

    def set_enabled(self, enabled):
        """Set method enabled state."""
        self.checkbox.setChecked(enabled)

    def get_parameters(self):
        """Get current parameters."""
        return self.parameters.copy()

    def get_weight(self):
        """Get current weight."""
        return self.weight_spin.value()

    def _on_weight_changed(self, value):
        """Called when weight changes."""
        self.weight = value
        self.weight_changed.emit(value)


class PipelineConfigWidget(QWidget):
    """Widget for configuring the verification pipeline."""

    # Use method definitions from VerificationPipeline (with clear French names)
    AVAILABLE_METHODS = VerificationPipeline.AVAILABLE_METHODS

    def __init__(self, parent=None):
        super().__init__(parent)
        self.method_widgets = []
        self.settings = QSettings("DuplicateFinder", "VideoDeduplicator")
        self._init_ui()

        # Load saved configuration or use default
        self.load_saved_config()

        # Update weight visibility based on initial mode
        self._on_mode_changed()

    def _init_ui(self):
        """Initialize the UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # ═══════════════════════════════════════════════════════════
        # MODE SELECTOR
        # ═══════════════════════════════════════════════════════════
        mode_group = QGroupBox("🎛️ Mode de Combinaison")
        mode_layout = QVBoxLayout(mode_group)

        # Mode combo box
        mode_select_layout = QHBoxLayout()
        mode_select_layout.addWidget(QLabel("Mode:"))

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("🔗 Filtrage Séquentiel", "filtering")
        self.mode_combo.addItem("⚖️ Pondération (Score Moyen)", "weighting")
        self.mode_combo.addItem("🎯 Hybride (Seuils + Pondération)", "hybrid")
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)

        mode_select_layout.addWidget(self.mode_combo)
        mode_select_layout.addStretch()
        mode_layout.addLayout(mode_select_layout)

        # Mode explanation
        self.mode_explanation = QLabel()
        self.mode_explanation.setWordWrap(True)
        self.mode_explanation.setStyleSheet("""
            QLabel {
                background-color: #E3F2FD;
                border-left: 4px solid #2196F3;
                padding: 8px;
                font-size: 10px;
                color: #1565C0;
            }
        """)
        mode_layout.addWidget(self.mode_explanation)

        # Seuil global (pondération/hybride)
        threshold_row = QHBoxLayout()
        threshold_label = QLabel("Seuil global (pondération/hybride) :")
        self.global_threshold_spin = QDoubleSpinBox()
        self.global_threshold_spin.setRange(50.0, 99.0)
        self.global_threshold_spin.setSingleStep(1.0)
        self.global_threshold_spin.setValue(80.0)
        self.global_threshold_spin.setSuffix(" %")
        self.global_threshold_spin.setToolTip(
            "Garde-fou simple : le score final doit dépasser ce seuil en mode Pondération/Hybride.\n"
            "80% = équilibré, 90% = strict, 70% = permissif. Ignoré en Filtrage."
        )
        threshold_row.addWidget(threshold_label)
        threshold_row.addWidget(self.global_threshold_spin)
        threshold_row.addStretch()
        mode_layout.addLayout(threshold_row)

        main_layout.addWidget(mode_group)

        # ═══════════════════════════════════════════════════════════
        # METHODS LIST
        # ═══════════════════════════════════════════════════════════
        methods_label = QLabel("<b>📋 Méthodes de Vérification:</b>")
        main_layout.addWidget(methods_label)

        self.methods_layout = QVBoxLayout()
        self.methods_layout.setSpacing(0)

        main_layout.addLayout(self.methods_layout)

        # Résumé rapide pour novices
        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet(
            "QLabel { background-color: #F8F9FA; color: #495057; padding: 6px; font-size: 10px; border-left: 3px solid #6C757D; }"
        )
        main_layout.addWidget(self.summary_label)

        # Control buttons
        controls_layout = QHBoxLayout()

        self.add_method_btn = QPushButton("+ Ajouter méthode")
        self.add_method_btn.setStyleSheet("""
            QPushButton {
                background-color: #28A745;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        self.add_method_btn.clicked.connect(self._show_add_method_dialog)

        controls_layout.addWidget(self.add_method_btn)
        controls_layout.addStretch()

        main_layout.addLayout(controls_layout)

        # Presets
        presets_layout = QHBoxLayout()
        presets_layout.addWidget(QLabel("Préconfigurations:"))

        fast_btn = QPushButton("⚡ Rapide")
        fast_btn.clicked.connect(lambda: self._load_preset('fast'))
        fast_btn.setStyleSheet("QPushButton { padding: 4px 8px; }")

        balanced_btn = QPushButton("⚖️ Équilibré")
        balanced_btn.clicked.connect(lambda: self._load_preset('balanced'))
        balanced_btn.setStyleSheet("QPushButton { padding: 4px 8px; }")

        precision_btn = QPushButton("🎯 Précision Max")
        precision_btn.clicked.connect(lambda: self._load_preset('precision'))
        precision_btn.setStyleSheet("QPushButton { padding: 4px 8px; }")

        scenes_btn = QPushButton("🎬 Scènes/Subsequence")
        scenes_btn.clicked.connect(lambda: self._load_preset('scenes'))
        scenes_btn.setStyleSheet("QPushButton { padding: 4px 8px; }")

        presets_layout.addWidget(fast_btn)
        presets_layout.addWidget(balanced_btn)
        presets_layout.addWidget(precision_btn)
        presets_layout.addWidget(scenes_btn)
        presets_layout.addStretch()

        main_layout.addLayout(presets_layout)

        # Debug / benchmark options
        debug_group = QGroupBox("🧪 Debug / Benchmark")
        debug_layout = QHBoxLayout(debug_group)

        self.debug_checkbox = QCheckBox("Enregistrer en mode debug")
        self.debug_checkbox.setToolTip(
            "Quand activé, chaque exécution enregistre les résultats détaillés des méthodes pour analyse/benchmark."
        )

        self.run_label_input = QLineEdit()
        self.run_label_input.setPlaceholderText("Label du run (ex: bench_scenes_v1)")
        self.run_label_input.setToolTip("Optionnel. Sert à taguer les runs dans la base pour comparaison.")

        debug_layout.addWidget(self.debug_checkbox)
        debug_layout.addWidget(QLabel("Label:"))
        debug_layout.addWidget(self.run_label_input)
        debug_layout.addStretch()

        main_layout.addWidget(debug_group)

        # Update mode explanation with default mode (after controls are created)
        self._on_mode_changed()

        self._update_summary()

    def _on_mode_changed(self):
        """Update explanation when mode changes."""
        mode = self.mode_combo.currentData()

        explanations = {
            'filtering': (
                "<b>Mode Filtrage Séquentiel:</b><br/>"
                "• Les méthodes sont exécutées <b>dans l'ordre</b><br/>"
                "• S'arrête dès qu'une méthode <b>rejette</b> (court-circuit)<br/>"
                "• Plus <b>rapide</b> car peut s'arrêter tôt<br/>"
                "• <b>Sévère</b>: toutes les méthodes doivent passer leur seuil<br/>"
                "• Les poids sont ignorés"
            ),
            'weighting': (
                "<b>Mode Pondération (Score Moyen):</b><br/>"
                "• Exécute <b>toutes</b> les méthodes activées<br/>"
                "• Calcule le <b>score moyen pondéré</b> selon les poids<br/>"
                "• Calcule le <b>seuil moyen pondéré</b> des seuils individuels<br/>"
                "• Accepte si: score pondéré ≥ seuil pondéré<br/>"
                "• <b>Flexible</b>: chaque méthode propose son seuil, les poids déterminent l'importance"
            ),
            'hybrid': (
                "<b>Mode Hybride (Seuils + Pondération):</b><br/>"
                "• Exécute <b>toutes</b> les méthodes activées<br/>"
                "• <b>DEUX conditions</b> requises:<br/>"
                "  1. Chaque méthode doit passer son seuil individuel<br/>"
                "  2. Score pondéré ≥ seuil pondéré (moyenne des seuils)<br/>"
                "• <b>Le plus strict</b> avec importance pondérée"
            )
        }

        self.mode_explanation.setText(explanations.get(mode, ""))

        # Show/hide weight spinboxes based on mode
        show_weights = (mode in ['weighting', 'hybrid'])
        for widget in self.method_widgets:
            method_widget = widget.method_widget
            method_widget.weight_label.setVisible(show_weights)
            method_widget.weight_spin.setVisible(show_weights)

        # Save configuration when mode changes
        self.save_config()

    def _load_default_config(self):
        """Load default balanced configuration."""
        self.global_threshold_spin.setValue(80.0)
        self._load_preset('balanced')

    def _load_preset(self, preset_name):
        """Load a preset configuration."""
        # Clear existing methods
        self._clear_methods()

        if preset_name == 'fast':
            self._add_method('color_histogram', {'threshold': 80.0})
            self._add_method('edge_pattern', {'threshold': 75.0})

        elif preset_name == 'balanced':
            self._add_method('color_histogram', {'threshold': 85.0})
            self._add_method('motion_analysis', {'correlation_threshold': 85.0, 'sample_interval': 3})
            self._add_method('dct_coefficients', {'threshold': 75.0, 'num_coeffs': 15})

        elif preset_name == 'precision':
            self._add_method('color_histogram', {'threshold': 85.0})
            self._add_method('edge_pattern', {'threshold': 80.0})
            self._add_method('motion_analysis', {'correlation_threshold': 85.0})
            self._add_method('dct_coefficients', {'threshold': 75.0})
            self._add_method('ssim', {'threshold': 0.85})
            self._add_method('feature_matching', {'detector': 'ORB', 'threshold': 70.0})
            self._add_method('strategy3', {'dct_threshold': 75.0, 'sequence_threshold': 95.0, 'max_workers': 8})

        elif preset_name == 'scenes':
            # Orienté détection de sous-séquences / scènes
            self._add_method('motion_analysis', {'correlation_threshold': 82.0, 'sample_interval': 2})
            self._add_method('dct_coefficients', {'threshold': 75.0, 'num_coeffs': 16})
            self._add_method('feature_matching', {'detector': 'ORB', 'threshold': 68.0})
            self._add_method('strategy3', {
                'scene_threshold': 50.0,
                'dct_threshold': 75.0,
                'sequence_threshold': 95.0,
                'num_samples': 12,
                'warmup_seconds': 0.5,
                'max_workers': 8
            })

    def _clear_methods(self):
        """Remove all methods."""
        for widget in self.method_widgets:
            self.methods_layout.removeWidget(widget)
            widget.deleteLater()
        self.method_widgets.clear()
        self._update_summary()

    def _add_method(self, method_name, parameters=None, weight=1.0):
        """Add a method to the pipeline."""
        if method_name not in self.AVAILABLE_METHODS:
            return

        method_info = self.AVAILABLE_METHODS[method_name]
        params = method_info['default_params'].copy()
        if parameters:
            params.update(parameters)

        method_widget = PipelineMethodItem(
            method_name,
            method_info['display_name'],
            params,
            weight=weight,
            method_info=method_info
        )

        # Add control buttons (up/down/remove)
        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)

        container_layout.addWidget(method_widget)

        # Buttons
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(2)

        up_btn = QPushButton("↑")
        up_btn.setMaximumSize(30, 25)
        up_btn.clicked.connect(lambda: self._move_method_up(container))

        down_btn = QPushButton("↓")
        down_btn.setMaximumSize(30, 25)
        down_btn.clicked.connect(lambda: self._move_method_down(container))

        remove_btn = QPushButton("✖")
        remove_btn.setMaximumSize(30, 25)
        remove_btn.setStyleSheet("QPushButton { background-color: #DC3545; color: white; }")
        remove_btn.clicked.connect(lambda: self._remove_method(container))

        buttons_layout.addWidget(up_btn)
        buttons_layout.addWidget(down_btn)
        buttons_layout.addWidget(remove_btn)

        container_layout.addLayout(buttons_layout)

        # Store reference to method_widget in container for later access
        container.method_widget = method_widget

        self.methods_layout.addWidget(container)
        self.method_widgets.append(container)
        self._update_summary()

    def _move_method_up(self, widget):
        """Move method up in the list."""
        idx = self.method_widgets.index(widget)
        if idx > 0:
            self.method_widgets[idx], self.method_widgets[idx-1] = self.method_widgets[idx-1], self.method_widgets[idx]
            # Rebuild UI
            self._rebuild_ui()

    def _move_method_down(self, widget):
        """Move method down in the list."""
        idx = self.method_widgets.index(widget)
        if idx < len(self.method_widgets) - 1:
            self.method_widgets[idx], self.method_widgets[idx+1] = self.method_widgets[idx+1], self.method_widgets[idx]
            # Rebuild UI
            self._rebuild_ui()

    def _remove_method(self, container):
        """Remove a method from the pipeline."""
        if container in self.method_widgets:
            self.method_widgets.remove(container)
            self.methods_layout.removeWidget(container)
            container.deleteLater()
        self.save_config()  # Save after removing
        self._update_summary()

    def _rebuild_ui(self):
        """Rebuild the UI after reordering."""
        # Remove all widgets from layout
        for i in reversed(range(self.methods_layout.count())):
            widget = self.methods_layout.itemAt(i).widget()
            if widget:
                self.methods_layout.removeWidget(widget)

        # Re-add in new order
        for container in self.method_widgets:
            self.methods_layout.addWidget(container)

        self.save_config()  # Save after reordering
        self._update_summary()

    def _show_add_method_dialog(self):
        """Show dialog to add a new method."""
        from PyQt6.QtWidgets import QDialog, QListWidget, QListWidgetItem

        dialog = QDialog(self)
        dialog.setWindowTitle("Ajouter une méthode")
        layout = QVBoxLayout(dialog)

        info = QLabel("Choisissez une méthode à ajouter. Chaque méthode affiche sa vitesse et son usage recommandé.")
        info.setWordWrap(True)
        layout.addWidget(info)

        list_widget = QListWidget()
        for key, meta in self.AVAILABLE_METHODS.items():
            item = QListWidgetItem(f"{meta['display_name']} — {meta.get('speed', '')}")
            item.setData(Qt.ItemDataRole.UserRole, key)
            item.setToolTip(meta.get('detailed_explanation', meta.get('description', '')))
            list_widget.addItem(item)
        layout.addWidget(list_widget)

        buttons = QHBoxLayout()
        add_btn = QPushButton("Ajouter")
        cancel_btn = QPushButton("Annuler")
        buttons.addStretch()
        buttons.addWidget(add_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

        added_method = {'name': None}

        def on_add():
            current = list_widget.currentItem()
            if current:
                added_method['name'] = current.data(Qt.ItemDataRole.UserRole)
                dialog.accept()

        add_btn.clicked.connect(on_add)
        cancel_btn.clicked.connect(dialog.reject)

        dialog.exec()

        if added_method['name']:
            self._add_method(added_method['name'])

    def get_pipeline_config(self):
        """Get the current pipeline configuration."""
        methods_config = []
        for container in self.method_widgets:
            method_widget = container.method_widget
            methods_config.append({
                'name': method_widget.method_name,
                'enabled': method_widget.is_enabled(),
                'parameters': method_widget.get_parameters(),
                'weight': method_widget.get_weight()
            })

        return {
            'mode': self.mode_combo.currentData(),
            'methods': methods_config,
            'debug_flag': self.debug_checkbox.isChecked(),
            'run_label': self.run_label_input.text().strip(),
            'global_threshold': float(self.global_threshold_spin.value())
        }

    def get_methods_only(self):
        """Get only the methods configuration (for backwards compatibility)."""
        return self.get_pipeline_config()['methods']

    def save_config(self):
        """Save current pipeline configuration to settings."""
        config = self.get_pipeline_config()

        # Save as JSON string
        self.settings.beginGroup("pipeline")
        self.settings.setValue("mode", config['mode'])
        self.settings.setValue("methods", json.dumps(config['methods']))
        self.settings.setValue("debug_flag", config.get('debug_flag', False))
        self.settings.setValue("run_label", config.get('run_label', ''))
        self.settings.setValue("global_threshold", config.get('global_threshold', 80.0))
        self.settings.endGroup()
        self.settings.sync()

        from src.core.logger import Logger
        logger = Logger.get_logger('DuplicateFinder.PipelineConfig')
        logger.info(f"Pipeline configuration saved: mode={config['mode']}, {len(config['methods'])} methods")
        self._update_summary()

    def load_pipeline_config(self, pipeline_data: dict):
        """
        Load pipeline configuration from a pipeline data dict.

        Args:
            pipeline_data: Dict with 'mode' and 'methods' keys
        """
        try:
            mode = pipeline_data.get('mode', 'filtering')
            methods = pipeline_data.get('methods', [])
            global_threshold = float(pipeline_data.get('global_threshold', self.global_threshold_spin.value()))

            # Set mode
            for i in range(self.mode_combo.count()):
                if self.mode_combo.itemData(i) == mode:
                    self.mode_combo.setCurrentIndex(i)
                    break

            # Clear and load methods
            self._clear_methods()
            for method_config in methods:
                self._add_method(
                    method_config['name'],
                    parameters=method_config.get('parameters'),
                    weight=method_config.get('weight', 1.0)
                )

                # Set enabled state
                if self.method_widgets:
                    container = self.method_widgets[-1]
                    container.method_widget.set_enabled(method_config.get('enabled', True))

            from src.core.logger import Logger
            logger = Logger.get_logger('DuplicateFinder.PipelineConfig')
            logger.info(f"Pipeline configuration loaded: mode={mode}, {len(methods)} methods")

            self._update_summary()
            self.global_threshold_spin.setValue(global_threshold)

        except (KeyError, Exception) as e:
            from src.core.logger import Logger
            logger = Logger.get_logger('DuplicateFinder.PipelineConfig')
            logger.error(f"Failed to load pipeline config: {e}")
            raise

    def load_saved_config(self):
        """Load pipeline configuration from settings."""
        self.settings.beginGroup("pipeline")
        mode = self.settings.value("mode", "filtering", type=str)
        methods_json = self.settings.value("methods", "", type=str)
        debug_flag = self.settings.value("debug_flag", False, type=bool)
        run_label = self.settings.value("run_label", "", type=str)
        global_threshold = self.settings.value("global_threshold", 80.0, type=float)
        self.settings.endGroup()

        if methods_json:
            try:
                methods = json.loads(methods_json)

                # Set mode
                for i in range(self.mode_combo.count()):
                    if self.mode_combo.itemData(i) == mode:
                        self.mode_combo.setCurrentIndex(i)
                        break

                # Clear and load methods
                self._clear_methods()
                for method_config in methods:
                    self._add_method(
                        method_config['name'],
                        parameters=method_config.get('parameters'),
                        weight=method_config.get('weight', 1.0)
                    )

                    # Set enabled state
                    if self.method_widgets:
                        container = self.method_widgets[-1]
                        container.method_widget.set_enabled(method_config.get('enabled', True))

                from src.core.logger import Logger
                logger = Logger.get_logger('DuplicateFinder.PipelineConfig')
                logger.info(f"Pipeline configuration loaded: mode={mode}, {len(methods)} methods")

            except (json.JSONDecodeError, KeyError) as e:
                from src.core.logger import Logger
                logger = Logger.get_logger('DuplicateFinder.PipelineConfig')
                logger.warning(f"Failed to load pipeline config: {e}, using default")
                self._load_default_config()
        else:
            # No saved config, use default
            self._load_default_config()
        self.debug_checkbox.setChecked(debug_flag)
        self.run_label_input.setText(run_label)
        self.global_threshold_spin.setValue(float(global_threshold))
        self._update_summary()

    def _update_summary(self):
        """Update the novice-friendly summary label."""
        mode = self.mode_combo.currentData()
        methods = self.get_methods_only()
        enabled_methods = [m for m in methods if m.get('enabled', True)]

        speed_map = {
            'Rapide': 0.5,
            'Moyen': 1.0,
            'Lent': 1.5,
            'Très Lent': 3.0
        }

        est_time = 0.0
        for m in enabled_methods:
            meta = self.AVAILABLE_METHODS.get(m['name'], {})
            est_time += speed_map.get(meta.get('speed', ''), 1.0)

        mode_text = {
            'filtering': "Filtrage (s'arrête au 1er rejet)",
            'weighting': "Pondération (moyenne des scores)",
            'hybrid': "Hybride (seuils + moyenne)"
        }.get(mode, mode)

        self.summary_label.setText(
            f"Mode: {mode_text} | Méthodes actives: {len(enabled_methods)} | Temps estimé/pair: ~{est_time:.1f}s. "
            f"Seuil global: {self.global_threshold_spin.value():.0f}% (pondération/hybride). "
            "Astuce: garde les méthodes lentes/fiables (Strategy3) en fin."
        )


class PipelineConfigDialog(QDialog):
    """
    Modal dialog for pipeline configuration.

    Provides a popup window with better space management for configuring
    verification pipelines. More user-friendly than a cramped side tab.

    Features:
        - Modal popup window (800x700px)
        - Scrollable content area
        - Save/Cancel buttons at bottom
        - Preview button to test configuration
        - Full access to all PipelineConfigWidget features

    Example:
        >>> dialog = PipelineConfigDialog(parent)
        >>> if dialog.exec() == QDialog.DialogCode.Accepted:
        >>>     config = dialog.get_pipeline_config()
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔧 Configuration du Pipeline")
        self.setMinimumSize(900, 750)
        self.resize(1000, 800)  # Comfortable default size

        self._init_ui()

    def _init_ui(self):
        """Initialize the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QLabel("🔧 <b>Configuration du Pipeline de Vérification</b>")
        header.setStyleSheet("""
            QLabel {
                font-size: 16px;
                padding: 15px;
                background-color: #E3F2FD;
                border-bottom: 2px solid #2196F3;
            }
        """)
        layout.addWidget(header)

        # Scrollable content area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")

        # Pipeline config widget (the actual configuration interface)
        self.pipeline_widget = PipelineConfigWidget()
        scroll_area.setWidget(self.pipeline_widget)

        layout.addWidget(scroll_area, stretch=1)

        # Button bar at bottom
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(15, 10, 15, 10)
        button_layout.setSpacing(10)

        # Preview button
        preview_btn = QPushButton("👁️ Prévisualiser")
        preview_btn.setToolTip("Afficher un résumé de la configuration")
        preview_btn.clicked.connect(self._on_preview)
        preview_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                font-size: 12px;
            }
        """)
        button_layout.addWidget(preview_btn)

        button_layout.addStretch()

        # Standard dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.button(QDialogButtonBox.StandardButton.Save).setText("💾 Sauvegarder")
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("❌ Annuler")

        button_box.accepted.connect(self._on_save)
        button_box.rejected.connect(self.reject)

        button_box.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton[text*="Sauvegarder"] {
                background-color: #28A745;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton[text*="Sauvegarder"]:hover {
                background-color: #218838;
            }
        """)

        button_layout.addWidget(button_box)

        layout.addLayout(button_layout)

    def _on_preview(self):
        """Show preview of current configuration."""
        from PyQt6.QtWidgets import QMessageBox

        config = self.pipeline_widget.get_pipeline_config()
        methods = config['methods']
        enabled = [m for m in methods if m.get('enabled', True)]

        preview_text = f"**Mode:** {config['mode']}\n\n"
        preview_text += f"**Méthodes actives:** {len(enabled)}/{len(methods)}\n\n"

        if enabled:
            preview_text += "**Ordre d'exécution:**\n"
            for i, method in enumerate(enabled, 1):
                meta = self.pipeline_widget.AVAILABLE_METHODS.get(method['name'], {})
                preview_text += f"{i}. {meta.get('display_name', method['name'])} (poids: {method.get('weight', 1.0)})\n"

        QMessageBox.information(self, "Aperçu de la Configuration", preview_text)

    def _on_save(self):
        """Save configuration and close dialog."""
        # Save config via the widget
        self.pipeline_widget.save_config()
        self.accept()

    def get_pipeline_config(self):
        """
        Get the current pipeline configuration.

        Returns:
            dict: Pipeline configuration with mode, methods, debug settings
        """
        return self.pipeline_widget.get_pipeline_config()

    def set_pipeline_config(self, config: dict):
        """
        Load a pipeline configuration into the dialog.

        Args:
            config: Pipeline configuration dict
        """
        # This would require adding a load method to PipelineConfigWidget
        # For now, configs are auto-loaded from QSettings
        pass

    def closeEvent(self, event):
        """
        CORRECTION BUG #18: Cleanup resources when widget is closed.

        Ensures proper cleanup of resources and signals.
        """
        # All signals are internal and auto-cleaned by Qt
        # Added for consistency with other widgets
        super().closeEvent(event)
