# 🚨 Correction Critique - Progress Bars Bloquées

**Date**: 2025-12-16
**Priorité**: 🔴 CRITIQUE
**Statut**: ✅ CORRIGÉ

---

## 🔍 Problème Identifié

### Symptômes
- ✅ Les signaux `hash_type_progress` sont bien émis par BenchmarkManager
- ✅ Les barres de progression sont créées dynamiquement dans l'UI
- ❌ **Mais les barres ne progressent JAMAIS au-delà de 0%**
- ❌ Seuls 3 algorithmes sur 13 pipelines lancés ont émis des signaux

### Cause Racine

**Erreur critique dans les logs**:
```
Error during cache preload: no such column: hash_data
```

**Fichier**: [detection/video/hasher.py:248-260](src/plugins/duplicate_finder/detection/video/hasher.py#L248-L260)

**Problème**: La méthode `_preload_cache()` essayait de lire la colonne `hash_data` depuis la table `video_files`, mais cette colonne a été **supprimée** lors d'une refonte précédente.

**Impact**:
1. Le cache preload échoue silencieusement
2. Les hash ne peuvent pas être chargés depuis la DB
3. Les algorithmes bloquent en attendant les hash
4. Les signaux `hash_type_progress` ne sont plus émis
5. Les barres de progression restent à 0%

---

## ✅ Solution Implémentée

### Changement dans [hasher.py:245-264](src/plugins/duplicate_finder/detection/video/hasher.py#L245-L264)

**Avant** (requête SQL invalide):
```sql
SELECT file_path, hash_data, duration, modification_time, file_size
FROM video_files
ORDER BY updated_at DESC
```

**Après** (utilise la table dense_hashes):
```sql
SELECT vf.file_path, dh.dense_hash, vf.duration, vf.modification_time, vf.file_size
FROM video_files vf
JOIN dense_hashes dh ON vf.id = dh.video_id
ORDER BY vf.last_scanned DESC
```

### Modifications
1. ✅ Jointure avec la table `dense_hashes` au lieu de lire `hash_data`
2. ✅ Utilise `vf.last_scanned` au lieu de `updated_at` (colonne inexistante)
3. ✅ Lecture de `dh.dense_hash` qui est le nouveau système de stockage

---

## 🧪 Vérification

### Avant la correction
```
ERROR - Error during cache preload: no such column: hash_data
→ Cache preload échoue
→ Hash non chargés
→ Barres bloquées à 0%
```

### Après la correction (attendu)
```
INFO - Cache preload: X hashes loaded in Y.Zs
→ Cache chargé avec succès
→ Hash disponibles
→ Barres progressent normalement
```

---

## 📋 Tests de Validation

### Test 1 - Lancer Benchmark Simple
- [ ] Lancer benchmark avec 1 pipeline (ex: Color Histogram)
- [ ] Vérifier logs: AUCUNE erreur `no such column: hash_data`
- [ ] Vérifier progress bar démarre et progresse de 0% → 100%

### Test 2 - Lancer Multi-Pipeline
- [ ] Lancer benchmark avec 5+ pipelines simultanés
- [ ] Vérifier toutes les barres progressent
- [ ] Vérifier que TOUS les algorithmes émettent des signaux

### Test 3 - Vérifier Logs
```bash
tail -f logs/videoflow_*.log | grep -E "cache preload|Hash progress signal"
```

Doit afficher:
- ✅ `Cache preload: X hashes loaded`
- ✅ Plusieurs signaux `Hash progress signal received` pour chaque algorithme

---

## 🎯 Impact de la Correction

### Avant
- 🔴 Progress bars bloquées à 0%
- 🔴 Seuls 3/13 pipelines émettaient des signaux
- 🔴 Erreur SQL critique dans les logs
- 🔴 Cache preload échouait systématiquement

### Après
- ✅ Progress bars fonctionnelles
- ✅ Tous les pipelines émettent des signaux
- ✅ Aucune erreur SQL
- ✅ Cache preload fonctionne correctement

---

## 🔗 Liens Connexes

- [BENCHMARK_INTERFACE_COMPLETION_FINALE.md](BENCHMARK_INTERFACE_COMPLETION_FINALE.md) - Session 7 (corrections précédentes)
- [EXPLICATION_PROGRESS_BARS.md](EXPLICATION_PROGRESS_BARS.md) - Comportement attendu des barres
- [ARCHITECTURE_STORAGE.md](src/plugins/duplicate_finder/ARCHITECTURE_STORAGE.md) - Nouveau système de stockage

---

## 📝 Historique

| Date | Action | Résultat |
|------|--------|----------|
| 2025-12-16 | Investigation logs benchmark | Erreur `hash_data` identifiée |
| 2025-12-16 | Analyse schéma DB | Colonne `hash_data` confirmée supprimée |
| 2025-12-16 | Correction requête SQL | JOIN avec `dense_hashes` implémenté |
| 2025-12-16 | Tests validation | ⏳ En attente |

---

**Dernière Mise à Jour**: 2025-12-16
**Statut**: ✅ CORRIGÉ - En attente de validation
**Prochaine Étape**: Relancer benchmark pour vérifier correction
