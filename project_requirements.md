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
    - Copy Manager : ⎘ (U+2398, symbole de copie)
    - Duplicate Finder : ⚲ (U+26B2, symbole de loupe)
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
│       └── copy_manager/     # Plugin de copie de structure
│           ├── __init__.py   # Initialisation du plugin
│           ├── plugin.py     # Définition du plugin
│           ├── window.py     # Interface utilisateur
│           └── copy_manager.py # Logique de copie
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

### Regex Renamer
- Fonctionnalités :
  - Gestion des expressions régulières pour le renommage
  - Prévisualisation en temps réel des modifications
  - Historique et restauration des noms
  - Suppression de séquences numériques/alphabétiques
  - Validation des noms de fichiers

- Interface :
  - Vue en deux colonnes (avant/après)
  - Coloration des parties modifiées
  - Mise à jour instantanée des prévisualisations
  - Barre de progression pour les opérations

- Gestion des Noms Originaux :
  - Stockage dans un attribut étendu spécifique à VideoFlow
  - Séparation des métadonnées système et VideoFlow
  - Restauration possible même après plusieurs modifications
  - Sauvegarde automatique avant modification

- Numérotation Avancée :
  - Suppression de séquences à position fixe
  - Support des séquences numériques et alphabétiques
  - Configuration de la longueur des séquences
  - Détection automatique des positions

- Sécurité et Validation :
  - Vérification des caractères invalides sous macOS
  - Détection des conflits de noms
  - Sauvegarde automatique avant modification
  - Validation des expressions régulières

## Plugin MetaRenamer

### Interface Utilisateur
- [ ] Tableau des fichiers avec colonnes :
  - Nom du fichier
  - Nom dans les métadonnées
  - Différence détectée (indicateur visuel)
  - Actions (renommer selon meta)
- [ ] Options de filtrage :
  - Afficher uniquement les fichiers avec différences
  - Filtrage par type de fichier vidéo
- [ ] Boutons d'action :
  - " Ajouter Fichiers"
  - " Ajouter Dossier"
  - " Synchroniser Tout"
  - " Synchroniser Sélection"

### Fonctionnalités
- [ ] Lecture des métadonnées :
  - Support des formats vidéo courants
  - Extraction du titre depuis les métadonnées
  - Gestion des erreurs de lecture
- [ ] Comparaison intelligente :
  - Détection des différences mineures
  - Prise en compte des extensions
  - Normalisation des noms pour comparaison
- [ ] Prévisualisation en temps réel :
  - Mise en évidence des différences
  - Aperçu du nouveau nom
- [ ] Renommage sélectif ou global
- [ ] Sauvegarde des préférences utilisateur

### Améliorations Techniques
- [ ] Cache des métadonnées pour performance
- [ ] Gestion robuste des erreurs de lecture
- [ ] Interface responsive
- [ ] Logging détaillé des opérations

## Plugin RegexRenamer

### Interface Utilisateur
- [x] Tableau des patterns avec colonnes :
  - "Utiliser" (case à cocher)
  - "Chercher" (pattern regex)
  - "Remplacer par" (texte de remplacement)
  - "Respecter Maj/Min" (case à cocher)
  - "Position" (options : mot complet, début, fin)
  - Actions (suppression)
- [x] Tableau des fichiers avec :
  - Nom original
  - Nouveau nom (prévisualisé en vert si modifié)
  - Tri par modification et ordre alphabétique
  - Infobulle détaillée pour les noms modifiés
- [x] Options de filtrage :
  - Case à cocher pour inclure les fichiers cachés
  - Filtrage automatique par type de fichier
  - Filtres d'extension dynamiques
- [x] Boutons d'action :
  - " Ajouter Fichiers"
  - " Ajouter Dossier"
  - " Nouveau Pattern"
  - " Renommer Tout"
  - " Renommer Sélection"

### Fonctionnalités
- [x] Gestion des patterns :
  - Sauvegarde/chargement des patterns personnalisés
  - Préservation de l'état actif/inactif des patterns
  - Patterns prédéfinis triés par impact
  - Application répétée des patterns jusqu'à stabilisation
  - Options de position (mot complet, début, fin)
  - Suppression fiable des patterns
- [x] Gestion des fichiers :
  - Exclusion des fichiers temporaires (.part, .crdownload, etc.)
  - Préservation des extensions lors du renommage
  - Préservation des tags macOS lors du renommage
  - Support des fichiers cachés (optionnel)
  - Tri intelligent des fichiers (modifiés/non-modifiés)
- [x] Prévisualisation en temps réel :
  - Mise à jour instantanée lors des modifications de patterns
  - Coloration des noms modifiés
  - Infobulles détaillées montrant les changements
- [x] Renommage sélectif ou global
- [x] Interface responsive et intuitive

### Patterns Prédéfinis
1. Suppression du texte entre parenthèses
2. Suppression des espaces
3. Suppression des chiffres
4. Suppression des hashtags
5. Suppression des numéros au début
6. Remplacement des points (sauf extension)
7. Remplacement des espaces par underscores
8. Remplacement des underscores par espaces

### Améliorations Techniques
- [x] Sauvegarde des patterns dans ~/.regex_renamer_patterns.json
- [x] Tri des patterns par impact pour optimiser le renommage
- [x] Protection contre les boucles infinies
- [x] Gestion robuste des erreurs
- [x] Interface responsive
- [x] Gestion intelligente des tooltips
- [x] Tri personnalisé des fichiers

## Gestion des Tags macOS
- Utilisation de la bibliothèque `osxmetadata` pour une gestion complète des métadonnées :
  - Tags macOS (étiquettes)
  - Commentaires Finder
  - Étiquettes de couleur
  - Dates personnalisées (ajout, dernière utilisation)
  - Métadonnées Spotlight (auteurs, mots-clés, titre, copyright)

### Copy Manager
- Fonctionnalités :
  - Copie de structure de dossiers
  - Copie optionnelle des fichiers
  - Préservation des métadonnées macOS
  - Exclusion des fichiers cachés par défaut
  - Gestion des conflits de noms (renommage automatique)
- Persistance :
  - Sauvegarde des chemins source et destination
  - Restauration automatique au démarrage
- Interface :
  - Sélection des dossiers source et destination
  - Options configurables :
    - Copier les fichiers (activé par défaut)
    - Préserver les métadonnées (activé par défaut)
    - Inclure les fichiers cachés (désactivé par défaut)
  - Barre de progression
  - Journal des opérations

### Duplicate Finder
- Fonctionnalités :
  - Recherche de vidéos en double
  - Comparaison par hash
  - Gestion des résultats
- Interface :
  - Sélection du dossier à analyser
  - Liste des doublons trouvés
  - Actions possibles sur les doublons

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

## Installation et Lancement
```bash
# Installation
pip install -r requirements.txt

# Lancement
python main.py
