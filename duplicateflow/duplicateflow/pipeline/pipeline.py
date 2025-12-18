"""
Pipeline for orchestrating multiple algorithms with weighted scoring.

A Pipeline executes multiple algorithms on the same video pair and combines
their results using weighted averaging.
"""

import logging
from typing import List, Dict, Any, Optional
from tqdm import tqdm
from duplicateflow.core import get_algorithm
from duplicateflow.storage import StorageManager

logger = logging.getLogger('duplicateflow.pipeline')


class Pipeline:
    """
    Multi-algorithm pipeline with weighted scoring.

    Executes multiple algorithms and combines their similarity scores
    using configurable weights. Supports caching via StorageManager.

    Example:
        >>> pipeline = Pipeline([
        ...     {'algorithm': 'frame_hash', 'weight': 0.3, 'threshold': 80},
        ...     {'algorithm': 'color_histogram', 'weight': 0.4, 'threshold': 70},
        ...     {'algorithm': 'motion_analysis', 'weight': 0.3, 'threshold': 70}
        ... ])
        >>>
        >>> result = pipeline.compare('short.mp4', 'long.mp4')
        >>> print(f"Global score: {result['global_score']:.2f}")
        >>> print(f"Accepted: {result['accepted']}")
    """

    def __init__(
        self,
        steps: List[Dict[str, Any]],
        storage: Optional[StorageManager] = None,
        global_threshold: float = 70.0,
        early_termination: bool = True,
        early_termination_margin: float = 10.0,
        show_progress: bool = False
    ):
        """
        Initialize pipeline with algorithm steps.

        Args:
            steps: List of algorithm configurations, each with:
                - algorithm: Algorithm name (str)
                - weight: Weight for scoring (float, sum should be 1.0)
                - threshold: Algorithm threshold (float)
                - params: Optional dict of algorithm parameters
            storage: Optional StorageManager for caching
            global_threshold: Global acceptance threshold (0-100)
            early_termination: Stop if global score exceeds threshold
            early_termination_margin: Margin above threshold for early stop
            show_progress: Show progress bar during execution

        Example steps:
            [
                {
                    'algorithm': 'frame_hash',
                    'weight': 0.3,
                    'threshold': 80,
                    'params': {'hash_method': 'pHash', 'num_samples': 8}
                },
                {
                    'algorithm': 'color_histogram',
                    'weight': 0.7,
                    'threshold': 70
                }
            ]
        """
        self.steps = steps
        self.storage = storage or StorageManager()
        self.global_threshold = global_threshold
        self.early_termination = early_termination
        self.early_termination_margin = early_termination_margin
        self.show_progress = show_progress

        # Validate and normalize weights
        self._validate_steps()

        # Initialize algorithm instances
        self.algorithms = []
        for step in self.steps:
            AlgoClass = get_algorithm(step['algorithm'])
            algo = AlgoClass()

            # Configure with threshold and optional params
            config = {'threshold': step['threshold']}
            if 'params' in step:
                config.update(step['params'])

            algo.configure(**config)
            self.algorithms.append({
                'instance': algo,
                'name': step['algorithm'],
                'weight': step['weight'],
                'threshold': step['threshold']
            })

    def _validate_steps(self):
        """Validate pipeline steps and normalize weights."""
        if not self.steps:
            raise ValueError("Pipeline must have at least one step")

        # Check all required fields
        for step in self.steps:
            if 'algorithm' not in step:
                raise ValueError("Each step must have 'algorithm' field")
            if 'weight' not in step:
                raise ValueError("Each step must have 'weight' field")
            if 'threshold' not in step:
                raise ValueError("Each step must have 'threshold' field")

        # Normalize weights to sum to 1.0
        total_weight = sum(step['weight'] for step in self.steps)
        if total_weight == 0:
            raise ValueError("Total weight cannot be zero")

        for step in self.steps:
            step['weight'] = step['weight'] / total_weight

    def compare(
        self,
        short_video: str,
        long_video: str,
        start_time: Optional[float] = None,
        duration: Optional[float] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Compare two videos using all pipeline algorithms.

        Args:
            short_video: Path to short video
            long_video: Path to long video
            start_time: Optional start time in long video
            duration: Optional duration to search
            use_cache: Use cached results if available

        Returns:
            Dictionary with:
                - global_score: Weighted average similarity (0-100)
                - accepted: Whether global score exceeds threshold
                - individual_results: List of per-algorithm results
                - weights: Weights used for each algorithm
                - metadata: Additional pipeline metadata
        """
        # Check if files are identical (quick duplicate check)
        logger.info(f"Comparing videos: {short_video} vs {long_video}")
        if self.storage.are_files_identical(short_video, long_video, method='fast'):
            logger.info("Files are identical (MD5 match)")
            return {
                'global_score': 100.0,
                'accepted': True,
                'individual_results': [],
                'weights': {},
                'metadata': {
                    'early_exit': True,
                    'reason': 'identical_files'
                }
            }

        individual_results = []
        weighted_sum = 0.0
        total_weight = 0.0

        # Create progress bar if enabled
        algo_iterator = tqdm(self.algorithms, desc="Running algorithms", disable=not self.show_progress) if self.show_progress else self.algorithms

        for algo_info in algo_iterator:
            algo = algo_info['instance']
            name = algo_info['name']
            weight = algo_info['weight']
            threshold = algo_info['threshold']

            # Update progress bar description
            if self.show_progress:
                algo_iterator.set_description(f"Running {name}")

            logger.debug(f"Running algorithm: {name} (threshold={threshold})")

            # Try to get cached result
            result = None
            if use_cache:
                # Get algorithm config for cache key
                config = {'threshold': threshold}
                result = self.storage.get_cached_result(
                    short_video, long_video, name, config
                )
                if result is not None:
                    logger.debug(f"Using cached result for {name}")

            # Run algorithm if not cached
            if result is None:
                logger.debug(f"Computing result for {name}")
                result = algo.compare(
                    short_video=short_video,
                    long_video=long_video,
                    start_time=start_time,
                    duration=duration
                )

                # Cache result
                if use_cache:
                    config = {'threshold': threshold}
                    self.storage.store_result(
                        short_video, long_video, name, config, result
                    )

            # Convert similarity to 0-100 scale if needed
            similarity = result.get('similarity', 0.0)
            if similarity is None:
                similarity = 0.0
            elif similarity <= 1.0:
                similarity = similarity * 100.0

            # Store result
            individual_results.append({
                'algorithm': name,
                'similarity': similarity,
                'accepted': result.get('accepted', False),
                'weight': weight,
                'metadata': result.get('metadata', {})
            })

            # Accumulate weighted score
            weighted_sum += similarity * weight
            total_weight += weight

            # Early termination check
            if self.early_termination and total_weight > 0:
                current_score = weighted_sum / total_weight
                # Handle None values (use defaults)
                threshold = self.global_threshold if self.global_threshold is not None else 70.0
                margin = self.early_termination_margin if self.early_termination_margin is not None else 10.0
                if current_score >= (threshold + margin):
                    # Extrapolate final score
                    global_score = weighted_sum / total_weight
                    logger.info(f"Early termination at {len(individual_results)}/{len(self.algorithms)} algorithms (score={global_score:.2f})")

                    # Use safe threshold
                    threshold_safe = self.global_threshold if self.global_threshold is not None else 70.0
                    return {
                        'global_score': global_score,
                        'accepted': global_score >= threshold_safe,
                        'individual_results': individual_results,
                        'weights': {r['algorithm']: r['weight'] for r in individual_results},
                        'metadata': {
                            'early_exit': True,
                            'algorithms_run': len(individual_results),
                            'total_algorithms': len(self.algorithms)
                        }
                    }

        # Calculate final global score
        global_score = weighted_sum / total_weight if total_weight > 0 else 0.0
        # Use safe threshold (handle None)
        threshold_safe = self.global_threshold if self.global_threshold is not None else 70.0
        logger.info(f"Pipeline complete: score={global_score:.2f}, accepted={global_score >= threshold_safe}")

        return {
            'global_score': global_score,
            'accepted': global_score >= threshold_safe,
            'individual_results': individual_results,
            'weights': {r['algorithm']: r['weight'] for r in individual_results},
            'metadata': {
                'early_exit': False,
                'algorithms_run': len(individual_results),
                'total_algorithms': len(self.algorithms)
            }
        }

    def get_config(self) -> Dict[str, Any]:
        """
        Get pipeline configuration.

        Returns:
            Dictionary with pipeline configuration
        """
        return {
            'steps': self.steps,
            'global_threshold': self.global_threshold,
            'early_termination': self.early_termination,
            'early_termination_margin': self.early_termination_margin,
            'num_algorithms': len(self.algorithms)
        }

    @classmethod
    def from_preset(cls, preset_name: str, **kwargs) -> 'Pipeline':
        """
        Create pipeline from preset configuration.

        Args:
            preset_name: Preset name ('fast', 'balanced', 'thorough', 'multimodal')
            **kwargs: Additional parameters to override

        Returns:
            Configured Pipeline instance
        """
        from duplicateflow.pipeline.presets import get_preset

        preset_config = get_preset(preset_name)

        # Override with kwargs
        if 'global_threshold' in kwargs:
            preset_config['global_threshold'] = kwargs['global_threshold']
        if 'early_termination' in kwargs:
            preset_config['early_termination'] = kwargs['early_termination']

        return cls(**preset_config)
