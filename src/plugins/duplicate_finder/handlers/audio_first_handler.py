"""
Audio-first analysis handler.

Implements the complete audio-first workflow:
1. Phase 1: Extract audio fingerprints (ALL videos)
2. Phase 2: LSH indexing + metadata filtering
3. Phase 3: Multi-resolution audio comparison
4. Phase 4: Selective video hashing (only candidates)
5. Phase 5: Video comparison with flip detection
"""
import os
import time
from typing import List, Optional, Dict, Any, Callable, Set, Tuple
from PyQt6.QtCore import QObject, pyqtSignal
import numpy as np

from ..audio_config import AudioFirstConfig
from ..audio_fingerprinting import AudioFingerprintDetector, PrecisionMode
from ..lsh_index import LSHIndex
from ..multi_resolution_comparator import MultiResolutionComparator
from ..metadata_filter import MetadataFilter
from ..workers.audio_worker import AudioExtractionWorker
from ..workers.audio_comparison_worker import AudioComparisonWorker
from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.AudioFirstHandler')


class AudioFirstHandler(QObject):
    """
    Handler for audio-first duplicate detection workflow.

    Orchestrates the complete pipeline from audio extraction to video comparison.

    Signals:
        audio_progress: (current, total, video_path) - Audio extraction progress
        audio_finished: () - Audio extraction complete
        audio_comparison_progress: (current, total) - Audio comparison progress
        audio_comparison_finished: (matches) - Audio comparison complete
        video_hash_progress: (current, total) - Video hashing progress
        video_hash_finished: () - Video hashing complete
        analysis_error: (error_msg) - Error occurred
        status_update: (status_msg) - Status message
    """

    # Signals for each phase
    audio_progress = pyqtSignal(int, int, str)  # current, total, video_path
    audio_finished = pyqtSignal()
    audio_comparison_progress = pyqtSignal(int, int)  # current, total
    audio_comparison_finished = pyqtSignal(list)  # [(video1, video2, similarity), ...]
    video_hash_progress = pyqtSignal(int, int)  # current, total
    video_hash_finished = pyqtSignal()
    analysis_error = pyqtSignal(str)
    status_update = pyqtSignal(str)

    def __init__(self, video_hasher, analysis_handler=None):
        """
        Initialize audio-first handler.

        Args:
            video_hasher: VideoHasher instance for selective video hashing
            analysis_handler: AnalysisHandler instance for hash/comparison operations
        """
        super().__init__()
        self.video_hasher = video_hasher
        self.analysis_handler = analysis_handler

        # Components (created when needed)
        self.audio_detector: Optional[AudioFingerprintDetector] = None
        self.lsh_index: Optional[LSHIndex] = None
        self.multi_res_comparator: Optional[MultiResolutionComparator] = None
        self.metadata_filter: Optional[MetadataFilter] = None

        # Workers
        self.audio_worker: Optional[AudioExtractionWorker] = None
        self.audio_comparison_worker: Optional[AudioComparisonWorker] = None

        # State
        self.config: Optional[AudioFirstConfig] = None
        self.fingerprints: Dict[str, np.ndarray] = {}
        self.audio_candidates: List[Tuple[str, str, float]] = []
        self.start_time: Optional[float] = None

        logger.info("Handler audio-first initialisé")

    def start_analysis(
        self,
        files: List[str],
        config: AudioFirstConfig,
        progress_callbacks: Optional[Dict[str, Callable]] = None
    ) -> None:
        """
        Start audio-first analysis.

        Args:
            files: List of video file paths
            config: AudioFirstConfig with all parameters
            progress_callbacks: Optional dict of callback functions
        """
        self.start_time = time.time()
        self.config = config
        self.fingerprints = {}
        self.audio_candidates = []

        logger.info(f"Démarrage de l'analyse audio-first sur {len(files)} fichiers")
        logger.info(f"Configuration: {config.to_dict()}")

        # Initialize components based on config
        self._initialize_components()

        # Start Phase 1: Audio extraction
        self._start_audio_extraction(files, progress_callbacks)

    def _initialize_components(self) -> None:
        """Initialize all analysis components based on configuration."""
        config = self.config

        # Audio detector
        precision_mode_map = {
            'fast': PrecisionMode.FAST,
            'balanced': PrecisionMode.BALANCED,
            'maximum': PrecisionMode.MAXIMUM
        }
        precision = precision_mode_map.get(config.audio.precision_mode, PrecisionMode.FAST)

        self.audio_detector = AudioFingerprintDetector(
            precision_mode=precision,
            max_cache_items=config.audio.cache_size
        )
        logger.info(f"Détecteur audio initialisé: précision={config.audio.precision_mode}")

        # LSH index
        if config.lsh.enabled:
            self.lsh_index = LSHIndex(
                bands=config.lsh.bands,
                rows_per_band=config.lsh.rows_per_band
            )
            logger.info(f"Index LSH initialisé: {config.lsh.bands} bandes")

        # Multi-resolution comparator
        if config.multi_resolution.enabled:
            self.multi_res_comparator = MultiResolutionComparator(
                coarse_duration=config.multi_resolution.coarse_duration,
                coarse_threshold=config.multi_resolution.coarse_threshold,
                medium_duration=config.multi_resolution.medium_duration,
                medium_threshold=config.multi_resolution.medium_threshold
            )
            logger.info("Comparateur multi-résolution initialisé")

        # Metadata filter
        if config.metadata.enabled:
            self.metadata_filter = MetadataFilter(
                duration_tolerance=config.metadata.duration_tolerance,
                min_size_ratio=config.metadata.min_size_ratio
            )
            logger.info("Filtre de métadonnées initialisé")

    def _start_audio_extraction(self, files: List[str], progress_callbacks: Optional[Dict] = None) -> None:
        """
        Start Phase 1: Audio fingerprint extraction.

        Args:
            files: List of video files
            progress_callbacks: Optional progress callbacks
        """
        self.status_update.emit("🎵 Phase 1: Extraction des empreintes audio...")
        logger.info(f"Phase 1: Extraction audio de {len(files)} vidéos")

        # Create audio extraction worker with database for caching
        self.audio_worker = AudioExtractionWorker(
            video_files=files,
            audio_detector=self.audio_detector,
            num_workers=self.config.audio.workers,
            precision_mode=self.config.audio.precision_mode,
            database=self.video_hasher.db  # Enable audio fingerprint caching
        )

        # Connect signals
        self.audio_worker.progress.connect(self._on_audio_progress)
        self.audio_worker.finished.connect(self._on_audio_finished)
        self.audio_worker.error.connect(self._on_error)

        # Forward to external callbacks
        if progress_callbacks and 'audio_progress' in progress_callbacks:
            self.audio_worker.progress.connect(progress_callbacks['audio_progress'])

        # Start worker
        self.audio_worker.start()

    def _on_audio_progress(self, current: int, total: int, video_path: str) -> None:
        """Handle audio extraction progress."""
        self.audio_progress.emit(current, total, video_path)
        if current % 10 == 0:  # Log every 10 files
            logger.info(f"Extraction audio: {current}/{total}")

    def _on_audio_finished(self, fingerprints: Dict[str, np.ndarray]) -> None:
        """
        Handle audio extraction completion.

        Start Phase 2: Audio comparison.
        """
        self.fingerprints = fingerprints
        logger.info(f"Phase 1 terminée: {len(fingerprints)} empreintes extraites")

        # Emit completion signal
        self.audio_finished.emit()

        # Build LSH index if enabled
        if self.config.lsh.enabled and self.lsh_index:
            self.status_update.emit("🔍 Construction de l'index LSH...")
            logger.info("Construction de l'index LSH...")
            for video_path, fingerprint in fingerprints.items():
                self.lsh_index.add(video_path, fingerprint)
            logger.info("Index LSH construit")

        # Start Phase 2: Audio comparison
        self._start_audio_comparison()

    def _start_audio_comparison(self) -> None:
        """Start Phase 2: Audio fingerprint comparison."""
        self.status_update.emit("🎵 Phase 2: Comparaison des empreintes audio...")
        logger.info(f"Phase 2: Comparaison des empreintes audio")

        # Create comparison worker
        self.audio_comparison_worker = AudioComparisonWorker(
            fingerprints=self.fingerprints,
            lsh_index=self.lsh_index,
            multi_res_comparator=self.multi_res_comparator,
            metadata_filter=self.metadata_filter,
            audio_threshold=self.config.audio.threshold,
            use_lsh=self.config.lsh.enabled,
            use_multi_res=self.config.multi_resolution.enabled,
            use_metadata=self.config.metadata.enabled
        )

        # Connect signals
        self.audio_comparison_worker.progress.connect(self._on_audio_comparison_progress)
        self.audio_comparison_worker.candidate_found.connect(self._on_audio_candidate_found)
        self.audio_comparison_worker.finished.connect(self._on_audio_comparison_finished)
        self.audio_comparison_worker.error.connect(self._on_error)

        # Start worker
        self.audio_comparison_worker.start()

    def _on_audio_comparison_progress(self, current: int, total: int) -> None:
        """Handle audio comparison progress."""
        self.audio_comparison_progress.emit(current, total)

    def _on_audio_candidate_found(self, video1: str, video2: str, similarity: float) -> None:
        """Handle audio candidate found."""
        logger.debug(f"Audio candidate: {video1} <-> {video2} ({similarity:.1f}%)")

    def _on_audio_comparison_finished(self, matches: List[Tuple[str, str, float]]) -> None:
        """
        Handle audio comparison completion.

        Start Phase 3: Selective video hashing.
        """
        self.audio_candidates = matches
        logger.info(f"Phase 2 terminée: {len(matches)} candidats audio trouvés")

        # Emit completion signal
        self.audio_comparison_finished.emit(matches)

        # Start Phase 3: Selective video hashing
        if len(matches) > 0:
            self._start_selective_video_hashing()
        else:
            logger.info("Aucun candidat audio, hash vidéo ignoré")
            self.video_hash_finished.emit()

    def _start_selective_video_hashing(self) -> None:
        """
        Start Phase 3: Selective video hashing.

        Only hash videos that appeared in audio candidates.
        """
        self.status_update.emit("📊 Phase 3: Hash des vidéos candidates...")

        # Get unique videos from audio candidates
        unique_videos = set()
        for video1, video2, _ in self.audio_candidates:
            unique_videos.add(video1)
            unique_videos.add(video2)

        videos_to_hash = [v for v in unique_videos if not self.video_hasher.has_hash(v)]

        logger.info(f"Phase 3: Hash sélectif de {len(videos_to_hash)}/{len(unique_videos)} vidéos")

        if len(videos_to_hash) == 0:
            logger.info("Toutes les vidéos candidates sont déjà hashées")
            self.video_hash_finished.emit()
            return

        # Hash videos synchronously (simple approach)
        # For a small number of candidates, synchronous hashing is acceptable
        total = len(videos_to_hash)
        for i, video_path in enumerate(videos_to_hash, 1):
            try:
                logger.info(f"Hash {i}/{total}: {video_path}")
                self.video_hash_progress.emit(i, total)

                # Compute hash if not cached
                video_hash, duration = self.video_hasher.compute_video_hash(video_path)
                if video_hash is not None:
                    logger.debug(f"Hash calculé pour {os.path.basename(video_path)}: {len(video_hash)} frames, {duration:.1f}s")
                else:
                    logger.warning(f"Échec du calcul du hash pour: {video_path}")
            except Exception as e:
                logger.error(f"Erreur hash {video_path}: {e}")

        logger.info(f"Phase 3 terminée: {total} vidéos hashées")
        self.video_hash_finished.emit()

    def _on_error(self, error_msg: str) -> None:
        """Handle error from any worker."""
        logger.error(f"Erreur d'analyse: {error_msg}")
        self.analysis_error.emit(error_msg)

    def stop_analysis(self) -> None:
        """Stop all running workers."""
        logger.info("Arrêt de l'analyse audio-first...")

        if self.audio_worker and self.audio_worker.isRunning():
            self.audio_worker.stop()
            self.audio_worker.wait()

        if self.audio_comparison_worker and self.audio_comparison_worker.isRunning():
            self.audio_comparison_worker.stop()
            self.audio_comparison_worker.wait()

        logger.info("Analyse audio-first arrêtée")

    def get_elapsed_time(self) -> float:
        """Get elapsed time since analysis start."""
        if self.start_time:
            return time.time() - self.start_time
        return 0.0

    def is_analyzing(self) -> bool:
        """Check if analysis is currently running."""
        return (
            (self.audio_worker and self.audio_worker.isRunning()) or
            (self.audio_comparison_worker and self.audio_comparison_worker.isRunning())
        )
