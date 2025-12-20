# 🎯 DuplicateFlow CLI - Cheatsheet Commandes

**Quick reference** des nouvelles commandes proposées

---

## 🔍 Recherche dans Arborescences

### Scan de dossier complet
```bash
# Scan simple
duplicateflow scan /path/to/videos --pipeline balanced

# Scan récursif avec filtres
duplicateflow scan /media/videos --recursive --extensions mp4,avi,mkv --pipeline thorough

# Avec limites de taille
duplicateflow scan /videos --min-size 10MB --max-size 5GB --group-duplicates

# Export résultats
duplicateflow scan /videos --output duplicates.json
```

### Détection scènes incluses
```bash
# Trouver où apparaît un court clip
duplicateflow find-scenes short_clip.mp4 --in /archive --show-timestamps

# Mode batch (plusieurs clips)
duplicateflow find-scenes /clips/*.mp4 --in /archive --batch

# Filtrer par durée minimale
duplicateflow find-scenes intro.mp4 --in /projects --min-duration 5
```

### Comparaison entre dossiers
```bash
# Compare 2 dossiers
duplicateflow cross-search /folder_A /folder_B --pipeline balanced

# Avec direction (A → B ou B → A)
duplicateflow cross-search /new_downloads /archive --show-direction
```

---

## 📊 Rapports et Visualisations

### Heatmap de similarité
```bash
# Matrice N×N interactive
duplicateflow heatmap /videos/*.mp4 --output similarity_heatmap.html

# Avec seuil de similarité
duplicateflow heatmap /videos/*.mp4 --threshold 80 --output report.html
```

### Timeline de détection
```bash
# Visualiser scènes dans longue vidéo
duplicateflow timeline long_video.mp4 --compare-with /scenes

# Export timeline
duplicateflow timeline movie.mp4 --compare-with /clips --output timeline.json
```

---

## 🤖 Automatisation

### Watch mode (surveillance)
```bash
# Surveillance simple avec rapport
duplicateflow watch /downloads --pipeline fast --action report

# Avec actions automatiques
duplicateflow watch /downloads --pipeline balanced --action move-duplicates --dest /duplicates

# Mode daemon (background)
duplicateflow watch /downloads --daemon --log /var/log/duplicateflow.log

# Avec webhook notifications
duplicateflow watch /uploads --action reject --notify-webhook https://api.example.com/duplicate
```

### Scans planifiés
```bash
# Scan quotidien à 2h du matin
duplicateflow schedule --daily --at 02:00 --scan /videos --pipeline balanced --report /reports

# Scan hebdomadaire le dimanche
duplicateflow schedule --weekly --day sunday --at 03:00 --scan /archive --pipeline thorough

# Lister tâches planifiées
duplicateflow schedule --list

# Supprimer une tâche
duplicateflow schedule --remove <task_id>
```

### Auto-clean (nettoyage automatique)
```bash
# Preview (dry-run) avant suppression
duplicateflow auto-clean /downloads --keep-best-quality --dry-run

# Nettoyage réel avec déplacement
duplicateflow auto-clean /downloads --keep-best-quality --move-rest /duplicates

# Avec critères personnalisés
duplicateflow auto-clean /videos \
  --scan \
  --group-duplicates \
  --keep-highest-resolution \
  --keep-highest-bitrate \
  --move-rest /backup

# Nettoyage agressif (suppression directe)
duplicateflow auto-clean /temp --delete-duplicates --confirm
```

---

## 📈 Historique et Régression

### Historique des benchmarks
```bash
# Voir historique d'un pipeline
duplicateflow benchmark --history --testset default --pipeline balanced

# Comparer avec dernier run
duplicateflow benchmark --testset default --pipeline balanced --compare-with-last

# Voir tendance (10 derniers runs)
duplicateflow benchmark --trend --testset default --pipeline balanced --limit 10
```

### Détection de régression
```bash
# Vérifier régression
duplicateflow benchmark --testset default --pipeline balanced --check-regression

# Fail si régression (pour CI/CD)
duplicateflow benchmark --testset default --pipeline balanced --fail-on-regression

# Avec seuil personnalisé (5% drop = error)
duplicateflow benchmark --testset default --pipeline balanced --check-regression --threshold 5.0
```

---

## ✅ Validation de Test Set

### Validation
```bash
# Valider un test set
duplicateflow testset validate default

# Valider tous les test sets
duplicateflow testset validate --all

# Avec auto-fix
duplicateflow testset validate default --fix

# Export rapport de validation
duplicateflow testset validate default --report validation_report.json
```

---

## 📦 Export Avancés

### Export HTML
```bash
# Rapport HTML interactif
duplicateflow benchmark --testset default --pipeline balanced --export html

# Avec tous les détails
duplicateflow benchmark --testset default --pipeline balanced --export html --include-failures --include-timings
```

### Export Markdown
```bash
# Résumé Markdown
duplicateflow benchmark --testset default --pipeline balanced --export markdown

# Markdown + JSON
duplicateflow benchmark --testset default --pipeline balanced --export markdown,json
```

### Export multi-formats
```bash
# Tous les formats
duplicateflow benchmark --testset default --pipeline balanced --export html,markdown,json,csv

# Vers dossier spécifique
duplicateflow benchmark --testset default --pipeline balanced --export-dir /reports --export html,json
```

---

## ⚙️ Configuration

### Profils
```bash
# Utiliser profil quick
duplicateflow benchmark --profile quick --testset default --pipeline balanced

# Profil production (full analysis)
duplicateflow benchmark --profile production --testset default --pipeline balanced

# Config personnalisée
duplicateflow benchmark --config myconfig.toml --testset default --pipeline balanced
```

### Cache
```bash
# Stats du cache
duplicateflow cache stats

# Vider le cache
duplicateflow cache clear

# Vider cache spécifique
duplicateflow cache clear --features
duplicateflow cache clear --results
```

---

## 🔍 Debug et Profiling

### Debug mode
```bash
# Mode debug avec logs détaillés
duplicateflow benchmark --debug --testset default --pipeline balanced

# Step-by-step
duplicateflow benchmark --debug --step-by-step --testset default --pipeline balanced
```

### Performance profiling
```bash
# Profile des performances
duplicateflow benchmark --profile-performance --testset default --pipeline balanced

# Memory profiling
duplicateflow benchmark --profile-memory --testset default --pipeline balanced

# Full profiling
duplicateflow benchmark --profile-performance --profile-memory --testset default --pipeline balanced
```

---

## 🚀 Workflows Complets

### Workflow 1: Setup initial d'une médiathèque
```bash
# 1. Scan initial
duplicateflow scan /media/videos --recursive --pipeline balanced --group-duplicates

# 2. Export rapport
duplicateflow scan /media/videos --output scan_report.json --export html

# 3. Preview nettoyage
duplicateflow auto-clean /media/videos --keep-best-quality --dry-run

# 4. Nettoyage réel
duplicateflow auto-clean /media/videos --keep-best-quality --move-rest /backup/duplicates

# 5. Setup monitoring
duplicateflow watch /downloads --pipeline fast --action move-duplicates --dest /backup/duplicates --daemon
```

### Workflow 2: Recherche de scènes
```bash
# 1. Trouver toutes occurrences d'une intro
duplicateflow find-scenes intro_v2.mp4 --in /projects --show-timestamps --output intro_matches.json

# 2. Vérifier dans archive
duplicateflow find-scenes intro_v2.mp4 --in /archive --batch

# 3. Timeline complète
duplicateflow timeline compilation_2024.mp4 --compare-with /intros --output timeline.html
```

### Workflow 3: CI/CD pour pipelines
```bash
# 1. Benchmark avec historique
duplicateflow benchmark --testset default --pipeline custom_v5 --analyze --history

# 2. Check régression
duplicateflow benchmark --testset default --pipeline custom_v5 --check-regression --fail-on-regression

# 3. Si OK, compare vs baseline
duplicateflow compare --testset default --pipelines custom_v5,balanced,thorough --export-matrix

# 4. Export pour review
duplicateflow benchmark --testset default --pipeline custom_v5 --export html,markdown --include-failures
```

### Workflow 4: Archiviste (nouvelle acquisition)
```bash
# 1. Valider nouvelle acquisition
duplicateflow testset validate new_acquisition

# 2. Cross-search vs archive existant
duplicateflow cross-search /new_acquisition /archive --pipeline thorough --report matches.json

# 3. Heatmap de similarité
duplicateflow heatmap /new_acquisition/*.mp4 --output similarity.html

# 4. Si pas de duplicates, ajouter à monitoring
duplicateflow watch /new_acquisition --action report --log acquisition.log
```

---

## 📝 Options Globales

```bash
# Options communes à toutes les commandes
--verbose, -v           # Mode verbeux
--quiet, -q             # Mode silencieux
--config PATH           # Config file custom
--cache-dir PATH        # Cache directory
--output PATH           # Output file/dir
--format FORMAT         # Output format (json, csv, html, markdown)
--no-cache              # Désactiver cache
--max-workers N         # Parallélisation (default: CPU count)
--timeout SECONDS       # Timeout global
--help, -h              # Aide
--version               # Version
```

---

## 🎯 Quick Tips

### Performance
```bash
# Scan rapide (1000 vidéos en <30s)
duplicateflow scan /videos --pipeline fast --index-only

# Scan précis (mais plus lent)
duplicateflow scan /videos --pipeline thorough --force-recompute
```

### Filtrage
```bash
# Par extension
duplicateflow scan /videos --extensions mp4,mkv,avi

# Par taille
duplicateflow scan /videos --min-size 100MB --max-size 10GB

# Par date
duplicateflow scan /videos --after 2024-01-01 --before 2024-12-31
```

### Actions batch
```bash
# Traiter plusieurs dossiers
for dir in /media/*; do
    duplicateflow scan "$dir" --output "scan_$(basename $dir).json"
done

# Pipeline avec xargs
find /videos -name "*.mp4" | xargs -I {} duplicateflow find-scenes {} --in /archive
```

---

**Dernière mise à jour**: 2025-12-19
**Version DuplicateFlow**: 2.0 (proposé)
**Documentation complète**: [CLI_IMPROVEMENTS_PROPOSALS.md](CLI_IMPROVEMENTS_PROPOSALS.md)
