# 🔍 Analyse du Duplicate Finder - Problèmes & Optimisations

**Date:** 2025-11-16
**Analysé par:** Claude Code
**Module:** src/plugins/duplicate_finder/

---

## 📋 Table des matières
1. [Fonctionnalités cachées (non exposées dans l'UI)](#1-fonctionnalités-cachées)
2. [Problèmes détectés](#2-problèmes-détectés)
3. [Optimisations possibles](#3-optimisations-possibles)
4. [Recommandations prioritaires](#4-recommandations-prioritaires)

---

## 1. Fonctionnalités cachées (non exposées dans l'UI)

### 🎯 **Méthodes de hashing alternatives**
**Localisation:** `video_hasher.py:20-30`

```python
class HashMethod(Enum):
    PHASH = "pHash"  # Utilisé actuellement
    DHASH = "dHash"  # Plus rapide - NON ACCESSIBLE
    AHASH = "aHash"  # Le plus rapide - NON ACCESSIBLE
```

**État:** Implémentée mais pas d'UI pour choisir
**Impact:** Les utilisateurs ne peuvent pas optimiser la vitesse vs précision
**Solution:** Ajouter un sélecteur dans l'onglet Settings

---

### 🔄 **Cache preloading configurable**
**Localisation:** `video_hasher.py:61`

```python
def __init__(self, method=HashMethod.PHASH.value,
             enable_preload=True,      # Hardcodé à True
             max_preload_items=1000):  # Hardcodé à 1000
```

**État:** Paramètres hardcodés
**Impact:** Utilisateurs avec de grandes bases ne peuvent pas ajuster
**Solution:** Exposer dans Settings avancés

---

### 💾 **Connection pool size**
**Localisation:** `database_manager.py:158`

```python
self.connection_pool = ConnectionPool(db_path, pool_size=5)  # Hardcodé
```

**État:** Taille fixe à 5 connexions
**Impact:** Peut limiter les performances sur machines puissantes
**Solution:** Rendre configurable selon CPU count

---

### 📊 **Statistiques d'early-exit**
**Localisation:** `database_manager.py:729`

```python
'early_exit_percentage': (early_exits / comparisons_count * 100)
```

**État:** Collectées mais PAS affichées dans l'UI
**Impact:** Info de performance utile cachée
**Solution:** Ajouter dans le dialogue de statistiques

---

### 🎬 **Play/Pause dans le comparateur vidéo**
**Localisation:** `keyboard_shortcuts.py:33`

```python
# Space for play/pause (future feature)
NAV_PLAY_PAUSE = Qt.Key.Key_Space
```

**État:** Défini mais jamais implémenté
**Impact:** Fonctionnalité attendue manquante
**Solution:** Implémenter la lecture/pause ou retirer le commentaire

---

### 🗂️ **Validation de taille de fichier**
**Localisation:** `validators.py:245`

```python
MIN_FILE_SIZE_BYTES = 10240  # 10KB minimum
```

**État:** Validateur existe mais pas utilisé partout
**Impact:** Fichiers corrompus peuvent être traités
**Solution:** Appliquer systématiquement avant analyse

---

### 🎨 **Taille du cache de comparaison LRU**
**Localisation:** `video_hasher.py:81`

```python
self.comparison_cache = LRUCache(max_size=10000)  # Hardcodé
```

**État:** Non configurable
**Impact:** Trop grand = RAM, trop petit = lent
**Solution:** Rendre ajustable dans Settings

---

## 2. Problèmes détectés

### ❌ **Imports inutilisés (26 warnings F401)**
**Impact:** Code mort, confusion
**Fichiers affectés:**
- `database_manager.py`: hashlib, datetime, numpy
- `design_system.py`: Theme
- `handlers/duplicate_handler.py`: QMessageBox
- `keyboard_shortcuts.py`: QKeySequence
- `progress_widgets.py`: ~~QTimer, pyqtSignal~~ ✅ CORRIGÉ
- `video_preview_widget.py`: numpy, QHBoxLayout, QTimer
- Et 8+ autres fichiers...

**Solution:** Nettoyage imports (non-critique)

---

### ⚠️ **Code mort dans database_manager.py**
**Localisation:** `database_manager.py:698-712`

```python
# Legacy compatibility removed - ignore_type always exists after migration
if False:  # <- CODE MORT
    # Version without ignore_type (compatibility - DEPRECATED)
    ...
```

**Impact:** Code mort confusant
**Solution:** Supprimer le bloc entier

---

### 🔄 **Gestion inefficace de la taille du pool SQLite**
**Localisation:** `database_manager.py:30-49`

**Problème:** Pool size fixe de 5 ne s'adapte pas au nombre de CPU
**Impact:** Sous-utilisation sur machines puissantes
**Solution:**
```python
optimal_pool_size = min(multiprocessing.cpu_count() + 2, 10)
```

---

### 📝 **Logs en français dans du code**
**Impact:** Inconsistance, problèmes i18n
**Exemples:**
- `database_manager.py:747`: "Nettoie la base des files"
- `database_manager.py:762`: "Removes en une seule transaction"

**Solution:** Uniformiser en anglais ou externaliser

---

## 3. Optimisations possibles

### ⚡ **#1 - Preload cache intelligent par défaut**
**Localisation:** `video_hasher.py:104-223`

**État actuel:**
- Charge TOUS les hash (limité à 1000)
- Pas de priorisation

**Optimisation:**
```python
def _preload_cache_intelligent(self, max_items=1000):
    """Preload only files that still exist AND were accessed recently"""
    # ORDER BY last_accessed DESC, updated_at DESC
    # WHERE file_exists = TRUE
```

**Gain estimé:** 30-50% temps de démarrage

---

### ⚡ **#2 - Batch size adaptatif**
**Localisation:** `workers/comparison_worker.py:232`

**État actuel:** Batch size fixe (50 par défaut)

**Optimisation:**
```python
adaptive_batch_size = min(
    len(pairs) // worker_count,
    max(50, worker_count * 10)
)
```

**Gain estimé:** 15-25% performances sur grands datasets

---

### ⚡ **#3 - Cache de frames pour SubsequenceDetector**
**Localisation:** `subsequence_detector.py:33`

**Problème actuel:** Pas de réutilisation des frames entre comparaisons

**Optimisation:**
```python
# Ajouter un cache temporal pour les frames récemment lus
self.frame_cache = LRUCache(max_memory_mb=200)
```

**Gain estimé:** 40-60% sur détection de sous-séquences

---

### ⚡ **#4 - Index manquant sur comparisons**
**Localisation:** `database_manager.py:231`

**Problème:** Requêtes sur `is_early_exit` sans index

**Optimisation:**
```sql
CREATE INDEX IF NOT EXISTS idx_comparisons_early_exit
ON comparisons(is_early_exit) WHERE is_early_exit = 1;
```

**Gain estimé:** 2-5x vitesse requêtes statistiques

---

### ⚡ **#5 - Parallélisation du cleanup**
**Localisation:** `database_manager.py:746-789`

**Problème:** Vérifie existence fichiers séquentiellement

**Optimisation:**
```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=4) as executor:
    missing_checks = executor.map(os.path.exists, file_paths)
```

**Gain estimé:** 3-10x vitesse cleanup

---

### ⚡ **#6 - Hash method switcher dynamique**
**Localisation:** `video_hasher.py:240-261`

**Idée:** Détecter vidéos similaires et switcher auto sur aHash pour vitesse

**Optimisation:**
```python
if detected_duplicates_rate > 0.3:
    self.method = HashMethod.AHASH.value  # Plus rapide
```

**Gain estimé:** 20-40% sur datasets avec beaucoup de doublons

---

## 4. Recommandations prioritaires

### 🔴 **PRIORITÉ HAUTE**

1. **Exposer les méthodes de hashing dans l'UI**
   - Fichier: `ui/panels.py` ligne ~287
   - Ajouter QComboBox avec PHASH/DHASH/AHASH
   - Impact: Énorme gain de temps utilisateur

2. **Afficher statistiques early-exit**
   - Fichier: `main_window.py` ligne ~1070
   - Ajouter ligne dans `show_statistics()`
   - Impact: Transparence performance

3. **Supprimer code mort**
   - `database_manager.py:698-712`
   - Impact: Maintenance

---

### 🟡 **PRIORITÉ MOYENNE**

4. **Rendre configurable:**
   - Cache preload items (Settings)
   - Pool size (auto-détection CPU)
   - LRU cache size (Settings avancés)

5. **Ajouter index database**
   - `idx_comparisons_early_exit`
   - `idx_video_files_mtime`

6. **Batch size adaptatif**
   - Auto-ajustement selon worker count

---

### 🟢 **PRIORITÉ BASSE**

7. **Nettoyage imports inutilisés**
   - Amélioration qualité code
   - Pas d'impact fonctionnel

8. **Uniformiser langue logs**
   - Anglais partout ou i18n

9. **Implémenter Play/Pause**
   - Ou retirer commentaire "future feature"

---

## 📈 Impact estimé global

Si TOUTES les optimisations sont appliquées:

| Métrique | Amélioration estimée |
|----------|---------------------|
| **Vitesse analyse** | +30-50% |
| **Temps démarrage** | +40-60% |
| **Utilisation RAM** | Configurable (±20%) |
| **Détection sous-séquences** | +50-70% |
| **Expérience utilisateur** | Significative ⭐⭐⭐⭐⭐ |

---

## 🛠️ Plan d'action suggéré

### Phase 1 (1-2 jours)
- [ ] Ajouter sélecteur méthode hashing dans UI
- [ ] Exposer statistiques early-exit
- [ ] Supprimer code mort
- [ ] Ajouter index database

### Phase 2 (2-3 jours)
- [ ] Implémenter batch size adaptatif
- [ ] Rendre configurables: preload, pool size, cache
- [ ] Paralléliser cleanup

### Phase 3 (optionnel)
- [ ] Nettoyer imports
- [ ] Uniformiser logs
- [ ] Hash method switcher auto

---

**Généré automatiquement par analyse statique du code**
**Fichiers analysés:** 30+ fichiers Python (~11,000 lignes)
