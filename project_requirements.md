# VideoFlow - Gestionnaire de Vidéos

## Description
Application de bureau pour la gestion et l'organisation de fichiers vidéo, avec une architecture modulaire basée sur des plugins.

## Architecture Globale
- Architecture basée sur des plugins
- Interface graphique en PyQt6
- Structure modulaire et extensible

## Structure du Projet
```
videoFlow/
├── main.py                     # Point d'entrée de l'application
├── src/
│   ├── core/
│   │   ├── logger.py          # Système de logging
│   │   ├── plugin_interface.py # Interface abstraite pour les plugins
│   │   └── plugin_manager.py  # Gestionnaire de plugins
│   │
│   ├── ui/
│   │   └── main_window.py     # Fenêtre principale
│   │
│   └── plugins/
│       ├── duplicate_finder/   # Plugin de recherche de doublons
│       │   ├── plugin.py      # Définition du plugin
│       │   ├── window.py      # Interface utilisateur
│       │   ├── video_hasher.py # Analyse des vidéos
│       │   └── data_manager.py # Gestion des données
│       │
│       ├── regex_renamer/     # [À implémenter]
│       ├── video_merger/      # [À implémenter]
│       └── tree_manager/      # [À implémenter]
│
├── data/                     # Données des plugins
├── logs/                    # Fichiers de log
├── resources/              # Ressources statiques
└── tests/                 # Tests unitaires [À implémenter]

### Plugins

#### Duplicate Finder
Plugin pour détecter et gérer les vidéos en double.

##### Interface Utilisateur
- Boutons de contrôle :
  - "Ajouter des fichiers" : Sélection multiple de vidéos (formats : mp4, avi, mkv, mov, wmv)
  - "Ajouter un dossier" : Analyse récursive d'un dossier
  - "Analyser" : Lance l'analyse des fichiers et affiche la fenêtre de comparaison
  - "Effacer les empreintes" : Réinitialise la base de données
  - "Fermer" : Ferme la fenêtre
- Sélecteur de niveau de précision :
  - Faible : Analyse rapide mais moins précise
  - Moyen : Équilibre vitesse/précision
  - Élevé : Analyse lente mais très précise
- Barre de progression pour l'analyse
- Table des fichiers :
  - Liste triable par ordre alphabétique (insensible à la casse)
  - Colonnes : Nom du fichier, État (analysé/en attente)
  - Tri par défaut : alphabétique croissant

##### Fenêtre de Comparaison
- Apparaît uniquement après l'analyse des fichiers
- Affiche pour chaque paire de doublons :
  - Informations détaillées :
    - Noms des fichiers
    - Tailles en MB
    - Chemins complets
  - Visualisation :
    - Images côte à côte des vidéos
    - Slider pour naviguer dans les vidéos
    - Images synchronisées au même instant
  - Options de gestion :
    - "Garder Fichier 1" : Déplace le fichier 2 vers la corbeille
    - "Garder Fichier 2" : Déplace le fichier 1 vers la corbeille
    - "Garder les Deux" : Conserve les deux fichiers
    - "Ignorer Temporairement" : Ignore jusqu'au prochain lancement
    - "Ignorer Définitivement" : Ignore jusqu'à l'effacement des empreintes

##### Sécurité des Fichiers
- Aucune suppression directe :
  - Utilisation exclusive de send2trash
  - Déplacement vers la corbeille système
  - Possibilité de restauration par l'utilisateur
- Messages d'erreur explicites :
  - Notification en cas d'échec de déplacement
  - Journal détaillé des opérations
- Confirmation des actions :
  - Demande de confirmation avant l'effacement des empreintes
  - Avertissement avant le déplacement vers la corbeille

##### Analyse des Vidéos
- Niveaux de précision configurables :
  - Faible : 32x32 pixels, seuil=12
  - Moyen : 64x64 pixels, seuil=8
  - Élevé : 128x128 pixels, seuil=4
- Échantillonnage intelligent :
  - 6 images par minute de vidéo
  - Traitement parallèle (multithreading)
- Hash perceptuel adaptatif :
  - Taille de hash variable selon le niveau
  - Comparaison robuste aux modifications mineures

##### Gestion des Doublons
- Détection interactive :
  - Analyse uniquement sur demande (bouton "Analyser")
  - Fenêtre de comparaison pour chaque paire de doublons
  - Choix du fichier à conserver
  - Suppression automatique des autres fichiers
- Suppression sécurisée :
  - Utilisation de send2trash
  - Déplacement vers la corbeille système
  - Mise à jour automatique de la base de données

##### Persistance des Données
- Stockage JSON :
  - Chemins des fichiers
  - Empreintes calculées
  - Paires de fichiers ignorées
- Gestion automatique :
  - Nettoyage des fichiers manquants
  - Sauvegarde après chaque modification
  - Conservation entre les sessions

#### Autres Plugins [À venir]
- Tree Manager : Organisation hiérarchique
- Video Merger : Fusion de vidéos
- Regex Renamer : Renommage par lots

## Dépendances
- PyQt6 : Interface graphique
- OpenCV : Traitement vidéo
- ImageHash : Détection de similitudes
- Send2Trash : Suppression sécurisée
- Pillow : Traitement d'images
- Numpy : Calculs numériques

## Installation et Lancement
```bash
# Installation
pip install -r requirements.txt

# Lancement
python main.py
