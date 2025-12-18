"""
Worker Optimization - Auto-détection du nombre optimal de workers

Calcule automatiquement le nombre de workers selon les ressources disponibles.
"""

import os
from typing import Dict
from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.WorkerOptimization')

# Essayer d'importer psutil pour info RAM
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    logger.warning("psutil non disponible - calcul workers basé sur CPU seulement")


def calculate_optimal_workers(
    min_workers: int = 2,
    max_workers: int = 16,
    cpu_usage_factor: float = 0.75,
    ram_per_worker_gb: float = 0.5,
    ram_os_reserve_gb: float = 2.0
) -> Dict[str, int]:
    """
    Calcule le nombre optimal de workers selon le matériel disponible.

    Stratégie :
    - CPU : Utiliser 75% des cores pour ne pas bloquer l'OS
    - RAM : Réserver 500MB par worker + 2GB pour l'OS
    - Limites : min 2, max 16 workers

    Args:
        min_workers: Nombre minimum de workers
        max_workers: Nombre maximum de workers
        cpu_usage_factor: Facteur d'utilisation CPU (0.75 = 75%)
        ram_per_worker_gb: RAM estimée par worker (GB)
        ram_os_reserve_gb: RAM à réserver pour l'OS (GB)

    Returns:
        Dict avec {
            'total': nombre total de workers recommandé,
            'cpu_based': workers selon CPU,
            'ram_based': workers selon RAM,
            'cpu_count': nombre de CPUs,
            'ram_available_gb': RAM disponible
        }
    """
    # 1. Workers basés sur CPU
    cpu_count = os.cpu_count() or 4
    cpu_workers = max(min_workers, int(cpu_count * cpu_usage_factor))
    cpu_workers = min(cpu_workers, max_workers)

    logger.debug(f"CPU: {cpu_count} cores → {cpu_workers} workers (factor {cpu_usage_factor})")

    # 2. Workers basés sur RAM (si psutil disponible)
    ram_workers = max_workers
    ram_available_gb = 0.0

    if HAS_PSUTIL:
        try:
            # RAM disponible en GB
            ram_available_gb = psutil.virtual_memory().available / (1024**3)

            # Calculer combien de workers on peut avoir
            ram_for_workers = ram_available_gb - ram_os_reserve_gb
            if ram_for_workers > 0:
                ram_workers = max(min_workers, int(ram_for_workers / ram_per_worker_gb))
                ram_workers = min(ram_workers, max_workers)
            else:
                logger.warning(f"RAM disponible ({ram_available_gb:.1f} GB) insuffisante")
                ram_workers = min_workers

            logger.debug(
                f"RAM: {ram_available_gb:.1f} GB disponible → {ram_workers} workers "
                f"({ram_per_worker_gb} GB/worker + {ram_os_reserve_gb} GB OS)"
            )
        except Exception as e:
            logger.warning(f"Erreur calcul RAM: {e}")
            ram_workers = max_workers
    else:
        logger.debug("psutil non disponible - pas de limite RAM")

    # 3. Prendre le minimum des deux contraintes
    optimal_workers = min(cpu_workers, ram_workers)
    optimal_workers = max(min_workers, min(optimal_workers, max_workers))

    result = {
        'total': optimal_workers,
        'cpu_based': cpu_workers,
        'ram_based': ram_workers,
        'cpu_count': cpu_count,
        'ram_available_gb': ram_available_gb
    }

    logger.info(
        f"✅ Workers optimaux: {optimal_workers} "
        f"(CPU: {cpu_workers}, RAM: {ram_workers}, CPUs: {cpu_count}, "
        f"RAM: {ram_available_gb:.1f} GB)"
    )

    return result


def calculate_benchmark_workers(
    num_pipelines: int,
    total_pairs: int,
    min_pipeline_workers: int = 1,
    max_pipeline_workers: int = 4,
    min_pair_workers: int = 2,
    max_pair_workers: int = 8
) -> Dict[str, int]:
    """
    Calcule le nombre optimal de workers pour un benchmark.

    Stratégie :
    - Déterminer total optimal de workers disponibles
    - Répartir entre workers pipeline et workers paire
    - Priorité : Plus de workers par paire si peu de pipelines

    Args:
        num_pipelines: Nombre de pipelines à tester
        total_pairs: Nombre total de paires à tester
        min_pipeline_workers: Minimum de pipelines en parallèle
        max_pipeline_workers: Maximum de pipelines en parallèle
        min_pair_workers: Minimum de paires en parallèle par pipeline
        max_pair_workers: Maximum de paires en parallèle par pipeline

    Returns:
        Dict avec {
            'pipeline_workers': nombre de pipelines en parallèle,
            'pair_workers': nombre de paires en parallèle par pipeline,
            'total_workers': total de workers utilisés,
            'explanation': explication de la stratégie
        }
    """
    # Calculer workers disponibles
    optimal = calculate_optimal_workers()
    total_available = optimal['total']

    # Stratégie : Adapter selon le nombre de pipelines
    if num_pipelines == 1:
        # Un seul pipeline : utiliser tous les workers pour les paires
        pipeline_workers = 1
        pair_workers = min(total_available, max_pair_workers)
        explanation = "1 pipeline → tous les workers pour les paires"

    elif num_pipelines <= 3:
        # Peu de pipelines : exécuter tous en parallèle, partager workers
        pipeline_workers = min(num_pipelines, total_available)
        pair_workers = max(
            min_pair_workers,
            min(total_available // pipeline_workers, max_pair_workers)
        )
        explanation = f"{num_pipelines} pipelines → tous en parallèle, workers partagés"

    else:
        # Beaucoup de pipelines : limiter parallélisme pipeline
        pipeline_workers = min(max_pipeline_workers, total_available // 2)
        pair_workers = max(
            min_pair_workers,
            min(total_available // pipeline_workers, max_pair_workers)
        )
        explanation = f"{num_pipelines} pipelines → limiter à {pipeline_workers} parallèles"

    # S'assurer des minimums
    pipeline_workers = max(min_pipeline_workers, min(pipeline_workers, num_pipelines))
    pair_workers = max(min_pair_workers, pair_workers)

    total_workers = pipeline_workers * pair_workers

    result = {
        'pipeline_workers': pipeline_workers,
        'pair_workers': pair_workers,
        'total_workers': total_workers,
        'total_available': total_available,
        'explanation': explanation
    }

    logger.info(
        f"📊 Benchmark workers: {pipeline_workers} pipelines × {pair_workers} paires "
        f"= {total_workers} workers totaux ({total_available} disponibles)\n"
        f"   Stratégie: {explanation}"
    )

    return result
