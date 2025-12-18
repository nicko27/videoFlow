"""CLI de benchmark/debug pour le pipeline de vérification.

Usage rapide :
    python -m src.plugins.duplicate_finder.benchmark_cli \
        --pairs pairs.json \
        --pipeline-config pipeline.json \
        --label bench_scenes_v1 \
        --debug

Format pairs.json (liste d'objets) :
[
  {
    "short": "clip.mp4",
    "long": "film.mp4",
    "start": 12.0,
    "duration": 5.0,
    "expected": "positive",   # "positive" (doit matcher) ou "negative" (ne doit pas matcher)
    "preference": "fn"         # "fp" (tolère faux positifs), "fn" (tolère faux négatifs), "balanced"
  }
]

Format pipeline.json :
{
  "mode": "filtering",
  "methods": [
    {"name": "color_histogram", "enabled": true, "parameters": {"threshold": 85.0}, "weight": 1.0},
    {"name": "motion_analysis", "enabled": true, "parameters": {"correlation_threshold": 85.0, "sample_interval": 3}, "weight": 1.0},
    {"name": "dct_coefficients", "enabled": true, "parameters": {"threshold": 75.0, "num_coeffs": 15}, "weight": 1.0},
    {"name": "strategy3", "enabled": true, "parameters": {"scene_threshold": 50.0, "dct_threshold": 75.0, "sequence_threshold": 95.0, "num_samples": 10, "warmup_seconds": 0.0, "max_workers": 8}, "weight": 1.0}
  ]
}

Ce script :
- construit un VerificationPipeline à partir du fichier pipeline.json (sinon preset équilibré par défaut) ;
- lance toutes les paires, enregistre runs/méthodes en base (tables pipeline_configs, verification_runs, etc.) ;
- enregistre des labels dans debug_labels (oracle) ;
- affiche les métriques TP/FP/FN/TN et une synthèse selon la préférence (faux positifs vs faux négatifs).
"""

import argparse
import json
import os
import sys
import time
from typing import List, Dict, Any

import cv2

from .verification_pipeline import VerificationPipeline
from .core.database_manager import VideoDatabase


def _load_json(path: str) -> Any:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _default_pipeline(db: VideoDatabase) -> VerificationPipeline:
    pipeline = VerificationPipeline(db_manager=db, max_workers=8, enable_caching=True, mode='filtering')
    pipeline.add_method('color_histogram', enabled=True, parameters={'threshold': 85.0}, weight=1.0)
    pipeline.add_method('motion_analysis', enabled=True, parameters={'correlation_threshold': 85.0, 'sample_interval': 3}, weight=1.0)
    pipeline.add_method('dct_coefficients', enabled=True, parameters={'threshold': 75.0, 'num_coeffs': 15}, weight=1.0)
    pipeline.add_method('strategy3', enabled=True, parameters={'scene_threshold': 50.0, 'dct_threshold': 75.0, 'sequence_threshold': 95.0, 'num_samples': 10, 'warmup_seconds': 0.0, 'max_workers': 8}, weight=1.0)
    return pipeline


def _duration_from_video(path: str) -> float:
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        return 0.0
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    cap.release()
    if fps <= 0 or total <= 0:
        return 0.0
    return float(total / fps)


def run_cli():
    parser = argparse.ArgumentParser(description="Benchmark/Debug du pipeline de vérification")
    parser.add_argument('--pairs', required=True, help='Fichier JSON contenant les paires et labels attendus')
    parser.add_argument('--pipeline-config', help='Fichier JSON de configuration du pipeline (mode + methods). Optionnel')
    parser.add_argument('--label', default='benchmark', help='Label du run stocké en base')
    parser.add_argument('--debug', action='store_true', help='Marque les runs en debug pour analyses')
    parser.add_argument('--no-cache', action='store_true', help="Ignore le cache pour forcer l'exécution")
    args = parser.parse_args()

    db = VideoDatabase()

    # Pipeline
    if args.pipeline_config:
        cfg = _load_json(args.pipeline_config)
        pipeline = VerificationPipeline(
            db_manager=db,
            max_workers=8,
            enable_caching=not args.no_cache,
            mode=cfg.get('mode', 'filtering')
        )
        pipeline.load_config(cfg.get('methods', []))
    else:
        pipeline = _default_pipeline(db)
        pipeline.enable_caching = not args.no_cache

    pairs: List[Dict[str, Any]] = _load_json(args.pairs)

    metrics = {'tp': 0, 'fp': 0, 'tn': 0, 'fn': 0}
    details = []

    for item in pairs:
        short = item['short']
        long = item['long']
        expected = item.get('expected', 'positive').lower()
        preference = item.get('preference', 'balanced').lower()
        start = float(item.get('start', 0.0))
        duration = item.get('duration')
        if duration is None:
            duration = _duration_from_video(short)

        # Oracle pour debug_labels
        try:
            db.upsert_debug_label(short, long, expected, notes=f"pref={preference}")
        except Exception:
            pass

        t0 = time.time()
        result = pipeline.verify(
            short_video=short,
            long_video=long,
            start_time=start,
            duration=duration,
            sequence_score=float(item.get('sequence_score', 100.0)),
            run_label=args.label,
            debug_flag=bool(args.debug)
        )
        elapsed = time.time() - t0
        predicted = bool(result.get('accepted'))

        if expected == 'positive':
            if predicted:
                metrics['tp'] += 1
            else:
                metrics['fn'] += 1
        else:
            if predicted:
                metrics['fp'] += 1
            else:
                metrics['tn'] += 1

        details.append({
            'short': short,
            'long': long,
            'expected': expected,
            'predicted': predicted,
            'preference': preference,
            'time_sec': elapsed,
            'rejection_method': result.get('rejection_method'),
            'weighted_score': result.get('weighted_score'),
            'mode': result.get('mode'),
            'pipeline': result.get('pipeline_config', [])
        })

        print(f"[{args.label}] {os.path.basename(short)} vs {os.path.basename(long)} -> {'ACCEPT' if predicted else 'REJECT'} (expected {expected}, {elapsed:.2f}s)")

    # Synthèse
    total = sum(metrics.values()) or 1
    fp_pref = [d for d in details if d['preference'] == 'fp']
    fn_pref = [d for d in details if d['preference'] == 'fn']

    print("\n=== Résumé ===")
    print(f"TP={metrics['tp']} FP={metrics['fp']} TN={metrics['tn']} FN={metrics['fn']} (total={total})")
    print(f"Préférence FP (tolère faux positifs): {len(fp_pref)} cas")
    print(f"Préférence FN (tolère faux négatifs): {len(fn_pref)} cas")


if __name__ == '__main__':
    run_cli()

