# 📋 PLAN DE CORRECTION COMPLET - VIDEOFLOW DUPLICATE FINDER

**Date de création:** 2025-12-14
**Bugs identifiés:** 35 (17 backend + 12 UI + 6 progression)
**Estimation totale:** 3-4 semaines
**Priorité:** Critique → Élevé → Moyen → Faible

---

## 🎯 VUE D'ENSEMBLE

### Répartition par Gravité
- 🔴 **Critiques:** 6 bugs (17%) → **Phase 1 (2-3 jours)**
- 🟠 **Élevés:** 11 bugs (31%) → **Phase 2 (5-7 jours)**
- 🟡 **Moyens:** 13 bugs (37%) → **Phase 3 (1-2 semaines)**
- 🟢 **Faibles:** 5 bugs (14%) → **Phase 4 (optionnel)**

### Répartition par Catégorie
- **Backend:** 17 bugs (49%)
- **UI/Mémoire:** 12 bugs (34%)
- **Progression:** 6 bugs (17%)

---

## 🚨 PHASE 1: CORRECTIONS CRITIQUES (2-3 JOURS)

**Objectif:** Stabiliser l'application, corriger les bugs qui causent crashes et fuites mémoire.

### Jour 1: Fixes Backend Critiques

#### Bug #1 - Tables `video_hashes` vs `method_signatures` dupliquées
**Fichiers:** Base de données SQLite
**Temps estimé:** 3-4 heures
**Complexité:** Moyenne

**Actions:**
```sql
-- 1. Migration des données (script SQL)
INSERT INTO method_signatures
  (video_id, method_name, params_hash, params_json, signature_blob,
   file_sha256, file_size, modification_time, created_at)
SELECT
  video_id, method_name, params_hash, params_json, hash_blob,
  file_sha256, file_size, modification_time, computed_at
FROM video_hashes
WHERE NOT EXISTS (
  SELECT 1 FROM method_signatures ms
  WHERE ms.video_id = video_hashes.video_id
    AND ms.method_name = video_hashes.method_name
    AND ms.params_hash = video_hashes.params_hash
);

-- 2. Supprimer l'ancienne table
DROP TABLE video_hashes;
DROP INDEX idx_video_hashes;
DROP INDEX idx_video_hashes_sha;

-- 3. Vérifier les contraintes
PRAGMA foreign_key_check;
```

**Refactoring code:**
```python
# Rechercher et remplacer dans TOUS les fichiers:
# video_hashes → method_signatures
# hash_blob → signature_blob
# computed_at → created_at
```

**Tests:**
- Vérifier que tous les caches fonctionnent
- Relancer un benchmark complet
- Valider les signatures vidéo

---

#### Bug #3 - Import manquant dans `benchmark_manager.py`
**Fichiers:** `src/plugins/duplicate_finder/services/benchmark_manager.py`
**Temps estimé:** 5 minutes
**Complexité:** Triviale

**Actions:**
```python
# Ligne 10: AJOUTER
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED

# Ligne 796: SUPPRIMER la ligne d'import local
# from concurrent.futures import wait, FIRST_COMPLETED  ← SUPPRIMER
```

**Tests:**
- Lancer un benchmark
- Vérifier qu'aucun NameError n'est levé

---

### Jour 2: Fixes UI Critiques (Fuites Mémoire)

#### Bug #18 - Fuites mémoire: Dialogues non nettoyés
**Fichiers:** `ui/multi_pipeline_benchmark.py`, `ui/benchmark_widgets.py`, etc.
**Temps estimé:** 4-5 heures
**Complexité:** Élevée

**Actions:**
```python
# 1. Créer méthode de cleanup dans MultiPipelineBenchmarkWidget
def _cleanup_previous_benchmark(self):
    """Nettoyer le benchmark précédent."""
    if self.runner:
        try:
            # Déconnecter TOUS les signaux
            self.runner.pipeline_progress.disconnect()
            self.runner.pair_progress.disconnect()
            self.runner.pipeline_metrics_updated.disconnect()
            self.runner.pipeline_completed.disconnect()
            self.runner.finished.disconnect()
            self.runner.error.disconnect()
            self.runner.hashing_progress.disconnect()
        except TypeError:
            pass  # Signaux déjà déconnectés

        # Arrêter le thread
        if self.runner.isRunning():
            self.runner.stop()
            self.runner.wait(2000)

        # Libérer la mémoire
        self.runner.deleteLater()
        self.runner = None

    # Fermer et détruire l'ancien dialog
    if self.monitor_dialog:
        self.monitor_dialog.close()
        self.monitor_dialog.deleteLater()
        self.monitor_dialog = None

# 2. Appeler au début de _on_start_benchmark
def _on_start_benchmark(self):
    # AJOUTER EN PREMIER:
    self._cleanup_previous_benchmark()

    # ... reste du code existant
```

**À répéter pour:**
- `benchmark_widgets.py` (ligne 1965)
- `simplified_benchmark.py` (ligne 294)
- `report_dialog.py` (ligne 264)
- `smart_test_set_dialog.py` (ligne 373)

**Tests:**
- Lancer 100 benchmarks consécutifs
- Monitorer la mémoire (doit rester stable)
- Vérifier que les dialogs se ferment proprement

---

#### Bug #19 - Matplotlib backend incorrect
**Fichiers:** `ui/benchmark_widgets.py`
**Temps estimé:** 10 minutes
**Complexité:** Triviale

**Actions:**
```python
# Ligne 24-32: MODIFIER
try:
    import matplotlib
    matplotlib.use('QtAgg')  # ✅ Backend universel PyQt5/PyQt6
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    FigureCanvas = None
```

**Tests:**
- Ouvrir un widget avec graphique ROC
- Vérifier qu'aucun crash ne se produit
- Afficher plusieurs graphiques

---

### Jour 3: Fixes Progression Critiques

#### Bug #30 - Double émission de progression finale
**Fichiers:** `services/benchmark_manager.py`
**Temps estimé:** 5 minutes
**Complexité:** Triviale

**Actions:**
```python
# Ligne 928-930: SUPPRIMER la ligne 930
emit_intermediate_metrics()
# self.pipeline_progress.emit(total_pairs, total_pairs, pipeline_name)  ← SUPPRIMER
```

**Tests:**
- Lancer un benchmark
- Observer les logs de progression
- Vérifier qu'aucune valeur n'est émise 2 fois

---

#### Bug #31 - Race condition sur `pairs_processed`
**Fichiers:** `services/benchmark_manager.py`
**Temps estimé:** 30 minutes
**Complexité:** Moyenne

**Actions:**
```python
# Ligne 591-627: MODIFIER emit_intermediate_metrics
def emit_intermediate_metrics():
    """Émet les métriques intermédiaires (thread-safe)."""
    # PROTÉGER la lecture avec le lock
    with metrics_lock:
        processed = pairs_processed[0]

    if processed == 0:
        return

    # Calculer métriques actuelles (avec la copie locale)
    elapsed = time.time() - pipeline_start_time
    tp, fp, tn, fn = metrics['tp'], metrics['fp'], metrics['tn'], metrics['fn']
    precision = (tp / (tp + fp)) * 100 if (tp + fp) > 0 else 0.0
    recall = (tp / (tp + fn)) * 100 if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    speed = elapsed / processed
    remaining = total_pairs - processed
    eta = speed * remaining

    # Émettre signaux (HORS du lock)
    self.pipeline_progress.emit(processed, total_pairs, pipeline_name)

    metrics_data = {
        'tp': tp, 'fp': fp, 'tn': tn, 'fn': fn,
        'precision': precision, 'recall': recall, 'f1': f1,
        'speed': speed, 'eta': eta,
        'processed': processed, 'total': total_pairs
    }
    self.pipeline_metrics_updated.emit(pipeline_name, metrics_data)
```

**Tests:**
- Lancer benchmark avec 1000 paires en parallèle
- Vérifier que la progression est monotone (jamais de recul)
- Aucune valeur dupliquée

---

### 📊 Livrable Phase 1
- ✅ Application stable (pas de crash)
- ✅ Fuites mémoire corrigées
- ✅ Progression correcte
- ✅ Tests de régression passés

**Temps total Phase 1:** 2-3 jours

---

## 🟠 PHASE 2: CORRECTIONS ÉLEVÉES (5-7 JOURS)

**Objectif:** Corriger les bugs qui causent des comportements incorrects.

### Jour 4-5: Fixes Backend Élevés

#### Bug #2 - Race condition dans `pipeline_manager.update_pipeline()`
**Fichiers:** `orchestration/pipeline_manager.py`
**Temps estimé:** 1-2 heures
**Complexité:** Moyenne

**Actions:**
```python
# Ligne 218-224: MODIFIER
elif global_threshold is not None:
    # Mettre à jour avec transaction atomique
    with self.db.pool.get_connection() as conn:
        cursor = conn.cursor()

        # SELECT FOR UPDATE pour verrouiller la ligne
        cursor.execute(
            "SELECT methods_json FROM saved_pipelines WHERE id = ? FOR UPDATE",
            (pipeline_id,)
        )
        row = cursor.fetchone()

        if not row:
            raise ValueError(f"Pipeline {pipeline_id} not found")

        # Parser et mettre à jour
        current_methods = self._parse_methods_payload(row[0])
        payload = {
            "methods": current_methods["methods"],
            "global_threshold": global_threshold
        }

        updates.append("methods_json = ?")
        params.append(json.dumps(payload, ensure_ascii=False))
```

**Tests:**
- Mettre à jour un pipeline depuis 2 threads simultanément
- Vérifier qu'aucune mise à jour n'est perdue

---

#### Bug #5 - Normalisation de labels incomplète
**Fichiers:** `services/benchmark_manager.py`
**Temps estimé:** 30 minutes
**Complexité:** Faible

**Actions:**
```python
# Ligne 23-52: REMPLACER la fonction
def normalize_expected_label(expected: str) -> str:
    """Normalise les labels de test en 'positive', 'negative', ou 'unknown'."""
    # Normaliser casse et whitespace
    expected_lower = str(expected).strip().lower()

    label_map = {
        # Anglais
        'scene_found': 'positive',
        'duplicate': 'positive',
        'positive': 'positive',
        'yes': 'positive',
        'true': 'positive',
        '1': 'positive',

        'scene_not_found': 'negative',
        'not_duplicate': 'negative',
        'negative': 'negative',
        'no': 'negative',
        'false': 'negative',
        '0': 'negative',

        # Français
        'positif': 'positive',
        'oui': 'positive',
        'négatif': 'negative',
        'non': 'negative',
        'inconnu': 'unknown',

        # Par défaut
        'unknown': 'unknown'
    }

    normalized = label_map.get(expected_lower, 'unknown')

    if normalized != expected_lower and normalized != 'unknown':
        logger.debug(f"Normalized label '{expected}' → '{normalized}'")

    return normalized
```

**Tests:**
- Tester avec tous les formats: 'YES', 'yes', 'oui', '1', 'true', etc.
- Vérifier les statistiques de benchmark

---

### Jour 6-7: Fixes UI Élevés

#### Bug #20 - Race condition signal `finished` connecté trop tard
**Fichiers:** `ui/multi_pipeline_benchmark.py`, `ui/benchmark_widgets.py`
**Temps estimé:** 2-3 heures
**Complexité:** Moyenne

**Actions:**
```python
# Réorganiser _on_start_benchmark pour connecter AVANT start()
def _on_start_benchmark(self):
    # 1. Cleanup
    self._cleanup_previous_benchmark()

    # 2. Validate
    if not self.test_set_combo.currentData():
        return

    selected_pipelines = self._get_selected_pipelines()
    if not selected_pipelines:
        return

    # 3. Créer runner
    test_set = self.test_set_combo.currentData()
    test_pairs = self.test_set_manager.get_test_set(test_set['name'])

    run_label = f"Benchmark: {test_set['name']} with {len(selected_pipelines)} pipelines"
    self.runner = BenchmarkRunner(
        self.db_manager, test_pairs, selected_pipelines, run_label,
        max_pipeline_workers=min(len(selected_pipelines), 3),
        max_pair_workers=4
    )

    # 4. Connecter TOUS les signaux AVANT start()
    self.runner.pipeline_progress.connect(self._on_pipeline_progress)
    self.runner.pair_progress.connect(self._on_pair_progress)
    self.runner.pipeline_metrics_updated.connect(self._on_pipeline_metrics_updated)
    self.runner.pipeline_completed.connect(self._on_pipeline_completed)
    self.runner.finished.connect(self._on_benchmark_finished)
    self.runner.error.connect(self._on_benchmark_error)

    # 5. Créer dialog
    self.monitor_dialog = EnhancedBenchmarkMonitor(parent=self)

    # 6. Connecter signaux du dialog
    self.runner.hashing_progress.connect(self.monitor_dialog.update_hash_progress)
    self.runner.pipeline_progress.connect(self.monitor_dialog.update_pipeline_progress)
    self.runner.pipeline_metrics_updated.connect(self.monitor_dialog.update_metrics)
    self.monitor_dialog.stop_requested.connect(self.stop_benchmark)

    # 7. Update UI
    self.start_btn.setEnabled(False)
    self.stop_btn.setVisible(True)
    self.monitor_dialog.start_benchmark()

    # 8. Afficher dialog
    self.monitor_dialog.show()

    # 9. DÉMARRER EN DERNIER (après TOUTES les connexions)
    self.runner.start()
```

**Tests:**
- Lancer 50 benchmarks rapides (1-2 paires)
- Vérifier que finished est toujours capturé
- Dialog se ferme toujours

---

#### Bug #32 - Progression peut dépasser 100%
**Fichiers:** `ui/multi_pipeline_benchmark.py`, `ui/benchmark_widgets.py`
**Temps estimé:** 1 heure
**Complexité:** Faible

**Actions:**
```python
# Ajouter validation dans TOUS les handlers de progression
def _on_pipeline_progress(self, current, total, pipeline_name):
    """Handle pipeline progress update (with validation)."""
    # VALIDATION: Clamper current à [0, total]
    current_clamped = max(0, min(current, total))

    if current != current_clamped:
        logger.warning(
            f"⚠️ Progress overflow detected: {current}/{total} for {pipeline_name}"
            f" (clamped to {current_clamped}/{total})"
        )

    # Mettre à jour barre de progression
    if pipeline_name in self.pipeline_progress_bars:
        label, pbar = self.pipeline_progress_bars[pipeline_name]
        pbar.setMaximum(total)
        pbar.setValue(current_clamped)

        # Calculer pourcentage avec validation
        percent = (current_clamped / total * 100) if total > 0 else 0
        percent_clamped = min(percent, 100.0)

        label.setText(f"{pipeline_name}: {current_clamped}/{total} ({percent_clamped:.1f}%)")
```

**Tests:**
- Simuler overflow (modifier temporairement le code)
- Vérifier que la barre ne dépasse jamais 100%

---

### 📊 Livrable Phase 2
- ✅ Comportements corrects (pas de race conditions)
- ✅ Progression validée (jamais >100%)
- ✅ Labels normalisés
- ✅ Tests d'intégration passés

**Temps total Phase 2:** 5-7 jours

---

## 🟡 PHASE 3: CORRECTIONS MOYENNES (1-2 SEMAINES)

**Objectif:** Améliorer la qualité, la performance et l'expérience utilisateur.

### Semaine 2: Cleanup & Performance

#### Bug #6 - Gestion d'erreur silencieuse
**Temps:** 2 heures

```python
# benchmark_manager.py ligne 539-542
except Exception as e:
    logger.error(f"[{pipeline_name}] Precompute hashes failed: {e}", exc_info=True)
    # Émettre progression réelle, pas 100%
    current = sum(1 for _ in completed_hashes if _ is not None)
    self.hashing_progress.emit(current, total, pipeline_name)
```

---

#### Bug #8 - Cache invalidation
**Temps:** 3-4 heures

```sql
-- Créer trigger SQL
CREATE TRIGGER invalidate_signatures_on_sha_change
AFTER UPDATE OF file_sha256 ON video_files
WHEN OLD.file_sha256 IS NOT NULL AND NEW.file_sha256 != OLD.file_sha256
BEGIN
    DELETE FROM method_signatures WHERE video_id = NEW.id;
    DELETE FROM dense_hashes WHERE video_id = NEW.id;
    DELETE FROM lsh_fingerprints WHERE video_id = NEW.id;
    DELETE FROM verification_cache
    WHERE short_video_id = NEW.id OR long_video_id = NEW.id;
END;
```

---

#### Bug #14 - Index manquant sur `verification_cache.config_hash`
**Temps:** 10 minutes

```sql
DROP INDEX idx_verification_videos;

CREATE INDEX idx_verification_cache_lookup
ON verification_cache(short_video_id, long_video_id, start_time, config_hash);
```

---

#### Bug #15 - Contrainte UNIQUE manquante sur `benchmark_results`
**Temps:** 15 minutes

```sql
CREATE UNIQUE INDEX idx_benchmark_results_unique
ON benchmark_results(benchmark_run_id, pipeline_name);
```

```python
# Modifier insertion
cursor.execute("""
    INSERT OR REPLACE INTO benchmark_results
    (benchmark_run_id, pipeline_name, ...)
    VALUES (?, ?, ...)
""", (...))
```

---

#### Bug #22 - Aucun `closeEvent()` pour cleanup
**Temps:** 4-5 heures

Ajouter `closeEvent()` dans 26 fichiers UI:

```python
# Template pour chaque widget
def closeEvent(self, event):
    """Cleanup lors de la fermeture."""
    # 1. Arrêter les timers
    if hasattr(self, 'refresh_timer') and self.refresh_timer:
        self.refresh_timer.stop()
        self.refresh_timer.deleteLater()
        self.refresh_timer = None

    # 2. Déconnecter les signaux
    if hasattr(self, 'runner') and self.runner:
        try:
            self.runner.disconnect()
        except TypeError:
            pass

    # 3. Appeler le closeEvent parent
    super().closeEvent(event)
```

---

#### Bug #23 - Import try/except dupliqué
**Temps:** 15 minutes

```python
# main_window.py: SUPPRIMER le try/except inutile (lignes 25-80)
# Garder uniquement les imports directs
from .detection.video import VideoHasher
from .ui.dialogs.comparison_dialog import ComparisonDialog
# ... tous les autres imports
```

---

#### Bug #34 - Progression reset pas appelée
**Temps:** 1 heure

```python
def _on_start_benchmark(self):
    # RESET toutes les progressions EN PREMIER
    self.progress_bar.setValue(0)
    self.progress_bar.setMaximum(100)
    self.status_label.setText("Démarrage...")
    self.pair_status_label.setText("")

    # Reset pipeline progress bars
    for name, (label, pbar) in self.pipeline_progress_bars.items():
        pbar.setValue(0)
        pbar.setMaximum(100)
        label.setText(f"{name}: En attente...")

    # Ensuite: cleanup, création runner, etc.
```

---

#### Bug #35 - emit() appelé trop fréquemment
**Temps:** 30 minutes

```python
# Throttle les émissions: 1 fois/seconde OU tous les 10 paires
last_emit_time = [0.0]
emit_interval = 1.0  # secondes

finally:
    with metrics_lock:
        pairs_processed[0] += 1
        processed = pairs_processed[0]

    current_time = time.time()
    should_emit = (
        current_time - last_emit_time[0] >= emit_interval  # Throttle temporel
        or processed % 10 == 0  # Ou tous les 10 paires
        or processed == total_pairs  # Ou à la fin
    )

    if should_emit:
        emit_intermediate_metrics()
        last_emit_time[0] = current_time
```

---

### 📊 Livrable Phase 3
- ✅ Performance optimisée (-50% overhead)
- ✅ Cleanup complet (tous les widgets)
- ✅ Cache invalidation automatique
- ✅ Index DB optimisés
- ✅ Code simplifié (imports, erreurs)

**Temps total Phase 3:** 1-2 semaines

---

## 🟢 PHASE 4: AMÉLIORATIONS OPTIONNELLES (1 semaine)

**Objectif:** Dette technique, refactoring, optimisations avancées.

### Bugs Faibles à Corriger

#### Bug #4 - `_precompute_hashes()` trop complexe (290 lignes)
**Temps:** 2-3 jours
**Complexité:** Élevée

Refactoriser en classe:
```python
class PrecomputeHashesStrategy:
    def __init__(self, db_manager, pipeline_config, test_pairs):
        self.db = db_manager
        self.config = pipeline_config
        self.test_pairs = test_pairs

    def execute(self, progress_callback):
        self._precompute_sha256(progress_callback)

        for method in self.config.get('methods', []):
            handler = self._get_handler(method['name'])
            handler.precompute(progress_callback)

    def _precompute_sha256(self, progress_callback):
        # 30 lignes max

    def _get_handler(self, method_name):
        handlers = {
            'frame_hash': FrameHashHandler(self.db),
            'dct_coefficients': DCTHandler(self.db),
            # ...
        }
        return handlers.get(method_name)
```

---

#### Bug #10 - Wildcard imports
**Temps:** 30 minutes

```python
# infrastructure/__init__.py
from .config import Config, ConfigManager, DefaultConfig
from .alerts import Alert, AlertManager, AlertLevel
# Au lieu de:
# from .config import *
# from .alerts import *
```

---

#### Bug #16 - BenchmarkRunner trop de responsabilités
**Temps:** 3-4 jours

Décomposer en:
- `BenchmarkRunner(QThread)` - Orchestration thread
- `BenchmarkOrchestrator` - Logique métier
- `BenchmarkExecutor` - Exécution parallèle
- `BenchmarkResultStorage` - Persistance

---

#### Bug #27 - Widgets recréés en boucle
**Temps:** 2 heures

Réutiliser au lieu de recréer:
```python
def _load_pipelines(self):
    pipelines = self.pipeline_manager.list_pipelines()
    current_names = set(self.pipeline_checkboxes.keys())
    new_names = {p['name'] for p in pipelines}

    # Supprimer uniquement les pipelines disparus
    for name in current_names - new_names:
        checkbox = self.pipeline_checkboxes.pop(name)
        self.pipeline_layout.removeWidget(checkbox)
        checkbox.deleteLater()

    # Ajouter uniquement les NOUVEAUX
    for pipeline in pipelines:
        name = pipeline['name']
        if name not in self.pipeline_checkboxes:
            checkbox = QCheckBox(...)
            self.pipeline_checkboxes[name] = checkbox
            self.pipeline_layout.addWidget(checkbox)
```

---

### 📊 Livrable Phase 4
- ✅ Code refactoré (meilleure maintenabilité)
- ✅ Performance optimale
- ✅ Architecture propre (SRP, DIP)

**Temps total Phase 4:** 1 semaine (optionnel)

---

## 📅 PLANNING GLOBAL

```
Semaine 1: Phase 1 (Critiques)
├─ Jour 1: Bugs backend critiques (#1, #3)
├─ Jour 2: Bugs UI critiques (#18, #19)
└─ Jour 3: Bugs progression critiques (#30, #31)

Semaine 2: Phase 2 (Élevés)
├─ Jour 4-5: Bugs backend élevés (#2, #5)
├─ Jour 6-7: Bugs UI élevés (#20, #32)
└─ Jour 8-9: Tests d'intégration

Semaine 3-4: Phase 3 (Moyens)
├─ Bugs 6-11: Cleanup & erreurs
├─ Bugs 14-15: Index DB
├─ Bugs 22-23: UI cleanup
└─ Bugs 34-35: Progression perf

Semaine 5 (optionnel): Phase 4 (Faibles)
├─ Refactoring majeur (#4, #16)
├─ Optimisations (#27, #28)
└─ Documentation
```

---

## ✅ CHECKLIST DE VALIDATION

### Après Phase 1
- [ ] Application ne crash plus
- [ ] Fuites mémoire corrigées (test 100 benchmarks)
- [ ] Progression correcte (monotone, pas >100%)
- [ ] Backend matplotlib fonctionne
- [ ] Imports tous présents

### Après Phase 2
- [ ] Aucune race condition détectée
- [ ] Labels tous normalisés
- [ ] Signal finished toujours capturé
- [ ] Progression validée (<= 100%)

### Après Phase 3
- [ ] Tous les widgets ont closeEvent()
- [ ] Émissions throttlées (perf +50%)
- [ ] Index DB optimisés
- [ ] Cache invalidation automatique
- [ ] Code simplifié (pas d'imports dupliqués)

### Après Phase 4 (optionnel)
- [ ] Architecture refactorée (classes <500 lignes)
- [ ] Widgets réutilisés (pas recréés)
- [ ] Tables virtualisées (10k+ lignes)
- [ ] Code coverage >80%

---

## 🎯 MÉTRIQUES DE SUCCÈS

### Performance
- **Avant:** 100 benchmarks → crash
- **Après Phase 1:** 1000+ benchmarks sans crash
- **Après Phase 3:** Overhead signaux -90%

### Qualité
- **Avant:** Score 6.5/10
- **Après Phase 1:** Score 7.5/10
- **Après Phase 2:** Score 8.5/10
- **Après Phase 3:** Score 9.0/10

### Stabilité
- **Avant:** Fuites mémoire +50MB/benchmark
- **Après Phase 1:** Mémoire stable
- **Après Phase 3:** CPU -30%

---

## 📝 NOTES IMPORTANTES

### Ordre des Corrections
- ✅ **TOUJOURS** corriger dans l'ordre: Critique → Élevé → Moyen → Faible
- ✅ **NE PAS** sauter les phases (dépendances entre bugs)
- ✅ **TESTER** après chaque bug corrigé

### Gestion des Risques
- Créer une branche `bugfix/critical` pour Phase 1
- Créer une branche `bugfix/high` pour Phase 2
- Merge après validation complète

### Documentation
- Mettre à jour CHANGELOG.md après chaque phase
- Documenter les breaking changes
- Créer guide de migration si nécessaire

---

**Auteur:** Claude Code Analysis System
**Date:** 2025-12-14
**Version:** 1.0
**Statut:** Plan validé, prêt pour exécution
