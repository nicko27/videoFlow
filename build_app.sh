#!/bin/bash

# Créer l'environnement virtuel
python3 -m venv venv
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt
pip install pyinstaller

# Nettoyer les anciens builds
rm -rf build dist

# Construire l'application
pyinstaller --name "VideoFlow" \
            --windowed \
            --icon=src/resources/icon.icns \
            --add-data "src/plugins:plugins" \
            --add-data "src/resources:resources" \
            --add-data "src/core:core" \
            --hidden-import PyQt6.QtCore \
            --hidden-import PyQt6.QtWidgets \
            --hidden-import PyQt6.QtGui \
            --hidden-import cv2 \
            --hidden-import numpy \
            --hidden-import moviepy \
            --hidden-import transformers \
            --hidden-import torch \
            src/main.py

# Copier les fichiers nécessaires
mkdir -p "dist/VideoFlow.app/Contents/Resources/plugins"
mkdir -p "dist/VideoFlow.app/Contents/Resources/core"

# Nettoyer les fichiers .pyc
find dist/VideoFlow.app -name "*.pyc" -delete
find dist/VideoFlow.app -name "__pycache__" -delete

echo "Application créée dans dist/VideoFlow.app"
