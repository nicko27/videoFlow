"""
Benchmark Manager - Exécution et gestion des benchmarks
"""
import json
import os
import time
import threading
from typing import Dict, List, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED
from threading import Lock
from PyQt6.QtCore import pyqtSignal, QThread

from src.core.logger import Logger
from ..verification import VerificationPipeline
from ..analysis.phash_visual import PHashComparator
from ..utils.timeout import timeout, TimeoutError
from ..utils.worker_optimization import calculate_benchmark_workers

logger = Logger.get_logger('DuplicateFinder.BenchmarkManager')


def normalize_expected_label(expected: str) -> str:
    """
    Normalize expected labels to standard positive/negative/unknown format.

    CORRECTION BUG #5: Complete label normalization including French, numeric, and boolean values.

    Maps:
    - 'scene_found', 'duplicate', 'positive', 'yes', 'true', '1', 'positif', 'oui' → 'positive'
    - 'scene_not_found', 'not_duplicate', 'negative', 'no', 'false', '0', 'négatif', 'non' → 'negative'
    - 'unknown', 'inconnu' → 'unknown'
    - Already normalized labels pass through unchanged

    Args:
        expected: The expected label from test pair

    Returns:
        Normalized label ('positive', 'negative', or 'unknown')
    """
    # Normalize case and whitespace
    expected_lower = str(expected).strip().lower()

    label_map = {
        # English - positive
        'scene_found': 'positive',
        'duplicate': 'positive',
        'positive': 'positive',
        'yes': 'positive',
        'true': 'positive',
        '1': 'positive',

        # English - negative
        'scene_not_found': 'negative',
        'not_duplicate': 'negative',
        'negative': 'negative',
        'no': 'negative',
        'false': 'negative',
        '0': 'negative',

        # French - positive
        'positif': 'positive',
        'oui': 'positive',
        'vrai': 'positive',

        # French - negative
        'négatif': 'negative',
        'negatif': 'negative',  # Without accent
        'non': 'negative',
        'faux': 'negative',

        # Unknown
        'unknown': 'unknown',
        'inconnu': 'unknown'
    }

    normalized = label_map.get(expected_lower, 'unknown')
    if normalized != expected:
        logger.debug(f"Normalized label '{expected}' → '{normalized}'")
    return normalized


class BenchmarkRunner(QThread):
    """
    Worker thread pour exécuter un benchmark batch.

    CORRECTION BUG #33: Clarified signal semantics to avoid confusion.

    Signals:
        pipeline_progress: (current, total, pipeline_name)
            CUMULATIVE progress across ALL pairs in the current pipeline.
            - current: Number of pairs processed so far (monotonically increasing)
            - total: Total number of pairs to process in this pipeline
            - Emitted after each pair is processed (subject to throttling)
            - Example: (45, 100, "Fast Audio") means 45/100 pairs done

        pair_progress: (current_pair, total_pairs, video1, video2)
            BATCH progress within the current ThreadPoolExecutor batch.
            - NOT cumulative - resets for each batch
            - Used for detailed "current operation" display
            - Example: (3, 10, "vid1.mp4", "vid2.mp4") means 3rd pair in current batch of 10

        hashing_progress: (current, total, pipeline_name)
            Progress of hash precomputation phase (SHA-256, signatures, etc.)
            - Emitted during _precompute_hashes() before actual comparison
            - Separate from pipeline_progress (different phase)

        pipeline_metrics_updated: (pipeline_name, metrics_dict)
            Real-time metrics update (TP, FP, TN, FN, precision, recall, F1, speed, ETA)

        pipeline_completed: (pipeline_name, results_dict)
            Final results when pipeline finishes all pairs

        finished: (benchmark_run_id)
            All pipelines complete, benchmark_run_id saved to database

        error: (error_msg)
            Critical error occurred, benchmark should stop
    """

    pipeline_progress = pyqtSignal(int, int, str)  # current, total, name
    pair_progress = pyqtSignal(int, int, str, str)  # current, total, video1, video2
    hashing_progress = pyqtSignal(int, int, str)  # current, total, name
    pipeline_metrics_updated = pyqtSignal(str, dict)  # name, metrics (tp, fp, tn, fn, p, r, f1, speed, eta)
    pipeline_completed = pyqtSignal(str, dict)  # name, results
    finished = pyqtSignal(int)  # run_id
    error = pyqtSignal(str)

    def __init__(
        self,
        db_manager,
        test_pairs: List[Dict],
        pipeline_configs: List[Dict],
        run_label: str,
        max_pipeline_workers: Optional[int] = None,
        max_pair_workers: Optional[int] = None,
        auto_optimize_workers: bool = True
    ):
        """
        Args:
            db_manager: Instance DatabaseManager
            test_pairs: Liste de paires de test
            pipeline_configs: Liste de configs pipeline
            run_label: Label du run
            max_pipeline_workers: Nombre de pipelines en parallèle (None = auto)
            max_pair_workers: Nombre de paires en parallèle par pipeline (None = auto)
            auto_optimize_workers: Si True, calcule automatiquement les workers optimaux
        """
        super().__init__()
        self.db = db_manager
        self.test_pairs = test_pairs
        self.pipeline_configs = pipeline_configs
        self.run_label = run_label
        self._stop = False
        self._progress_lock = Lock()
        self._completed_pipelines = 0

        # Auto-optimisation des workers si activée
        if auto_optimize_workers and (max_pipeline_workers is None or max_pair_workers is None):
            workers_config = calculate_benchmark_workers(
                num_pipelines=len(pipeline_configs),
                total_pairs=len(test_pairs)
            )

            self.max_pipeline_workers = max_pipeline_workers or workers_config['pipeline_workers']
            self.max_pair_workers = max_pair_workers or workers_config['pair_workers']

            logger.info(
                f"🔧 Auto-optimisation: {self.max_pipeline_workers} pipelines × "
                f"{self.max_pair_workers} paires = {workers_config['total_workers']} workers\n"
                f"   {workers_config['explanation']}"
            )
        else:
            # Valeurs par défaut si pas d'auto-optimisation
            self.max_pipeline_workers = max_pipeline_workers or 2
            self.max_pair_workers = max_pair_workers or 4
            logger.info(
                f"Workers manuels: {self.max_pipeline_workers} pipelines × "
                f"{self.max_pair_workers} paires"
            )

    def stop(self):
        """Arrête le benchmark."""
        self._stop = True

    def run(self):
        """Exécute le benchmark batch avec parallélisation."""
        try:
            # Créer le run dans la DB
            run_id = self._create_benchmark_run()

            total_pipelines = len(self.pipeline_configs)
            logger.info(f"Starting parallel benchmark with {self.max_pipeline_workers} pipeline workers, "
                       f"{self.max_pair_workers} pair workers per pipeline")

            # Exécuter les pipelines en parallèle
            with ThreadPoolExecutor(max_workers=self.max_pipeline_workers) as executor:
                # Soumettre tous les pipelines
                future_to_pipeline = {
                    executor.submit(self._run_single_pipeline, run_id, pipeline_config, idx, total_pipelines):
                    pipeline_config
                    for idx, pipeline_config in enumerate(self.pipeline_configs, 1)
                }

                # Attendre la complétion
                for future in as_completed(future_to_pipeline):
                    if self._stop:
                        # Annuler les futures restants
                        for f in future_to_pipeline:
                            f.cancel()
                        break

                    pipeline_config = future_to_pipeline[future]
                    try:
                        future.result()  # Récupérer le résultat ou lever l'exception
                    except Exception as e:
                        logger.error(f"Pipeline {pipeline_config['name']} failed: {e}", exc_info=True)
                        # Continue avec les autres pipelines

            # Marquer run comme complété
            if not self._stop:
                self._complete_benchmark_run(run_id)
                self.finished.emit(run_id)
            else:
                logger.info("Benchmark stopped by user")

        except Exception as e:
            logger.error(f"Erreur benchmark: {e}", exc_info=True)
            self.error.emit(str(e))

    def _run_single_pipeline(self, run_id: int, pipeline_config: Dict, pipeline_idx: int, total_pipelines: int):
        """Exécute un seul pipeline (appelé dans un thread)."""
        if self._stop:
            return

        pipeline_name = pipeline_config['name']
        logger.info(f"📊 [PIPELINE START] {pipeline_idx}/{total_pipelines}: {pipeline_name}")

        try:
            # Émettre progression pipeline (thread-safe)
            self.pipeline_progress.emit(pipeline_idx, total_pipelines, pipeline_name)

            # Exécuter benchmark pour ce pipeline (avec nom pour métriques intermédiaires)
            results = self._run_pipeline_benchmark(pipeline_config, pipeline_name)

            # Stocker résultats
            logger.info(f"💾 [STORING RESULTS] {pipeline_name}")
            self._store_pipeline_results(run_id, pipeline_config, results)

            # Incrémenter compteur de pipelines complétés (thread-safe)
            with self._progress_lock:
                self._completed_pipelines += 1

            # Émettre complétion
            self.pipeline_completed.emit(pipeline_name, results)

            logger.info(f"✅ [PIPELINE COMPLETE] {pipeline_name} - F1: {results.get('f1_score', 0):.1f}%")

        except Exception as e:
            logger.error(f"❌ [PIPELINE FAILED] {pipeline_name}: {e}", exc_info=True)
            # Still increment counter to avoid blocking
            with self._progress_lock:
                self._completed_pipelines += 1
            # Re-raise to be caught in run()
            raise

    def _create_benchmark_run(self) -> int:
        """Crée l'entrée benchmark_run dans la DB."""
        # Déterminer le test set name (depuis la première paire)
        test_set_name = 'default'
        if self.test_pairs:
            # Chercher dans la DB le test_set_name de la première paire
            with self.db.pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT test_set_name FROM test_pairs
                    WHERE video1_path = ? AND video2_path = ?
                    LIMIT 1
                """, (self.test_pairs[0]['video1_path'], self.test_pairs[0]['video2_path']))
                row = cursor.fetchone()
                if row:
                    test_set_name = row[0]

        with self.db.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO benchmark_runs
                (run_label, test_set_name, total_pairs, pipelines_count, status)
                VALUES (?, ?, ?, ?, 'running')
            """, (self.run_label, test_set_name, len(self.test_pairs), len(self.pipeline_configs)))
            conn.commit()
            return cursor.lastrowid

    def _complete_benchmark_run(self, run_id: int):
        """Marque le run comme complété."""
        with self.db.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE benchmark_runs
                SET status = 'completed', completed_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), run_id))
            conn.commit()

    def _precompute_hashes(self, pipeline_name: str, total_pairs: int, pipeline_config: Dict):
        """
        Passe de pré-calcul pour alimenter la barre de progression "hash".
        - SHA-256 de base pour toutes les vidéos concernées
        - Pré-calcul optionnel des signatures légères (frame_hash, DCT) selon le pipeline

        VERSION PARALLÉLISÉE - Utilise plusieurs workers pour accélérer le pré-calcul (3-5× plus rapide)
        """
        video_paths = set()
        for pair in self.test_pairs:
            if pair.get('video1_path'):
                video_paths.add(pair['video1_path'])
            if pair.get('video2_path'):
                video_paths.add(pair['video2_path'])

        methods = pipeline_config.get('methods', [])
        wants_frame_hash = any(m.get('name') == 'frame_hash' and m.get('enabled', True) for m in methods)
        wants_dct = any(m.get('name') == 'dct_coefficients' and m.get('enabled', True) for m in methods)
        wants_ssim = any(m.get('name') == 'ssim' and m.get('enabled', True) for m in methods)
        wants_optflow = any(m.get('name') == 'optical_flow' and m.get('enabled', True) for m in methods)
        wants_motion = any(m.get('name') == 'motion_analysis' and m.get('enabled', True) for m in methods)
        wants_feature = any(m.get('name') == 'feature_matching' and m.get('enabled', True) for m in methods)
        wants_color = any(m.get('name') == 'color_histogram' and m.get('enabled', True) for m in methods)
        wants_edge = any(m.get('name') == 'edge_pattern' and m.get('enabled', True) for m in methods)
        # Ajouter un bonus pour pré-hasher quelques fenêtres du long si certaines méthodes sont actives
        windows_per_video = 4 if (wants_feature or wants_motion or wants_ssim or wants_optflow or wants_color or wants_edge) else 0
        extra_work = len(video_paths) * (wants_frame_hash + wants_dct + wants_ssim + wants_optflow + wants_motion + wants_feature + wants_color + wants_edge + windows_per_video)

        total = max(1, total_pairs * 2 + extra_work)  # deux vidéos par paire + signatures
        current = 0
        progress_lock = threading.Lock()
        self.hashing_progress.emit(current, total, pipeline_name)

        def update_progress():
            """Thread-safe progress update."""
            nonlocal current
            with progress_lock:
                current += 1
                self.hashing_progress.emit(current, total, pipeline_name)

        def compute_sha256_for_video(path: str):
            """Compute SHA-256 for a single video (thread-safe)."""
            if self._stop or not path:
                return
            try:
                with self.db.pool.get_connection() as conn:
                    cursor = conn.cursor()
                    vid = self.db._get_or_create_video_id(path, cursor)
                    cursor.execute("SELECT file_sha256, file_size, modification_time FROM video_files WHERE id = ?", (vid,))
                    row = cursor.fetchone()
                    needs_sha = (not row) or (row[0] is None)
                    if needs_sha and os.path.exists(path):
                        sha_val = self.db._compute_file_sha256(path)
                        stat = os.stat(path)
                        cursor.execute(
                            "UPDATE video_files SET file_sha256 = ?, file_size = ?, modification_time = ? WHERE id = ?",
                            (sha_val, stat.st_size, stat.st_mtime, vid)
                        )
                        conn.commit()
            except Exception:
                # Best effort: on ignore mais on continue la progression
                pass
            finally:
                update_progress()

        try:
            # Étape 1 : SHA-256 + entrée video_files (PARALLÉLISÉ)
            # Collecter tous les chemins de vidéos uniques
            all_video_paths = []
            for pair in self.test_pairs:
                for path in (pair.get('video1_path'), pair.get('video2_path')):
                    if path:
                        all_video_paths.append(path)

            # Traiter en parallèle avec ThreadPoolExecutor
            hash_workers = min(self.max_pair_workers, len(all_video_paths))
            executor = ThreadPoolExecutor(max_workers=hash_workers)
            try:
                futures = {executor.submit(compute_sha256_for_video, path) for path in all_video_paths}

                # Attendre toutes les tâches avec vérification du stop
                while futures and not self._stop:
                    done, futures = wait(futures, timeout=2, return_when=FIRST_COMPLETED)
                    # Les résultats sont ignorés car update_progress() est appelé dans chaque worker

                if self._stop:
                    logger.info("🛑 Arrêt du pré-calcul SHA-256 demandé")
            finally:
                executor.shutdown(wait=False)

            # Étape 2 : signatures légères selon le pipeline (frame_hash, DCT, SSIM, optflow, motion, features, color, edge)
            if (wants_frame_hash or wants_dct or wants_ssim or wants_optflow or wants_motion or wants_feature or wants_color or wants_edge) and not self._stop:
                # Configurer un VideoAnalysisMethods minimal pour réutiliser les caches
                vam_kwargs = {}
                feature_params = {}
                motion_params = {}
                for m in methods:
                    params = m.get('parameters', {}) or {}
                    if m.get('name') == 'frame_hash':
                        vam_kwargs.update({
                            'framehash_size': params.get('hash_size', 16),
                            'framehash_threshold': params.get('threshold', 75.0),
                            'framehash_sample_rate': params.get('sample_rate', 5),
                            'framehash_max_windows': params.get('max_windows', 200),
                            'framehash_search_step': params.get('search_step', 3.0),
                        })
                        if 'max_samples' in params:
                            vam_kwargs['framehash_max_samples'] = params.get('max_samples', 300)
                    if m.get('name') == 'dct_coefficients':
                        vam_kwargs.update({
                            'dct_num_coeffs': params.get('num_coeffs', 15),
                            'dct_threshold': params.get('threshold', 75.0),
                            'dct_sample_interval': params.get('sample_interval', 5.0),
                            'dct_num_samples': params.get('num_samples', 5),
                            'dct_search_step': params.get('search_step', 3.0),
                            'dct_max_windows': params.get('max_windows', 200),
                        })
                    if m.get('name') == 'ssim':
                        vam_kwargs.update({
                            'ssim_threshold': params.get('threshold', 0.85),
                            'ssim_sample_interval': params.get('sample_interval', 5.0),
                            'ssim_num_samples': params.get('num_samples', 5),
                            'ssim_search_step': params.get('search_step', 3.0),
                            'ssim_max_windows': params.get('max_windows', 200),
                        })
                    if m.get('name') == 'optical_flow':
                        vam_kwargs.update({
                            'optflow_threshold': params.get('threshold', 70.0),
                            'optflow_max_frames': params.get('max_frames', 30),
                            'optflow_frame_step': params.get('frame_step', 3),
                            'optflow_min_variance': params.get('min_variance', 0.0),
                            'optflow_search_step': params.get('search_step', 3.0),
                            'optflow_max_windows': params.get('max_windows', 200),
                        })
                    if m.get('name') == 'motion_analysis':
                        motion_params = params
                        vam_kwargs.update({
                            'motion_sample_interval': params.get('sample_interval', 3),
                            'motion_min_variance': params.get('min_variance', 0.0),
                            'motion_search_step': params.get('search_step', 3.0),
                            'motion_max_windows': params.get('max_windows', 200),
                        })
                    if m.get('name') == 'feature_matching':
                        feature_params = params
                        vam_kwargs.update({
                            'feature_detector': params.get('detector', 'ORB'),
                            'feature_max_features': params.get('max_features', 500),
                            'feature_match_threshold': params.get('threshold', 70.0),
                            'feature_min_matches': params.get('min_matches', 10),
                            'feature_ratio_test': params.get('ratio_test', 0.75),
                            'feature_search_step': params.get('search_step', 3.0),
                            'feature_max_windows': params.get('max_windows', 100),
                        })
                    if m.get('name') == 'color_histogram':
                        vam_kwargs.update({
                            'color_hist_threshold': params.get('threshold', 85.0),
                            'color_search_step': params.get('search_step', 3.0),
                            'color_max_windows': params.get('max_windows', 200),
                        })
                    if m.get('name') == 'edge_pattern':
                        vam_kwargs.update({
                            'edge_threshold': params.get('threshold', 80.0),
                            'edge_search_step': params.get('search_step', 3.0),
                            'edge_max_windows': params.get('max_windows', 200),
                            'edge_canny_low': params.get('canny_low', 50),
                            'edge_canny_high': params.get('canny_high', 150),
                        })

                # Créer un VAM par worker pour thread-safety
                def process_video_signatures(path: str):
                    """Compute all signatures for a single video (thread-safe)."""
                    if self._stop:
                        return

                    # Chaque worker a son propre VAM (thread-safe)
                    vam_worker = VideoAnalysisMethods(db_manager=self.db, **vam_kwargs)

                    try:
                        if wants_frame_hash:
                            sample_rate = vam_worker.framehash_sample_rate
                            max_samples = getattr(vam_worker, 'framehash_max_samples', 300)
                            vam_worker._get_frame_hash_signature(path, sample_rate, max_samples)
                            update_progress()

                        if wants_dct:
                            duration = vam_worker._get_duration(path)
                            if duration:
                                vam_worker._get_dct_signature(
                                    path,
                                    duration,
                                    getattr(vam_worker, 'dct_sample_interval', 5.0),
                                    getattr(vam_worker, 'dct_num_samples', None)
                                )
                            update_progress()

                        if wants_ssim:
                            duration = vam_worker._get_duration(path)
                            if duration:
                                vam_worker._get_ssim_reference(
                                    path,
                                    getattr(vam_worker, 'ssim_sample_interval', 5.0),
                                    getattr(vam_worker, 'ssim_num_samples', None)
                                )
                            update_progress()

                        if wants_optflow:
                            vam_worker._get_optflow_signature(path)
                            update_progress()

                        if wants_motion:
                            vam_worker._get_motion_signature(path, sample_interval=motion_params.get('sample_interval', getattr(vam_worker, 'motion_sample_interval', 3)))
                            update_progress()

                        if wants_feature:
                            # Pré-calcul des descripteurs du short; pour les longs on utilisera frame-by-frame
                            vam_worker._get_feature_descriptors(
                                path,
                                num_samples=feature_params.get('num_samples', 5) if isinstance(feature_params, dict) else 5,
                                detector_name=vam_worker.feature_detector,
                                size=(640, 360)
                            )
                            update_progress()

                        if wants_color:
                            duration = vam_worker._get_duration(path)
                            if duration:
                                vam_worker._get_color_signatures(path, duration, max(3, int(duration / 5)))
                            update_progress()

                        if wants_edge:
                            duration = vam_worker._get_duration(path)
                            if duration:
                                vam_worker._get_edge_signatures(path, duration, max(3, int(duration / 5)))
                            update_progress()

                        # Pré-calcul léger sur quelques fenêtres du long (pour SSIM/feature/motion/optflow/color/edge)
                        if windows_per_video > 0 and not self._stop:
                            dur = vam_worker._get_duration(path) or 0
                            if dur > 0:
                                win_count = windows_per_video
                                step = max(1.0, dur / (win_count + 1))
                                starts = [i * step for i in range(win_count)]
                                for start in starts:
                                    if self._stop:
                                        break
                                    if wants_ssim:
                                        vam_worker._get_ssim_reference(
                                            path,
                                            getattr(vam_worker, 'ssim_sample_interval', 5.0),
                                            getattr(vam_worker, 'ssim_num_samples', None)
                                        )
                                    if wants_feature:
                                        vam_worker._get_feature_descriptors(
                                            path,
                                            num_samples=feature_params.get('num_samples', 5) if isinstance(feature_params, dict) else 5,
                                            detector_name=vam_worker.feature_detector,
                                            size=(640, 360)
                                        )
                                    if wants_motion:
                                        # Motion sur fenêtre ciblée (fallback vers compute_motion_pattern)
                                        vam_worker.compute_motion_pattern(path, start, min(30.0, dur))
                                    if wants_optflow:
                                        vam_worker._compute_flow_magnitude(path, duration=min(30.0, dur), start_time=start)
                                    if wants_color:
                                        vam_worker._get_color_signatures(path, min(30.0, dur), max(3, int(min(30.0, dur) / 5)))
                                    if wants_edge:
                                        vam_worker._get_edge_signatures(path, min(30.0, dur), max(3, int(min(30.0, dur) / 5)))
                                    update_progress()
                    except Exception:
                        # Best effort - on continue même en cas d'erreur
                        pass

                # Traiter en parallèle avec ThreadPoolExecutor (PARALLÉLISÉ)
                sig_workers = min(self.max_pair_workers, len(video_paths))
                executor_sig = ThreadPoolExecutor(max_workers=sig_workers)
                try:
                    futures_sig = {executor_sig.submit(process_video_signatures, path) for path in video_paths}

                    # Attendre toutes les tâches avec vérification du stop
                    while futures_sig and not self._stop:
                        done, futures_sig = wait(futures_sig, timeout=2, return_when=FIRST_COMPLETED)

                    if self._stop:
                        logger.info("🛑 Arrêt du pré-calcul des signatures demandé")
                finally:
                    executor_sig.shutdown(wait=False)
        except Exception as e:
            # CORRECTION BUG #10: Log error and emit accurate progress instead of falsely showing 100%
            logger.error(f"[{pipeline_name}] Precompute hashes failed: {e}", exc_info=True)
            # Emit actual progress (current state), not 100% which would be misleading
            with progress_lock:
                actual_current = current
            self.hashing_progress.emit(actual_current, total, pipeline_name)
            # Note: Don't re-raise - precompute failure shouldn't stop benchmark
            # The comparison will just be slower without cached hashes

    def _run_pipeline_benchmark(self, pipeline_config: Dict, pipeline_name: str = None) -> Dict:
        """
        Exécute un benchmark pour un pipeline avec traitement parallèle des paires.

        Args:
            pipeline_config: Configuration du pipeline
            pipeline_name: Nom du pipeline (pour émission de métriques)

        Returns:
            Dict avec {tp, fp, tn, fn, precision, recall, f1, total_time, per_pair_results}
        """
        # Créer le pipeline
        pipeline = self._create_pipeline(pipeline_config)

        # Métriques (thread-safe)
        metrics_lock = Lock()
        metrics = {
            'tp': 0, 'fp': 0, 'tn': 0, 'fn': 0,
            'accepted': 0, 'rejected': 0,  # Raw counts for unlabeled sets
            'labeled_count': 0, 'unlabeled_count': 0
        }
        per_pair_results = []
        pairs_processed = [0]  # Liste pour mutabilité dans la closure
        pipeline_start_time = time.time()
        confirmation_cfg = pipeline_config.get('confirmation') or {}
        confirmation_enabled = confirmation_cfg.get('enabled', False)
        phash_params = confirmation_cfg.get('parameters', {})
        phash_comparator = None
        if confirmation_enabled:
            phash_comparator = PHashComparator(
                phash_threshold=int(phash_params.get('phash_threshold', 10)),
                frame_rate_threshold=float(phash_params.get('frame_rate_threshold', 0.8)),
                n_frames=int(phash_params.get('n_frames', 10)),
                step_seconds=float(phash_params.get('step_seconds', 1.0)),
                max_offsets=30
            )

        total_pairs = len(self.test_pairs)

        # Pour le nom du pipeline
        if pipeline_name is None:
            pipeline_name = pipeline_config.get('name', 'Unknown')

        # Initialiser la barre de progression à 0
        self.pipeline_progress.emit(0, total_pairs, pipeline_name)
        # Pré-calcul / hash des fichiers pour afficher une vraie progression dédiée
        self._precompute_hashes(pipeline_name, total_pairs, pipeline_config)

        # CORRECTION BUG #35: Throttle emissions to reduce overhead
        # Instead of emitting after every pair (1000x for 1000 pairs), emit every 0.5s or every 10 pairs
        last_emit_time = [0.0]  # List for mutability in closure
        last_emit_pairs = [0]   # Track last emission pair count
        EMIT_INTERVAL_SECONDS = 0.5  # Minimum time between emissions
        EMIT_INTERVAL_PAIRS = 10     # Minimum pairs between emissions for small benchmarks

        def emit_intermediate_metrics(force=False):
            """
            Émet les métriques intermédiaires (appelé après chaque paire) - THREAD-SAFE.

            CORRECTION BUG #35: Throttled to emit max every 0.5s or every 10 pairs (whichever comes first),
            reducing signal overhead from 100-200ms on large benchmarks.

            Args:
                force: If True, emit regardless of throttling (used for final emission)
            """
            elapsed = time.time() - pipeline_start_time

            # CORRECTION BUG #31: Protéger la lecture avec le lock
            with metrics_lock:
                processed = pairs_processed[0]

            if processed == 0:
                return

            # CORRECTION BUG #35: Throttle emissions (skip if too soon)
            current_time = time.time()
            pairs_since_last_emit = processed - last_emit_pairs[0]

            if not force:
                # Skip if both conditions are true:
                # 1. Less than EMIT_INTERVAL_SECONDS has passed
                # 2. Less than EMIT_INTERVAL_PAIRS have been processed
                time_too_soon = (current_time - last_emit_time[0]) < EMIT_INTERVAL_SECONDS
                pairs_too_few = pairs_since_last_emit < EMIT_INTERVAL_PAIRS

                if time_too_soon and pairs_too_few:
                    return  # Skip this emission

            # Update throttle tracking
            last_emit_time[0] = current_time
            last_emit_pairs[0] = processed

            # Calculer métriques actuelles (avec la copie locale thread-safe)
            tp, fp, tn, fn = metrics['tp'], metrics['fp'], metrics['tn'], metrics['fn']
            precision = (tp / (tp + fp)) * 100 if (tp + fp) > 0 else 0.0
            recall = (tp / (tp + fn)) * 100 if (tp + fn) > 0 else 0.0
            f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

            # Calculer vitesse et ETA
            speed = elapsed / processed  # secondes par paire
            remaining = total_pairs - processed
            eta = speed * remaining  # secondes restantes

            # Émettre signal de progression pour la timeline globale
            self.pipeline_progress.emit(processed, total_pairs, pipeline_name)

            # Émettre signal de métriques pour les détails
            metrics_data = {
                'tp': tp,
                'fp': fp,
                'tn': tn,
                'fn': fn,
                'precision': precision,
                'recall': recall,
                'f1': f1,
                'speed': speed,
                'eta': eta,
                'processed': processed,
                'total': total_pairs
            }
            self.pipeline_metrics_updated.emit(pipeline_name, metrics_data)

        def process_pair(pair_data):
            """Traite une paire de vidéos (appelé dans un thread)."""
            pair, pair_idx = pair_data

            if self._stop:
                return None

            video1 = pair['video1_path']
            video2 = pair['video2_path']
            expected = pair['expected']

            logger.info(f"🎬 [{pipeline_name}] PAIR {pair_idx}/{total_pairs} STARTED: {video1} vs {video2}")

            # Émettre progression (thread-safe)
            self.pair_progress.emit(pair_idx, total_pairs, video1, video2)

            # Vérifier avec le pipeline
            pair_start = time.time()
            try:
                # Handle None values from database for start_time and duration
                # Note: Test pairs should have valid durations set during creation,
                # but we default to 0.0 if missing to avoid errors
                start_time = pair.get('start_time') if pair.get('start_time') is not None else 0.0
                duration = pair.get('duration') if pair.get('duration') is not None else 0.0
                sequence_score = pair.get('sequence_score') if pair.get('sequence_score') is not None else 100.0

                logger.debug(f"  [{pipeline_name}] Calling pipeline.verify() for pair {pair_idx}...")

                # NOTE: Timeout individuel désactivé car signal.SIGALRM ne fonctionne pas dans les threads workers
                # Le timeout global de 180s (no_progress_timeout) gère les blocages
                try:
                    result = pipeline.verify(
                        short_video=video1,
                        long_video=video2,
                        start_time=start_time,
                        duration=duration,
                        sequence_score=sequence_score
                    )
                except Exception as e:
                    pair_time = time.time() - pair_start
                    logger.error(f"❌ [{pipeline_name}] PAIR {pair_idx}/{total_pairs} ERROR after {pair_time:.1f}s: {e}")
                    # Retourner résultat d'erreur
                    return {
                        'video1': video1,
                        'video2': video2,
                        'expected': expected,
                        'accepted': False,
                        'is_match': False,
                        'error': str(e),
                        'total_time': pair_time
                    }

                logger.debug(f"  [{pipeline_name}] pipeline.verify() returned for pair {pair_idx}")

                pair_time = time.time() - pair_start
                accepted = result['accepted']

                # Confirmation visuelle optionnelle (pHash) sur les paires acceptées
                confirmation_info = None
                if accepted and confirmation_enabled and phash_comparator:
                    try:
                        confirm_res = phash_comparator.verify_visual_similarity(
                            short_video_path=video1,
                            long_video_path=video2,
                            start_time=start_time,
                            duration=duration,
                            search_window=phash_params.get('search_window', True)
                        )
                        confirmation_info = {
                            'phash_distance': confirm_res.get('avg_distance'),
                            'phash_similarity_rate': confirm_res.get('similarity_rate'),
                            'phash_frames_similar': confirm_res.get('frames_similar'),
                            'phash_frames_compared': confirm_res.get('frames_compared'),
                            'phash_confirmed': confirm_res.get('is_duplicate', False),
                            'phash_best_offset': confirm_res.get('best_offset')
                        }
                        # Si la confirmation infirme, marquer rejet
                        if not confirm_res.get('is_duplicate', False):
                            accepted = False
                    except Exception as e:
                        logger.error(f"PHash confirmation failed for {video1} vs {video2}: {e}", exc_info=True)

                logger.info(f"✅ [{pipeline_name}] PAIR {pair_idx}/{total_pairs} COMPLETED in {pair_time:.2f}s → {('ACCEPTED' if accepted else 'REJECTED')} (expected: {expected})")

                # Normalize expected label for metrics calculation
                normalized_expected = normalize_expected_label(expected)

                # Calculer métrique (thread-safe)
                with metrics_lock:
                    # Track raw results (for all pairs)
                    if accepted:
                        metrics['accepted'] += 1
                    else:
                        metrics['rejected'] += 1

                    # Track labeled vs unlabeled
                    if normalized_expected in ['positive', 'negative']:
                        metrics['labeled_count'] += 1
                        # Standard metrics (TP/FP/TN/FN)
                        if normalized_expected == 'positive':
                            if accepted:
                                metrics['tp'] += 1
                            else:
                                metrics['fn'] += 1
                        else:  # negative
                            if accepted:
                                metrics['fp'] += 1
                            else:
                                metrics['tn'] += 1
                    else:
                        # 'unknown' pairs
                        metrics['unlabeled_count'] += 1

                # Retourner résultat détaillé
                # Note: cached results use 'execution_time', fresh results use 'total_time'
                total_time = result.get('total_time', result.get('execution_time', 0.0))

                return {
                    'video1': video1,
                    'video2': video2,
                    'expected': expected,
                    'accepted': accepted,
                    'is_match': accepted,  # alias for downstream tools expecting is_match
                    'rejection_method': result.get('rejection_method'),
                    'pipeline_results': result.get('pipeline_results'),
                    'mode': result.get('mode'),
                    'weighted_score': result.get('weighted_score'),
                    'total_time': total_time,
                    'from_cache': result.get('from_cache', False),
                    'start_time': start_time,
                    'duration': duration,
                    'confirmation': confirmation_info
                }

            except Exception as e:
                pair_time = time.time() - pair_start
                logger.error(f"❌ [{pipeline_name}] PAIR {pair_idx}/{total_pairs} FAILED after {pair_time:.2f}s: {e}", exc_info=True)
                logger.error(f"   Failed videos: {video1} vs {video2}")

                return {
                    'video1': video1,
                    'video2': video2,
                    'expected': expected,
                    'accepted': False,
                    'is_match': False,
                    'error': str(e)
                }

            finally:
                # Toujours incrémenter le compteur et émettre les métriques
                # (exactement UNE fois par paire, succès ou échec)
                with metrics_lock:
                    pairs_processed[0] += 1
                emit_intermediate_metrics()

        # Traiter les paires en parallèle avec BATCH PROCESSING INTELLIGENT
        pairs_with_idx = [(pair, idx) for idx, pair in enumerate(self.test_pairs, 1)]

        # BATCH PROCESSING: Calculer taille de batch optimale
        # - Si peu de paires (<50): tout en une fois
        # - Si beaucoup de paires: batches de 50 pour réduire overhead mémoire
        batch_size = min(50, max(10, total_pairs // 4)) if total_pairs > 50 else total_pairs
        num_batches = (total_pairs + batch_size - 1) // batch_size

        logger.info(f"🚀 [{pipeline_name}] Starting parallel processing of {total_pairs} pairs with {self.max_pair_workers} workers")
        logger.info(f"📦 [{pipeline_name}] Using BATCH PROCESSING: {num_batches} batches of ~{batch_size} pairs")

        # NE PAS UTILISER 'with' - permet shutdown non-bloquant
        executor = ThreadPoolExecutor(max_workers=self.max_pair_workers)

        try:
            # BATCH PROCESSING: Soumettre les paires par batches
            all_futures = set()
            batch_num = 0

            for batch_start in range(0, total_pairs, batch_size):
                if self._stop:
                    logger.info(f"🛑 [{pipeline_name}] Stopped before batch {batch_num + 1}/{num_batches}")
                    break

                batch_end = min(batch_start + batch_size, total_pairs)
                batch_pairs = pairs_with_idx[batch_start:batch_end]
                batch_num += 1

                logger.info(f"📤 [{pipeline_name}] Submitting batch {batch_num}/{num_batches} ({len(batch_pairs)} pairs)...")

                # Soumettre ce batch
                batch_futures = {executor.submit(process_pair, pair_data) for pair_data in batch_pairs}
                all_futures.update(batch_futures)

                logger.debug(f"✅ [{pipeline_name}] Batch {batch_num}/{num_batches} submitted ({len(batch_futures)} futures)")

            futures = all_futures
            logger.info(f"✅ [{pipeline_name}] All {len(futures)} futures submitted in {num_batches} batches, waiting for completion...")

            # Collecter les résultats au fur et à mesure avec timeout robuste
            completed_count = 0
            # OPTIMISÉ: Timeout réduit à 2s pour réactivité maximale au stop
            timeout_per_wait = 2  # Vérifier stop toutes les 2 secondes (vs 5s avant, vs 180s dans l'ancien code)
            last_progress_time = time.time()
            no_progress_timeout = 180  # Timeout global sans progrès

            while futures and not self._stop:
                # Attendre qu'au moins un future se termine (avec timeout court)
                done, futures = wait(futures, timeout=timeout_per_wait, return_when=FIRST_COMPLETED)

                current_time = time.time()
                elapsed_since_progress = current_time - last_progress_time

                if done:
                    # Au moins un future s'est terminé
                    last_progress_time = current_time

                    for future in done:
                        completed_count += 1

                        # Log progress every pair for debugging
                        logger.debug(f"🔄 [{pipeline_name}] Future {completed_count}/{total_pairs} completed")

                        # Log progress every 10 pairs
                        if completed_count % 10 == 0 or completed_count == total_pairs:
                            logger.info(f"📊 [{pipeline_name}] Progress: {completed_count}/{total_pairs} futures completed")

                        try:
                            # Get result (should be immediate since future is done)
                            result = future.result(timeout=1)
                            if result:
                                per_pair_results.append(result)
                        except TimeoutError:
                            logger.error(f"⏰ [{pipeline_name}] TIMEOUT getting result for completed future")
                        except Exception as e:
                            logger.error(f"❌ [{pipeline_name}] Error getting result: {e}", exc_info=True)
                else:
                    # Aucun future ne s'est terminé pendant timeout_per_wait secondes
                    if elapsed_since_progress > no_progress_timeout:
                        logger.error(f"⏰ [{pipeline_name}] NO PROGRESS for {no_progress_timeout}s! Some futures may be stuck.")
                        logger.error(f"   Processed {completed_count}/{total_pairs} pairs so far")
                        logger.error(f"   {len(futures)} futures still pending - CANCELLING THEM")

                        # Annuler tous les futures restants
                        for f in futures:
                            f.cancel()
                            logger.debug(f"   Cancelled stuck future")

                        # Sortir de la boucle
                        break

            if self._stop:
                logger.info(f"🛑 [{pipeline_name}] Stopped by user at {completed_count}/{total_pairs}")
                for f in futures:
                    f.cancel()

        finally:
            # Shutdown NON-BLOQUANT avec timeout
            logger.debug(f"[{pipeline_name}] Shutting down executor...")
            executor.shutdown(wait=False)  # Ne pas attendre

            # OPTIMISÉ: Attendre maximum 2 secondes pour shutdown propre (vs 3s avant)
            shutdown_start = time.time()
            while executor._threads and time.time() - shutdown_start < 2:
                time.sleep(0.05)  # Vérification toutes les 50ms (vs 100ms avant)

            if executor._threads:
                logger.warning(f"⚠️ [{pipeline_name}] Some workers didn't shutdown cleanly - they will be terminated")

        logger.info(f"🏁 [{pipeline_name}] Completed. Processed {completed_count}/{total_pairs} pairs. Collected {len(per_pair_results)} results")

        total_time = time.time() - pipeline_start_time

        # Extract metrics
        tp, fp, tn, fn = metrics['tp'], metrics['fp'], metrics['tn'], metrics['fn']
        accepted = metrics['accepted']
        rejected = metrics['rejected']
        labeled_count = metrics['labeled_count']
        unlabeled_count = metrics['unlabeled_count']

        # Determine if this is a labeled test set
        # Consider it labeled if at least 50% of pairs have labels
        is_labeled = labeled_count > (total_pairs * 0.5)

        # Calculer métriques finales (standard metrics only for labeled sets)
        if is_labeled:
            precision = (tp / (tp + fp)) * 100 if (tp + fp) > 0 else 0.0
            recall = (tp / (tp + fn)) * 100 if (tp + fn) > 0 else 0.0
            f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
            logger.info(f"Pipeline completed: {pairs_processed[0]}/{total_pairs} pairs processed "
                       f"in {total_time:.1f}s (P: {precision:.1f}%, R: {recall:.1f}%, F1: {f1:.1f}%)")
        else:
            # For unlabeled sets, precision/recall/f1 are not meaningful
            precision = 0.0
            recall = 0.0
            f1 = 0.0
            acceptance_rate = (accepted / total_pairs) * 100 if total_pairs > 0 else 0.0
            logger.info(f"Pipeline completed: {pairs_processed[0]}/{total_pairs} pairs processed "
                       f"in {total_time:.1f}s (Unlabeled set: {accepted} accepted, {rejected} rejected, "
                       f"{acceptance_rate:.1f}% acceptance rate)")

        # Émettre métriques finales et progression à 100%
        # CORRECTION BUG #35: Force final emission to ensure 100% is shown
        emit_intermediate_metrics(force=True)
        # Note: emit_intermediate_metrics() émet déjà pipeline_progress, pas besoin de dupliquer

        return {
            'tp': tp,
            'fp': fp,
            'tn': tn,
            'fn': fn,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'total_time': total_time,
            'per_pair_results': per_pair_results,
            # Raw results for unlabeled sets
            'accepted': accepted,
            'rejected': rejected,
            'is_labeled': is_labeled,
            'labeled_count': labeled_count,
            'unlabeled_count': unlabeled_count
        }

    def _create_pipeline(self, pipeline_config: Dict) -> VerificationPipeline:
        """Crée une instance VerificationPipeline depuis la config."""
        pipeline_name = pipeline_config.get('name', 'Unknown')
        mode = pipeline_config['mode']
        methods = pipeline_config['methods']
        # Extract max_workers from config if provided, otherwise default to 8
        max_workers = pipeline_config.get('max_workers', 8)

        logger.info(f"🔧 [CREATING PIPELINE] {pipeline_name} (mode: {mode}, max_workers: {max_workers})")

        try:
            pipeline = VerificationPipeline(
                db_manager=self.db,
                max_workers=max_workers,
                enable_caching=True,
                mode=mode
            )

            enabled_methods = []
            for method in methods:
                if method.get('enabled', True):
                    method_name = method['name']
                    enabled_methods.append(method_name)
                    pipeline.add_method(
                        method_name,
                        enabled=True,
                        parameters=method.get('parameters', {}),
                        weight=method.get('weight', 1.0)
                    )

            logger.info(f"✅ [PIPELINE CREATED] {pipeline_name} with {len(enabled_methods)} methods: {', '.join(enabled_methods)}")
            return pipeline

        except Exception as e:
            logger.error(f"❌ [PIPELINE CREATION FAILED] {pipeline_name}: {e}", exc_info=True)
            raise

    def _store_pipeline_results(self, run_id: int, pipeline_config: Dict, results: Dict):
        """Stocke les résultats d'un pipeline dans la DB."""
        with self.db.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO benchmark_results
                (benchmark_run_id, pipeline_name, pipeline_config_json,
                 tp, fp, tn, fn, precision, recall, f1_score, total_time,
                 per_pair_results_json, accepted, rejected, is_labeled,
                 labeled_count, unlabeled_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                pipeline_config['name'],
                json.dumps(pipeline_config, ensure_ascii=False),
                results['tp'], results['fp'], results['tn'], results['fn'],
                results['precision'], results['recall'], results['f1_score'],
                results['total_time'],
                json.dumps(results['per_pair_results'], ensure_ascii=False),
                results['accepted'], results['rejected'],
                1 if results['is_labeled'] else 0,  # Store as INTEGER (0 or 1)
                results['labeled_count'], results['unlabeled_count']
            ))
            conn.commit()


class BenchmarkManager:
    """Gestionnaire pour les benchmarks et leurs résultats."""

    def __init__(self, db_manager):
        """
        Args:
            db_manager: Instance DatabaseManager
        """
        self.db = db_manager
        logger.info("BenchmarkManager initialisé")

    # ═══════════════════════════════════════════════════════════
    # MÉTHODES DE RÉCUPÉRATION
    # ═══════════════════════════════════════════════════════════

    def get_run_details(self, run_id: int) -> Optional[Dict]:
        """
        Récupère les métadonnées d'un run (inclut durée calculée).

        Returns:
            Dict avec {id, run_label, test_set_name, total_pairs, pipelines_count,
                       created_at, completed_at, status, duration_seconds,
                       pipeline_name (si disponible)}
        """
        with self.db.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, run_label, test_set_name, total_pairs, pipelines_count,
                       created_at, completed_at, status
                FROM benchmark_runs WHERE id = ?
            """, (run_id,))
            row = cursor.fetchone()

            if not row:
                return None

            # Optionally fetch first pipeline name for convenience in exporters
            cursor.execute("""
                SELECT pipeline_name FROM benchmark_results
                WHERE benchmark_run_id = ?
                LIMIT 1
            """, (run_id,))
            pipeline_row = cursor.fetchone()

            run = {
                'id': row[0],
                'run_label': row[1],
                'test_set_name': row[2],
                'total_pairs': row[3],
                'pipelines_count': row[4],
                'created_at': row[5],
                'completed_at': row[6],
                'status': row[7],
                'pipeline_name': pipeline_row[0] if pipeline_row else None
            }

            # Calculer la durée si possible
            try:
                if run['created_at'] and run['completed_at']:
                    created = datetime.fromisoformat(run['created_at'])
                    completed = datetime.fromisoformat(run['completed_at'])
                    run['duration_seconds'] = (completed - created).total_seconds()
            except Exception:
                run['duration_seconds'] = None

            return run

    def get_run_history(self, limit: int = 50) -> List[Dict]:
        """
        Récupère l'historique des runs (ordre décroissant).

        Args:
            limit: nombre max d'entrées
        """
        with self.db.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, run_label, test_set_name, total_pairs, pipelines_count,
                       created_at, completed_at, status
                FROM benchmark_runs
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))

            runs = []
            for row in cursor.fetchall():
                runs.append({
                    'id': row[0],
                    'run_label': row[1],
                    'test_set_name': row[2],
                    'total_pairs': row[3],
                    'pipelines_count': row[4],
                    'created_at': row[5],
                    'completed_at': row[6],
                    'status': row[7]
                })

            return runs

    def get_benchmark_run(self, run_id: int) -> Optional[Dict]:
        """Récupère les informations d'un run."""
        with self.db.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, run_label, test_set_name, total_pairs, pipelines_count,
                       created_at, completed_at, status
                FROM benchmark_runs WHERE id = ?
            """, (run_id,))
            row = cursor.fetchone()

            if not row:
                return None

            return {
                'id': row[0],
                'run_label': row[1],
                'test_set_name': row[2],
                'total_pairs': row[3],
                'pipelines_count': row[4],
                'created_at': row[5],
                'completed_at': row[6],
                'status': row[7]
            }

    def get_benchmark_results(self, run_id: int) -> List[Dict]:
        """
        Récupère tous les résultats d'un run.

        Returns:
            Liste de dicts avec résultats par pipeline
        """
        with self.db.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT pipeline_name, pipeline_config_json,
                       tp, fp, tn, fn, precision, recall, f1_score, total_time,
                       per_pair_results_json, accepted, rejected, is_labeled,
                       labeled_count, unlabeled_count
                FROM benchmark_results
                WHERE benchmark_run_id = ?
                ORDER BY f1_score DESC
            """, (run_id,))

            results = []
            for row in cursor.fetchall():
                result_dict = {
                    'pipeline_name': row[0],
                    'pipeline_config': json.loads(row[1]),
                    'tp': row[2],
                    'fp': row[3],
                    'tn': row[4],
                    'fn': row[5],
                    'precision': row[6],
                    'recall': row[7],
                    'f1_score': row[8],
                    'total_time': row[9],
                    'per_pair_results': json.loads(row[10])
                }
                # Add raw result fields (may be None for old results)
                if len(row) > 11:
                    result_dict['accepted'] = row[11] if row[11] is not None else 0
                    result_dict['rejected'] = row[12] if row[12] is not None else 0
                    result_dict['is_labeled'] = bool(row[13]) if row[13] is not None else True
                    result_dict['labeled_count'] = row[14] if row[14] is not None else 0
                    result_dict['unlabeled_count'] = row[15] if row[15] is not None else 0
                else:
                    # Backwards compatibility for old results
                    result_dict['accepted'] = 0
                    result_dict['rejected'] = 0
                    result_dict['is_labeled'] = True
                    result_dict['labeled_count'] = 0
                    result_dict['unlabeled_count'] = 0

                results.append(result_dict)

            return results

    def list_benchmark_runs(self, limit: int = 20) -> List[Dict]:
        """Liste les runs récents."""
        with self.db.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, run_label, test_set_name, total_pairs, pipelines_count,
                       created_at, completed_at, status
                FROM benchmark_runs
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))

            runs = []
            for row in cursor.fetchall():
                runs.append({
                    'id': row[0],
                    'run_label': row[1],
                    'test_set_name': row[2],
                    'total_pairs': row[3],
                    'pipelines_count': row[4],
                    'created_at': row[5],
                    'completed_at': row[6],
                    'status': row[7]
                })

            return runs

    def delete_benchmark_run(self, run_id: int) -> bool:
        """Supprime un run (et tous ses résultats via CASCADE)."""
        with self.db.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM benchmark_runs WHERE id = ?", (run_id,))
            conn.commit()
            return cursor.rowcount > 0
