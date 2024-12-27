# VideoFlow

Application de gestion et traitement de fichiers vidéo développée en Python avec PyQt6.

## Fonctionnalités

- Détection et suppression des doublons de vidéos
- Conversion automatique basée sur la taille
- Fusion de vidéos avec ordre personnalisable
- Nettoyage des noms de fichiers avec expressions régulières
- Extraction visuelle de segments vidéo

## Installation

1. Cloner le repository
```bash
git clone [URL_DU_REPO]
```

2. Installer les dépendances
```bash
pip install -r requirements.txt
```

## Configuration requise

- Python 3.8+
- FFmpeg
- Qt 6.4+

## Utilisation

Lancer l'application :
```bash
python -m src.main
```

## Structure du projet

```
videoFlow/
├── src/              # Code source
├── tests/            # Tests
├── docs/             # Documentation
├── config/           # Fichiers de configuration
└── resources/        # Ressources (icons, etc.)
```
