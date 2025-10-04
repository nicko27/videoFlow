
# ============================================================================
# window.py - Fichier principal simplifié (pour compatibilité)
# ============================================================================

"""
Fichier principal du module window - Version restructurée
Importe et expose la fenêtre principale pour compatibilité
"""

# Import de la fenêtre principale redesignée
from .main_window import DuplicateFinderWindow

# Import du dialogue de comparaison redesigné  
from .comparison_dialog import ComparisonDialog

# Import des widgets utilitaires
from .video_preview_widget import VideoPreviewWidget
from .progress_widgets import ModernProgressWidget, FileListWidget, StatusIndicator

# Import des workers
from .main_window import ParallelHashWorker, OptimizedComparisonWorker

# Classes principales pour l'export
__all__ = [
    'DuplicateFinderWindow',
    'ComparisonDialog', 
    'VideoPreviewWidget',
    'ModernProgressWidget',
    'FileListWidget',
    'StatusIndicator',
    'ParallelHashWorker',
    'OptimizedComparisonWorker'
]

# ============================================================================
# Structure des fichiers recommandée:
# ============================================================================

"""
src/plugins/duplicate_finder/
├── __init__.py
├── plugin.py
├── video_hasher.py
├── database_manager.py
├── window/
│   ├── __init__.py (ce fichier)
│   ├── video_preview_widget.py
│   ├── comparison_dialog.py  
│   ├── progress_widgets.py
│   ├── main_window.py
│   └── window.py (ce fichier - pour compatibilité)
└── README.md
"""

# ============================================================================
# Exemple d'utilisation:
# ============================================================================

"""
# Import simple depuis le plugin principal
from src.plugins.duplicate_finder.window import DuplicateFinderWindow

# Ou import spécifique
from src.plugins.duplicate_finder.window import (
    DuplicateFinderWindow,
    ComparisonDialog,
    VideoPreviewWidget
)

# Utilisation
window = DuplicateFinderWindow()
window.show()
"""

# ============================================================================
# Notes de migration:
# ============================================================================

"""
CHANGEMENTS MAJEURS:

1. STRUCTURE MODULAIRE:
   - Séparation des classes en fichiers dédiés
   - Responsabilité unique par fichier
   - Import centralisé via __init__.py

2. INTERFACE REDESIGNÉE:
   - Dialogue de comparaison totalement refondu
   - Interface moderne avec cartes vidéo
   - Navigation synchronisée améliorée
   - Boutons d'action plus visibles

3. WIDGETS OPTIMISÉS:
   - VideoPreviewWidget simplifié et robuste
   - Widgets de progression modernes
   - Gestion d'erreurs améliorée
   - Nettoyage automatique des ressources

4. CORRECTIONS DE BUGS:
   - Plus d'erreur NameError avec video_path
   - Gestion propre des ressources OpenCV
   - Validation des fichiers améliorée
   - Thread safety renforcé

COMPATIBILITÉ:
   - Les imports existants continuent de fonctionner
   - API publique inchangée
   - Fonctionnalités étendues, pas supprimées

MIGRATION RECOMMANDÉE:
   1. Remplacer le contenu du dossier window/
   2. Mettre à jour les imports si nécessaire
   3. Tester l'interface redesignée
   4. Adapter les paramètres selon les besoins

AVANTAGES:
   ✅ Code plus maintenable
   ✅ Interface utilisateur moderne
   ✅ Performance améliorée
   ✅ Bugs corrigés
   ✅ Meilleure séparation des responsabilités
   ✅ Tests plus faciles
   ✅ Documentation intégrée
"""