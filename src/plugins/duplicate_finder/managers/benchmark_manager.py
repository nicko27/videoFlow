"""
Benchmark Manager - Exécution et gestion des benchmarks
"""
import json
import time
from typing import Dict, List, Optional
from datetime import datetime
from PyQt6.QtCore import pyqtSignal, QThread

from src.core.logger import Logger
from ..verification_pipeline import VerificationPipeline

logger = Logger.get_logger('DuplicateFinder.BenchmarkManager')


class BenchmarkRunner(QThread):
    """
    Worker thread pour exécuter un benchmark batch.

    Signals:
        pipeline_progress: (current_pipeline, total_pipelines, pipeline_name)
        pair_progress: (current_pair, total_pairs, video1, video2)
        pipeline_completed: (pipeline_name, results_dict)
        finished: (benchmark_run_id)
        error: (error_msg)
    """

    pipeline_progress = pyqtSignal(int, int, str)  # current, total, name
    pair_progress = pyqtSignal(int, int, str, str)  # current, total, video1, video2
    pipeline_completed = pyqtSignal(str, dict)  # name, results
    finished = pyqtSignal(int)  # run_id
    error = pyqtSignal(str)

    def __init__(
        self,
        db_manager,
        test_pairs: List[Dict],
        pipeline_configs: List[Dict],
        run_label: str
    ):
        """
        Args:
            db_manager: Instance VideoDatabase
            test_pairs: Liste de paires de test
            pipeline_configs: Liste de configs pipeline
            run_label: Label du run
        """
        super().__init__()
        self.db = db_manager
        self.test_pairs = test_pairs
        self.pipeline_configs = pipeline_configs
        self.run_label = run_label
        self._stop = False

    def stop(self):
        """Arrête le benchmark."""
        self._stop = True

    def run(self):
        """Exécute le benchmark batch."""
        try:
            # Créer le run dans la DB
            run_id = self._create_benchmark_run()

            # Pour chaque pipeline
            total_pipelines = len(self.pipeline_configs)

            for pipeline_idx, pipeline_config in enumerate(self.pipeline_configs, 1):
                if self._stop:
                    break

                pipeline_name = pipeline_config['name']
                logger.info(f"Benchmark pipeline {pipeline_idx}/{total_pipelines}: {pipeline_name}")

                # Émettre progression pipeline
                self.pipeline_progress.emit(pipeline_idx, total_pipelines, pipeline_name)

                # Exécuter benchmark pour ce pipeline
                results = self._run_pipeline_benchmark(pipeline_config)

                # Stocker résultats
                self._store_pipeline_results(run_id, pipeline_config, results)

                # Émettre complétion
                self.pipeline_completed.emit(pipeline_name, results)

            # Marquer run comme complété
            self._complete_benchmark_run(run_id)

            # Émettre fin
            self.finished.emit(run_id)

        except Exception as e:
            logger.error(f"Erreur benchmark: {e}", exc_info=True)
            self.error.emit(str(e))

    def _create_benchmark_run(self) -> int:
        """Crée l'entrée benchmark_run dans la DB."""
        # Déterminer le test set name (depuis la première paire)
        test_set_name = 'default'
        if self.test_pairs:
            # Chercher dans la DB le test_set_name de la première paire
            with self.db.connection_pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT test_set_name FROM test_pairs
                    WHERE video1_path = ? AND video2_path = ?
                    LIMIT 1
                """, (self.test_pairs[0]['video1_path'], self.test_pairs[0]['video2_path']))
                row = cursor.fetchone()
                if row:
                    test_set_name = row[0]

        with self.db.connection_pool.get_connection() as conn:
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
        with self.db.connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE benchmark_runs
                SET status = 'completed', completed_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), run_id))
            conn.commit()

    def _run_pipeline_benchmark(self, pipeline_config: Dict) -> Dict:
        """
        Exécute un benchmark pour un pipeline.

        Returns:
            Dict avec {tp, fp, tn, fn, precision, recall, f1, total_time, per_pair_results}
        """
        # Créer le pipeline
        pipeline = self._create_pipeline(pipeline_config)

        # Métriques
        tp = fp = tn = fn = 0
        per_pair_results = []
        start_time = time.time()

        total_pairs = len(self.test_pairs)

        # Pour chaque paire
        for pair_idx, pair in enumerate(self.test_pairs, 1):
            if self._stop:
                break

            video1 = pair['video1_path']
            video2 = pair['video2_path']
            expected = pair['expected']

            # Émettre progression
            self.pair_progress.emit(pair_idx, total_pairs, video1, video2)

            # Vérifier avec le pipeline
            try:
                result = pipeline.verify(
                    short_video=video1,
                    long_video=video2,
                    start_time=pair.get('start_time', 0.0),
                    duration=pair.get('duration', 0.0),
                    sequence_score=pair.get('sequence_score', 100.0)
                )

                accepted = result['accepted']

                # Calculer métrique
                if expected == 'positive':
                    if accepted:
                        tp += 1
                    else:
                        fn += 1
                elif expected == 'negative':
                    if accepted:
                        fp += 1
                    else:
                        tn += 1
                # 'unknown' n'est pas compté

                # Stocker résultat détaillé
                per_pair_results.append({
                    'video1': video1,
                    'video2': video2,
                    'expected': expected,
                    'accepted': accepted,
                    'weighted_score': result.get('weighted_score'),
                    'total_time': result['total_time']
                })

            except Exception as e:
                logger.error(f"Erreur vérification {video1} vs {video2}: {e}")
                per_pair_results.append({
                    'video1': video1,
                    'video2': video2,
                    'expected': expected,
                    'accepted': False,
                    'error': str(e)
                })

        total_time = time.time() - start_time

        # Calculer métriques
        precision = (tp / (tp + fp)) * 100 if (tp + fp) > 0 else 0.0
        recall = (tp / (tp + fn)) * 100 if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        return {
            'tp': tp,
            'fp': fp,
            'tn': tn,
            'fn': fn,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'total_time': total_time,
            'per_pair_results': per_pair_results
        }

    def _create_pipeline(self, pipeline_config: Dict) -> VerificationPipeline:
        """Crée une instance VerificationPipeline depuis la config."""
        mode = pipeline_config['mode']
        methods = pipeline_config['methods']

        pipeline = VerificationPipeline(
            db_manager=self.db,
            max_workers=8,
            enable_caching=True,
            mode=mode
        )

        for method in methods:
            if method.get('enabled', True):
                pipeline.add_method(
                    method['name'],
                    enabled=True,
                    parameters=method.get('parameters', {}),
                    weight=method.get('weight', 1.0)
                )

        return pipeline

    def _store_pipeline_results(self, run_id: int, pipeline_config: Dict, results: Dict):
        """Stocke les résultats d'un pipeline dans la DB."""
        with self.db.connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO benchmark_results
                (benchmark_run_id, pipeline_name, pipeline_config_json,
                 tp, fp, tn, fn, precision, recall, f1_score, total_time,
                 per_pair_results_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                pipeline_config['name'],
                json.dumps(pipeline_config, ensure_ascii=False),
                results['tp'], results['fp'], results['tn'], results['fn'],
                results['precision'], results['recall'], results['f1_score'],
                results['total_time'],
                json.dumps(results['per_pair_results'], ensure_ascii=False)
            ))
            conn.commit()


class BenchmarkManager:
    """Gestionnaire pour les benchmarks et leurs résultats."""

    def __init__(self, db_manager):
        """
        Args:
            db_manager: Instance VideoDatabase
        """
        self.db = db_manager
        logger.info("BenchmarkManager initialisé")

    # ═══════════════════════════════════════════════════════════
    # MÉTHODES DE RÉCUPÉRATION
    # ═══════════════════════════════════════════════════════════

    def get_benchmark_run(self, run_id: int) -> Optional[Dict]:
        """Récupère les informations d'un run."""
        with self.db.connection_pool.get_connection() as conn:
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
        with self.db.connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT pipeline_name, pipeline_config_json,
                       tp, fp, tn, fn, precision, recall, f1_score, total_time,
                       per_pair_results_json
                FROM benchmark_results
                WHERE benchmark_run_id = ?
                ORDER BY f1_score DESC
            """, (run_id,))

            results = []
            for row in cursor.fetchall():
                results.append({
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
                })

            return results

    def list_benchmark_runs(self, limit: int = 20) -> List[Dict]:
        """Liste les runs récents."""
        with self.db.connection_pool.get_connection() as conn:
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
        with self.db.connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM benchmark_runs WHERE id = ?", (run_id,))
            conn.commit()
            return cursor.rowcount > 0
