# 📚 Documentation DuplicateFlow

**Bienvenue dans la documentation complète de DuplicateFlow !**

Cette documentation a été créée le **2025-12-19** pour faciliter la reprise de développement par n'importe quelle session Claude Code.

---

## 🎯 Par où commencer ?

### Si vous reprenez le développement:
1. **[RESUME_CONTEXT.md](RESUME_CONTEXT.md)** - Contexte complet pour reprise instantanée ⭐
2. **[CURRENT_WORK.md](CURRENT_WORK.md)** - État actuel du développement
3. **[../NEXT_STEPS.md](../NEXT_STEPS.md)** - Checklist des prochaines étapes

### Si vous voulez comprendre le code:
1. **[DUPLICATEFLOW_ARCHITECTURE.md](DUPLICATEFLOW_ARCHITECTURE.md)** - Architecture complète (800+ lignes)
2. **[DUPLICATEFLOW_QUICK_REFERENCE.md](DUPLICATEFLOW_QUICK_REFERENCE.md)** - Référence rapide avec exemples

---

## 📁 Structure de la documentation

```
docs/
├── README.md                           # Ce fichier - Point d'entrée
│
├── RESUME_CONTEXT.md                   # ⭐ COMMENCER ICI pour reprise
│   └── TL;DR, contexte complet, commandes essentielles
│
├── CURRENT_WORK.md                     # État actuel du développement
│   └── Fichiers modifiés, tâches en cours, problèmes connus
│
├── DUPLICATEFLOW_ARCHITECTURE.md       # Architecture détaillée
│   └── 800+ lignes: composants, patterns, flux de données
│
└── DUPLICATEFLOW_QUICK_REFERENCE.md    # Référence rapide
    └── 600+ lignes: exemples, API, debugging
```

---

## 📖 Guide de lecture

### Scénario 1: "Je reprends le développement"

**Temps estimé: 15 min**

1. Lire **[RESUME_CONTEXT.md](RESUME_CONTEXT.md)** (5 min)
   - Section TL;DR
   - Section "Comment reprendre le développement"
   - Section "Tâches restantes"

2. Lire **[CURRENT_WORK.md](CURRENT_WORK.md)** (5 min)
   - Section "Fichiers modifiés récemment"
   - Section "Tâches en cours"
   - Section "Problèmes connus"

3. Lire **[../NEXT_STEPS.md](../NEXT_STEPS.md)** (5 min)
   - Checklist complète des actions

4. Exécuter:
   ```bash
   git status
   git log --oneline -10
   pytest duplicateflow/tests/ -v
   ```

### Scénario 2: "Je veux comprendre l'architecture"

**Temps estimé: 30 min**

1. Lire **[DUPLICATEFLOW_QUICK_REFERENCE.md](DUPLICATEFLOW_QUICK_REFERENCE.md)** (10 min)
   - Section "Démarrage rapide"
   - Section "Les 12 Presets"
   - Section "Les 16 Algorithmes"

2. Lire **[DUPLICATEFLOW_ARCHITECTURE.md](DUPLICATEFLOW_ARCHITECTURE.md)** (20 min)
   - Section "Vue d'ensemble"
   - Section "Composants principaux"
   - Section "Patterns de code"

3. Explorer le code:
   ```bash
   # Voir structure
   tree duplicateflow/ -L 2

   # Lire fichiers clés
   cat duplicateflow/core/registry.py
   cat duplicateflow/pipeline/pipeline.py
   cat duplicateflow/algorithms/frame_hash.py
   ```

### Scénario 3: "Je veux utiliser DuplicateFlow"

**Temps estimé: 10 min**

1. Lire **[DUPLICATEFLOW_QUICK_REFERENCE.md](DUPLICATEFLOW_QUICK_REFERENCE.md)** (10 min)
   - Section "Démarrage rapide"
   - Section "Les 12 Presets" (choisir un preset)
   - Section "Format des résultats"

2. Tester:
   ```python
   from duplicateflow.pipeline import Pipeline

   # Via preset
   pipeline = Pipeline.from_preset('balanced')
   result = pipeline.compare('video1.mp4', 'video2.mp4')
   print(f"Score: {result.global_score:.2f}%")
   print(f"Match: {result.accepted}")
   ```

### Scénario 4: "Je veux ajouter un algorithme"

**Temps estimé: 20 min**

1. Lire **[DUPLICATEFLOW_QUICK_REFERENCE.md](DUPLICATEFLOW_QUICK_REFERENCE.md)**
   - Section "Créer un algorithme custom"

2. Lire **[DUPLICATEFLOW_ARCHITECTURE.md](DUPLICATEFLOW_ARCHITECTURE.md)**
   - Section "Algorithms"
   - Section "Pattern d'enregistrement"

3. Étudier un algorithme existant:
   ```bash
   cat duplicateflow/algorithms/frame_hash.py
   cat duplicateflow/algorithms/color_histogram.py
   ```

4. Créer le vôtre en suivant le template

### Scénario 5: "Je dois débugger un problème"

**Temps estimé: variable**

1. Lire **[CURRENT_WORK.md](CURRENT_WORK.md)**
   - Section "Problèmes connus"

2. Lire **[DUPLICATEFLOW_QUICK_REFERENCE.md](DUPLICATEFLOW_QUICK_REFERENCE.md)**
   - Section "Debugging"

3. Lire **[../NEXT_STEPS.md](../NEXT_STEPS.md)**
   - Section "Commandes de diagnostic"
   - Section "En cas de problème"

4. Activer logs et analyser:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   # Re-run code problématique
   ```

---

## 🎓 Concepts clés à comprendre

Avant de plonger dans le code, familiarisez-vous avec ces concepts:

### 1. Registry Pattern
Tous les algorithmes s'auto-enregistrent:
```python
@register_algorithm(name="my_algo", ...)
class MyAlgorithm(Algorithm):
    pass
```

### 2. Pipeline Orchestration
Multi-algorithmes avec scoring pondéré:
```python
Pipeline([
    {'algorithm': 'A', 'weight': 0.5},
    {'algorithm': 'B', 'weight': 0.5}
])
```

### 3. Cache 3 niveaux
- Memory: File hashes
- SQLite: Extracted features
- SQLite: Comparison results

### 4. Validators
Filtrage pré/post comparaison:
```python
pre_validators=[LengthValidator(...)]
```

### 5. Partial Analysis
Analyser seulement N secondes:
```python
analyze_duration=60.0
```

---

## 📊 Tableau récapitulatif

| Document | Taille | Usage | Temps lecture |
|----------|--------|-------|---------------|
| **RESUME_CONTEXT.md** | ~900 lignes | Reprise développement | 15 min |
| **CURRENT_WORK.md** | ~600 lignes | État actuel | 10 min |
| **ARCHITECTURE.md** | ~800 lignes | Comprendre architecture | 30 min |
| **QUICK_REFERENCE.md** | ~600 lignes | Référence rapide | 20 min |
| **NEXT_STEPS.md** | ~400 lignes | Checklist actions | 10 min |

**Total**: ~3,300 lignes de documentation

---

## 🔗 Liens vers le code

### Fichiers les plus importants

**Core**:
- [duplicateflow/core/registry.py](../duplicateflow/core/registry.py) - Registry pattern
- [duplicateflow/core/models.py](../duplicateflow/core/models.py) - Data models

**Pipeline**:
- [duplicateflow/pipeline/pipeline.py](../duplicateflow/pipeline/pipeline.py) - Orchestration
- [duplicateflow/pipeline/presets.py](../duplicateflow/pipeline/presets.py) - 12 presets

**SDK**:
- [duplicateflow/sdk/algorithm.py](../duplicateflow/sdk/algorithm.py) - Base Algorithm class
- [duplicateflow/sdk/validator.py](../duplicateflow/sdk/validator.py) - Validators (NEW)

**Storage**:
- [duplicateflow/storage/storage_manager.py](../duplicateflow/storage/storage_manager.py) - Cache manager
- [duplicateflow/storage/pipeline_store.py](../duplicateflow/storage/pipeline_store.py) - Pipeline persistence (NEW)

**Algorithms** (exemples):
- [duplicateflow/algorithms/frame_hash.py](../duplicateflow/algorithms/frame_hash.py) - Simple
- [duplicateflow/algorithms/optical_flow.py](../duplicateflow/algorithms/optical_flow.py) - Complex

**Integration UI**:
- [src/plugins/duplicate_finder/integration/duplicateflow_api.py](../src/plugins/duplicate_finder/integration/duplicateflow_api.py)
- [src/plugins/duplicate_finder/orchestration/pipeline_manager.py](../src/plugins/duplicate_finder/orchestration/pipeline_manager.py)

---

## 🛠️ Outils de navigation

### Commandes utiles

```bash
# Vue d'ensemble structure
tree duplicateflow/ -L 2

# Rechercher dans code
grep -r "def compare" duplicateflow/algorithms/

# Compter lignes
find duplicateflow/ -name "*.py" | xargs wc -l

# Lister algorithmes
ls duplicateflow/algorithms/*.py | grep -v __

# Lister presets
grep "PRESET = {" duplicateflow/pipeline/presets.py

# Voir imports
grep -r "^from duplicateflow" duplicateflow/

# Voir tests
ls duplicateflow/tests/
ls tests/duplicate_finder/
```

### Dans Python

```python
# Lister tous les algorithmes
from duplicateflow.algorithms import list_algorithms
algos = list_algorithms()
for algo in algos:
    print(f"{algo.name} ({algo.category}) - {algo.speed}")

# Lister tous les presets
from duplicateflow.pipeline.presets import PRESETS
for name in PRESETS.keys():
    print(name)

# Inspector un algorithme
from duplicateflow.algorithms import get_algorithm
algo = get_algorithm('frame_hash')
print(algo.__doc__)
print(algo.threshold)

# Inspector une pipeline
from duplicateflow.pipeline import Pipeline
p = Pipeline.from_preset('balanced')
print(p.steps)
print(p.global_threshold)
```

---

## 📝 Conventions de la documentation

### Icônes utilisées
- ⭐ = Recommandé, important
- ✅ = Complété, OK
- ⏳ = En cours
- ❌ = À éviter
- 🔴 = Priorité haute
- 🟡 = Priorité moyenne
- 🟢 = Priorité basse
- 📁 = Fichier/dossier
- 🎯 = Objectif
- 💡 = Tip/conseil
- 🐛 = Bug/problème
- 🚀 = Action/commande

### Format des exemples de code

```python
# ✅ CORRECT
code_correct = "ceci"

# ❌ INCORRECT
code_incorrect = "cela"
```

### Format des commandes shell

```bash
# Commande simple
command arg1 arg2

# Commande avec explication
command arg1 arg2  # Explication
```

---

## 🆘 Support

### Si la documentation est insuffisante

1. **Lire le code source**
   - Le code est bien commenté avec docstrings
   - Type hints partout pour clarté

2. **Lire les tests**
   - `duplicateflow/tests/` - Tests unitaires
   - `tests/duplicate_finder/` - Tests intégration

3. **Consulter git history**
   ```bash
   git log --oneline -- duplicateflow/pipeline/pipeline.py
   git show <commit-hash>
   ```

4. **Demander à Claude Code**
   - "Explique-moi le Registry pattern dans DuplicateFlow"
   - "Comment fonctionne le cache à 3 niveaux ?"
   - "Montre-moi un exemple d'utilisation de LengthValidator"

---

## 📈 Historique de la documentation

### Version 1.0 - 2025-12-19
- Création initiale après Phase 12
- Documentation complète de l'architecture
- Guide de reprise pour Claude Code
- Quick reference avec exemples
- Checklist des prochaines étapes

---

## 🎯 Objectifs de cette documentation

### Court terme
- ✅ Permettre reprise instantanée du développement
- ✅ Documenter toutes les fonctionnalités existantes
- ✅ Fournir exemples de code pour chaque feature
- ✅ Lister toutes les tâches restantes

### Moyen terme
- ⏳ Générer API Reference auto (Sphinx)
- ⏳ Créer User Guide pour utilisateurs finaux
- ⏳ Créer Developer Guide pour contributeurs
- ⏳ Ajouter diagrammes d'architecture

### Long terme
- ⏳ Documentation interactive (ReadTheDocs)
- ⏳ Tutoriels vidéo
- ⏳ Exemples d'intégration
- ⏳ Best practices guide

---

## ✨ Contribuer à la documentation

Si vous ajoutez du code:
1. **Mettre à jour CURRENT_WORK.md** - Noter changements
2. **Ajouter exemples dans QUICK_REFERENCE.md** - Si nouvelle feature
3. **Expliquer dans ARCHITECTURE.md** - Si nouveau composant
4. **Docstrings dans le code** - Toujours !

Si vous trouvez des erreurs:
1. Noter dans CURRENT_WORK.md section "Problèmes connus"
2. Créer issue GitHub si pertinent

---

## 🙏 Note finale

Cette documentation a été créée avec soin pour permettre à **n'importe quelle session Claude Code** de reprendre le travail **immédiatement** avec le **contexte complet**.

**Prochaine étape recommandée**: Lire [RESUME_CONTEXT.md](RESUME_CONTEXT.md)

---

**Bonne lecture ! 📚**

**Dernière mise à jour**: 2025-12-19
**Auteur**: Claude Code (Sonnet 4.5)
**Statut**: ✅ Complet et à jour
