"""
Verification Pipeline - DuplicateFlow Facade

This module provides a simplified facade to DuplicateFlow's pipeline system.
All algorithm execution is delegated to DuplicateFlow via the DuplicateFlowAdapter.

Example Usage:
    pipeline = VerificationPipeline(db_manager=db)

    # Configure pipeline with ordered methods
    pipeline.add_method('audio_fingerprint', enabled=True, parameters={'threshold': 85.0})
    pipeline.add_method('dct_coefficients', enabled=True, parameters={'threshold': 75.0})
    pipeline.add_method('motion_analysis', enabled=True, parameters={'threshold': 85.0})

    # Run pipeline (delegates to DuplicateFlow)
    result = pipeline.verify(short_video, long_video, start_time, duration)

    # Get configuration
    config = pipeline.get_config()
"""

import time
import json
import hashlib
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from src.core.logger import Logger

# Import DuplicateFlow integration
from .integration import (
    DUPLICATEFLOW_AVAILABLE,
    get_all_algorithms_dict,
    is_duplicateflow_algorithm,
)
from .adapters.duplicateflow_adapter import DuplicateFlowAdapter

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
    Configurable verification pipeline that delegates to DuplicateFlow.

    This class is a facade that converts duplicate_finder's pipeline
    configuration format into DuplicateFlow's native format and delegates
    all execution to DuplicateFlow.
    """

    # Available verification methods - loaded dynamically from DuplicateFlow
    # This is a cached dict for backward compatibility. Use get_available_methods() for fresh data.
    AVAILABLE_METHODS = {}

    # Load DuplicateFlow algorithms if available
    if DUPLICATEFLOW_AVAILABLE:
        AVAILABLE_METHODS = get_all_algorithms_dict()
        logger.info(f"✅ Loaded {len(AVAILABLE_METHODS)} DuplicateFlow algorithms")
    else:
        logger.warning("⚠️ DuplicateFlow not available - pipeline will not function")

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
            max_workers: Number of parallel workers (unused, kept for compatibility)
            enable_caching: Whether to cache results in database
            mode: Pipeline mode - 'filtering', 'weighting', or 'hybrid'
        """
        self.db = db_manager
        self.max_workers = max_workers
        self.enable_caching = enable_caching
        self.mode = mode

        # Pipeline configuration (ordered list of methods)
        self.methods: List[PipelineMethod] = []

        # Initialize DuplicateFlow adapter
        self.adapter = DuplicateFlowAdapter() if DUPLICATEFLOW_AVAILABLE else None

        logger.info(f"VerificationPipeline initialized with mode={mode}")

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
            enabled: Whether this method is enabled
            parameters: Method-specific parameters
            position: Position to insert at (None = append)
            weight: Method weight for weighting/hybrid modes

        Returns:
            True if method was added successfully
        """
        if method_name not in self.AVAILABLE_METHODS:
            logger.warning(f"Unknown method: {method_name}")
            return False

        if parameters is None:
            # Use default parameters from algorithm metadata
            parameters = self.AVAILABLE_METHODS[method_name].get('default_params', {}).copy()

        method = PipelineMethod(
            name=method_name,
            enabled=enabled,
            parameters=parameters,
            order=len(self.methods) if position is None else position,
            weight=weight
        )

        if position is None:
            self.methods.append(method)
        else:
            self.methods.insert(position, method)

        logger.debug(f"Added method: {method_name} (enabled={enabled}, weight={weight})")
        return True

    def verify(
        self,
        short_video: str,
        long_video: str,
        start_time: float = 0.0,
        duration: Optional[float] = None,
        sequence_score: Optional[float] = None
    ) -> Dict:
        """
        Execute verification pipeline via DuplicateFlow.

        Args:
            short_video: Path to short video
            long_video: Path to long video
            start_time: Start time in long video (seconds)
            duration: Duration to analyze (seconds)
            sequence_score: Pre-existing sequence score (compatibility param, unused)

        Returns:
            {
                'accepted': bool,
                'similarity': float,
                'confidence': str,
                'methods_executed': int,
                'method_results': list,
                'final_scores': dict,
                'execution_time': float,
                'rejection_reason': str (if rejected),
                'config_hash': str
            }
        """
        if not DUPLICATEFLOW_AVAILABLE or self.adapter is None:
            logger.error("DuplicateFlow not available - cannot verify")
            return {
                'accepted': False,
                'similarity': 0.0,
                'confidence': 'none',
                'methods_executed': 0,
                'method_results': [],
                'final_scores': {},
                'execution_time': 0.0,
                'rejection_reason': 'DuplicateFlow not available',
                'config_hash': ''
            }

        # Generate config hash for caching
        config_hash = self._compute_config_hash()

        # Check cache if enabled
        if self.enable_caching and self.db:
            cached = self._check_cache(short_video, long_video, start_time, config_hash)
            if cached:
                logger.info("✓ Using cached pipeline result")
                return cached

        # Build DuplicateFlow pipeline config
        pipeline_config = self._build_duplicateflow_config()

        # Execute via DuplicateFlow
        start = time.time()
        df_result = self.adapter.compare_videos_with_pipeline(
            video1=short_video,
            video2=long_video,
            pipeline_config=pipeline_config
        )
        execution_time = time.time() - start

        # Transform DuplicateFlow result to duplicate_finder format
        result = self._transform_result(df_result, execution_time, config_hash)

        # Cache result if enabled
        if self.enable_caching and self.db and result['accepted']:
            self._cache_result(short_video, long_video, start_time, result, config_hash)

        return result

    def _build_duplicateflow_config(self) -> Dict:
        """Build DuplicateFlow pipeline configuration from methods."""
        methods_config = []

        for method in self.methods:
            if not method.enabled:
                continue

            methods_config.append({
                'name': method.name,
                'enabled': True,
                'weight': method.weight,
                'parameters': method.parameters.copy()
            })

        # Get global threshold (use first method's threshold or default)
        global_threshold = 70.0
        if self.methods:
            first_params = self.methods[0].parameters
            global_threshold = first_params.get('threshold', 70.0)

        return {
            'mode': self.mode,
            'methods': methods_config,
            'global_threshold': global_threshold
        }

    def _transform_result(self, df_result: Dict, execution_time: float, config_hash: str) -> Dict:
        """Transform DuplicateFlow result to duplicate_finder format."""
        method_results = []
        final_scores = {}

        # Extract individual algorithm results
        individual_results = df_result.get('metadata', {}).get('individual_results', [])

        for algo_result in individual_results:
            method_results.append({
                'method_name': algo_result.get('algorithm', 'unknown'),
                'accepted': algo_result.get('accepted', False),
                'similarity': algo_result.get('similarity', 0.0),
                'weight': algo_result.get('weight', 1.0),
                'metadata': algo_result.get('metadata', {})
            })

            # Add scores to final_scores
            algo_name = algo_result.get('algorithm', 'unknown')
            final_scores[f'{algo_name}_score'] = algo_result.get('similarity', 0.0)

        # Determine rejection reason if rejected
        rejection_reason = None
        if not df_result['accepted']:
            if 'error' in df_result.get('metadata', {}):
                rejection_reason = df_result['metadata']['error']
            else:
                rejection_reason = f"Score {df_result['similarity']:.1f} below threshold"

        return {
            'accepted': df_result['accepted'],
            'similarity': df_result['similarity'],
            'confidence': df_result.get('confidence', 'none'),
            'methods_executed': len(method_results),
            'method_results': method_results,
            'final_scores': final_scores,
            'execution_time': execution_time,
            'rejection_reason': rejection_reason,
            'config_hash': config_hash,
            'metadata': df_result.get('metadata', {})
        }

    def _check_cache(self, short_video: str, long_video: str, start_time: float, config_hash: str) -> Optional[Dict]:
        """Check database cache for existing result."""
        try:
            return self.db.get_cached_verification(
                short_video, long_video, start_time, config_hash=config_hash
            )
        except Exception as e:
            logger.warning(f"Cache check failed: {e}")
            return None

    def _cache_result(self, short_video: str, long_video: str, start_time: float, result: Dict, config_hash: str):
        """Cache result in database."""
        try:
            self.db.cache_verification_result(
                short_video, long_video, start_time, result, config_hash=config_hash
            )
        except Exception as e:
            logger.warning(f"Failed to cache result: {e}")

    def _compute_config_hash(self) -> str:
        """Compute hash of current pipeline configuration."""
        config_str = json.dumps(self.get_config(), sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()[:8]

    def get_config(self) -> Dict:
        """
        Get current pipeline configuration.

        Returns:
            {
                'mode': str,
                'methods': [
                    {
                        'name': str,
                        'enabled': bool,
                        'parameters': dict,
                        'weight': float,
                        'order': int
                    },
                    ...
                ]
            }
        """
        return {
            'mode': self.mode,
            'methods': [
                {
                    'name': m.name,
                    'enabled': m.enabled,
                    'parameters': m.parameters.copy(),
                    'weight': m.weight,
                    'order': m.order
                }
                for m in self.methods
            ]
        }

    def get_available_methods(self) -> Dict[str, Dict]:
        """Get dictionary of all available methods (fresh from DuplicateFlow)."""
        if DUPLICATEFLOW_AVAILABLE:
            return get_all_algorithms_dict()
        return {}

    # Compatibility methods for existing code

    def clear_methods(self):
        """Remove all methods from pipeline."""
        self.methods.clear()
        logger.debug("Pipeline methods cleared")

    def remove_method(self, method_name: str) -> bool:
        """Remove a method from the pipeline."""
        for i, method in enumerate(self.methods):
            if method.name == method_name:
                self.methods.pop(i)
                logger.debug(f"Removed method: {method_name}")
                return True
        return False

    def move_method(self, from_index: int, to_index: int):
        """Move a method from one position to another."""
        if 0 <= from_index < len(self.methods) and 0 <= to_index < len(self.methods):
            method = self.methods.pop(from_index)
            self.methods.insert(to_index, method)
            logger.debug(f"Moved method from {from_index} to {to_index}")

    def set_mode(self, mode: str):
        """Set pipeline mode."""
        if mode in [self.MODE_FILTERING, self.MODE_WEIGHTING, self.MODE_HYBRID]:
            self.mode = mode
            logger.info(f"Pipeline mode set to: {mode}")
        else:
            logger.warning(f"Invalid mode: {mode}")

    def __repr__(self) -> str:
        """String representation."""
        return f"<VerificationPipeline mode={self.mode} methods={len(self.methods)}>"
