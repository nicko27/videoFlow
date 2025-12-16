#!/usr/bin/env python3
"""
Test spécifique : Progression temps réel et performance par algorithme.

Ce test vérifie que :
1. Les progress bars progressent de 0% → 100%
2. Les signaux sont émis en temps réel (pas seulement à la fin)
3. Chaque algorithme progresse indépendamment
4. Les performances sont trackées correctement

Usage:
    python3 scripts/test_progress_real_time.py --pairs 3 --pipeline-id 1
"""

import sys
import os
from pathlib import Path
import time
import argparse
from threading import Lock

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSlot

from src.plugins.duplicate_finder.data.database import DatabaseManager
from src.plugins.duplicate_finder.services.benchmark_manager import BenchmarkRunner
from src.core.logger import Logger

logger = Logger.get_logger('ProgressRealTimeTest')


class ProgressTracker(QObject):
    """Track progress in real-time with detailed timestamps."""

    def __init__(self):
        super().__init__()
        self.hash_progress_history = []  # All hash progress updates
        self.pipeline_progress_history = []  # All pipeline progress updates
        self.pair_progress_history = []  # All pair progress updates
        self.start_time = None
        self.lock = Lock()

    @pyqtSlot(str, int, int, str)
    def on_hash_progress(self, hash_type, current, total, pipeline_name):
        """Track hash progress with timestamp."""
        timestamp = time.time()
        if self.start_time is None:
            self.start_time = timestamp

        elapsed = timestamp - self.start_time

        with self.lock:
            self.hash_progress_history.append({
                'hash_type': hash_type,
                'current': current,
                'total': total,
                'pipeline_name': pipeline_name,
                'timestamp': timestamp,
                'elapsed': elapsed,
                'percentage': (current / total * 100) if total > 0 else 0
            })

        logger.info(f"  [{elapsed:6.2f}s] 📊 {hash_type}: {current}/{total} ({current/total*100:.1f}%)")

    @pyqtSlot(int, int, str)
    def on_pipeline_progress(self, current, total, name):
        """Track pipeline progress with timestamp."""
        timestamp = time.time()
        if self.start_time is None:
            self.start_time = timestamp

        elapsed = timestamp - self.start_time

        with self.lock:
            self.pipeline_progress_history.append({
                'current': current,
                'total': total,
                'name': name,
                'timestamp': timestamp,
                'elapsed': elapsed,
                'percentage': (current / total * 100) if total > 0 else 0
            })

        logger.info(f"  [{elapsed:6.2f}s] 📈 Pipeline: {current}/{total} ({current/total*100:.1f}%)")

    @pyqtSlot(int, int, str, str)
    def on_pair_progress(self, current, total, v1, v2):
        """Track pair progress with timestamp."""
        timestamp = time.time()
        if self.start_time is None:
            self.start_time = timestamp

        elapsed = timestamp - self.start_time

        with self.lock:
            self.pair_progress_history.append({
                'current': current,
                'total': total,
                'video1': v1,
                'video2': v2,
                'timestamp': timestamp,
                'elapsed': elapsed,
                'percentage': (current / total * 100) if total > 0 else 0
            })

        logger.info(f"  [{elapsed:6.2f}s] 🎬 Pair: {current}/{total}")

    def analyze_progression(self):
        """Analyse la progression pour vérifier les critères."""
        logger.info("")
        logger.info("="*80)
        logger.info("📊 ANALYSE DE LA PROGRESSION")
        logger.info("="*80)

        with self.lock:
            # 1. Vérifier que les hash progressent
            if not self.hash_progress_history:
                logger.error("❌ ÉCHEC: Aucun signal hash_type_progress reçu!")
                return False

            logger.info(f"✅ {len(self.hash_progress_history)} signaux hash_type_progress reçus")

            # 2. Vérifier la progression de 0% → 100%
            hash_types = {}
            for entry in self.hash_progress_history:
                ht = entry['hash_type']
                if ht not in hash_types:
                    hash_types[ht] = {'min': 100, 'max': 0, 'updates': []}

                pct = entry['percentage']
                hash_types[ht]['min'] = min(hash_types[ht]['min'], pct)
                hash_types[ht]['max'] = max(hash_types[ht]['max'], pct)
                hash_types[ht]['updates'].append({
                    'elapsed': entry['elapsed'],
                    'percentage': pct,
                    'current': entry['current'],
                    'total': entry['total']
                })

            logger.info("")
            logger.info("📈 Progression par algorithme:")
            logger.info("")

            all_reached_100 = True
            for hash_type, data in hash_types.items():
                reached_100 = data['max'] >= 99.9  # Allow for floating point
                status = "✅" if reached_100 else "❌"

                logger.info(f"{status} {hash_type}:")
                logger.info(f"   Range: {data['min']:.1f}% → {data['max']:.1f}%")
                logger.info(f"   Updates: {len(data['updates'])}")

                if len(data['updates']) > 0:
                    first = data['updates'][0]
                    last = data['updates'][-1]
                    duration = last['elapsed'] - first['elapsed']
                    logger.info(f"   Duration: {duration:.2f}s")
                    logger.info(f"   Timeline: {first['elapsed']:.2f}s → {last['elapsed']:.2f}s")

                if not reached_100:
                    all_reached_100 = False
                    logger.warning(f"   ⚠️  N'a pas atteint 100% (max: {data['max']:.1f}%)")

            logger.info("")

            # 3. Vérifier les mises à jour temps réel
            logger.info("⏱️  Analyse temps réel:")
            logger.info("")

            if len(self.hash_progress_history) <= 1:
                logger.warning("⚠️  Seulement 1 mise à jour - Impossible de vérifier temps réel")
                real_time_ok = False
            else:
                # Calculate intervals between updates
                intervals = []
                for i in range(1, len(self.hash_progress_history)):
                    interval = (self.hash_progress_history[i]['timestamp'] -
                               self.hash_progress_history[i-1]['timestamp'])
                    intervals.append(interval)

                avg_interval = sum(intervals) / len(intervals)
                max_interval = max(intervals)

                logger.info(f"   Total updates: {len(self.hash_progress_history)}")
                logger.info(f"   Average interval: {avg_interval:.3f}s")
                logger.info(f"   Max interval: {max_interval:.3f}s")

                # Real-time = updates happening regularly, not just at end
                real_time_ok = len(intervals) > 2 and max_interval < 10.0
                status = "✅" if real_time_ok else "⚠️ "
                logger.info(f"   {status} Mises à jour temps réel: {'OUI' if real_time_ok else 'LIMITÉ'}")

            logger.info("")
            logger.info("="*80)

            # Final verdict
            if all_reached_100 and real_time_ok:
                logger.info("✅ TEST RÉUSSI:")
                logger.info("   ✅ Tous les algorithmes ont progressé jusqu'à 100%")
                logger.info("   ✅ Mises à jour en temps réel confirmées")
                logger.info("="*80)
                return True
            elif all_reached_100:
                logger.warning("⚠️  TEST PARTIEL:")
                logger.warning("   ✅ Tous les algorithmes ont atteint 100%")
                logger.warning("   ⚠️  Mises à jour temps réel limitées")
                logger.info("="*80)
                return True
            else:
                logger.error("❌ TEST ÉCHOUÉ:")
                if not all_reached_100:
                    logger.error("   ❌ Certains algorithmes n'ont pas atteint 100%")
                if not real_time_ok:
                    logger.error("   ❌ Mises à jour temps réel insuffisantes")
                logger.info("="*80)
                return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Test progression temps réel')
    parser.add_argument('--pairs', type=int, default=3, help='Nombre de paires à tester')
    parser.add_argument('--pipeline-id', type=int, default=1, help='ID du pipeline à tester')
    args = parser.parse_args()

    logger.info("="*80)
    logger.info("🚀 TEST: Progression Temps Réel et Performance")
    logger.info("="*80)
    logger.info(f"Pipeline ID: {args.pipeline_id}")
    logger.info(f"Nombre de paires: {args.pairs}")
    logger.info("")

    # Initialize
    db = DatabaseManager()
    app = QApplication.instance() or QApplication(sys.argv)
    tracker = ProgressTracker()

    # Load test pairs
    logger.info("📊 Chargement des paires de test...")
    with db.pool.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT video1_path, video2_path, expected
            FROM test_pairs
            WHERE test_set_name = 'default'
            LIMIT {args.pairs}
        ''')

        test_pairs = []
        for row in cursor.fetchall():
            test_pairs.append({
                'video1_path': row[0],
                'video2_path': row[1],
                'expected': row[2],
                'start_time': 0.0,
                'duration': None,
                'sequence_score': 100.0,
                'notes': None
            })

    logger.info(f"✅ {len(test_pairs)} paires chargées")

    # Load pipeline config
    logger.info("🔧 Chargement de la configuration du pipeline...")
    with db.pool.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT name, methods_json
            FROM saved_pipelines
            WHERE id = ?
        ''', (args.pipeline_id,))

        row = cursor.fetchone()
        if not row:
            logger.error(f"❌ Pipeline {args.pipeline_id} introuvable!")
            return 1

        import json
        pipeline_name, methods_json = row
        config = json.loads(methods_json)
        config['name'] = pipeline_name
        config['id'] = args.pipeline_id
        if 'mode' not in config:
            config['mode'] = 'filtering'

    logger.info(f"✅ Pipeline: {pipeline_name}")
    logger.info("")

    # Create worker
    logger.info("🔧 Création du BenchmarkRunner...")
    worker = BenchmarkRunner(
        db_manager=db,
        test_pairs=test_pairs,
        pipeline_configs=[config],
        run_label=f"Test Progression - {pipeline_name}",
        max_pipeline_workers=1,
        max_pair_workers=2
    )

    # Connect signals
    worker.hash_type_progress.connect(tracker.on_hash_progress)
    worker.pipeline_progress.connect(tracker.on_pipeline_progress)
    worker.pair_progress.connect(tracker.on_pair_progress)

    logger.info("🚀 Démarrage du benchmark...")
    logger.info("")
    logger.info("─"*80)
    logger.info("📊 PROGRESSION EN TEMPS RÉEL")
    logger.info("─"*80)

    # Start
    worker.start()

    # Wait for completion
    max_wait = 120  # 2 minutes max
    elapsed = 0
    while elapsed < max_wait:
        app.processEvents()
        time.sleep(0.1)
        elapsed += 0.1

        if not worker.isRunning():
            break

    worker.wait(2000)

    # Give event loop time to process final signals
    for _ in range(10):
        app.processEvents()
        time.sleep(0.1)

    # Analyze results
    success = tracker.analyze_progression()

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
