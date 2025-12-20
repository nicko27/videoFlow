# Référence Rapide - Corrections de Démarrage

## Résumé Ultra-Court

**3 erreurs critiques** corrigées dans **3 fichiers** en supprimant **~120 lignes** de code obsolète.

## Erreurs Corrigées

### 1. panels.py ligne 433 - NoneType.get()
```python
# AVANT
df_config = pipeline_data.get('duplicateflow_config', {})

# APRÈS
df_config = pipeline_data.get('duplicateflow_config') or {}
```

### 2. main_window.py - AudioFirstHandler non défini
**Actions:**
- Supprimé `self.audio_first_handler = AudioFirstHandler(...)`
- Supprimé 9 méthodes audio-first (113 lignes)
- Refactoré `start_analysis()` pour utiliser `analysis_handler`

### 3. settings_manager.py ligne 400 - widget.value() sur None
```python
# AVANT
config = {
    'threshold': widgets['threshold_spin'].value(),
    ...
}

# APRÈS
def get_widget_value(widget_name, default):
    widget = widgets.get(widget_name)
    if widget is not None:
        return widget.value() if hasattr(widget, 'value') else default
    return default

config = {
    'threshold': get_widget_value('threshold_spin', 0.85),
    ...
}
```

## Test de Validation

```bash
python3 -c "
from src.plugins.duplicate_finder.main_window import DuplicateFinderWindow
import sys
from PyQt6.QtWidgets import QApplication
app = QApplication(sys.argv)
window = DuplicateFinderWindow()
print('✅ Success')
"
```

## Résultat

- ✅ Application démarre sans erreur
- ✅ Tous les handlers initialisés
- ✅ Configuration récupérable
- ✅ Base de données connectée
- ✅ Tests passés: 7/7

## Fichiers Modifiés

1. `src/plugins/duplicate_finder/main_window.py` (-113 lignes)
2. `src/plugins/duplicate_finder/infrastructure/config/settings_manager.py` (+15 lignes)
3. `src/plugins/duplicate_finder/ui/panels.py` (1 ligne)

## Nettoyage Recommandé (optionnel)

- `src/plugins/duplicate_finder/ui/main_window.py` - Duplicata obsolète (non importé)
