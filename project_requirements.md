# VideoFlow - Gestionnaire de Vidéos

## Description
Application de bureau pour la gestion et l'organisation de fichiers vidéo, avec une architecture modulaire basée sur des plugins.

## Architecture Globale
- Architecture basée sur des plugins
- Interface graphique en PyQt6
- Structure modulaire et extensible

## Interface Principale
- Fenêtre principale avec une grille de boutons pour les plugins
- Chaque plugin est représenté par :
  - Un grand bouton coloré (200x150 pixels minimum)
  - Une icône Unicode représentative (48pt)
    - Copy Manager : 📋 (U+1F4CB, presse-papiers)
    - Duplicate Finder : 🔍 (U+1F50D, loupe)
    - Video Adder : 🎬 (U+1F3AC, clap de cinéma)
    - Video Converter : 🔄 (U+1F504, flèches de conversion)
    - Regex Renamer : ✏️ (U+270F, crayon)
    - Video Editor : ✂️ (U+2702, ciseaux)
    - Icône par défaut : ◈ (U+25C8, losange)
  - Le nom du plugin en gras (12pt)
  - Une courte description (10pt)
- Menu supplémentaire dans la barre de menus pour accès alternatif
- Effets visuels :
  - Boutons avec coins arrondis
  - Effet de survol avec assombrissement et bordure blanche
  - Texte centré et adapté à la taille

## Structure du Projet
```
videoFlow/
├── main.py                     # Point d'entrée de l'application
├── src/
│   ├── core/
│   │   ├── __init__.py        # Initialisation du package core
│   │   ├── logger.py          # Système de logging
│   │   ├── plugin_interface.py # Interface abstraite pour les plugins
│   │   └── plugin_manager.py  # Gestionnaire de plugins
│   │
│   ├── ui/
│   │   ├── __init__.py       # Initialisation du package ui
│   │   └── main_window.py    # Fenêtre principale
│   │
│   └── plugins/
│       ├── __init__.py       # Initialisation du package plugins
│       │
│       ├── duplicate_finder/  # Plugin de recherche de doublons
│       │   ├── __init__.py   # Initialisation du plugin
│       │   ├── plugin.py     # Définition du plugin
│       │   ├── window.py     # Interface utilisateur
│       │   ├── video_hasher.py # Analyse des vidéos
│       │   └── data_manager.py # Gestion des données
│       │
│       ├── copy_manager/     # Plugin de copie de structure
│       │   ├── __init__.py   # Initialisation du plugin
│       │   ├── plugin.py     # Définition du plugin
│       │   ├── window.py     # Interface utilisateur
│       │   └── copy_manager.py # Logique de copie
│       │
│       └── video_adder/      # Plugin de fusion de vidéos
│           ├── __init__.py   # Initialisation du plugin
│           ├── plugin.py     # Définition du plugin
│           └── window.py     # Interface utilisateur
│
├── data/                     # Données des plugins
│   ├── duplicate_finder/     # Données du plugin duplicate_finder
│   └── copy_manager/        # Données du plugin copy_manager
│
├── logs/                    # Fichiers de log
│   └── videoflow.log       # Journal principal de l'application
│
└── tests/                 # Tests unitaires [À implémenter]

### Plugins

#### Duplicate Finder
Plugin pour détecter et gérer les vidéos en double.

##### Interface Utilisateur
- Fenêtre principale :
  - Taille minimale : 1200x600 pixels
  - Boutons d'action :
    - Ajouter des fichiers
    - Ajouter un dossier
    - Analyser
    - Effacer les empreintes
    - Supprimer la sélection
    - Fermer
  - Niveau de précision :
    - Slider de 1 à 3
    - Affichage des graduations
  - Table des fichiers :
    - Colonnes : Fichier, État
    - États possibles : En attente, Analysé, Introuvable
    - Sélection multiple
    - Tri par colonne
    - Fichiers introuvables en rouge
- Fenêtre de doublons :
  - Liste des groupes de doublons
  - Actions par fichier :
    - Ouvrir
    - Supprimer
    - Ignorer
  - Prévisualisation des vidéos

##### Gestion des Fichiers
- États des fichiers :
  - En attente : pas encore analysé
  - Analysé : empreinte calculée
  - Introuvable : fichier supprimé/déplacé
- Actions :
  - Effacer les empreintes : conserve les fichiers, reset leur état
  - Supprimer de la liste : retire les fichiers sélectionnés
  - Ignorer un doublon : mémorisé entre les sessions

##### Analyse Vidéo
- Calcul d'empreintes :
  - Extraction de frames
  - Hash perceptuel
  - Niveaux de précision (1-3)
- Comparaison :
  - Entre nouveaux fichiers
  - Avec fichiers existants
  - Évite les doublons
- Progression :
  - 0-50% : calcul des empreintes
  - 50-100% : comparaison

##### Persistance des Données
- Stockage JSON :
  - Chemins des fichiers
  - Empreintes vidéo (hash perceptuel)
    - Conversion des tableaux numpy en listes pour JSON
    - Reconversion en numpy lors du chargement
  - Paires de fichiers ignorées
    - Stockées sous forme de tuples triés
    - Garantit l'unicité des paires
- Gestion automatique :
  - Nettoyage des fichiers manquants
  - Sauvegarde après chaque modification
  - Conservation entre les sessions
  - Vérification de l'intégrité des données
- Format du fichier JSON :
  ```json
  {
    "analyzed_files": {
      "/chemin/vers/video1.mp4": [[true, false, ...], [false, true, ...]],
      "/chemin/vers/video2.mp4": [[true, true, ...], [false, false, ...]]
    },
    "ignored_pairs": [
      ["/chemin/vers/video1.mp4", "/chemin/vers/video2.mp4"],
      ["/chemin/vers/video3.mp4", "/chemin/vers/video4.mp4"]
    ]
  }
  ```

#### Copy Manager
Plugin pour copier la structure des dossiers avec ou sans les fichiers.

##### Interface Utilisateur
- Fenêtre principale :
  - Sélection du dossier source
  - Sélection du dossier destination
  - Deux modes de copie :
    - Structure seule
    - Structure avec fichiers
  - Options :
    - Préserver les tags macOS
    - Renommage automatique
  - Barre de progression
  - Journal des opérations

##### Modes de Copie
- Structure seule :
  - Copie uniquement l'arborescence
  - Crée les dossiers vides
  - Préserve les attributs des dossiers
  - Préserve les tags macOS des dossiers
- Structure avec fichiers :
  - Copie l'arborescence complète
  - Copie tous les fichiers
  - Renommage automatique si conflit
  - Préserve les tags macOS
  - Préserve les attributs

##### Gestion des Conflits
- Renommage automatique :
  - Format : nom (1).ext, nom (2).ext, etc.
  - Incrémente jusqu'à trouver un nom libre
  - Conserve l'extension d'origine
- Journalisation :
  - Liste des fichiers renommés
  - Liste des fichiers copiés
  - Erreurs éventuelles

##### Attributs macOS
- Préservation des tags :
  - Lecture des tags source
  - Copie vers la destination
  - Vérification après copie
- Préservation des métadonnées :
  - Date de création
  - Date de modification
  - Attributs étendus

##### Performance
- Opérations asynchrones
- Barre de progression détaillée :
  - Analyse en cours
  - Copie en cours
  - Fichier en cours
- Estimation du temps restant

#### Video Adder
Plugin pour fusionner plusieurs vidéos en une seule.

##### Interface Utilisateur
- Fenêtre principale :
  - Sélection des vidéos à fusionner
  - Sélection du dossier de sortie
  - Options de fusion :
    - Format de sortie (mp4, mov, mkv, etc.)
    - Codec vidéo (h264, h265, etc.)
    - Qualité vidéo (CRF)
    - Codec audio (aac, mp3, etc.)
    - Bitrate audio
    - Résolution
    - FPS
  - Barre de progression
  - Journal des opérations

##### Modes de Fusion
- Fusion rapide avec FFmpeg si les vidéos sont compatibles
- Repli sur MoviePy pour les vidéos incompatibles
- Préservation de la qualité originale si possible
- Suppression sécurisée des fichiers originaux (optionnel)
- Suggestion intelligente du nom de fichier final

##### Gestion des Fichiers
- États des fichiers :
  - En attente : pas encore fusionné
  - Fusionné : fichier créé
  - Erreur : erreur lors de la fusion
- Actions :
  - Supprimer de la liste : retire les fichiers sélectionnés
  - Ignorer un fichier : mémorisé entre les sessions

##### Analyse Vidéo
- Lecture des métadonnées vidéo
- Détection de la compatibilité des vidéos
- Sélection du codec vidéo et audio approprié

##### Persistance des Données
- Stockage JSON :
  - Chemins des fichiers
  - Métadonnées vidéo
  - Paires de fichiers ignorées
- Gestion automatique :
  - Nettoyage des fichiers manquants
  - Sauvegarde après chaque modification
  - Conservation entre les sessions
  - Vérification de l'intégrité des données

#### Video Editor
Plugin pour éditer et découper des vidéos.

##### Interface Utilisateur
- Fenêtre principale :
  - Timeline avec aperçu des frames
  - Contrôles de lecture (play, pause, stop)
  - Marqueurs de début et fin
  - Boutons d'action :
    - "✂️ Découper"
    - "🗑️ Supprimer Segment"
    - "💾 Sauvegarder"
    - "❌ Fermer"
  - Options d'édition :
    - Découpe précise (frame par frame)
    - Suppression de segments
    - Réorganisation des segments
  - Prévisualisation en temps réel
  - Barre de progression
  - Journal des opérations

##### Fonctionnalités
- Édition de base :
  - Découpe de segments
  - Suppression de parties
  - Réorganisation des segments
  - Préservation de la qualité originale
- Édition avancée :
  - Navigation frame par frame
  - Détection automatique des scènes
  - Marqueurs personnalisés
  - Points de repère temporels
- Prévisualisation :
  - Aperçu en temps réel
  - Miniatures des frames clés
  - Forme d'onde audio
  - Zoom sur la timeline

##### Gestion des Fichiers
- États des fichiers :
  - Original : fichier non modifié
  - Édité : modifications en cours
  - Sauvegardé : modifications appliquées
- Actions :
  - Sauvegarde automatique
  - Restauration de version
  - Historique des modifications
  - Export des segments

##### Analyse Vidéo
- Lecture des métadonnées
- Détection des scènes
- Analyse des frames clés
- Extraction de la forme d'onde audio

##### Persistance des Données
- Stockage JSON :
  - Points de découpe
  - Segments supprimés
  - Marqueurs personnalisés
  - Historique des modifications
- Gestion automatique :
  - Sauvegarde périodique
  - Restauration de session
  - Backup avant modification
  - Journal des opérations

### Plugin DuplicateFinder

### Description
Le plugin DuplicateFinder permet de détecter les vidéos en double dans une collection en utilisant des empreintes perceptuelles (perceptual hashing).

### Fonctionnalités

#### Interface utilisateur
- Ajout de fichiers individuels ou de dossiers complets
- Liste des fichiers avec leur statut (En attente, Traité)
- Barre de progression pour le calcul des hashs et la comparaison
- Fenêtre de comparaison côte à côte des doublons potentiels
- Seuils ajustables pour la similarité et la durée

#### Calcul des empreintes
- Utilisation de l'algorithme pHash (Perceptual Hash)
- Échantillonnage intelligent des frames (première, dernière, et frames à intervalles réguliers)
- Cache des empreintes pour éviter les recalculs
- Gestion des erreurs de lecture de frames

#### Comparaison des vidéos
- Comparaison bit à bit des empreintes
- Calcul de similarité en pourcentage
- Prise en compte de la durée des vidéos
- Gestion des paires ignorées

### Architecture

#### Classes principales
1. `DuplicateFinderWindow`
   - Fenêtre principale du plugin
   - Gestion de l'interface utilisateur
   - Coordination des opérations d'analyse

2. `VideoHasher`
   - Calcul et stockage des empreintes
   - Gestion du cache
   - Comparaison des empreintes

3. `DuplicateComparisonDialog`
   - Affichage côte à côte des vidéos similaires
   - Lecture synchronisée
   - Options de suppression

#### Workflow
1. L'utilisateur ajoute des fichiers vidéo
2. Au clic sur "Analyser" :
   - Calcul des empreintes manquantes
   - Comparaison de toutes les paires possibles
   - Affichage des doublons potentiels
3. Pour chaque doublon :
   - Comparaison visuelle dans une fenêtre dédiée
   - Possibilité de supprimer un des fichiers
   - Option pour ignorer la paire

### Stockage des données

#### Cache des empreintes (video_hashes.json)
```json
{
    "pHash": {
        "/chemin/vers/video.mp4": {
            "hash": [...],  // Matrice 3D de booléens
            "duration": 123.45,  // Durée en secondes
            "frames": [0, 500, 1000, ...]  // Indices des frames utilisées
        }
    }
}
```

#### Paires ignorées (ignored_pairs.json)
```json
[
    ["/chemin/vers/video1.mp4", "/chemin/vers/video2.mp4"],
    ...
]
```

### Performances
- Utilisation de numpy pour les calculs d'empreintes
- Cache pour éviter les recalculs
- Traitement asynchrone via QThread
- Échantillonnage intelligent des frames

### Limitations connues
- Les vidéos doivent être lisibles par OpenCV
- La comparaison est sensible aux modifications de format
- Les différences de durée > 5 minutes sont ignorées par défaut

### Dépendances
- PyQt6 : Interface graphique
- OpenCV (cv2) : Lecture et traitement vidéo
- numpy : Calculs matriciels
- json : Stockage des données

### Fonctionnalités des Plugins

### Copy Manager
- Copie de structure de dossiers
- Copie optionnelle des fichiers
- Préservation des métadonnées macOS
- Exclusion des fichiers cachés par défaut

### Duplicate Finder
- Détection de vidéos similaires ou identiques
- Comparaison par hash perceptuel
- Affichage des résultats en groupes
- Prévisualisation des vidéos
- Suppression sécurisée des doublons

### Video Adder
- Fusion de plusieurs vidéos en une seule
- Fusion rapide avec FFmpeg si les vidéos sont compatibles
- Repli sur MoviePy pour les vidéos incompatibles
- Préservation de la qualité originale si possible
- Suppression sécurisée des fichiers originaux (optionnel)
- Suggestion intelligente du nom de fichier final

### Video Editor
- Édition et découpage de vidéos
- Découpe précise (frame par frame)
- Suppression de segments
- Réorganisation des segments
- Préservation de la qualité originale
- Prévisualisation en temps réel

## Dépendances
- PyQt6 : Interface graphique
- osxmetadata : Gestion des métadonnées macOS
- xattr : Gestion des attributs étendus
- send2trash : Suppression sécurisée
- opencv-python : Traitement vidéo
- imagehash : Génération de hash
- Pillow : Traitement d'images
- numpy : Calculs numériques
- regex : Gestion des expressions régulières
- ffmpeg-python : Conversion vidéo
- moviepy : Traitement vidéo

## Installation et Lancement
```bash
# Installation
pip install -r requirements.txt

# Lancement
python main.py

```
# VideoFlow - Spécifications du Projet

## Description Générale
Application de gestion et d'édition de vidéos avec une interface graphique PyQt6.

## Fonctionnalités

### 1. Interface Principale
- [x] Fenêtre principale avec menu et barre d'outils
- [x] Système de plugins modulaire
- [x] Gestion des préférences utilisateur
- [x] Interface responsive et moderne

### 2. Gestion des Fichiers
- [x] Explorateur de fichiers intégré
- [x] Prévisualisation des vidéos
- [x] Gestion des formats vidéo courants
- [x] Détection automatique des doublons

### 3. Plugins

#### 3.1 Video Editor
- [x] Prévisualisation vidéo en temps réel
- [x] Timeline interactive avec marqueurs
- [x] Découpage de segments vidéo
  - [x] Marqueurs de début et fin
  - [x] Prévisualisation des points de découpe
  - [x] Export rapide avec ffmpeg
  - [x] Tableau de gestion des segments
- [x] Forme d'onde audio
- [ ] Filtres vidéo basiques
- [ ] Ajustements audio

#### 3.2 Video Converter
- [x] Conversion entre formats vidéo
- [x] Préréglages de conversion
- [x] Options de compression
- [x] Conversion par lots

#### 3.3 Regex Renamer
- [x] Renommage par expressions régulières
- [x] Prévisualisation des changements
- [x] Renommage par lots
- [x] Modèles de renommage

#### 3.4 Duplicate Finder
- [x] Détection des doublons vidéo
- [x] Comparaison par hash
- [x] Affichage des résultats en groupes
- [x] Prévisualisation des vidéos
- [x] Suppression sécurisée des doublons

### 4. Performance
- [x] Chargement asynchrone des vidéos
- [x] Mise en cache des prévisualisations
- [x] Optimisation des opérations lourdes
- [x] Utilisation efficace de la mémoire

### 5. Interface Utilisateur
- [x] Design moderne et intuitif
- [x] Thème sombre
- [x] Icônes et indicateurs visuels clairs
- [x] Retours visuels des opérations

### 6. Sécurité et Stabilité
- [x] Gestion des erreurs robuste
- [x] Sauvegarde automatique des préférences
- [x] Validation des entrées utilisateur
- [x] Logs détaillés des opérations

## Dépendances Principales
- PyQt6 : Interface graphique
- OpenCV (cv2) : Traitement vidéo
- FFmpeg : Conversion et découpage vidéo
- MoviePy : Édition vidéo avancée
- NumPy : Traitement numérique

## Configuration Requise
- Python 3.8+
- FFmpeg installé sur le système
- Qt 6.0+
- 4GB RAM minimum
- Espace disque selon les vidéos traitées

## Notes de Développement
- Architecture modulaire avec système de plugins
- Code documenté et testé
- Gestion des versions avec Git
- Logs détaillés pour le débogage
