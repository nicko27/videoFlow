
# ============================================================================
# window.py - File principal simplifié (pour compatibilité)
# ============================================================================

"""
File principal du module window - Version restructurée
Importe et expose the window principale pour compatibilité
"""

# Import de the window principale redesignée
from .main_window import DuplicateFinderWindow

# Import du dialogue de comparison redesigné  
from .comparison_dialog import ComparisonDialog

# Import des widgets utilitaires
from .video_preview_widget import VideoPreviewWidget
from .progress_widgets import ModernProgressWidget, FileListWidget, StatusIndicator

# Import des workers
from .workers.hash_worker import ParallelHashWorker
from .workers.comparison_worker import OptimizedComparisonWorker

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
# Structure des files recommandée:
# ============================================================================

"""
src/plugins/duplicate_finder/
├── __init__.py
├── plugin.py
├── video_hasher.py
├── database_manager.py
├── window/
│   ├── __init__.py (ce file)
│   ├── video_preview_widget.py
│   ├── comparison_dialog.py  
│   ├── progress_widgets.py
│   ├── main_window.py
│   └── window.py (ce file - pour compatibilité)
└── README.md
"""

# ============================================================================
# Exemple d'utilisation:
# ============================================================================

"""
# Import simple depuis the plugin principal
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
   - Séparation des classes en files dédiés
   - Responsabilité unique par file
   - Import centralisé via __init__.py

2. INTERFACE REDESIGNÉE:
   - Dialogue de comparison totalement refondu
   - Interface moderne with cartes vidéo
   - Navigation synchronisée améliorée
   - Boutons d'action plus visibles

3. WIDGETS OPTIMISÉS:
   - VideoPreviewWidget simplifié et robuste
   - Widgets de progression modernes
   - Handling d'erreurs améliorée
   - Nettoyage automatique des ressources

4. CORRECTIONS DE BUGS:
   - Plus d'error NameError with video_path
   - Handling propre des ressources OpenCV
   - Validation des files améliorée
   - Thread safety renforcé

COMPATIBILITÉ:
   - Les imports existants continuent de fonctionner
   - API publique inchangée
   - Fonctionnalités étendues, pas supprimées

MIGRATION RECOMMANDÉE:
   1. Remplacer le contenu du folder window/
   2. Mettre à jour les imports si nécessaire
   3. Tester l'interface redesignée
   4. Adapter les settings selon les besoins

AVANTAGES:
   ✅ Code plus maintenable
   ✅ Interface utilisateur moderne
   ✅ Performance améliorée
   ✅ Bugs corrigés
   ✅ Meilleure séparation des responsabilités
   ✅ Tests plus faciles
   ✅ Documentation intégrée
"""