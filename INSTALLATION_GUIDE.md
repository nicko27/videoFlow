# Installation Guide - VideoFlow

## 📦 Installation de Base

### 1. Installer les Dépendances Système

#### macOS
```bash
# Installer Homebrew (si pas déjà installé)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Installer ffmpeg
brew install ffmpeg

# Installer chromaprint (pour audio fingerprinting)
brew install chromaprint
```

#### Linux (Ubuntu/Debian)
```bash
# Mettre à jour les paquets
sudo apt update

# Installer ffmpeg
sudo apt install ffmpeg

# Installer chromaprint (pour audio fingerprinting)
sudo apt install libchromaprint-dev chromaprint-tools
```

#### Windows
1. **FFmpeg** : Télécharger depuis https://ffmpeg.org/download.html
2. **Chromaprint** : Télécharger depuis https://acoustid.org/chromaprint
3. Ajouter les dossiers à votre PATH

---

### 2. Installer Python (3.9+)

#### macOS
```bash
brew install python@3.11
```

#### Linux
```bash
sudo apt install python3.11 python3-pip
```

#### Windows
Télécharger depuis https://www.python.org/downloads/

---

### 3. Installer VideoFlow

```bash
# Cloner le repository
git clone https://github.com/nicko27/videoFlow.git
cd videoFlow

# Créer un environnement virtuel (recommandé)
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# ou
venv\Scripts\activate  # Windows

# Installer les dépendances de base
pip install -r requirements.txt
```

---

## 🎬 Installation pour Détection de Scènes

### Option 1 : Installation Minimale (Scènes au début uniquement)

**Déjà inclus** dans `requirements.txt` - aucune action nécessaire

**Limitations** :
- ✅ Détecte les scènes au **début** des vidéos
- ❌ Ne détecte **pas** les scènes au milieu/fin

---

### Option 2 : Installation Complète (Scènes partout) ⭐ RECOMMANDÉ

```bash
# Installer pyacoustid
pip install pyacoustid
```

**Avantages** :
- ✅ Détecte les scènes **partout** dans les vidéos
- ✅ 99% de précision
- ✅ Rapide (5-15 secondes par vidéo)

**Vérification** :
```bash
python3 -c "import acoustid; print('✅ pyacoustid OK')"
fpcalc -version
```

---

### Option 3 : Toutes les Options Audio

```bash
# Installer toutes les options d'audio fingerprinting
pip install -r requirements-audio-fingerprinting.txt
```

Inclut :
- `pyacoustid` (Chromaprint) - Recommandé
- Options pour Dejavu (Shazam-like)
- Options pour Audfprint

---

## 🚀 Lancer VideoFlow

```bash
# Activer l'environnement virtuel (si utilisé)
source venv/bin/activate  # macOS/Linux

# Lancer l'application
python3 main.py
```

---

## 🧪 Test de l'Installation

### Test Basique
```bash
python3 -c "
import PyQt6
import cv2
import numpy
print('✅ Dépendances de base OK')
"
```

### Test Audio Fingerprinting
```bash
# Test fpcalc
fpcalc --help

# Test pyacoustid (si installé)
python3 -c "
import acoustid
print('✅ pyacoustid installé')
"
```

### Test Complet
```bash
# Lancer VideoFlow
python3 main.py

# Aller dans Duplicate Finder
# → Debug tab
# → Tester Hash Debugger (hachage visuel)
# → Tester Audio Fingerprint Debugger (audio fingerprinting)
```

---

## 📋 Dépendances par Fonctionnalité

| Fonctionnalité | Dépendance Requise | Installation |
|----------------|-------------------|--------------|
| Interface PyQt6 | `PyQt6>=6.4.0` | Dans `requirements.txt` |
| Traitement vidéo | `opencv-python` | Dans `requirements.txt` |
| Métadonnées (macOS) | `osxmetadata`, `xattr` | Dans `requirements.txt` |
| Duplicate Detection | `imagehash`, `numpy` | Dans `requirements.txt` |
| Scene Detection (basique) | Built-in | Aucune |
| Scene Detection (avancé) | `pyacoustid` | **`pip install pyacoustid`** |

---

## ⚠️ Problèmes Courants

### 1. "fpcalc: command not found"

**Solution** :
```bash
# macOS
brew install chromaprint

# Linux
sudo apt install chromaprint-tools
```

### 2. "No module named 'acoustid'"

**Solution** :
```bash
pip install pyacoustid
```

### 3. "ERROR: No matching distribution found for pyacoustid"

**Cause** : Chromaprint n'est pas installé système

**Solution** :
```bash
# macOS
brew install chromaprint
pip install pyacoustid

# Linux
sudo apt install libchromaprint-dev
pip install pyacoustid
```

### 4. "Qt platform plugin could not be initialized"

**Solution** :
```bash
# Réinstaller PyQt6
pip uninstall PyQt6
pip install PyQt6
```

### 5. Scènes détectées uniquement au début

**Cause** : pyacoustid n'est pas installé

**Solution** :
```bash
pip install pyacoustid
# Relancer VideoFlow
```

---

## 🔧 Installation Développeur

### Pour contribuer au projet

```bash
# Cloner le repo
git clone https://github.com/nicko27/videoFlow.git
cd videoFlow

# Installer en mode éditable
pip install -e .

# Installer les dépendances dev
pip install -r requirements-dev.txt

# Lancer les tests (si disponibles)
pytest
```

---

## 📚 Ressources

### Documentation
- **VideoFlow** : README.md
- **Scene Detection** : SCENE_DETECTION_INSTALL.md
- **Audio Fingerprinting** : AUDIO_FINGERPRINTING_METHODS.md
- **Limitations** : SCENE_DETECTION_LIMITATIONS.md

### Liens Externes
- **FFmpeg** : https://ffmpeg.org/
- **Chromaprint** : https://acoustid.org/chromaprint
- **PyQt6** : https://www.riverbankcomputing.com/software/pyqt/
- **OpenCV** : https://opencv.org/

---

## ✅ Installation Rapide (TL;DR)

### macOS
```bash
# Système
brew install ffmpeg chromaprint

# Python
cd videoFlow
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install pyacoustid  # Pour scènes partout

# Lancer
python3 main.py
```

### Linux
```bash
# Système
sudo apt install ffmpeg libchromaprint-dev chromaprint-tools

# Python
cd videoFlow
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install pyacoustid  # Pour scènes partout

# Lancer
python3 main.py
```

---

## 🎯 Configurations Recommandées

### Configuration Minimale
```
- Python 3.9+
- 4 GB RAM
- FFmpeg
- requirements.txt
```

### Configuration Recommandée
```
- Python 3.11+
- 8 GB RAM
- FFmpeg
- Chromaprint
- requirements.txt + pyacoustid
```

### Configuration Optimale
```
- Python 3.11+
- 16 GB RAM
- FFmpeg
- Chromaprint
- requirements-audio-fingerprinting.txt (tout)
- SSD pour stockage vidéo
```

---

## 📞 Support

- **Issues** : https://github.com/nicko27/videoFlow/issues
- **Documentation** : Voir fichiers *.md dans le projet
- **Logs** : Consultez les logs dans l'interface pour déboguer

---

**Bonne utilisation ! 🎉**
