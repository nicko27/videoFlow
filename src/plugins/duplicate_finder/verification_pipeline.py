"""
Verification Pipeline - Configurable Multi-Method Verification System

This module provides a flexible pipeline system that can execute multiple
verification methods in any order, with full caching and parameterization.

Example Usage:
    pipeline = VerificationPipeline(db_manager=db)

    # Configure pipeline with ordered methods
    pipeline.add_method('color_histogram', enabled=True, threshold=85.0)
    pipeline.add_method('dct_coefficients', enabled=True, threshold=75.0)
    pipeline.add_method('motion_analysis', enabled=True, threshold=85.0)

    # Run pipeline (short-circuits on first rejection)
    result = pipeline.verify(short_video, long_video, start_time, duration)

    # Reorder methods
    pipeline.move_method(0, 2)  # Move first method to third position

    # Get configuration
    config = pipeline.get_config()
"""

import time
import json
import hashlib
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from src.core.logger import Logger
from .analysis.video_analysis_methods import VideoAnalysisMethods
from .analysis.subsequence_verification import SubsequenceVerificationMethods

logger = Logger.get_logger('DuplicateFinder.VerificationPipeline')


@dataclass
class PipelineMethod:
    """Configuration for a single pipeline method."""
    name: str
    enabled: bool = True
    parameters: Dict = field(default_factory=dict)
    order: int = 0
    weight: float = 1.0  # Weight for weighting mode (0.0-10.0)


class VerificationPipeline:
    """
    Configurable verification pipeline that executes multiple methods in sequence.

    Methods are executed in order until one rejects the match (short-circuit).
    All results are cached in the database for performance.
    """

    # Available verification methods with clear names and detailed descriptions
    AVAILABLE_METHODS = {
        'color_histogram': {
            'display_name': '🎨 Histogramme de Couleurs',
            'short_name': 'Couleurs',
            'description': 'Compare la distribution des couleurs (HSV)',
            'detailed_explanation': (
                'Analyse la répartition des couleurs dans les vidéos. '
                'Efficace pour détecter des scènes avec des palettes de couleurs distinctes. '
                'Rapide (~0.5s par paire).'
            ),
            'use_case': 'Scènes avec couleurs caractéristiques',
            'speed': 'Rapide',
            'default_params': {
                'bins': (32, 32, 32),
                'threshold': 85.0
            }
        },
        'edge_pattern': {
            'display_name': '📐 Détection de Contours',
            'short_name': 'Contours',
            'description': 'Analyse la densité et les motifs de bords',
            'detailed_explanation': (
                'Détecte les bords avec l\'algorithme Canny puis analyse leur densité spatiale. '
                'Robuste aux changements de luminosité. '
                'Moyennement rapide (~0.8s par paire).'
            ),
            'use_case': 'Structures géométriques marquées',
            'speed': 'Moyen',
            'default_params': {
                'canny_low': 50,
                'canny_high': 150,
                'grid_size': (4, 4),
                'threshold': 80.0
            }
        },
        'motion_analysis': {
            'display_name': '🎬 Analyse de Mouvement',
            'short_name': 'Mouvement',
            'description': 'Compare les patterns de mouvement frame par frame',
            'detailed_explanation': (
                'Calcule les différences entre frames consécutives et mesure la corrélation temporelle. '
                'Excellent pour détecter des scènes avec mouvements caractéristiques. '
                'Moyennement rapide (~1.0s par paire).'
            ),
            'use_case': 'Vidéos avec mouvements distincts',
            'speed': 'Moyen',
            'default_params': {
                'sample_interval': 3,
                'correlation_threshold': 85.0
            }
        },
        'dct_coefficients': {
            'display_name': '📊 Coefficients Fréquentiels (DCT)',
            'short_name': 'Fréquences',
            'description': 'Compare les coefficients dans le domaine fréquentiel',
            'detailed_explanation': (
                'Utilise la Transformée en Cosinus Discrète pour comparer les composantes fréquentielles. '
                'Très robuste au réencodage et aux changements de qualité/bitrate. '
                'Moyennement rapide (~1.2s par paire).'
            ),
            'use_case': 'Vidéos réencodées ou de qualité différente',
            'speed': 'Moyen',
            'default_params': {
                'block_size': 8,
                'num_coeffs': 15,
                'threshold': 75.0
            }
        },
        'ssim': {
            'display_name': '🔍 Similarité Structurelle (SSIM)',
            'short_name': 'Structure',
            'description': 'Mesure la similarité perceptuelle',
            'detailed_explanation': (
                'Calcule un index de similarité structurelle qui corrèle bien avec la perception humaine. '
                'Sensible aux déformations structurelles. '
                'Moyennement lent (~1.5s par paire).'
            ),
            'use_case': 'Détection haute précision',
            'speed': 'Lent',
            'default_params': {
                'window_size': 7,
                'threshold': 0.85
            }
        },
        'feature_matching': {
            'display_name': '🎯 Correspondance de Points Clés',
            'short_name': 'Points Clés',
            'description': 'Détecte et fait correspondre les features visuelles',
            'detailed_explanation': (
                'Détecte des points d\'intérêt (ORB/SIFT/AKAZE) puis les fait correspondre entre vidéos. '
                'Robuste aux transformations géométriques (rotation, zoom). '
                'Lent (~2.0s par paire avec ORB, ~3.5s avec SIFT).'
            ),
            'use_case': 'Transformations géométriques',
            'speed': 'Lent',
            'default_params': {
                'detector': 'ORB',
                'max_features': 500,
                'threshold': 70.0
            }
        },
        'strategy3': {
            'display_name': '✨ Détection de Scènes + DCT',
            'short_name': 'Scènes+DCT',
            'description': 'Méthode combinée haute précision (100% testé)',
            'detailed_explanation': (
                'Détecte les transitions de scènes puis vérifie avec DCT. '
                'Précision testée: 100% (zéro faux positifs), Rappel: 72.7%, F1: 84.2%. '
                'Très lent (~3.0s par paire) mais extrêmement fiable. '
                'Pour novices: monter les seuils = moins de faux positifs, plus lent; '
                'baisser les seuils = plus permissif, plus de détections mais à vérifier manuellement.'
            ),
            'use_case': 'Validation finale, zéro faux positif toléré',
            'speed': 'Très Lent',
            'default_params': {
                'scene_threshold': 50.0,
                'dct_threshold': 75.0,
                'sequence_threshold': 95.0,
                'num_samples': 10,
                'warmup_seconds': 0.0,
                'max_workers': 8
            }
        }
    }

    # Pipeline modes
    MODE_FILTERING = 'filtering'  # Sequential filtering (short-circuit on first rejection)
    MODE_WEIGHTING = 'weighting'  # Weighted average of all scores
    MODE_HYBRID = 'hybrid'  # Weighted average but with minimum thresholds

    def __init__(
        self,
        db_manager=None,
        max_workers: int = 8,
        enable_caching: bool = True,
        mode: str = MODE_FILTERING
    ):
        """
        Initialize verification pipeline.

        Args:
            db_manager: Database manager for caching results
            max_workers: Number of parallel workers for methods that support it
            enable_caching: Whether to cache results in database
            mode: Pipeline mode - 'filtering', 'weighting', or 'hybrid'

        Note:
            In weighting mode, the threshold is calculated as the weighted average
            of individual method thresholds (each method proposes its own threshold)
        """
        self.db = db_manager
        self.max_workers = max_workers
        self.enable_caching = enable_caching
        self.mode = mode

        # Pipeline configuration (ordered list of methods)
        self.methods: List[PipelineMethod] = []

        # Initialize method instances
        self.video_methods = None
        self.strategy3_methods = None

        logger.info(f"VerificationPipeline initialized with {max_workers} workers, mode={mode}")

    def _ensure_methods_initialized(self):
        """Lazy initialization of method instances."""
        if self.video_methods is None:
            # Collect all parameters from configured methods
            params = self._collect_method_parameters()

            self.video_methods = VideoAnalysisMethods(
                db_manager=self.db,
                max_workers=self.max_workers,
                **params
            )

        if self.strategy3_methods is None:
            strategy3_params = next(
                (m.parameters for m in self.methods if m.name == 'strategy3' and m.enabled),
                {}
            )

            self.strategy3_methods = SubsequenceVerificationMethods(
                scene_threshold=strategy3_params.get('scene_threshold', 50.0),
                dct_threshold=strategy3_params.get('dct_threshold', 75.0),
                sequence_threshold=strategy3_params.get('sequence_threshold', 95.0),
                num_samples=strategy3_params.get('num_samples', 10),
                warmup_seconds=strategy3_params.get('warmup_seconds', 0.0),
                max_workers=strategy3_params.get('max_workers', self.max_workers)
            )

    def _collect_method_parameters(self) -> Dict:
        """Collect parameters from all configured methods."""
        params = {}

        for method in self.methods:
            if not method.enabled:
                continue

            if method.name == 'color_histogram':
                params['color_hist_bins'] = method.parameters.get('bins', (32, 32, 32))
                params['color_hist_threshold'] = method.parameters.get('threshold', 85.0)

            elif method.name == 'edge_pattern':
                params['edge_canny_low'] = method.parameters.get('canny_low', 50)
                params['edge_canny_high'] = method.parameters.get('canny_high', 150)
                params['edge_grid_size'] = method.parameters.get('grid_size', (4, 4))
                params['edge_threshold'] = method.parameters.get('threshold', 80.0)

            elif method.name == 'motion_analysis':
                params['motion_sample_interval'] = method.parameters.get('sample_interval', 3)
                params['motion_correlation_threshold'] = method.parameters.get('correlation_threshold', 85.0)

            elif method.name == 'dct_coefficients':
                params['dct_block_size'] = method.parameters.get('block_size', 8)
                params['dct_num_coeffs'] = method.parameters.get('num_coeffs', 15)
                params['dct_threshold'] = method.parameters.get('threshold', 75.0)

            elif method.name == 'ssim':
                params['ssim_window_size'] = method.parameters.get('window_size', 7)
                params['ssim_threshold'] = method.parameters.get('threshold', 0.85)

            elif method.name == 'feature_matching':
                params['feature_detector'] = method.parameters.get('detector', 'ORB')
                params['feature_max_features'] = method.parameters.get('max_features', 500)
                params['feature_match_threshold'] = method.parameters.get('threshold', 70.0)

        return params

    def add_method(
        self,
        method_name: str,
        enabled: bool = True,
        parameters: Optional[Dict] = None,
        position: Optional[int] = None,
        weight: float = 1.0
    ) -> bool:
        """
        Add a verification method to the pipeline.

        Args:
            method_name: Name of the method (must be in AVAILABLE_METHODS)
            enabled: Whether the method is enabled
            parameters: Custom parameters (uses defaults if not provided)
            position: Position in pipeline (None = append to end)
            weight: Weight for weighting mode (0.0-10.0, default: 1.0)

        Returns:
            True if added successfully, False otherwise
        """
        if method_name not in self.AVAILABLE_METHODS:
            logger.error(f"Unknown method: {method_name}")
            return False

        # Get default parameters
        default_params = self.AVAILABLE_METHODS[method_name]['default_params'].copy()

        # Override with custom parameters
        if parameters:
            default_params.update(parameters)

        # Create method instance
        order = len(self.methods) if position is None else position
        method = PipelineMethod(
            name=method_name,
            enabled=enabled,
            parameters=default_params,
            order=order,
            weight=weight
        )

        # Insert at position or append
        if position is not None and 0 <= position <= len(self.methods):
            self.methods.insert(position, method)
            # Update order for all methods after insertion point
            for i in range(position + 1, len(self.methods)):
                self.methods[i].order = i
        else:
            self.methods.append(method)

        logger.info(f"Added method '{method_name}' at position {order} (enabled={enabled})")
        return True

    def remove_method(self, position: int) -> bool:
        """
        Remove a method from the pipeline.

        Args:
            position: Position of method to remove

        Returns:
            True if removed successfully
        """
        if 0 <= position < len(self.methods):
            removed = self.methods.pop(position)
            # Update order for remaining methods
            for i in range(position, len(self.methods)):
                self.methods[i].order = i
            logger.info(f"Removed method '{removed.name}' from position {position}")
            return True
        return False

    def move_method(self, from_pos: int, to_pos: int) -> bool:
        """
        Move a method to a different position in the pipeline.

        Args:
            from_pos: Current position
            to_pos: New position

        Returns:
            True if moved successfully
        """
        if not (0 <= from_pos < len(self.methods) and 0 <= to_pos < len(self.methods)):
            return False

        method = self.methods.pop(from_pos)
        self.methods.insert(to_pos, method)

        # Update all orders
        for i, m in enumerate(self.methods):
            m.order = i

        logger.info(f"Moved method '{method.name}' from position {from_pos} to {to_pos}")
        return True

    def enable_method(self, position: int, enabled: bool = True) -> bool:
        """Enable or disable a method."""
        if 0 <= position < len(self.methods):
            self.methods[position].enabled = enabled
            logger.info(f"Method '{self.methods[position].name}' {'enabled' if enabled else 'disabled'}")
            return True
        return False

    def update_method_parameters(self, position: int, parameters: Dict) -> bool:
        """Update parameters for a method."""
        if 0 <= position < len(self.methods):
            self.methods[position].parameters.update(parameters)
            logger.info(f"Updated parameters for method '{self.methods[position].name}'")
            return True
        return False

    def verify(
        self,
        short_video: str,
        long_video: str,
        start_time: float,
        duration: float,
        sequence_score: float = 100.0,
        run_label: Optional[str] = None,
        debug_flag: bool = False
    ) -> Dict:
        """
        Run verification pipeline on a video pair.

        Methods are executed in order. If any method rejects the match,
        the pipeline stops immediately (short-circuit).

        Args:
            short_video: Path to short video
            long_video: Path to long video
            start_time: Start time in long video
            duration: Duration to verify
            sequence_score: Initial sequence match score

        Returns:
            Dictionary with verification results:
            {
                'accepted': bool,
                'pipeline_results': List[Dict],  # Results from each method
                'total_time': float,
                'methods_executed': int,
                'rejection_method': str or None,
                'final_scores': Dict
            }
        """
        self._ensure_methods_initialized()

        start = time.time()
        pipeline_results = []
        final_scores = {'sequence_score': sequence_score}
        methods_executed = 0
        rejection_method = None

        # Compute config hash (used for cache invalidation) - includes full pipeline config
        config_snapshot = {
            'mode': self.mode,
            'methods': [
                {
                    'name': m.name,
                    'enabled': m.enabled,
                    'parameters': m.parameters,
                    'weight': m.weight,
                    'order': m.order
                }
                for m in self.methods
            ]
        }

        strategy3_params = next((m.parameters for m in self.methods if m.name == 'strategy3'), {})

        config_hash = hashlib.sha1(json.dumps(config_snapshot, sort_keys=True).encode('utf-8')).hexdigest()

        # Check cache if enabled
        if self.enable_caching and self.db:
            cached = self.db.get_cached_verification(short_video, long_video, start_time, config_hash=config_hash)
            if cached:
                logger.info("✓ Using cached pipeline result (config match)")
                return cached

        # Execute methods based on mode
        for method in self.methods:
            if not method.enabled:
                continue

            method_start = time.time()
            result = None

            try:
                # Execute the appropriate method
                if method.name == 'color_histogram':
                    result = self.video_methods.compare_color_histograms(
                        short_video, long_video, start_time, duration
                    )

                elif method.name == 'edge_pattern':
                    result = self.video_methods.compare_edge_patterns(
                        short_video, long_video, start_time, duration
                    )

                elif method.name == 'motion_analysis':
                    result = self.video_methods.compare_motion_patterns(
                        short_video, long_video, start_time, duration
                    )

                elif method.name == 'dct_coefficients':
                    result = self.video_methods.compare_dct_signatures(
                        short_video, long_video, start_time, duration
                    )

                elif method.name == 'ssim':
                    result = self.video_methods.compare_ssim(
                        short_video, long_video, start_time, duration
                    )

                elif method.name == 'feature_matching':
                    result = self.video_methods.detect_and_match_features(
                        short_video, long_video, start_time, duration
                    )

                elif method.name == 'strategy3':
                    result = self.strategy3_methods.verify_with_strategy3(
                        short_video=short_video,
                        long_video=long_video,
                        start_time=start_time,
                        duration=duration,
                        sequence_score=sequence_score
                    )

                if result:
                    method_time = time.time() - method_start
                    result['execution_time'] = method_time
                    result['weight'] = method.weight
                    result['method_name'] = method.name
                    result['threshold'] = self._get_method_threshold(method)
                    result['params'] = method.parameters
                    pipeline_results.append(result)
                    methods_executed += 1

                    # Collect scores
                    for key, value in result.items():
                        if key.endswith('_score') and isinstance(value, (int, float)):
                            final_scores[key] = value

                    # MODE: FILTERING - Short-circuit on first rejection
                    if self.mode == self.MODE_FILTERING:
                        if not result['accepted']:
                            rejection_method = method.name
                            logger.info(f"[FILTERING] Pipeline rejected by {method.name}: {result.get('rejection_reason', 'N/A')}")
                            break
                        logger.info(f"✓ [FILTERING] {method.name} passed ({method_time:.2f}s)")

                    # MODE: HYBRID - Check individual threshold but continue
                    elif self.mode == self.MODE_HYBRID:
                        if not result['accepted']:
                            rejection_method = method.name
                            logger.info(f"[HYBRID] {method.name} failed individual threshold: {result.get('rejection_reason', 'N/A')}")
                        else:
                            logger.info(f"✓ [HYBRID] {method.name} passed threshold ({method_time:.2f}s)")

                    # MODE: WEIGHTING - Just collect scores, continue
                    else:  # MODE_WEIGHTING
                        logger.info(f"✓ [WEIGHTING] {method.name} executed ({method_time:.2f}s)")

            except Exception as e:
                logger.error(f"Error executing method {method.name}: {e}")
                result = {
                    'accepted': False,
                    'rejection_reason': f"Error: {str(e)}",
                    'method': method.name,
                    'weight': method.weight
                }
                pipeline_results.append(result)
                if self.mode == self.MODE_FILTERING:
                    rejection_method = method.name
                    break

        # Calculate final acceptance based on mode
        total_time = time.time() - start
        accepted = False
        weighted_score = 0.0

        if self.mode == self.MODE_FILTERING:
            # FILTERING: Accepted if no method rejected
            accepted = rejection_method is None

        elif self.mode == self.MODE_WEIGHTING:
            # WEIGHTING: Calculate weighted average of all scores
            # Each method proposes its own threshold, we calculate weighted average of both scores and thresholds
            total_weight = 0.0
            weighted_sum = 0.0
            weighted_threshold_sum = 0.0

            for i, result in enumerate(pipeline_results):
                # Extract primary score for this method
                method_score = self._extract_primary_score(result)
                weight = result.get('weight', 1.0)

                # Get the threshold for this method
                method = self.methods[i] if i < len(self.methods) else None
                method_threshold = self._get_method_threshold(method) if method else 80.0

                weighted_sum += method_score * weight
                weighted_threshold_sum += method_threshold * weight
                total_weight += weight

            if total_weight > 0:
                weighted_score = weighted_sum / total_weight
                weighted_threshold = weighted_threshold_sum / total_weight
                accepted = weighted_score >= weighted_threshold
                logger.info(f"[WEIGHTING] Weighted score: {weighted_score:.1f}%, Weighted threshold: {weighted_threshold:.1f}% -> {'ACCEPTED' if accepted else 'REJECTED'}")

        elif self.mode == self.MODE_HYBRID:
            # HYBRID: Weighted average AND all individual thresholds must pass
            total_weight = 0.0
            weighted_sum = 0.0
            weighted_threshold_sum = 0.0

            for i, result in enumerate(pipeline_results):
                method_score = self._extract_primary_score(result)
                weight = result.get('weight', 1.0)

                # Get the threshold for this method
                method = self.methods[i] if i < len(self.methods) else None
                method_threshold = self._get_method_threshold(method) if method else 80.0

                weighted_sum += method_score * weight
                weighted_threshold_sum += method_threshold * weight
                total_weight += weight

            if total_weight > 0:
                weighted_score = weighted_sum / total_weight
                weighted_threshold = weighted_threshold_sum / total_weight
                # Accepted if: no individual rejection AND weighted score >= weighted threshold
                accepted = (rejection_method is None) and (weighted_score >= weighted_threshold)
                logger.info(f"[HYBRID] Weighted score: {weighted_score:.1f}%, Weighted threshold: {weighted_threshold:.1f}%, Individual thresholds: {'OK' if rejection_method is None else 'FAILED'} -> {'ACCEPTED' if accepted else 'REJECTED'}")

        final_result = {
            'accepted': accepted,
            'pipeline_results': pipeline_results,
            'total_time': total_time,
            'methods_executed': methods_executed,
            'rejection_method': rejection_method,
            'final_scores': final_scores,
            'pipeline_config': [m.name for m in self.methods if m.enabled],
            'mode': self.mode,
            'weighted_score': weighted_score if self.mode in [self.MODE_WEIGHTING, self.MODE_HYBRID] else None,
            'config_hash': config_hash,
            'run_label': run_label,
            'debug_flag': debug_flag
        }

        # Cache result
        if self.enable_caching and self.db:
            # Extract Strategy3 metrics if present
            strategy3_result = next((r for r in pipeline_results if 'scene_cuts_score' in r and 'dct_score' in r), None)
            cache_payload = {
                'accepted': final_result['accepted'],
                'scene_cuts_score': strategy3_result.get('scene_cuts_score', 0.0) if strategy3_result else 0.0,
                'dct_score': strategy3_result.get('dct_score', 0.0) if strategy3_result else 0.0,
                'rejection_reason': strategy3_result.get('rejection_reason') if strategy3_result else None,
                'config_hash': config_hash,
                'num_samples': strategy3_result.get('num_samples') if strategy3_result else strategy3_params.get('num_samples'),
                'warmup_seconds': strategy3_result.get('warmup_seconds') if strategy3_result else strategy3_params.get('warmup_seconds'),
                'execution_time': strategy3_result.get('execution_time') if strategy3_result else None,
                'sequence_score': final_scores.get('sequence_score', 0.0)
            }
            self.db.store_verification_result(
                short_video, long_video, start_time,
                duration, sequence_score, cache_payload
            )

            # Persist run + per-method results for benchmarking/debug
            try:
                pipeline_config_id = self.db.upsert_pipeline_config(
                    config_hash=config_hash,
                    mode=self.mode,
                    config_json=json.dumps(config_snapshot)
                )

                run_id = self.db.store_verification_run(
                    pipeline_config_id=pipeline_config_id,
                    short_video_path=short_video,
                    long_video_path=long_video,
                    start_time=start_time,
                    duration=duration,
                    sequence_score=sequence_score,
                    accepted=accepted,
                    total_time=total_time,
                    run_label=run_label,
                    debug_flag=debug_flag
                )

                for method, result in zip([m for m in self.methods if m.enabled], pipeline_results):
                    params_hash = hashlib.sha1(json.dumps(result.get('params', {}), sort_keys=True).encode('utf-8')).hexdigest()
                    method_config_id = self.db.upsert_method_config(
                        method_name=method.name,
                        params_hash=params_hash,
                        params_json=json.dumps(result.get('params', {}))
                    )

                    primary_score = self._extract_primary_score(result)
                    threshold = result.get('threshold', self._get_method_threshold(method))
                    extra_json = json.dumps({k: v for k, v in result.items() if k not in {'accepted', 'rejection_reason', 'weight', 'threshold', 'method_name', 'execution_time'}})

                    self.db.store_verification_method_result(
                        run_id=run_id,
                        method_name=method.name,
                        accepted=result.get('accepted', False),
                        primary_score=primary_score,
                        threshold=threshold,
                        execution_time=result.get('execution_time'),
                        extra_json=extra_json,
                        method_config_id=method_config_id
                    )

            except Exception as e:
                logger.warning(f"Failed to persist verification run details: {e}")

        mode_str = {'filtering': 'FILTERING', 'weighting': 'WEIGHTING', 'hybrid': 'HYBRID'}.get(self.mode, self.mode)
        logger.info(f"Pipeline [{mode_str}] completed in {total_time:.2f}s: "
                   f"{'ACCEPTED' if accepted else f'REJECTED'}"
                   f"{f' (weighted score: {weighted_score:.1f}%)' if weighted_score else ''} "
                   f"({methods_executed} methods executed)")

        return final_result

    def _extract_primary_score(self, result: Dict) -> float:
        """
        Extract the primary score from a method result.

        Args:
            result: Method result dictionary

        Returns:
            Primary score as percentage (0-100)
        """
        # Try to find the primary score key for each method
        if 'color_score' in result:
            return result['color_score']
        elif 'edge_score' in result:
            return result['edge_score']
        elif 'motion_score' in result:
            return result['motion_score']
        elif 'dct_score' in result:
            return result['dct_score']
        elif 'ssim_score' in result:
            return result['ssim_score'] * 100.0  # SSIM is 0-1, convert to percentage
        elif 'feature_score' in result:
            return result['feature_score']
        elif 'scene_cuts_score' in result:
            return result['scene_cuts_score']
        elif 'sequence_score' in result:
            return result['sequence_score']
        else:
            # Fallback: if accepted, return 100, else 0
            return 100.0 if result.get('accepted', False) else 0.0

    def _get_method_threshold(self, method: PipelineMethod) -> float:
        """
        Extract the threshold from a method's parameters.

        Args:
            method: Pipeline method

        Returns:
            Threshold as percentage (0-100)
        """
        params = method.parameters

        # Each method has its own threshold parameter name
        if method.name == 'color_histogram':
            return params.get('threshold', 85.0)
        elif method.name == 'edge_pattern':
            return params.get('threshold', 80.0)
        elif method.name == 'motion_analysis':
            return params.get('correlation_threshold', 85.0)
        elif method.name == 'dct_coefficients':
            return params.get('threshold', 75.0)
        elif method.name == 'ssim':
            return params.get('threshold', 0.85) * 100.0  # SSIM is 0-1, convert to percentage
        elif method.name == 'feature_matching':
            return params.get('threshold', 70.0)
        elif method.name == 'strategy3':
            return params.get('sequence_threshold', 95.0)
        else:
            return 80.0  # Default threshold

    def get_config(self) -> List[Dict]:
        """
        Get current pipeline configuration.

        Returns:
            List of method configurations
        """
        return [
            {
                'name': m.name,
                'display_name': self.AVAILABLE_METHODS[m.name]['display_name'],
                'enabled': m.enabled,
                'order': m.order,
                'parameters': m.parameters,
                'weight': m.weight
            }
            for m in self.methods
        ]

    def load_config(self, config: List[Dict]):
        """
        Load pipeline configuration from a list of method configs.

        Args:
            config: List of method configurations
        """
        self.methods = []
        for i, method_config in enumerate(config):
            self.add_method(
                method_name=method_config['name'],
                enabled=method_config.get('enabled', True),
                parameters=method_config.get('parameters', {}),
                position=i,
                weight=method_config.get('weight', 1.0)
            )
        logger.info(f"Loaded pipeline config with {len(self.methods)} methods")

    def get_available_methods(self) -> Dict:
        """Get dictionary of all available methods with their metadata."""
        return self.AVAILABLE_METHODS.copy()
