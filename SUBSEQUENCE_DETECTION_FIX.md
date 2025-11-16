# 🐛 Fix Subsequence Detection Parameters

**Date:** 2025-11-16
**Problème:** Les paramètres de détection de sous-séquences semblaient ignorés

---

## 🔍 Problème Identifié

Les paramètres de la détection de sous-séquences avaient **des valeurs par défaut incohérentes** entre l'interface utilisateur et le code backend, ce qui donnait l'impression que les valeurs de l'utilisateur étaient ignorées.

### **Incohérences trouvées:**

| Paramètre | UI (panels.py) | Load Settings | Get Analysis Config |
|-----------|----------------|---------------|---------------------|
| **Sample Interval** | 3.0 sec ✅ | 1.5 sec ❌ | 1.5 sec ❌ |
| **Min Match Ratio** | 80.0% ✅ | 70.0% ❌ | 0.70 (ratio) ❌ |
| **Cache Memory** | 500 MB ✅ | 500 MB ✅ | 500 MB ✅ |

### **Conséquence:**

Quand l'utilisateur ne modifiait pas les valeurs dans l'UI:
- Il voyait "3.0 sec" et "80%"
- Mais le code utilisait 1.5 sec et 70%
- Ses paramètres semblaient "ignorés"

---

## ✅ Corrections Appliquées

### **1. Settings Manager - load_settings() (lignes 112-117)**

**Avant:**
```python
self._load_widget_value(
    widgets, 'subsequence_sample_interval_spin', 'sample_interval', 1.5, float  # ❌
)
self._load_widget_value(
    widgets, 'subsequence_min_match_spin', 'min_match_ratio', 70.0, float  # ❌
)
```

**Après:**
```python
self._load_widget_value(
    widgets, 'subsequence_sample_interval_spin', 'sample_interval', 3.0, float  # ✅
)
self._load_widget_value(
    widgets, 'subsequence_min_match_spin', 'min_match_ratio', 80.0, float  # ✅
)
```

---

### **2. Settings Manager - get_analysis_config() (lignes 384-411)**

**Avant:**
```python
config['subsequence_detection'] = {
    'enabled': widgets['enable_subsequence_check'].isChecked(),
    'sample_interval': 1.5,  # ❌
    'min_match_ratio': 0.70,  # ❌ Ratio au lieu de pourcentage
    'cache_memory_mb': 500
}

# Puis override avec widgets...
```

**Après:**
```python
# Get actual widget values (with defaults matching UI)
sample_interval = 3.0  # ✅ Default from UI
min_match_ratio = 0.80  # ✅ Default 80% from UI, converted to ratio
cache_memory_mb = 500  # ✅ Default from UI

# Override with actual widget values if available
if 'subsequence_sample_interval_spin' in widgets and widgets['subsequence_sample_interval_spin'] is not None:
    sample_interval = widgets['subsequence_sample_interval_spin'].value()

if 'subsequence_min_match_spin' in widgets and widgets['subsequence_min_match_spin'] is not None:
    min_match_ratio = widgets['subsequence_min_match_spin'].value() / 100.0  # Convert %

config['subsequence_detection'] = {
    'enabled': enabled,
    'sample_interval': sample_interval,
    'min_match_ratio': min_match_ratio,
    'cache_memory_mb': cache_memory_mb
}
```

**Avantages:**
- Les valeurs par défaut correspondent maintenant à l'UI
- La conversion pourcentage → ratio est claire
- Code plus lisible et maintenable

---

### **3. Main Window - _start_subsequence_detection() (lignes 847-854)**

**Avant:**
```python
if self.subsequence_detector is None:
    self.subsequence_detector = SubsequenceDetector(
        hasher=self.video_hasher,
        max_cache_memory_mb=subseq_config.get('cache_memory_mb', 500),
        sample_interval_seconds=subseq_config.get('sample_interval', 1.5),  # ❌
        min_match_ratio=subseq_config.get('min_match_ratio', 0.70)  # ❌
    )
```

**Après:**
```python
if self.subsequence_detector is None:
    self.subsequence_detector = SubsequenceDetector(
        hasher=self.video_hasher,
        max_cache_memory_mb=subseq_config.get('cache_memory_mb', 500),
        sample_interval_seconds=subseq_config.get('sample_interval', 3.0),  # ✅
        min_match_ratio=subseq_config.get('min_match_ratio', 0.80)  # ✅
    )
```

---

### **4. Ajout de Logging (lignes 825-835)**

**Nouveau code:**
```python
logger.info(f"Subsequence detection enabled: {is_enabled}")
if is_enabled:
    logger.info(f"Subsequence parameters: sample_interval={subseq_config.get('sample_interval')}s, "
               f"min_match_ratio={subseq_config.get('min_match_ratio', 0)*100:.1f}%, "
               f"cache_memory={subseq_config.get('cache_memory_mb')}MB")
    # Start subsequence detection
    self._start_subsequence_detection()
else:
    logger.info("Subsequence detection skipped (not enabled)")
```

**Bénéfice:** L'utilisateur peut maintenant voir dans les logs:
- Si la détection de sous-séquences est activée ou non
- Quels paramètres sont utilisés (sample_interval, min_match_ratio, cache_memory)

---

## 📊 Valeurs Finales (Toutes Alignées)

| Paramètre | Valeur par défaut | Stockage |
|-----------|------------------|----------|
| **Enable Subsequence** | False (non coché) | Boolean |
| **Sample Interval** | 3.0 secondes | Float (secondes) |
| **Min Match Ratio** | 80.0% | Float (pourcentage dans UI, ratio 0.80 dans code) |
| **Cache Memory** | 500 MB | Integer (MB) |

---

## 🔧 Comment Utiliser

### **1. Activer la détection de sous-séquences:**
1. Ouvrir l'onglet **"⚙️ Settings"** (panneau gauche)
2. Descendre jusqu'au groupe **"🎬 Subsequence Detection (Optional)"**
3. Cocher **"Enable subsequence detection"**

### **2. Ajuster les paramètres (optionnel):**
- **Sample interval (3.0s):** Intervalle entre les frames échantillonnées. Plus petit = plus précis mais plus lent.
- **Min match ratio (80%):** Pourcentage minimal de correspondance pour considérer une sous-séquence.
- **Cache memory limit (500MB):** Mémoire maximale pour le cache LRU de hashes denses.

### **3. Lancer l'analyse:**
1. Ajouter au moins 2 vidéos
2. Cliquer sur **"🔍 Analyze"**
3. Après la comparaison des doublons, la détection de sous-séquences démarre automatiquement (si activée)

### **4. Vérifier dans les logs:**

Si la détection est **activée**, vous verrez dans les logs:
```
INFO - Subsequence detection enabled: True
INFO - Subsequence parameters: sample_interval=3.0s, min_match_ratio=80.0%, cache_memory=500MB
INFO - Starting subsequence detection on 10 files
```

Si la détection est **désactivée**, vous verrez:
```
INFO - Subsequence detection enabled: False
INFO - Subsequence detection skipped (not enabled)
```

---

## 🎯 Résultat

Maintenant, les paramètres de subsequence detection sont **cohérents** entre l'UI et le code:
- ✅ Les valeurs affichées dans l'UI correspondent aux valeurs utilisées
- ✅ Les modifications de l'utilisateur sont correctement prises en compte
- ✅ Les logs montrent clairement les paramètres utilisés
- ✅ Le comportement est prévisible et transparent

---

## 📝 Fichiers Modifiés

1. **`src/plugins/duplicate_finder/managers/settings_manager.py`**
   - Ligne 113: `sample_interval` default 1.5 → 3.0
   - Ligne 116: `min_match_ratio` default 70.0 → 80.0
   - Lignes 384-411: Refactorisé `get_analysis_config()` pour clarté

2. **`src/plugins/duplicate_finder/main_window.py`**
   - Lignes 825-835: Ajout de logging pour visibilité
   - Ligne 852: `sample_interval` default 1.5 → 3.0
   - Ligne 853: `min_match_ratio` default 0.70 → 0.80

---

**Status:** ✅ **CORRIGÉ ET TESTÉ**
