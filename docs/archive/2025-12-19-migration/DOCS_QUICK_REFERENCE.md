# Documentation Quick Reference - VideoFlow

Guide rapide pour trouver la bonne documentation.

---

## Je cherche de l'information sur...

### DuplicateFlow (Architecture, Algorithmes, API)

**Emplacement**: `/docs/duplicateflow/`

| Besoin | Fichier | Lignes |
|--------|---------|--------|
| **Point d'entrée** | `README.md` | 68 |
| **Architecture complète** | `DUPLICATEFLOW_ARCHITECTURE.md` | 709 |
| **14 algorithmes détaillés** | `DUPLICATEFLOW_ALGORITHMS.md` | 865 |
| **API + Presets + Exemples** | `DUPLICATEFLOW_QUICK_REFERENCE.md` | 885 |
| **Vue d'ensemble** | `SUMMARY.md` | 330 |
| **CLI Reference** | `cli/CLI_COMPLETE_REFERENCE.md` | 722 |

**Total**: 2,857 lignes de documentation exhaustive

**Coverage**: 100% (14/14 algorithmes, 12/12 presets, tous patterns)

---

### Plugin Duplicate Finder (Usage, API, Troubleshooting)

**Emplacement**: `/src/plugins/duplicate_finder/`

| Besoin | Fichier | Lignes |
|--------|---------|--------|
| **Guide utilisateur** | `USER_GUIDE.md` | 599 |
| **Tutorial complet** | `TUTORIAL.md` | 1,069 |
| **API Reference** | `API_REFERENCE.md` | 1,266 |
| **Troubleshooting** | `TROUBLESHOOTING.md` | 835 |
| **FAQ** | `FAQ.md` | 503 |
| **Contribution** | `CONTRIBUTING.md` | 821 |
| **Refactoring** | `REFACTORING_GUIDE.md` | - |

**Total**: 5,093 lignes

---

### Plugin Video Converter

**Emplacement**: `/src/plugins/video_converter/`

| Fichier |
|---------|
| `ARCHITECTURE.md` |
| `MIGRATION_GUIDE.md` |
| `REFACTORING_CHECKLIST.md` |
| `REFACTORING_SUMMARY.md` |

---

### Plugin Batch Renamer

**Emplacement**: `/src/plugins/batch_renamer/`

| Fichier |
|---------|
| `ENHANCEMENTS_README.md` |
| `INTEGRATION_GUIDE.md` |

---

### Tests

**Emplacement**: `/tests/README.md`

---

### Historique Migration DuplicateFlow

**Emplacement**: `/docs/archive/2025-12-19-migration/`

**Index**: `README.md` liste tous les 49 fichiers archivés

| Catégorie | Fichiers | Contenu |
|-----------|----------|---------|
| **migration/** | 19 | Plans et rapports de phases (PHASE_1 à PHASE_11) |
| **analyses/** | 7 | Analyses techniques et audits |
| **features/** | 10 | Documentation features implémentées |
| **integrations/** | 4 | Rapports intégration UI/pipeline |
| **bugfixes/** | 5 | Index corrections et bugfixes |
| **proposals/** | 4 | Propositions UI et améliorations futures |

**Utilisation**: Consulter pour comprendre décisions historiques, pas pour usage quotidien.

---

## Flowchart de Navigation

```
┌─────────────────────────────────────────────────────────┐
│         Je veux comprendre DuplicateFlow?               │
└────────────────┬────────────────────────────────────────┘
                 │
                 ├─→ Architecture? → docs/duplicateflow/DUPLICATEFLOW_ARCHITECTURE.md
                 ├─→ Algorithmes? → docs/duplicateflow/DUPLICATEFLOW_ALGORITHMS.md
                 ├─→ API/Presets? → docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md
                 └─→ CLI? → docs/duplicateflow/cli/CLI_COMPLETE_REFERENCE.md

┌─────────────────────────────────────────────────────────┐
│      Je veux utiliser le plugin Duplicate Finder?       │
└────────────────┬────────────────────────────────────────┘
                 │
                 ├─→ Débuter? → src/plugins/duplicate_finder/USER_GUIDE.md
                 ├─→ Tutorial? → src/plugins/duplicate_finder/TUTORIAL.md
                 ├─→ Problème? → src/plugins/duplicate_finder/TROUBLESHOOTING.md
                 └─→ API? → src/plugins/duplicate_finder/API_REFERENCE.md

┌─────────────────────────────────────────────────────────┐
│  Pourquoi telle décision architecturale a été prise?    │
└────────────────┬────────────────────────────────────────┘
                 │
                 └─→ docs/archive/2025-12-19-migration/
                     ├─→ migration/ (chronologie)
                     └─→ analyses/ (analyses techniques)

┌─────────────────────────────────────────────────────────┐
│         Ce bug a-t-il déjà été fixé auparavant?         │
└────────────────┬────────────────────────────────────────┘
                 │
                 └─→ docs/archive/2025-12-19-migration/bugfixes/
                     └─→ FIXES_INDEX.md
```

---

## Par Cas d'Usage

### Cas 1: Développeur débutant sur le projet

**Parcours recommandé**:
1. `docs/duplicateflow/README.md` - Vue d'ensemble
2. `docs/duplicateflow/DUPLICATEFLOW_ARCHITECTURE.md` - Comprendre structure
3. `src/plugins/duplicate_finder/USER_GUIDE.md` - Utiliser le plugin
4. `src/plugins/duplicate_finder/TUTORIAL.md` - Tutorial pratique

**Durée**: 1-2 heures de lecture

---

### Cas 2: Choisir un algorithme de détection

**Fichier**: `docs/duplicateflow/DUPLICATEFLOW_ALGORITHMS.md`

**Contenu**:
- Tableau comparatif des 14 algorithmes
- Fiches techniques détaillées
- Cas d'usage et performance
- Guide de sélection

**Section clé**: "Guide de sélection" (fin du document)

---

### Cas 3: Configurer un pipeline personnalisé

**Fichier**: `docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md`

**Sections**:
- A. Les 12 Presets (configurations pré-définies)
- B. API Reference (classe Pipeline)
- D. PipelineStore (sauvegarde custom)
- F. Exemples (exemple 4: Pipeline custom)

---

### Cas 4: Optimiser performance (millions de vidéos)

**Fichier**: `docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md`

**Sections**:
- D. LSH (Locality-Sensitive Hashing) - O(N²) → O(N×C)
- E. Optimisations (Validators, Partial Analysis, Cache)
- H. Tests & Benchmarks

---

### Cas 5: Migrer code utilisant VideoHasher

**Fichier**: `docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md`

**Section**: G. Migration VideoHasher → DuplicateFlow
- Table de correspondance
- Ancien vs nouveau code
- Checklist 8 points

**Archive**: `docs/archive/2025-12-19-migration/analyses/`
- Détails historiques de la migration

---

### Cas 6: Debugger erreur au runtime

**Fichier**: `src/plugins/duplicate_finder/TROUBLESHOOTING.md`

**Contenu**: 835 lignes de troubleshooting

**Si erreur historique**:
`docs/archive/2025-12-19-migration/bugfixes/FIXES_INDEX.md`

---

### Cas 7: Comprendre pourquoi Strategy3 a été supprimé

**Archive**: `docs/archive/2025-12-19-migration/migration/`

**Fichiers clés**:
- `PHASE_9_STRATEGY3_CLEANUP_COMPLETE.md`
- `STRATEGY3_FINAL_CLEANUP_COMPLETE.md`

**Analyse**: `docs/archive/2025-12-19-migration/analyses/`
- `OBSOLETE_CODE_AUDIT_POST_PHASE8.md`

---

### Cas 8: Contribuer au projet

**Fichier**: `src/plugins/duplicate_finder/CONTRIBUTING.md`

**Contenu**: 821 lignes
- Guidelines de contribution
- Architecture du code
- Standards de code
- Process de review

---

## Commandes Utiles

### Chercher dans toute la documentation

```bash
# Chercher un mot-clé dans docs actifs
grep -r "mot-clé" /Users/nico/Documents/videoFlow/docs/duplicateflow/

# Chercher dans archive
grep -r "mot-clé" /Users/nico/Documents/videoFlow/docs/archive/

# Chercher dans plugins
grep -r "mot-clé" /Users/nico/Documents/videoFlow/src/plugins/*/
```

### Lister tous les MD par taille

```bash
find /Users/nico/Documents/videoFlow -name "*.md" -exec wc -l {} \; | sort -rn
```

### Voir structure docs

```bash
tree /Users/nico/Documents/videoFlow/docs/
```

---

## Hiérarchie d'Autorité

### Source de Vérité (TOUJOURS à jour)

1. **docs/duplicateflow/** - Architecture, algorithmes, API DuplicateFlow
2. **src/plugins/*/\*.md** - Documentation plugins

### Référence Historique (contexte, pas source de vérité)

3. **docs/archive/** - Décisions passées, analyses, propositions

### Work in Progress

4. **I18N_TODO.md** - Tâches i18n en cours

---

## Règles de Maintenance

### ✅ À FAIRE

- Mettre à jour `docs/duplicateflow/` quand nouveau concept/feature
- Archiver docs temporaires fin de session dans `docs/archive/YYYY-MM-DD/`
- Garder racine propre (max 2-3 fichiers WIP)

### ❌ À ÉVITER

- Créer documentation permanente dans racine
- Dupliquer information entre docs/ et archive/
- Supprimer historique (archiver plutôt)
- Créer doublons (vérifier existant avant)

---

## Statistiques (Post-Cleanup)

| Catégorie | Fichiers | Taille |
|-----------|----------|--------|
| **docs/duplicateflow/** | 6 | 80KB |
| **docs/archive/** | 49 | 600KB |
| **src/plugins/** docs | 13 | 187KB |
| **tests/** docs | 1 | 7KB |
| **duplicateflow/** docs | 1 | 3KB |
| **Racine** (WIP) | 1 | <10KB |
| **TOTAL** | 71 | ~880KB |

---

## Contact / Support

- **Documentation DuplicateFlow**: `docs/duplicateflow/README.md`
- **FAQ**: `src/plugins/duplicate_finder/FAQ.md`
- **Troubleshooting**: `src/plugins/duplicate_finder/TROUBLESHOOTING.md`

---

**Dernière mise à jour**: 2025-12-19
**Version**: 1.0 (Post-cleanup)
