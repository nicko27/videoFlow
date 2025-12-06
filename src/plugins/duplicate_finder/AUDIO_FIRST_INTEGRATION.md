# Guide d'intégration Audio-First dans main_window.py

## Modifications nécessaires dans main_window.py

### 1. Imports à ajouter

```python
from .audio_config import AudioFirstConfig
from .handlers.audio_first_handler import AudioFirstHandler
```

### 2. Dans __init__()

Ajouter après la création de l'analysis_handler :

```python
# Initialize audio-first handler
self.audio_first_handler = AudioFirstHandler(self.video_hasher)
self._connect_audio_first_signals()
```

### 3. Nouvelle méthode : _connect_audio_first_signals()

```python
def _connect_audio_first_signals(self) -> None:
    """Connect audio-first handler signals to UI updates."""
    if self.audio_first_handler:
        # Phase 1: Audio extraction
        self.audio_first_handler.audio_progress.connect(self._on_audio_extraction_progress)
        self.audio_first_handler.audio_finished.connect(self._on_audio_extraction_finished)

        # Phase 2: Audio comparison
        self.audio_first_handler.audio_comparison_progress.connect(self._on_audio_comparison_progress)
        self.audio_first_handler.audio_comparison_finished.connect(self._on_audio_comparison_finished)

        # Phase 3: Video hashing
        self.audio_first_handler.video_hash_finished.connect(self._on_video_hash_finished)

        # Errors
        self.audio_first_handler.analysis_error.connect(self.handle_error)
        self.audio_first_handler.status_update.connect(self._on_status_update)
```

### 4. Nouvelles méthodes callback

```python
def _on_audio_extraction_progress(self, current: int, total: int, video_path: str) -> None:
    """Update audio extraction progress."""
    if self.audio_progress:
        self.audio_progress.update_progress(current, total, f"Extracting audio: {current}/{total}")
        short_name = os.path.basename(video_path)[:30]
        self.audio_progress.set_status(f"🎵 {short_name}", "#17A2B8")

def _on_audio_extraction_finished(self) -> None:
    """Handle audio extraction completion."""
    if self.audio_progress:
        self.audio_progress.set_status("Complete", "#28A745")
    logger.info("Audio extraction phase complete")

def _on_audio_comparison_progress(self, current: int, total: int) -> None:
    """Update audio comparison progress."""
    if self.duplicate_progress:
        self.duplicate_progress.update_progress(current, total, f"Comparing audio: {current}/{total}")

def _on_audio_comparison_finished(self, matches: list) -> None:
    """Handle audio comparison completion."""
    logger.info(f"Audio comparison complete: {len(matches)} candidates")
    # Continue to video hashing automatically
    # The audio_first_handler will handle this

def _on_video_hash_finished(self) -> None:
    """Handle selective video hashing completion."""
    logger.info("Selective video hashing complete")
    # Now do video comparison on the candidates
    self._start_video_comparison_on_candidates()

def _on_status_update(self, status: str) -> None:
    """Handle status updates from audio-first handler."""
    if self.status_indicator:
        self.status_indicator.update_status("🎵", status)

def _start_video_comparison_on_candidates(self) -> None:
    """Start video comparison on audio candidates."""
    # Get audio candidates from handler
    candidates = self.audio_first_handler.audio_candidates

    if not candidates:
        self._finish_analysis()
        return

    # Extract unique videos
    unique_videos = set()
    for v1, v2, _ in candidates:
        unique_videos.add(v1)
        unique_videos.add(v2)

    # Now compare these videos (use existing comparison logic)
    # TODO: Modify comparison to only compare candidate pairs with flip detection
    logger.info(f"Starting video comparison on {len(candidates)} candidate pairs")

    # Call existing comparison logic but with filtered pairs
    config = self.get_analysis_config()
    self.analysis_handler.start_comparison_analysis(
        list(unique_videos),
        config,
        duplicate_callback=self._on_duplicate_found,
        progress_callback=self.update_duplicate_progress,
        status_callback=self.update_comparison_status,
        total_comparisons_callback=self.set_comparison_total,
        comparison_details_callback=self.update_comparison_details
    )
```

### 5. Modifier start_analysis()

Remplacer l'appel à `analysis_handler.start_hash_analysis()` par :

```python
def start_analysis(self) -> None:
    """Start the duplicate detection analysis."""
    # ... validation code ...

    # Get configuration from UI
    params_tab = self._get_params_tab()
    audio_config = AudioFirstConfig.from_ui_widgets(params_tab)

    # Start audio-first analysis
    self.audio_first_handler.start_analysis(
        valid_files,
        audio_config,
        progress_callbacks={
            'audio_progress': self._on_audio_extraction_progress
        }
    )

    # Initialize progress displays
    self.audio_progress.update_progress(0, len(valid_files), "Starting audio extraction...")
    self.audio_progress.set_status("Starting", "#FFC107")
```

### 6. Méthode helper : _get_params_tab()

```python
def _get_params_tab(self):
    """Get parameters tab widget."""
    # Find the params tab from the config_tabs
    for child in self.findChildren(QWidget):
        if hasattr(child, 'audio_threshold_spin'):
            return child
    return None
```

### 7. Modifier stop_analysis()

Ajouter :

```python
# Stop audio-first handler
if self.audio_first_handler:
    self.audio_first_handler.stop_analysis()
```

### 8. Modifier cleanup_resources()

Ajouter :

```python
# Cleanup audio-first handler
if self.audio_first_handler:
    self.audio_first_handler.stop_analysis()
```

## Ordre d'exécution

1. User clicks START
2. `start_analysis()` → Creates `AudioFirstConfig` from UI
3. `audio_first_handler.start_analysis()` starts Phase 1 (audio extraction)
4. Phase 1 completes → automatically starts Phase 2 (audio comparison)
5. Phase 2 completes → automatically starts Phase 3 (selective video hashing)
6. Phase 3 completes → `_start_video_comparison_on_candidates()`
7. Video comparison completes → normal duplicate processing

## Points importants

- L'audio_progress sera maintenant utilisée pour afficher le progrès de l'extraction audio
- Le file_progress sera utilisé pour le hachage vidéo sélectif
- Le duplicate_progress sera utilisé pour la comparaison vidéo finale
- Tous les paramètres de l'UI sont lus via `AudioFirstConfig.from_ui_widgets()`
- Le workflow est automatique : chaque phase déclenche la suivante

## Test

Pour tester :
1. Sélectionner quelques vidéos
2. Configurer les paramètres dans l'onglet Settings
3. Cliquer START
4. Observer les 3 barres de progression :
   - 🎵 Audio fingerprinting
   - 📊 File hashing (sélectif)
   - 🔍 Duplicate detection (finale)
