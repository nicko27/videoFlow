#!/bin/bash
# Documentation Cleanup Script
# Date: 2025-12-19
# Purpose: Archive obsolete documentation and restructure docs

set -e  # Exit on error

echo "=== VideoFlow Documentation Cleanup ==="
echo ""
echo "This script will:"
echo "  - Archive 46 session/migration files"
echo "  - Delete 5 obsolete files"
echo "  - Reorganize CLI documentation"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    exit 1
fi

# Change to project root
cd /Users/nico/Documents/videoFlow

# ============================================
# STEP 1: Create archive structure
# ============================================
echo ""
echo "[1/5] Creating archive structure..."

mkdir -p docs/archive/2025-12-19-migration/{migration,analyses,features,integrations,bugfixes,proposals}
mkdir -p docs/duplicateflow/cli

echo "✓ Archive directories created"

# ============================================
# STEP 2: Archive Migration files (19 files)
# ============================================
echo ""
echo "[2/5] Archiving migration files (19 files)..."

git mv MASTER_PLAN_MIGRATION_DUPLICATEFLOW.md docs/archive/2025-12-19-migration/migration/
git mv PHASE_1_2_3_MIGRATION_COMPLETE.md docs/archive/2025-12-19-migration/migration/
git mv PHASE_3_WORKERS_MIGRATION_COMPLETE.md docs/archive/2025-12-19-migration/migration/
git mv PHASE_3_SESSION_SUMMARY.md docs/archive/2025-12-19-migration/migration/
git mv PHASE_4_UI_ALGORITHM_NAMES_FIX.md docs/archive/2025-12-19-migration/migration/
git mv PHASE_5_LEGACY_CODE_ANALYSIS.md docs/archive/2025-12-19-migration/migration/
git mv PHASE_6_COMPARISON_WORKER_MIGRATION_COMPLETE.md docs/archive/2025-12-19-migration/migration/
git mv PHASE_6_VIDEOHASHER_REMOVAL_COMPLETE.md docs/archive/2025-12-19-migration/migration/
git mv PHASE_7_TESTS_PLAN.md docs/archive/2025-12-19-migration/migration/
git mv PHASE_7_TESTS_COMPLETE.md docs/archive/2025-12-19-migration/migration/
git mv PHASE_8_CRITICAL_FIXES_COMPLETE.md docs/archive/2025-12-19-migration/migration/
git mv PHASE_9_STRATEGY3_CLEANUP_COMPLETE.md docs/archive/2025-12-19-migration/migration/
git mv PHASE_11_AUDIO_FIRST_REMOVAL_COMPLETE.md docs/archive/2025-12-19-migration/migration/
git mv SESSION_COMPLETE_PHASES_3_TO_6.md docs/archive/2025-12-19-migration/migration/
git mv SESSION_FINAL_PHASE_7_COMPLETE.md docs/archive/2025-12-19-migration/migration/
git mv SESSION_PHASE_10_COMPLETE.md docs/archive/2025-12-19-migration/migration/
git mv PANELS_CLEANUP_GUIDE.md docs/archive/2025-12-19-migration/migration/
git mv PANELS_CLEANUP_COMPLETE.md docs/archive/2025-12-19-migration/migration/
git mv STRATEGY3_FINAL_CLEANUP_COMPLETE.md docs/archive/2025-12-19-migration/migration/

# Archive Analyses (7 files)
git mv ANALYSE_COMPLETE_MIGRATION_DUPLICATEFLOW.md docs/archive/2025-12-19-migration/analyses/
git mv ANALYSE_P2_VERIFICATION_COMPLETE.md docs/archive/2025-12-19-migration/analyses/
git mv ADAPTERS_ANALYSIS.md docs/archive/2025-12-19-migration/analyses/
git mv OBSOLETE_CODE_AUDIT_POST_PHASE8.md docs/archive/2025-12-19-migration/analyses/
git mv CRITICAL_ERRORS_FOUND_PHASE_7.md docs/archive/2025-12-19-migration/analyses/
git mv MIGRATION_VERIFICATION_COMMANDS.md docs/archive/2025-12-19-migration/analyses/
git mv DUPLICATEFLOW_MIGRATION_COMPLETE.md docs/archive/2025-12-19-migration/analyses/

# Archive Features (9 files)
git mv DUPLICATEFLOW_NEW_FEATURES.md docs/archive/2025-12-19-migration/features/
git mv DUPLICATEFLOW_PIPELINE_STORAGE.md docs/archive/2025-12-19-migration/features/
git mv DUPLICATEFLOW_LSH_ENHANCEMENT.md docs/archive/2025-12-19-migration/features/
git mv DUPLICATEFLOW_API_MIGRATION.md docs/archive/2025-12-19-migration/features/
git mv CHANGELOG_DUPLICATEFLOW_FEATURES.md docs/archive/2025-12-19-migration/features/
git mv README_NEW_FEATURES.md docs/archive/2025-12-19-migration/features/
git mv IMPLEMENTATION_SUMMARY.md docs/archive/2025-12-19-migration/features/
git mv FINAL_SUMMARY_DUPLICATEFLOW.md docs/archive/2025-12-19-migration/features/
git mv IMPLEMENTATION_COMPLETE_20251219.md docs/archive/2025-12-19-migration/features/

# Archive Integrations (4 files)
git mv INTEGRATION_DUPLICATE_FINDER.md docs/archive/2025-12-19-migration/integrations/
git mv INTEGRATION_COMPLETE_SUMMARY.md docs/archive/2025-12-19-migration/integrations/
git mv UI_INTEGRATION_PHASE1_COMPLETE.md docs/archive/2025-12-19-migration/integrations/
git mv PIPELINE_SELECTOR_INTEGRATION.md docs/archive/2025-12-19-migration/integrations/

# Archive Bugfixes (5 files)
git mv BUGFIX_POOL_CONNECTION.md docs/archive/2025-12-19-migration/bugfixes/
git mv STARTUP_ERRORS_FIXES.md docs/archive/2025-12-19-migration/bugfixes/
git mv CORRECTIONS_COMPLETES_20251219.md docs/archive/2025-12-19-migration/bugfixes/
git mv QUICK_FIX_REFERENCE.md docs/archive/2025-12-19-migration/bugfixes/
git mv FIXES_INDEX.md docs/archive/2025-12-19-migration/bugfixes/

# Archive Proposals (4 files)
git mv PROPOSITION_ONGLET_PARAMETRES.md docs/archive/2025-12-19-migration/proposals/
git mv PLAN_INTERFACE_FINALE.md docs/archive/2025-12-19-migration/proposals/
git mv UI_IMPROVEMENTS_PROPOSAL.md docs/archive/2025-12-19-migration/proposals/
git mv ONGLET_PARAMETRES_ANALYSE.md docs/archive/2025-12-19-migration/proposals/

echo "✓ Archived 48 files"

# ============================================
# STEP 3: Delete obsolete files (2 files)
# ============================================
echo ""
echo "[3/5] Deleting obsolete files (2 files)..."

git rm LEGACY_STRATEGY3_DOCUMENTATION.md
git rm AUDIO_FIRST_SYSTEM_ARCHIVE.md

echo "✓ Deleted 2 obsolete files"

# ============================================
# STEP 4: Reorganize CLI docs
# ============================================
echo ""
echo "[4/5] Reorganizing CLI documentation..."

git mv duplicateflow/CLI_COMPLETE_REFERENCE.md docs/duplicateflow/cli/
git mv duplicateflow/CLI_IMPROVEMENTS.md docs/archive/2025-12-19-migration/features/

echo "✓ CLI docs reorganized"

# ============================================
# STEP 5: Create archive index
# ============================================
echo ""
echo "[5/5] Creating archive index..."

cat > docs/archive/2025-12-19-migration/README.md << 'EOF'
# Archive - Migration DuplicateFlow (Décembre 2025)

Documentation historique de la migration complète vers DuplicateFlow.

## Contenu

### migration/ (19 fichiers)
Plans et rapports de phases de migration (PHASE_1 à PHASE_11, SESSION_*).

**Fichiers clés:**
- `MASTER_PLAN_MIGRATION_DUPLICATEFLOW.md` - Plan master complet
- `PHASE_11_AUDIO_FIRST_REMOVAL_COMPLETE.md` - Suppression système Audio-First
- `SESSION_PHASE_10_COMPLETE.md` - Résumé phase 10

### analyses/ (7 fichiers)
Analyses techniques, audits et vérifications.

**Fichiers clés:**
- `ANALYSE_COMPLETE_MIGRATION_DUPLICATEFLOW.md` - Analyse complète migration
- `ADAPTERS_ANALYSIS.md` - Analyse des adapters (21KB)
- `CRITICAL_ERRORS_FOUND_PHASE_7.md` - Erreurs critiques découvertes

### features/ (10 fichiers)
Documentation des nouvelles features implémentées.

**Fichiers clés:**
- `DUPLICATEFLOW_NEW_FEATURES.md` - Nouvelles features DuplicateFlow
- `DUPLICATEFLOW_PIPELINE_STORAGE.md` - Système de stockage pipelines
- `FINAL_SUMMARY_DUPLICATEFLOW.md` - Résumé final des améliorations
- `CLI_IMPROVEMENTS.md` - Améliorations CLI

### integrations/ (4 fichiers)
Rapports d'intégration UI et pipeline.

**Fichiers clés:**
- `INTEGRATION_DUPLICATE_FINDER.md` - Intégration dans VideoFlow
- `PIPELINE_SELECTOR_INTEGRATION.md` - Intégration sélecteur de pipeline

### bugfixes/ (5 fichiers)
Index des corrections et bugfixes.

**Fichiers clés:**
- `BUGFIX_POOL_CONNECTION.md` - Fix pool de connexion DB
- `FIXES_INDEX.md` - Index de tous les fixes

### proposals/ (4 fichiers)
Propositions UI et améliorations futures.

**Fichiers clés:**
- `PLAN_INTERFACE_FINALE.md` - Plan interface finale (30KB)
- `PROPOSITION_ONGLET_PARAMETRES.md` - Proposition onglet paramètres
- `UI_IMPROVEMENTS_PROPOSAL.md` - Propositions améliorations UI

## Période

Décembre 2025 (2025-12-18 → 2025-12-19)

## Statistiques

- **Total fichiers**: 49
- **Total taille**: ~600KB
- **Lignes de documentation**: ~15,000+

## Raison de l'archivage

Ces documents représentent l'historique détaillé de la migration mais ne sont pas nécessaires pour l'usage quotidien.

**La documentation de référence actuelle se trouve dans:**
- `/docs/duplicateflow/` - Base de connaissance DuplicateFlow
- `/src/plugins/duplicate_finder/*.md` - Documentation plugin

## Utilisation

Consulter cette archive pour:
- Comprendre les décisions architecturales passées
- Retrouver l'historique d'un bugfix spécifique
- Voir l'évolution chronologique des features
- Référencer les analyses techniques détaillées
- Comprendre pourquoi certains systèmes ont été supprimés (Audio-First, Strategy3)

## Navigation

```
2025-12-19-migration/
├── README.md (ce fichier)
├── migration/      # Chronologie des phases
├── analyses/       # Analyses techniques
├── features/       # Features implémentées
├── integrations/   # Intégrations réalisées
├── bugfixes/       # Corrections de bugs
└── proposals/      # Propositions futures
```

## Notes importantes

### Systèmes supprimés documentés ici
- **VideoHasher**: Remplacé par DuplicateFlow (Phase 6)
- **Strategy3**: Remplacé par pipelines DuplicateFlow (Phase 9)
- **Audio-First System**: Remplacé par partial analysis (Phase 11)

### Nouvelles features implémentées
- Validators (LengthValidator + custom)
- Partial Analysis (analyze_duration, analyze_from_start)
- Pipeline Storage (sauvegarde en DB)
- LSH enhancement (scalabilité)

---

**Archive créée**: 2025-12-19
**Par**: Claude Code (Documentation Cleanup)
**Dernière modification**: 2025-12-19
EOF

git add docs/archive/2025-12-19-migration/README.md

echo "✓ Archive index created"

# ============================================
# SUMMARY
# ============================================
echo ""
echo "=== CLEANUP COMPLETE ==="
echo ""
echo "Summary:"
echo "  - Archived: 48 files"
echo "  - Deleted: 2 files"
echo "  - Created: docs/archive/2025-12-19-migration/"
echo "  - Created: docs/duplicateflow/cli/"
echo ""
echo "Root directory .md files:"
echo "  Before: ~50 files"
echo "  After: 2 files (I18N_TODO.md + DOCUMENTATION_AUDIT_REPORT.md)"
echo ""
echo "Next steps:"
echo "  1. Review changes: git status"
echo "  2. Commit: git commit -m 'Docs: Archive migration docs, restructure documentation'"
echo "  3. Optional: Archive DOCUMENTATION_AUDIT_REPORT.md after review"
echo ""
