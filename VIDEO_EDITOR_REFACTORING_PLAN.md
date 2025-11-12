# Plan Complet de Refonte - Video Editor

**Date**: 2025-11-12
**Objectif**: Moderniser l'architecture, l'interface et les fonctionnalités du plugin Video Editor
**Statut Actuel**: 16,023 lignes de code, 42 fichiers, architecture monolithique

---

## 🎯 Objectifs de la Refonte

### Objectifs Principaux
1. **Architecture**: Éliminer le "God Object" (window.py - 2,822 lignes)
2. **Performance**: Améliorer la réactivité et la gestion mémoire
3. **Interface**: Moderniser et simplifier l'UI
4. **Maintenabilité**: Faciliter l'évolution et la correction de bugs
5. **Qualité**: Ajouter tests, documentation, gestion d'erreurs

### Métriques de Succès
- ✅ Aucun fichier > 500 lignes
- ✅ Couverture de tests > 70%
- ✅ Temps de chargement < 2s
- ✅ Export 4K sans freeze de l'UI
- ✅ Code 100% anglais

---

## 📊 État des Lieux

### Points Critiques Identifiés

#### 🔴 CRITIQUE: Architecture Monolithique
```
window.py: 2,822 lignes (17.6% du code total!)
├── 100+ méthodes
├── Gestion playback, segments, export, UI, events
├── Impossible à tester
└── Impossible à maintenir
```

#### 🔴 CRITIQUE: 3 Implémentations de Timeline
- `timeline.py` (297 lignes)
- `enhanced_timeline.py` (447 lignes) ← Utilisé actuellement
- `multi_track_timeline.py` (500 lignes) ← NON intégré

#### 🟡 Code Dupliqué
- `black_frame_detector.py` (racine ET `detectors/`)
- `dialogs.py` ET `dialogs/` directory
- `widgets.py` ET `widgets/` directory

#### 🟡 Mélange Français/Anglais
- Comments en français
- Variables mixtes
- Messages utilisateur en français

#### 🟡 Absence de Tests
- 0% de couverture
- Aucun test unitaire
- Aucun test d'intégration

---

## 🏗️ Nouvelle Architecture

### Architecture MVC Moderne

```
src/plugins/video_editor/
│
├── 📦 Core (Point d'entrée)
│   ├── __init__.py
│   ├── plugin.py                    # Plugin interface (unchanged)
│   └── constants.py                 # Configuration globale
│
├── 🎨 UI (Vue - Interface Utilisateur)
│   ├── __init__.py
│   ├── main_window.py               # Shell principal (< 200 lignes)
│   ├── layouts/
│   │   └── davinci_layout.py        # Layout DaVinci (supprimer Classic)
│   │
│   ├── panels/                      # Panneaux de l'interface
│   │   ├── __init__.py
│   │   ├── preview_panel.py         # Panneau de prévisualisation
│   │   ├── timeline_panel.py        # Conteneur timeline
│   │   ├── inspector_panel.py       # Propriétés segment (KEEP)
│   │   ├── media_browser_panel.py   # Navigateur média (KEEP)
│   │   └── tools_panel.py           # Outils d'édition
│   │
│   ├── widgets/                     # Widgets réutilisables
│   │   ├── __init__.py
│   │   ├── timeline_widget.py       # Timeline unique (merge enhanced + multitrack)
│   │   ├── preview_widget.py        # Lecteur vidéo (KEEP)
│   │   ├── waveform_widget.py       # NEW: Visualisation audio
│   │   └── playback_controls.py     # NEW: Contrôles playback séparés
│   │
│   ├── dialogs/                     # Fenêtres de dialogue
│   │   ├── __init__.py
│   │   ├── export_dialog.py
│   │   ├── transition_dialog.py     # KEEP
│   │   ├── text_editor_dialog.py    # KEEP (refactor en widgets)
│   │   ├── preferences_dialog.py    # KEEP
│   │   └── project_settings_dialog.py  # NEW
│   │
│   └── dashboard/
│       ├── __init__.py
│       └── dashboard_view.py        # Dashboard (KEEP)
│
├── 🎮 Controllers (Logique de Contrôle)
│   ├── __init__.py
│   ├── playback_controller.py       # Play/Pause/Seek/Speed
│   ├── segment_controller.py        # CRUD segments
│   ├── timeline_controller.py       # État timeline (zoom, scroll, sélection)
│   ├── export_controller.py         # Orchestration export
│   ├── import_controller.py         # Chargement fichiers
│   ├── edit_controller.py           # Opérations édition (cut/split/merge)
│   └── effects_controller.py        # Transitions, texte, audio
│
├── 💾 Models (Données)
│   ├── __init__.py
│   ├── project.py                   # Modèle projet principal
│   ├── segment.py                   # Modèle segment amélioré
│   ├── track.py                     # NEW: Modèle piste (multi-track)
│   ├── timeline_state.py            # État de la timeline
│   ├── transition.py                # Modèle transition
│   ├── text_overlay.py              # Modèle overlay texte
│   └── marker.py                    # Modèle marqueur
│
├── 🔧 Services (Logique Métier)
│   ├── __init__.py
│   ├── video_service.py             # Abstraction cv2.VideoCapture
│   ├── ffmpeg_service.py            # Génération commandes FFmpeg
│   ├── thumbnail_service.py         # Génération thumbnails (async)
│   ├── export_service.py            # Pipeline d'export
│   ├── project_service.py           # Sauvegarde/chargement projets
│   ├── cache_service.py             # NEW: Gestion cache (frames, thumbnails)
│   └── task_service.py              # NEW: Gestionnaire de tâches async
│
├── 🔍 Features (Fonctionnalités Spécialisées)
│   ├── __init__.py
│   ├── transitions/                 # Système de transitions
│   │   ├── __init__.py
│   │   ├── transition_engine.py
│   │   ├── transition_presets.py
│   │   └── transition_renderer.py
│   │
│   ├── text/                        # Système de texte
│   │   ├── __init__.py
│   │   ├── text_engine.py
│   │   ├── text_templates.py        # KEEP
│   │   └── text_renderer.py
│   │
│   ├── audio/                       # Système audio
│   │   ├── __init__.py
│   │   ├── audio_mixer.py
│   │   ├── audio_extractor.py
│   │   └── audio_analyzer.py        # NEW: Waveform data
│   │
│   ├── detection/                   # Détection automatique
│   │   ├── __init__.py
│   │   ├── scene_detector.py        # KEEP
│   │   ├── black_frame_detector.py  # KEEP (remove duplicate)
│   │   └── silence_detector.py      # NEW
│   │
│   └── transcription/               # Auto-transcription
│       ├── __init__.py
│       └── transcription_service.py # KEEP (consider separate plugin)
│
├── 💿 Data (Persistance)
│   ├── __init__.py
│   ├── project_io.py                # Lecture/écriture projets
│   ├── segment_io.py                # Sérialisation segments
│   ├── history_manager.py           # KEEP: Undo/Redo
│   └── schema.py                    # NEW: Validation schéma projet
│
├── 🎨 Themes (Thèmes)
│   ├── __init__.py
│   ├── theme_manager.py             # KEEP
│   └── themes.py                    # KEEP
│
├── 🛠️ Utils (Utilitaires)
│   ├── __init__.py
│   ├── video_utils.py               # Helpers vidéo
│   ├── ffmpeg_utils.py              # Helpers FFmpeg
│   ├── time_utils.py                # Conversions timecode
│   └── file_utils.py                # Helpers fichiers
│
└── 🧪 Tests (Tests Unitaires/Intégration)
    ├── __init__.py
    ├── unit/
    │   ├── test_models.py
    │   ├── test_controllers.py
    │   ├── test_services.py
    │   └── test_features.py
    ├── integration/
    │   ├── test_export_pipeline.py
    │   ├── test_project_io.py
    │   └── test_editing_workflow.py
    └── fixtures/
        ├── sample_project.json
        └── sample_video.mp4
```

### Principes Architecturaux

1. **Separation of Concerns**
   - UI ne contient QUE du code PyQt6
   - Controllers orchestrent les opérations
   - Services contiennent la logique métier
   - Models sont de simples dataclasses

2. **Single Responsibility**
   - Chaque classe a UNE responsabilité
   - Fichiers < 500 lignes
   - Méthodes < 50 lignes

3. **Dependency Injection**
   - Controllers reçoivent leurs dépendances
   - Facilite les tests (mock)
   - Découplage des composants

4. **Event-Driven**
   - Communication via signals/slots Qt
   - État centralisé avec observers
   - Pas de couplage direct UI ↔ Services

---

## 🎨 Refonte Interface Utilisateur

### Philosophie de Design

**Objectif**: Interface professionnelle, épurée, inspirée de DaVinci Resolve

### Layout Unique: "DaVinci Modern"

```
┌─────────────────────────────────────────────────────────────────┐
│ ☰ Menu Bar (Native Mac)                                        │
├─────────────────────────────────────────────────────────────────┤
│ 🎬 🎞️ ✂️ 📝 🎵 🎨 ⚙️  [Search] [Undo] [Redo]  👤 Project Name │ ← Toolbar
├──────┬──────────────────────────────────────────┬───────────────┤
│      │                                          │               │
│ 📁   │          🎥 Preview                      │  ⚙️ Inspector │
│Media │          (16:9 ratio)                    │               │
│      │                                          │  ┌─────────┐  │
│ 📂   │   ◄◄ ◄ ▶ ►► [====■====] 🔊 1x          │  │Segment 1│  │
│Recent│                                          │  └─────────┘  │
│      │   00:01:23:15 / 00:05:45:00             │               │
│ 🔍   │                                          │  Name: _____  │
│Search│                                          │  Duration: __  │
│      │                                          │               │
│      │                                          │  🎨Transition │
│      │                                          │  📝 Text      │
│      │                                          │  🎵 Audio     │
│      │                                          │  🗑️ Delete    │
├──────┴──────────────────────────────────────────┴───────────────┤
│ 📊 Enhanced Multi-Track Timeline (50% height)                   │
│ ┌───────────────────────────────────────────────────────────┐  │
│ │ V1 🔇│▓▓▓▓▓▓▓▓▓▓▓▓│    │▓▓▓▓▓▓│                          │  │
│ │ A1 🔇│~~~~~~~~~~~~│    │~~~~~~│                          │  │← Waveform
│ │ T1 🔇│            │TEXT│      │                          │  │
│ └───────────────────────────────────────────────────────────┘  │
│ ├─IN─┼──────┼──────┼─OUT─┼──────┼──────┼──────┼──────┼────┤  │← Ruler
│ 00:00   00:15  00:30  00:45  01:00  01:15  01:30  01:45       │
└─────────────────────────────────────────────────────────────────┘
```

### Nouvelles Fonctionnalités UI

#### 1. Timeline Unifiée Multi-Track
- **Fusion** de `enhanced_timeline.py` + `multi_track_timeline.py`
- **Pistes**:
  - Video (V1, V2, V3...)
  - Audio (A1, A2, A3...)
  - Text Overlays (T1, T2...)
  - Effects (FX1, FX2...)
- **Contrôles par piste**:
  - Mute/Solo/Lock
  - Visibilité
  - Volume (audio)
- **Waveform** intégrée sur pistes audio
- **Miniatures** sur segments vidéo
- **Drag & Drop** entre pistes
- **Ripple/Roll/Slip/Slide** editing modes

#### 2. Preview Amélioré
- **Dual Preview** (Source/Program) en mode avancé
- **Overlay Guides**: Safe zones, grille, aspect ratios
- **Scopes**: Waveform, Vectorscope (optionnel)
- **Playback Controls** séparés et customisables
- **Frame Stepping** précis (±1, ±5, ±10 frames)
- **Markers** visuels sur la preview

#### 3. Inspector Panel Modernisé
✅ **Garder l'implémentation actuelle** (bien conçue)
- Ajouter onglets: Properties / Effects / Motion
- Keyframe editing pour animations
- Preset management intégré

#### 4. Media Browser Amélioré
- **Vues**: Grille/Liste/Timeline
- **Filtres**: Type, durée, résolution, date
- **Métadonnées**: Codec, bitrate, fps, dimensions
- **Import** par drag & drop
- **Bins** (dossiers de projet)

#### 5. Toolbar Contextuelle
- **Outils** visibles selon le mode:
  - Selection (V)
  - Trim (T)
  - Razor (C)
  - Slip (Y)
  - Slide (U)
  - Hand (H) - Pan timeline
- **Indicateurs** d'état: Snap, Ripple, Audio Scrub

#### 6. Effects Panel (Nouveau)
```
┌──────────────────┐
│ 🎨 Effects       │
├──────────────────┤
│ 🔍 Search...     │
├──────────────────┤
│ 📁 Video         │
│   └ Transitions  │
│   └ Color        │
│   └ Transform    │
│ 📁 Audio         │
│   └ Filters      │
│   └ EQ           │
│ 📁 Text          │
│   └ Templates    │
│   └ Animations   │
└──────────────────┘
```

#### 7. Keyboard Shortcuts Customization
- **Profiles**: Premiere Pro, Final Cut Pro, DaVinci
- **Visual Editor**: Clic sur action → Press key
- **Conflict Detection**: Alerte si conflit
- **Cheat Sheet**: Popup avec raccourcis actifs

### Design System

#### Couleurs (Light Theme - Default)
```css
Background Primary:   #FFFFFF
Background Secondary: #F5F5F5
Background Tertiary:  #EBEBEB

Text Primary:         #1A1A1A
Text Secondary:       #666666
Text Disabled:        #999999

Accent Primary:       #0066CC  /* Blue */
Accent Secondary:     #00AA66  /* Green */
Accent Tertiary:      #FF6B00  /* Orange */

Border:               #CCCCCC
Hover:                #E5E5E5
Selection:            #CCE8FF

Timeline BG:          #F8F8F8
Video Track:          #64B4FF
Audio Track:          #66CC99
Text Track:           #FFB366
```

#### Typography
```css
Font Family: -apple-system, "Segoe UI", "Roboto", sans-serif

Sizes:
  Title:     16pt Bold
  Subtitle:  14pt Semibold
  Body:      12pt Regular
  Caption:   11pt Regular
  Monospace: "SF Mono", "Consolas", monospace 11pt
```

#### Spacing
```
Base Unit: 4px

Padding:
  XS:  4px
  S:   8px
  M:   12px
  L:   16px
  XL:  24px

Border Radius:
  Small:  3px
  Medium: 5px
  Large:  8px
```

---

## ⚙️ Refonte Fonctionnalités

### Fonctionnalités à Conserver (✅)

#### Core Editing
- ✅ Multi-format support
- ✅ Frame-accurate editing
- ✅ Segment creation (IN/OUT)
- ✅ Timeline scrubbing
- ✅ Playback controls
- ✅ Variable speed

#### Advanced
- ✅ Undo/Redo (améliorer limite à 100)
- ✅ Copy/Paste segments
- ✅ Markers
- ✅ Segment naming

#### Effects
- ✅ Transitions (7 types)
- ✅ Text Overlays
- ✅ Audio mixing

#### Export
- ✅ Multi-format
- ✅ Quality presets
- ✅ Batch export

### Fonctionnalités à Améliorer (🔄)

#### 1. Multi-Track Timeline (PRIORITÉ HAUTE)
**Statut**: Implémenté mais non intégré
**Action**: Intégration complète dans l'UI

**Améliorations**:
- Mode Simple (single track - débutants)
- Mode Avancé (multi-track - professionnels)
- Drag & Drop entre pistes
- Piste Audio séparée de Vidéo
- Lock/Mute/Solo par piste

#### 2. Export Pipeline (PRIORITÉ HAUTE)
**Problèmes actuels**:
- UI freeze pendant export
- Pas de pause/resume
- Pas de queue

**Améliorations**:
- Export en background (worker thread)
- Queue d'export avec priorités
- Pause/Resume/Cancel
- Presets sauvegardables
- Export rapide (proxy) pour preview
- Notification à la fin

#### 3. Text Overlay System (PRIORITÉ MOYENNE)
**Problèmes actuels**:
- 754 lignes dans un seul dialog
- Pas d'organisation des templates

**Améliorations**:
- Refactor en composants séparés
- Template Browser avec catégories
- Import/Export de templates
- Animation timeline intégrée
- Keyframe editing
- Font management amélioré

#### 4. Transition System (PRIORITÉ MOYENNE)
**Problèmes actuels**:
- Preset management basique
- Pas de preview temps réel

**Améliorations**:
- Preview temps réel dans dialog
- Custom transitions (courbes Bezier)
- Transition templates
- Offset calculation auto-amélioré

#### 5. Audio System (PRIORITÉ MOYENNE)
**Améliorations**:
- Waveform sur timeline
- Audio ducking automatique
- Noise reduction
- Audio effects (EQ, compressor)
- Multi-track audio mixing visuel

#### 6. Project Management (PRIORITÉ HAUTE)
**Problèmes actuels**:
- Fichiers cachés dans `.videoflow/`
- Pas de format de projet portable

**Nouveau Format de Projet**:
```
my_project.veproj  (Format ZIP)
├── project.json           # Métadonnées projet
├── timeline.json          # État timeline
├── segments/              # Définitions segments
│   ├── segment_001.json
│   └── segment_002.json
├── cache/                 # Cache local (thumbnails, waveforms)
│   ├── thumbnails/
│   └── waveforms/
├── media/                 # Médias référencés (optionnel)
│   └── video_001.mp4
└── exports/               # Historique exports
    └── export_001_settings.json
```

**Features**:
- Auto-save toutes les 2 minutes
- Version history (10 dernières versions)
- Cloud sync (optionnel)
- Project packaging (inclure médias)
- Project templates

### Fonctionnalités Nouvelles (🆕)

#### 1. Ripple/Roll/Slip/Slide Editing (PRIORITÉ HAUTE)
Modes d'édition professionnels manquants:

**Ripple Edit**:
- Déplacer un point d'édition
- Décaler automatiquement le reste de la timeline

**Roll Edit**:
- Déplacer un point d'édition
- Ajuster les segments adjacents sans gap

**Slip Edit**:
- Changer le contenu d'un segment
- Sans changer sa position/durée

**Slide Edit**:
- Déplacer un segment
- Ajuster les segments adjacents

#### 2. Nested Sequences (PRIORITÉ MOYENNE)
- Créer une séquence dans une séquence
- Modifier la séquence imbriquée
- Changements se propagent

#### 3. Color Grading (PRIORITÉ BASSE)
- Basic color wheels (Lift/Gamma/Gain)
- Curves (RGB, Luma)
- HSL adjustments
- LUT support
- Scopes (Waveform, Vectorscope, Histogram)

#### 4. Keyframe Animation (PRIORITÉ MOYENNE)
- Animer: Position, Scale, Rotation, Opacity
- Courbes d'animation (Linear, Ease In/Out, Bezier)
- Keyframe timeline intégrée

#### 5. Proxy Workflow (PRIORITÉ BASSE)
- Générer proxies basse résolution
- Éditer avec proxies (performant)
- Export en pleine résolution

#### 6. Collaboration Features (PRIORITÉ BASSE)
- Comments/Notes sur timeline
- Export/Import EDL (Edit Decision List)
- Share project link (cloud)

### Fonctionnalités à Retirer/Déprécier (❌)

#### Auto-Transcription
**Raison**: 635 lignes pour une feature très spécialisée
**Action**: Extraire en plugin séparé optionnel
**Bénéfice**: Réduction complexité, dépendances (Whisper)

#### Classic Layout Mode
**Raison**: Code dupliqué, maintenance double
**Action**: Supprimer, garder uniquement DaVinci
**Bénéfice**: Simplification UI, code unique

#### Video Merger Dialog
**Raison**: Fonctionnalité couverte par timeline multi-segment
**Action**: Supprimer dialog, utiliser timeline normale
**Bénéfice**: Moins de code à maintenir

---

## 🚀 Performance & Optimisation

### Problèmes Identifiés

1. **UI Freeze** pendant opérations longues
2. **Memory Leaks** avec cv2.VideoCapture
3. **Thumbnails** générés de manière synchrone
4. **Export** bloque l'UI
5. **Scene Detection** freeze l'app

### Solutions

#### 1. Background Task Management
```python
# src/plugins/video_editor/services/task_service.py

class TaskService:
    """Gestionnaire centralisé de tâches asynchrones."""

    def __init__(self):
        self.task_queue = PriorityQueue()
        self.worker_pool = QThreadPool.globalInstance()
        self.active_tasks = {}

    def submit_task(self, task: Task, priority: Priority):
        """Soumet une tâche avec priorité."""

    def cancel_task(self, task_id: str):
        """Annule une tâche en cours."""

    def pause_task(self, task_id: str):
        """Met en pause une tâche."""
```

**Tâches à exécuter en background**:
- ✅ Export vidéo
- ✅ Scene detection
- ✅ Thumbnail generation
- ✅ Audio extraction
- ✅ Transcription
- ✅ Waveform generation

#### 2. Frame Cache (LRU)
```python
# src/plugins/video_editor/services/cache_service.py

class CacheService:
    """Cache LRU pour frames et thumbnails."""

    def __init__(self, max_size_mb: int = 500):
        self.frame_cache = LRUCache(max_size_mb)
        self.thumbnail_cache = LRUCache(max_size_mb // 2)
        self.waveform_cache = LRUCache(max_size_mb // 4)

    def get_frame(self, video_path: str, frame_number: int) -> np.ndarray:
        """Récupère un frame du cache ou le génère."""

    def invalidate(self, video_path: str):
        """Invalide le cache pour une vidéo."""
```

**Configuration**:
- Cache size: 500 MB par défaut (configurable)
- Eviction: LRU (Least Recently Used)
- Persistance: Cache sur disque pour waveforms

#### 3. VideoCapture Pooling
```python
# src/plugins/video_editor/services/video_service.py

class VideoService:
    """Service de gestion des VideoCapture avec pooling."""

    def __init__(self):
        self.capture_pool = {}  # path -> VideoCapture
        self.locks = {}         # path -> Lock

    def get_capture(self, video_path: str) -> cv2.VideoCapture:
        """Récupère un VideoCapture (réutilise si possible)."""

    def release_all(self):
        """Libère tous les VideoCapture."""
```

#### 4. Lazy Loading
- **Segments**: Charger seulement les segments visibles
- **Thumbnails**: Générer à la demande lors du scroll
- **Waveforms**: Générer en priorité pour segment actuel

#### 5. Profiling & Benchmarking
```python
# tests/benchmarks/
├── bench_export.py          # Benchmark pipeline export
├── bench_frame_extraction.py # Benchmark extraction frames
├── bench_scene_detection.py  # Benchmark détection scènes
└── bench_ui_responsiveness.py # Benchmark réactivité UI
```

**Cibles de Performance**:
- Ouverture vidéo 4K: < 1s
- Génération thumbnail: < 100ms
- Scroll timeline: 60 FPS
- Export 1080p: temps réel minimum (1h video = 1h export)

---

## 🧪 Tests & Qualité

### Stratégie de Tests

#### Tests Unitaires (Cible: 70% couverture)
```python
# tests/unit/

test_models/
├── test_project.py          # Modèle Project
├── test_segment.py          # Modèle Segment
├── test_track.py            # Modèle Track
└── test_timeline_state.py   # État timeline

test_controllers/
├── test_playback_controller.py
├── test_segment_controller.py
├── test_export_controller.py
└── test_edit_controller.py

test_services/
├── test_video_service.py
├── test_ffmpeg_service.py
├── test_thumbnail_service.py
├── test_cache_service.py
└── test_project_service.py

test_features/
├── test_transitions.py
├── test_text_engine.py
└── test_audio_mixer.py
```

#### Tests d'Intégration
```python
# tests/integration/

test_export_pipeline.py       # Pipeline complet d'export
test_project_io.py            # Save/Load projet
test_editing_workflow.py      # Workflow édition complet
test_undo_redo.py             # Undo/Redo sur opérations complexes
```

#### Tests E2E (End-to-End)
```python
# tests/e2e/

test_complete_edit.py         # Scénario complet:
                              # 1. Import vidéo
                              # 2. Créer segments
                              # 3. Ajouter transitions
                              # 4. Ajouter texte
                              # 5. Export
```

### Qualité du Code

#### Linting & Formatting
```bash
# .pre-commit-config.yaml

repos:
  - repo: https://github.com/psf/black
    hooks:
      - id: black
        args: [--line-length=100]

  - repo: https://github.com/pycqa/flake8
    hooks:
      - id: flake8
        args: [--max-line-length=100]

  - repo: https://github.com/pycqa/isort
    hooks:
      - id: isort
        args: [--profile=black]

  - repo: https://github.com/pre-commit/mirrors-mypy
    hooks:
      - id: mypy
        args: [--strict]
```

#### Documentation
```python
# Chaque module doit avoir:

"""Module docstring with architecture explanation.

This module handles [responsibility].

Architecture:
    - Class A: Does X
    - Class B: Does Y

Example:
    >>> controller = PlaybackController(...)
    >>> controller.play()
"""
```

#### Error Handling
```python
# src/plugins/video_editor/exceptions.py

class VideoEditorException(Exception):
    """Base exception for Video Editor."""
    pass

class VideoLoadError(VideoEditorException):
    """Error loading video file."""
    pass

class ExportError(VideoEditorException):
    """Error during export."""
    pass

class ProjectCorruptedError(VideoEditorException):
    """Project file is corrupted."""
    pass
```

---

## 📅 Roadmap d'Implémentation

### Phase 1: Foundation (4 semaines)

#### Semaine 1-2: Setup & Documentation
- [ ] Create new architecture folders
- [ ] Setup testing framework (pytest)
- [ ] Setup linting (black, flake8, mypy)
- [ ] Document current architecture
- [ ] Create migration plan
- [ ] Translate ALL code to English

#### Semaine 3-4: Core Models & Services
- [ ] Implement new models (Project, Segment, Track)
- [ ] Implement VideoService with pooling
- [ ] Implement CacheService with LRU
- [ ] Implement TaskService for async
- [ ] Implement FFmpegService refactored
- [ ] Write unit tests (models, services)

**Deliverable**: Core services testés et fonctionnels

---

### Phase 2: Timeline Consolidation (3 semaines)

#### Semaine 5-6: Unified Timeline
- [ ] Merge EnhancedTimeline + MultiTrackTimeline
- [ ] Implement track management
- [ ] Implement waveform display
- [ ] Implement drag & drop
- [ ] Delete old timeline implementations

#### Semaine 7: Timeline Controller
- [ ] Implement TimelineController
- [ ] Implement TimelineState management
- [ ] Connect timeline to new architecture
- [ ] Write integration tests

**Deliverable**: Timeline unique multi-track fonctionnelle

---

### Phase 3: Controllers (3 semaines)

#### Semaine 8: Playback & Segment Controllers
- [ ] Extract PlaybackController from window.py
- [ ] Extract SegmentController from window.py
- [ ] Extract EditController from window.py
- [ ] Write unit tests

#### Semaine 9-10: Export & Import Controllers
- [ ] Extract ExportController
- [ ] Implement async export with queue
- [ ] Extract ImportController
- [ ] Implement background import
- [ ] Write integration tests

**Deliverable**: Controllers découplés et testés

---

### Phase 4: UI Refactoring (4 semaines)

#### Semaine 11-12: Main Window Decomposition
- [ ] Create new MainWindow shell (< 200 lines)
- [ ] Migrate to DaVinci layout only
- [ ] Remove Classic layout
- [ ] Connect controllers to UI
- [ ] Update all panels

#### Semaine 13: Enhanced Panels
- [ ] Refactor Preview Panel
- [ ] Add waveform to Preview
- [ ] Enhance Inspector Panel (tabs)
- [ ] Create Effects Panel
- [ ] Update Media Browser

#### Semaine 14: Polish & Testing
- [ ] Add keyboard shortcut customization
- [ ] Add workspace management
- [ ] Polish animations and transitions
- [ ] E2E tests for UI flows

**Deliverable**: UI moderne et performante

---

### Phase 5: Advanced Features (3 semaines)

#### Semaine 15: Multi-Track Integration
- [ ] Full multi-track timeline integration
- [ ] Track management UI
- [ ] Track effects
- [ ] Multi-track export

#### Semaine 16: Editing Modes
- [ ] Implement Ripple edit
- [ ] Implement Roll edit
- [ ] Implement Slip edit
- [ ] Implement Slide edit

#### Semaine 17: Project Management
- [ ] New project format (.veproj)
- [ ] Auto-save system
- [ ] Version history
- [ ] Project templates

**Deliverable**: Features professionnelles complètes

---

### Phase 6: Performance & Polish (2 semaines)

#### Semaine 18: Optimizations
- [ ] Profile critical paths
- [ ] Optimize export pipeline
- [ ] Optimize frame extraction
- [ ] Optimize UI rendering
- [ ] Memory leak hunting

#### Semaine 19: Final Polish
- [ ] Fix all known bugs
- [ ] Complete documentation
- [ ] User manual
- [ ] Video tutorials
- [ ] Release preparation

**Deliverable**: Production-ready release

---

## 📈 Metrics de Succès

### Code Quality
- ✅ 0 fichiers > 500 lignes
- ✅ 70%+ test coverage
- ✅ 0 linting errors (flake8, mypy)
- ✅ 100% code in English
- ✅ All public APIs documented

### Performance
- ✅ Video 4K load < 1s
- ✅ Thumbnail gen < 100ms
- ✅ Timeline scroll 60 FPS
- ✅ Export ne freeze pas UI
- ✅ Memory usage < 2GB pour projet 1080p

### Features
- ✅ Multi-track timeline fully integrated
- ✅ Ripple/Roll/Slip/Slide editing
- ✅ Waveform on timeline
- ✅ Export queue with pause/resume
- ✅ Keyboard shortcuts customizable

### User Experience
- ✅ App launch < 2s
- ✅ Pas de freeze > 100ms
- ✅ Toutes les actions undo/redo-able
- ✅ Clear error messages
- ✅ Onboarding tutorial

---

## 🎓 Ressources & Références

### Documentation Technique
- **PyQt6**: https://www.riverbankcomputing.com/static/Docs/PyQt6/
- **FFmpeg**: https://ffmpeg.org/documentation.html
- **OpenCV**: https://docs.opencv.org/4.x/

### Architecture Patterns
- **MVC**: Model-View-Controller pattern
- **Observer**: For state management
- **Command**: For undo/redo
- **Factory**: For effect/transition creation

### Inspiration UI
- **DaVinci Resolve**: Timeline, color grading
- **Adobe Premiere Pro**: Effects panel, keyboard shortcuts
- **Final Cut Pro**: Magnetic timeline, metadata

### Testing
- **pytest**: https://docs.pytest.org/
- **pytest-qt**: https://pytest-qt.readthedocs.io/
- **pytest-cov**: Coverage reporting

---

## 🚦 Décisions Clés

### À Valider Avant de Commencer

1. **Approuver l'architecture MVC proposée**
   - Controllers / Models / Services / UI separation
   - Impact: Refactoring complet

2. **Supprimer Classic Layout**
   - Garder uniquement DaVinci Modern
   - Impact: Simplification UI

3. **Format de projet .veproj**
   - Nouveau format (pas compatible ancien)
   - Migration automatique à prévoir
   - Impact: Breaking change

4. **Extraire Auto-Transcription en plugin séparé**
   - Réduit complexité core
   - Impact: Feature optionnelle

5. **Timeline multi-track par défaut**
   - Mode simple vs avancé
   - Impact: Changement UX majeur

6. **Couverture de tests minimale 70%**
   - Temps de développement augmenté
   - Impact: Qualité long-terme

---

## 📝 Notes Finales

### Risques Identifiés

1. **Temps de développement**: 19 semaines estimées
2. **Breaking changes**: Ancien projets incompatibles
3. **Learning curve**: Nouvelle architecture pour contributeurs
4. **Régression**: Risque de casser features existantes

### Mitigation

1. **Phase de transition**: Garder old version en parallèle
2. **Migration tool**: Convertir anciens projets
3. **Documentation**: Architecture guide détaillé
4. **Tests**: Extensive testing avant chaque merge

### Livrables

- ✅ Code source refactoré
- ✅ Tests (unit + integration + E2E)
- ✅ Documentation technique
- ✅ User manual
- ✅ Video tutorials
- ✅ Migration guide

---

**Date de révision**: À réviser tous les mois
**Responsable**: À définir
**Budget temps**: 19 semaines (95 jours-personne)

