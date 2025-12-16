# 🔍 Diagnostic Final - Progress Bars

**Date**: 2025-12-16 13:35
**Statut**: 🔴 **BUG CRITIQUE IDENTIFIÉ**

---

## 🎯 Résumé

Les progress bars **fonctionnent partiellement** :
- ✅ Signaux `hash_type_progress` **sont bien émis** au démarrage
- ❌ Signaux **ne progressent JAMAIS** au-delà de 0%
- ❌ Signaux **ne sont jamais émis à 100%**

---

## 🐛 Bug Critique Détecté

### Symptôme

```
[  0.000s] color: 0/4 (  0.0%)
... benchmark se termine ...
AUCUNE autre mise à jour!
```

**Résultat** : La progress bar reste bloquée à 0% même si le benchmark se termine avec succès.

### Cause Racine

Le code émet `hash_type_progress` dans deux situations :

1. **Initialisation** (`init_hash_type`) :
   ```python
   self.hash_type_progress.emit(hash_type, 0, total_work, pipeline_name)
   ```
   ✅ **Appelé** → Signal émis à 0%

2. **Mise à jour** (`update_hash_type_progress`) :
   ```python
   hash_progress[hash_type]['current'] += 1
   self.hash_type_progress.emit(hash_type, current, total, pipeline_name)
   ```
   ❌ **JAMAIS APPELÉ** si hash en cache

### Pourquoi `update_hash_type_progress()` n'est jamais appelé ?

**Fichier** : [benchmark_manager.py:613-668](src/plugins/duplicate_finder/services/benchmark_manager.py#L613-L668)

Le code appelle `update_hash_type_progress()` **UNIQUEMENT** après calcul de hash :

```python
if wants_color:
    vam_worker._get_color_signatures(path, duration, samples)
    update_hash_type_progress('color')  # ← APPELÉ ICI
```

**MAIS** : Si les hash sont déjà dans le **cache du VideoHasher**, `_precompute_hashes()` **n'est jamais appelé** ou **skip le calcul**.

**Résultat** :
- Init signal émis : `color = 0/4`
- Hash déjà en cache → Skip calcul
- `update_hash_type_progress('color')` jamais appelé
- **Progress bar reste à 0%** ❌

---

## 📊 Tests Effectués

### Test 1: Test Minimal (20s)
**Script**: [test_pipelines_minimal.sh](scripts/test_pipelines_minimal.sh)

**Résultat** :
```
✅ 3 signaux hash_type_progress détectés (color, edge, motion)
```

**Mais** : Aucune vérification de la **progression** (0% → 100%)

### Test 2: Test Temps Réel (avec cache)
**Script**: [test_progress_real_time.py](scripts/test_progress_real_time.py)

**Résultat** :
```
❌ color: Range 0.0% → 0.0%
❌ Updates: 1
❌ N'a pas atteint 100%
```

**Cause** : Cache de vérification utilisé → Aucun calcul → Aucune mise à jour

### Test 3: Test Sans Cache
**Script**: [test_progress_no_cache.py](scripts/test_progress_no_cache.py)

**Résultat** :
```
✅ Cache de vérification vidé (121 entrées supprimées)
❌ color: 0/4 (0.0%) → JAMAIS MIS À JOUR
❌ Progression: 0.0% → 0.0%
❌ N'a pas atteint 100%
```

**Cause** : Hash déjà dans le cache du **VideoHasher** (pas le cache de vérification) → `_precompute_hashes()` skip le calcul → Aucune mise à jour émise

---

## 🔧 Solution Proposée

### Option 1: Émettre signal final à 100%

Ajouter dans `_run_single_pipeline()` après completion :

```python
# At end of pipeline
for hash_type in hash_progress.keys():
    total = hash_progress[hash_type]['total']
    self.hash_type_progress.emit(hash_type, total, total, pipeline_name)  # 100%
```

**Avantage** : Simple, garanti que la barre atteint 100%
**Inconvénient** : Pas de progression intermédiaire si cache utilisé

### Option 2: Émettre à chaque vidéo traitée

Dans la boucle de traitement des paires, émettre une mise à jour :

```python
# After each video processed
for hash_type in hash_progress.keys():
    hash_progress[hash_type]['current'] += 1
    current = hash_progress[hash_type]['current']
    total = hash_progress[hash_type]['total']
    self.hash_type_progress.emit(hash_type, current, total, pipeline_name)
```

**Avantage** : Progression visible même avec cache
**Inconvénient** : Plus complexe, doit tracker quel hash pour quelle vidéo

### Option 3: Mode "cache" spécial

Si détection que tout vient du cache :
```python
if all_from_cache:
    # Emit simulated progress
    for i in range(0, total+1):
        self.hash_type_progress.emit(hash_type, i, total, pipeline_name)
        time.sleep(0.01)  # Smooth animation
```

**Avantage** : UX fluide même avec cache
**Inconvénient** : "Faux" progrès, pas le vrai état

---

## 📈 Recommandation

**Implémenter Option 1 + Option 2** :

1. **Option 1** (garanti) : Toujours émettre à 100% à la fin
2. **Option 2** (nice-to-have) : Émettre pendant traitement si possible

**Code proposé** :

```python
def _run_single_pipeline(self, pipeline_config: Dict):
    # ... existing code ...

    # At the END, ensure all progress bars reach 100%
    with progress_lock:
        for hash_type, progress_data in hash_progress.items():
            total = progress_data['total']
            # Force emit 100%
            self.hash_type_progress.emit(hash_type, total, total, pipeline_name)
            logger.debug(f"✅ Progress bar {hash_type} completed: {total}/{total}")
```

---

## 🎯 Impact

### Avant Fix
- Progress bar démarre à 0%
- **Reste bloquée à 0%** pendant tout le benchmark
- Utilisateur pense que c'est gelé
- **UX cassée** ❌

### Après Fix
- Progress bar démarre à 0%
- **Progresse** pendant le traitement (si pas de cache)
- **Atteint toujours 100%** à la fin
- Utilisateur voit la complétion
- **UX OK** ✅

---

## 📝 Fichiers à Modifier

### 1. [benchmark_manager.py](src/plugins/duplicate_finder/services/benchmark_manager.py)

**Ligne ~720** (fin de `_run_single_pipeline`) :

```python
# Ensure all hash progress bars reach 100%
with progress_lock:
    for hash_type in list(hash_progress.keys()):
        total = hash_progress[hash_type]['total']
        current = hash_progress[hash_type]['current']

        if current < total:
            # Force complete
            self.hash_type_progress.emit(hash_type, total, total, pipeline_name)
            logger.debug(f"[{pipeline_name}] Completed progress: {hash_type} → 100%")
```

---

## ✅ Tests de Validation

Après fix, relancer :

```bash
# Test 1: Vérifier que la barre atteint 100%
python3 scripts/test_progress_real_time.py --pairs 2 --pipeline-id 1

# Attendu:
# ✅ color: 0.0% → 100.0%
# ✅ N'a atteint 100%
```

```bash
# Test 2: Test sans cache
python3 scripts/test_progress_no_cache.py

# Attendu:
# ✅ color: Updates > 1
# ✅ Max reached: 100.0%
```

---

## 🚨 Conclusion

**La correction `hash_data` fonctionne** ✅ (les signaux sont émis)

**MAIS** il y a un **bug additionnel** ❌ :
- Les signaux ne progressent jamais au-delà de 0%
- Les progress bars restent bloquées
- L'UX est cassée

**Next Action** : Implémenter le fix proposé (Option 1) pour garantir que les barres atteignent toujours 100%.

---

**Dernière Mise à Jour**: 2025-12-16 13:40
**Statut**: 🔴 BUG IDENTIFIÉ - FIX PROPOSÉ
**Priorité**: 🔴 CRITIQUE (UX)
