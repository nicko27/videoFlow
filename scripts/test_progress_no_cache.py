#!/usr/bin/env python3
"""
Test progression SANS cache - Force le calcul des hash.

Ce test désactive temporairement le cache pour forcer le calcul
des hash et voir la vraie progression 0% → 100%.

Usage:
    python3 scripts/test_progress_no_cache.py
"""

import sys
import os
from pathlib import Path
import time

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSlot

from src.plugins.duplicate_finder.data.database import DatabaseManager
from src.plugins.duplicate_finder.services.benchmark_manager import BenchmarkRunner
from src.core.logger import Logger

logger = Logger.get_logger('ProgressNoCacheTest')


class DetailedProgressTracker(QObject):
    """Track every single progress update."""

    def __init__(self):
        super().__init__()
        self.hash_updates = []
        self.start_time = None

    @pyqtSlot(str, int, int, str)
    def on_hash_progress(self, hash_type, current, total, pipeline_name):
        timestamp = time.time()
        if self.start_time is None:
            self.start_time = timestamp
        elapsed = timestamp - self.start_time
        pct = (current / total * 100) if total > 0 else 0

        self.hash_updates.append({
            'hash_type': hash_type,
            'current': current,
            'total': total,
            'percentage': pct,
            'elapsed': elapsed
        })

        logger.info(f"  [{elapsed:7.3f}s] {hash_type}: {current}/{total} ({pct:5.1f}%)")

    def print_summary(self):
        logger.info("")
        logger.info("="*80)
        logger.info("📊 RÉSUMÉ DE LA PROGRESSION")
        logger.info("="*80)

        if not self.hash_updates:
            logger.error("❌ Aucun signal reçu!")
            return False

        logger.info(f"✅ {len(self.hash_updates)} mises à jour reçues")
        logger.info("")

        # Group by hash type
        by_type = {}
        for update in self.hash_updates:
            ht = update['hash_type']
            if ht not in by_type:
                by_type[ht] = []
            by_type[ht].append(update)

        all_ok = True
        for hash_type, updates in by_type.items():
            first = updates[0]
            last = updates[-1]
            max_pct = max(u['percentage'] for u in updates)

            logger.info(f"📊 {hash_type}:")
            logger.info(f"   Updates: {len(updates)}")
            logger.info(f"   Timeline: {first['elapsed']:.3f}s → {last['elapsed']:.3f}s")
            logger.info(f"   Duration: {last['elapsed'] - first['elapsed']:.3f}s")
            logger.info(f"   Progress: {first['percentage']:.1f}% → {last['percentage']:.1f}%")
            logger.info(f"   Max reached: {max_pct:.1f}%")

            if max_pct >= 99.9:
                logger.info(f"   ✅ Atteint 100%")
            else:
                logger.warning(f"   ❌ N'a pas atteint 100% (max: {max_pct:.1f}%)")
                all_ok = False

            # Show progression curve
            if len(updates) > 1:
                logger.info(f"   Courbe: ", end="")
                step = max(1, len(updates) // 10)
                for i in range(0, len(updates), step):
                    logger.info(f"{updates[i]['percentage']:.0f}% ", end="")
                logger.info("")

            logger.info("")

        if all_ok:
            logger.info("✅ TEST RÉUSSI - Tous les algorithmes ont progressé jusqu'à 100%")
        else:
            logger.warning("⚠️  TEST PARTIEL - Certains algorithmes n'ont pas atteint 100%")

        logger.info("="*80)
        return all_ok


def main():
    logger.info("="*80)
    logger.info("🚀 TEST: Progression SANS Cache")
    logger.info("="*80)
    logger.info("")

    # Initialize
    db = DatabaseManager()
    app = QApplication.instance() or QApplication(sys.argv)
    tracker = DetailedProgressTracker()

    # Clear verification cache to force recalculation
    logger.info("🗑️  Nettoyage du cache de vérification...")
    with db.pool.get_connection() as conn:
        cursor = conn.cursor()
        # Get count first
        cursor.execute('SELECT COUNT(*) FROM verification_cache')
        count_before = cursor.fetchone()[0]

        # Delete ALL entries to force recalculation
        cursor.execute('DELETE FROM verification_cache')
        conn.commit()

        cursor.execute('SELECT COUNT(*) FROM verification_cache')
        count_after = cursor.fetchone()[0]

    logger.info(f"   Avant: {count_before} entrées")
    logger.info(f"   Après: {count_after} entrées")
    logger.info(f"   Supprimé: {count_before} entrées")
    logger.info("")

    # Load 2 pairs only (to be quick)
    logger.info("📊 Chargement de 2 paires...")
    with db.pool.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT video1_path, video2_path, expected
            FROM test_pairs
            WHERE test_set_name = 'default'
            LIMIT 2
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
    logger.info("")

    # Load Color Histogram pipeline (simple, fast)
    logger.info("🔧 Chargement du pipeline Color Histogram...")
    with db.pool.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT name, methods_json
            FROM saved_pipelines
            WHERE id = 1
        ''')

        import json
        row = cursor.fetchone()
        pipeline_name, methods_json = row
        config = json.loads(methods_json)
        config['name'] = pipeline_name
        config['id'] = 1
        config['mode'] = 'filtering'

    logger.info(f"✅ Pipeline: {pipeline_name}")
    logger.info("")

    # Create worker with cache DISABLED
    logger.info("🔧 Création du BenchmarkRunner (cache désactivé)...")

    # Monkey-patch VerificationPipeline to disable cache
    from src.plugins.duplicate_finder.verification import pipeline
    original_init = pipeline.VerificationPipeline.__init__

    def patched_init(self, *args, **kwargs):
        kwargs['enable_caching'] = False  # Force disable cache
        original_init(self, *args, **kwargs)

    pipeline.VerificationPipeline.__init__ = patched_init

    worker = BenchmarkRunner(
        db_manager=db,
        test_pairs=test_pairs,
        pipeline_configs=[config],
        run_label="Test Sans Cache",
        max_pipeline_workers=1,
        max_pair_workers=1  # 1 at a time to see progression clearly
    )

    # Connect signal
    worker.hash_type_progress.connect(tracker.on_hash_progress)

    logger.info("🚀 Démarrage du benchmark...")
    logger.info("")
    logger.info("─"*80)
    logger.info("📊 PROGRESSION EN TEMPS RÉEL (cache désactivé)")
    logger.info("─"*80)

    # Start
    worker.start()

    # Wait
    max_wait = 120
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

    # Restore original
    pipeline.VerificationPipeline.__init__ = original_init

    # Show results
    success = tracker.print_summary()

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
