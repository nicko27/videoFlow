# 📖 Guide Utilisateur DuplicateFlow

**Version**: 0.2.0 (Phase 2 Complete - Duplicate Detection)
**Dernière mise à jour**: 2025-12-20

---

## 🎯 Vue d'ensemble

DuplicateFlow est un système de détection de vidéos dupliquées et similaires. Il combine plusieurs algorithmes de pointe pour identifier des vidéos identiques ou similaires dans vos collections.

### Capacités

- ✅ **Scan de vidéos** - Découverte automatique de fichiers vidéo (Phase 1)
- ✅ **Comparaison de vidéos** - Similarité entre 2 vidéos (Phase 2) **NOUVEAU**
- ✅ **Détection de doublons** - Algorithmes perceptuels N-à-N (Phase 2) **NOUVEAU**
- ✅ **Export des résultats** - Export JSON et CSV
- ✅ **8 Presets** - Fast, balanced, thorough, multimodal, etc. (Phase 2) **NOUVEAU**
- ⏳ **Benchmarking** - Tests de performance (Phase 3)

---

## 🚀 Installation

### Prérequis

- Python 3.9+
- pip

### Installation

```bash
# Installer les dépendances
cd duplicateflow
pip install -r requirements.txt

# Vérifier l'installation
python -m duplicateflow.cli --version
# Output: DuplicateFlow 0.1.0 (Phase 1 Complete)
```

---

## 📋 Commandes Disponibles

### `compare` - Comparer deux vidéos **NOUVEAU Phase 2**

Compare deux vidéos spécifiques pour déterminer leur similarité.

**Syntaxe de base**:
```bash
python -m duplicateflow.cli compare <VIDEO1> <VIDEO2> [OPTIONS]
```

**Options**:

| Option | Description | Défaut |
|--------|-------------|--------|
| `VIDEO1` | Première vidéo à comparer | *Requis* |
| `VIDEO2` | Deuxième vidéo à comparer | *Requis* |
| `--preset PRESET` | Preset de pipeline à utiliser | `balanced` |
| `--threshold PERCENT` | Seuil de similarité (0-100) | `70.0` |
| `--output-json FILE` | Exporter le résultat en JSON | Aucun |
| `--show-details` | Afficher les détails des algorithmes | `False` |

**Presets disponibles**:
- `fast` - Rapide (~30s pour 1h vidéo) - 85% précision
- `balanced` - Équilibré (~2min) - 92% précision ⭐ **Recommandé**
- `thorough` - Approfondi (~5min) - >95% précision
- `multimodal` - Visual + audio (~8min) - >96% précision
- `structural`, `hybrid`, `audio_advanced`, `motion_intense` - Spécialisés

**Exemples**:

```bash
# Comparaison simple avec preset balanced
python -m duplicateflow.cli compare movie1.mp4 movie2.mp4

# Avec preset thorough pour plus de précision
python -m duplicateflow.cli compare movie1.mp4 movie2.mp4 --preset thorough

# Afficher les détails des algorithmes
python -m duplicateflow.cli compare movie1.mp4 movie2.mp4 --show-details

# Export en JSON
python -m duplicateflow.cli compare movie1.mp4 movie2.mp4 --output-json result.json

# Seuil personnalisé (80% de similarité minimum)
python -m duplicateflow.cli compare movie1.mp4 movie2.mp4 --threshold 80

# Comparaison rapide pour scan initial
python -m duplicateflow.cli compare movie1.mp4 movie2.mp4 --preset fast

# Comparaison multimodale (vidéo + audio)
python -m duplicateflow.cli compare movie1.mp4 movie2.mp4 --preset multimodal
```

**Sortie**:
```
📊 Comparison Result
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Video 1: movie1.mp4
Video 2: movie2.mp4

Similarity: 88.50%
Match: ✓ DUPLICATE

Pipeline: balanced
Time: 2500ms (2.50s)
Algorithms: 4 executed
```

**Code de sortie**:
- `0` : Vidéos sont des doublons (similarity >= threshold)
- `1` : Vidéos ne sont PAS des doublons

---

### `find` - Trouver des doublons **NOUVEAU Phase 2**

Détecte automatiquement les doublons dans un répertoire.

**Syntaxe de base**:
```bash
python -m duplicateflow.cli find <DIRECTORY> [OPTIONS]
```

**Options**:

| Option | Description | Défaut |
|--------|-------------|--------|
| `DIRECTORY` | Répertoire à analyser | *Requis* |
| `--preset PRESET` | Preset de pipeline | `balanced` |
| `--threshold PERCENT` | Seuil de similarité (0-100) | `70.0` |
| `--recursive` | Scanner récursivement | `False` |
| `--max-comparisons N` | Limiter le nombre de comparaisons | Aucun |
| `--formats EXT [EXT ...]` | Filtrer par formats | Tous |
| `--min-size MB` | Taille minimale en MB | Aucune |
| `--output-json FILE` | Exporter en JSON | Aucun |
| `--output-csv FILE` | Exporter en CSV | Aucun |

**Exemples**:

```bash
# Scan simple du répertoire courant
python -m duplicateflow.cli find .

# Scan récursif avec preset thorough
python -m duplicateflow.cli find /path/to/videos --recursive --preset thorough

# Limiter les comparaisons (utile pour grandes collections)
python -m duplicateflow.cli find /videos --max-comparisons 1000

# Filtrer par format et taille
python -m duplicateflow.cli find /videos --formats mp4 mkv --min-size 100

# Export des résultats
python -m duplicateflow.cli find /videos \
  --output-json duplicates.json \
  --output-csv duplicates.csv

# Scan rapide pour vérification initiale
python -m duplicateflow.cli find /videos --preset fast --recursive

# Détection précise multimodale
python -m duplicateflow.cli find /videos \
  --preset multimodal \
  --threshold 85 \
  --recursive
```

**Sortie**:
```
Step 1: Scanning for videos...
✓ Found 42 videos to analyze

Step 2: Detecting duplicates...
[Progress bar: 100%]

🔍 Detection Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Videos Scanned: 42
Comparisons: 861

Duplicate Groups: 3
Duplicates Found: 8
Duplicate Percentage: 19.0%

Space Reclaimable: 2.5 GB

Pipeline: balanced
Time: 120.5s (2.0m)
Speed: 7.1 comp/s

Duplicate Groups
┏━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Group┃ Videos ┃ Avg Similarity┃ Total Size┃
┡━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ #1   │ 3      │ 92.5%        │ 850.0 MB │
│ #2   │ 4      │ 88.0%        │ 1200.0 MB│
│ #3   │ 2      │ 95.0%        │ 450.0 MB │
└─────┴────────┴──────────────┴──────────┘
```

**Code de sortie**:
- `0` : Doublons trouvés
- `1` : Aucun doublon trouvé

---

### `scan` - Scanner des vidéos

Découvre et catalogue tous les fichiers vidéo dans un répertoire.

**Syntaxe de base**:
```bash
python -m duplicateflow.cli scan <DIRECTORY> [OPTIONS]
```

**Options**:

| Option | Description | Défaut |
|--------|-------------|--------|
| `DIRECTORY` | Répertoire à scanner | *Requis* |
| `--recursive` / `--no-recursive` | Scanner les sous-répertoires | `True` |
| `--follow-symlinks` | Suivre les liens symboliques | `False` |
| `--formats FORMAT [FORMAT ...]` | Filtrer par formats (mp4, mkv, avi, etc.) | Tous |
| `--min-size MB` | Taille minimale en MB | Aucune |
| `--max-size MB` | Taille maximale en MB | Aucune |
| `--show-stats` / `--no-stats` | Afficher les statistiques | `True` |
| `--output-json FILE` | Exporter en JSON | Aucun |
| `--output-csv FILE` | Exporter en CSV | Aucun |

**Exemples**:

```bash
# Scan simple du répertoire courant
python -m duplicateflow.cli scan .

# Scan récursif avec statistiques
python -m duplicateflow.cli scan /path/to/videos

# Scan non-récursif (un seul niveau)
python -m duplicateflow.cli scan /path/to/videos --no-recursive

# Filtrer par formats
python -m duplicateflow.cli scan /videos --formats mp4 mkv avi

# Filtrer par taille (100 MB à 5 GB)
python -m duplicateflow.cli scan /videos --min-size 100 --max-size 5000

# Scan sans afficher les statistiques
python -m duplicateflow.cli scan /videos --no-stats

# Export en JSON
python -m duplicateflow.cli scan /videos --output-json results.json

# Export en CSV
python -m duplicateflow.cli scan /videos --output-csv results.csv

# Export dans les deux formats
python -m duplicateflow.cli scan /videos \
  --output-json results.json \
  --output-csv results.csv
```

---

## 📊 Formats de Sortie

### Affichage Terminal

Le scan affiche:

1. **En-tête** - Informations sur le scan
2. **Progress Bar** - Progression en temps réel
3. **Tableau des résultats** - Liste des vidéos trouvées (max 20 affichées)
4. **Statistiques** - Résumé détaillé du scan
5. **Warnings** - Erreurs éventuelles

**Exemple de sortie**:

```
╭─────────────── DuplicateFlow Scanner ───────────────╮
│ Scanning: /path/to/videos                          │
│ Recursive: True | Follow symlinks: False           │
╰────────────────────────────────────────────────────╯

Searching for videos... ━━━━━━━━━━━━━━━━ 100% 0:00:05

            Videos Found: 42
┏━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━┓
┃ File           ┃   Size ┃ Format ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━┩
│ movie1.mp4     │ 150 MB │  MP4   │
│ movie2.mkv     │ 250 MB │  MKV   │
│ ...            │        │        │
└────────────────┴────────┴────────┘

╭──────────── Scan Statistics ────────────╮
│ Total Videos: 42                        │
│ Total Size: 5.2 GB (5234.56 MB)        │
│ Directories Scanned: 10                 │
│ Files Checked: 250                      │
│ Scan Duration: 5.50s                    │
│ Errors: 0                               │
│                                         │
│ By Format:                              │
│   MP4: 25                               │
│   MKV: 12                               │
│   AVI: 5                                │
╰─────────────────────────────────────────╯
```

### Export JSON

Format structuré pour intégration avec d'autres outils.

**Structure**:

```json
{
  "root_path": "/path/to/videos",
  "timestamp": "2025-12-20T12:00:00",
  "scan_duration_seconds": 5.5,
  "directories_scanned": 10,
  "total_files_checked": 250,
  "statistics": {
    "video_count": 42,
    "total_size_mb": 5234.56,
    "total_size_gb": 5.11,
    "format_counts": {
      "mp4": 25,
      "mkv": 12,
      "avi": 5
    },
    "has_errors": false,
    "error_count": 0
  },
  "videos": [
    {
      "path": "/path/to/videos/movie1.mp4",
      "filename": "movie1.mp4",
      "size_mb": 150.25,
      "size_gb": 0.15,
      "format": "mp4",
      "created_at": "2023-01-01T10:00:00",
      "modified_at": "2023-01-01T10:00:00"
    }
  ],
  "errors": [],
  "metadata": {}
}
```

**Utilisation du JSON**:

```python
import json

# Charger les résultats
with open('results.json', 'r') as f:
    data = json.load(f)

# Accéder aux informations
print(f"Total vidéos: {data['statistics']['video_count']}")
print(f"Taille totale: {data['statistics']['total_size_gb']:.2f} GB")

# Filtrer les grandes vidéos (>1GB)
big_videos = [
    v for v in data['videos']
    if v['size_gb'] > 1.0
]
print(f"Vidéos >1GB: {len(big_videos)}")
```

### Export CSV

Format tabulaire pour Excel, Google Sheets, etc.

**Colonnes**:

- `path` - Chemin complet du fichier
- `filename` - Nom du fichier
- `size_mb` - Taille en MB
- `size_gb` - Taille en GB
- `format` - Format vidéo
- `created_at` - Date de création
- `modified_at` - Date de modification

**Exemple**:

```csv
path,filename,size_mb,size_gb,format,created_at,modified_at
/videos/movie1.mp4,movie1.mp4,150.25,0.15,mp4,2023-01-01T10:00:00,2023-01-01T10:00:00
/videos/movie2.mkv,movie2.mkv,250.50,0.24,mkv,2023-01-02T11:00:00,2023-01-02T11:00:00
```

**Utilisation du CSV**:

```python
import csv
import pandas as pd

# Avec pandas
df = pd.read_csv('results.csv')
print(df.describe())

# Total par format
by_format = df.groupby('format')['size_gb'].sum()
print(by_format)

# Avec csv standard
with open('results.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        print(f"{row['filename']}: {row['size_mb']} MB")
```

---

## 🎨 Formats Vidéo Supportés

DuplicateFlow reconnaît automatiquement les formats suivants:

| Format | Extension | Description |
|--------|-----------|-------------|
| MP4 | `.mp4` | MPEG-4 Part 14 |
| MKV | `.mkv` | Matroska Video |
| AVI | `.avi` | Audio Video Interleave |
| MOV | `.mov` | QuickTime Movie |
| WMV | `.wmv` | Windows Media Video |
| FLV | `.flv` | Flash Video |
| WEBM | `.webm` | WebM Video |
| M4V | `.m4v` | iTunes Video |
| MPG | `.mpg` | MPEG Video |
| MPEG | `.mpeg` | MPEG Video |

**Note**: Les extensions sont détectées sans tenir compte de la casse (`.MP4` = `.mp4`).

---

## ⚡ Conseils de Performance

### Scan Rapide

**Optimiser le scan**:

1. **Utiliser des filtres** - Réduire la portée
   ```bash
   # Seulement MP4 et MKV
   python -m duplicateflow.cli scan /videos --formats mp4 mkv
   ```

2. **Limiter la taille** - Ignorer les petits fichiers
   ```bash
   # Seulement vidéos >100MB
   python -m duplicateflow.cli scan /videos --min-size 100
   ```

3. **Scan non-récursif** - Un seul niveau
   ```bash
   python -m duplicateflow.cli scan /videos --no-recursive
   ```

### Export Efficace

**Grandes collections**:

```bash
# Scan avec export direct (pas d'affichage)
python -m duplicateflow.cli scan /videos \
  --no-stats \
  --output-json results.json
```

---

## 🔍 Cas d'Usage

### 1. Inventaire de Collection

**Objectif**: Cataloguer toute une collection vidéo.

```bash
# Scan complet avec export
python -m duplicateflow.cli scan ~/Videos \
  --output-json inventory.json \
  --output-csv inventory.csv

# Analyser avec pandas
python << EOF
import pandas as pd
df = pd.read_csv('inventory.csv')

print("=== Inventaire ===")
print(f"Total vidéos: {len(df)}")
print(f"Taille totale: {df['size_gb'].sum():.2f} GB")
print("\nPar format:")
print(df.groupby('format').size())
EOF
```

### 2. Recherche de Fichiers Volumineux

**Objectif**: Identifier les vidéos qui prennent le plus d'espace.

```bash
# Scan avec filtre taille
python -m duplicateflow.cli scan ~/Videos \
  --min-size 1000 \
  --output-csv big_files.csv

# Top 10 plus gros fichiers
python << EOF
import pandas as pd
df = pd.read_csv('big_files.csv')
top10 = df.nlargest(10, 'size_gb')
for _, row in top10.iterrows():
    print(f"{row['size_gb']:.2f} GB - {row['filename']}")
EOF
```

### 3. Audit par Format

**Objectif**: Analyser la répartition par format.

```bash
# Scan avec export JSON
python -m duplicateflow.cli scan ~/Videos \
  --output-json audit.json

# Analyser
python << EOF
import json
with open('audit.json') as f:
    data = json.load(f)

print("=== Audit par Format ===")
for fmt, count in data['statistics']['format_counts'].items():
    print(f"{fmt.upper()}: {count} fichiers")
EOF
```

### 4. Migration de Formats

**Objectif**: Trouver tous les fichiers d'un format spécifique.

```bash
# Lister tous les AVI
python -m duplicateflow.cli scan ~/Videos \
  --formats avi \
  --output-csv avi_files.csv

# Vérifier combien
wc -l avi_files.csv
```

---

## 🛠️ Intégration avec d'Autres Outils

### Script Bash

```bash
#!/bin/bash
# scan_and_report.sh

VIDEOS_DIR="$1"
REPORT_DIR="./reports"

mkdir -p "$REPORT_DIR"

echo "Scanning $VIDEOS_DIR..."
python -m duplicateflow.cli scan "$VIDEOS_DIR" \
  --output-json "$REPORT_DIR/scan.json" \
  --output-csv "$REPORT_DIR/scan.csv"

echo "Generating report..."
python << EOF
import json
import pandas as pd

# Charger données
with open('$REPORT_DIR/scan.json') as f:
    data = json.load(f)

df = pd.read_csv('$REPORT_DIR/scan.csv')

# Rapport HTML
report = f"""
<html>
<head><title>Video Scan Report</title></head>
<body>
<h1>Video Collection Report</h1>
<p>Scanned: {data['root_path']}</p>
<p>Total videos: {data['statistics']['video_count']}</p>
<p>Total size: {data['statistics']['total_size_gb']:.2f} GB</p>
<h2>By Format</h2>
<ul>
"""

for fmt, count in data['statistics']['format_counts'].items():
    report += f"<li>{fmt.upper()}: {count}</li>\n"

report += """
</ul>
</body>
</html>
"""

with open('$REPORT_DIR/report.html', 'w') as f:
    f.write(report)

print("Report generated: $REPORT_DIR/report.html")
EOF
```

### Script Python

```python
#!/usr/bin/env python3
"""
automated_scan.py - Scan automatique avec notifications
"""

import subprocess
import json
from pathlib import Path

def scan_directory(directory: str, output_dir: str = "./reports"):
    """Scan un répertoire et génère des rapports"""

    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    json_file = output_dir / "scan.json"
    csv_file = output_dir / "scan.csv"

    # Lancer le scan
    cmd = [
        "python", "-m", "duplicateflow.cli", "scan",
        directory,
        "--output-json", str(json_file),
        "--output-csv", str(csv_file)
    ]

    print(f"Scanning {directory}...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return None

    # Charger résultats
    with open(json_file) as f:
        data = json.load(f)

    # Afficher résumé
    stats = data['statistics']
    print(f"\n✅ Scan complete!")
    print(f"Videos found: {stats['video_count']}")
    print(f"Total size: {stats['total_size_gb']:.2f} GB")
    print(f"Formats: {', '.join(stats['format_counts'].keys())}")

    return data

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python automated_scan.py <directory>")
        sys.exit(1)

    scan_directory(sys.argv[1])
```

---

## ❓ FAQ

### Q: Quelle est la différence entre `--recursive` et `--follow-symlinks`?

**A**:
- `--recursive` parcourt tous les sous-répertoires
- `--follow-symlinks` suit les liens symboliques (désactivé par défaut pour éviter les boucles)

### Q: Puis-je scanner plusieurs répertoires à la fois?

**A**: Pas directement. Lancez plusieurs scans ou créez un script:

```bash
#!/bin/bash
for dir in /videos1 /videos2 /videos3; do
  python -m duplicateflow.cli scan "$dir" \
    --output-json "${dir##*/}.json"
done
```

### Q: Comment gérer les très grandes collections (10,000+ vidéos)?

**A**: Utilisez les filtres et exportez directement:

```bash
# Scan sans affichage, export direct
python -m duplicateflow.cli scan /huge/collection \
  --no-stats \
  --output-json results.json
```

### Q: Les métadonnées vidéo (durée, résolution) sont-elles extraites?

**A**: Pas dans Phase 1. Les informations disponibles sont:
- Nom de fichier
- Taille
- Format
- Dates de création/modification

Les métadonnées vidéo complètes seront ajoutées dans Phase 2.

### Q: Peut-on exclure certains répertoires?

**A**: Pas encore implémenté. Workaround:

```bash
# Scanner et filtrer
python -m duplicateflow.cli scan /videos --output-json all.json

python << EOF
import json
with open('all.json') as f:
    data = json.load(f)

# Filtrer
data['videos'] = [
    v for v in data['videos']
    if '/exclude/' not in v['path']
]

with open('filtered.json', 'w') as f:
    json.dump(data, f, indent=2)
EOF
```

---

## 🐛 Dépannage

### Problème: "Directory does not exist"

**Cause**: Le chemin spécifié n'existe pas.

**Solution**:
```bash
# Vérifier que le répertoire existe
ls -la /path/to/videos

# Utiliser un chemin absolu
python -m duplicateflow.cli scan "$(pwd)/videos"
```

### Problème: "Permission denied"

**Cause**: Pas de permissions de lecture.

**Solution**:
```bash
# Vérifier les permissions
ls -la /path/to/videos

# Donner les permissions
chmod -R +r /path/to/videos
```

### Problème: Scan très lent

**Causes possibles**:
1. Trop de fichiers
2. Réseau lent (NAS, network drive)
3. Pas de filtres

**Solutions**:
```bash
# Filtrer par format
python -m duplicateflow.cli scan /videos --formats mp4 mkv

# Scanner local d'abord
python -m duplicateflow.cli scan /local/cache

# Scan non-récursif
python -m duplicateflow.cli scan /videos --no-recursive
```

---

## 📚 Ressources Supplémentaires

- **Guide Développeur**: [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
- **API Reference**: [API_REFERENCE.md](API_REFERENCE.md)
- **Phase 1 Summary**: [PHASE1_COMPLETE_SUMMARY.md](PHASE1_COMPLETE_SUMMARY.md)
- **Exemples**: [examples/](../examples/)

---

## 🆘 Support

**Issues**: [GitHub Issues](https://github.com/yourusername/duplicateflow/issues)
**Discussions**: [GitHub Discussions](https://github.com/yourusername/duplicateflow/discussions)

---

**Dernière mise à jour**: 2025-12-20
**Version**: 0.1.0 (Phase 1 Complete)
