"""
Pipeline for orchestrating multiple algorithms with weighted scoring.

A Pipeline executes multiple algorithms on the same video pair and combines
their results using weighted averaging. Supports optional validation steps
for pre-filtering or post-verification.
"""

import logging
from typing import List, Dict, Any, Optional
from tqdm import tqdm
from duplicateflow.core import get_algorithm
from duplicateflow.storage import StorageManager
from duplicateflow.sdk.validator import Validator

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
        show_progress: bool = False,
        pre_validators: Optional[List[Validator]] = None,
        post_validators: Optional[List[Validator]] = None,
        validation_mode: str = 'all',
        analyze_duration: Optional[float] = None,
        analyze_from_start: bool = True
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
            pre_validators: Optional list of validators to run BEFORE comparison
                           (e.g., LengthValidator to filter by duration)
            post_validators: Optional list of validators to run AFTER comparison
                            (e.g., scene boundary validation)
            validation_mode: How to handle multiple validators:
                - 'all': All validators must pass (AND logic)
                - 'any': At least one validator must pass (OR logic)
            analyze_duration: Optional duration limit for video analysis (seconds)
                - None: Analyze full videos (default)
                - float: Only analyze first N seconds of each video
                - Useful for duplicate detection (vs scene detection)
            analyze_from_start: If True, analyze from start of video (default)
                              If False, analyze from end of video

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

        Example with validators:
            >>> from duplicateflow.sdk import LengthValidator
            >>> pipeline = Pipeline(
            ...     steps=[...],
            ...     pre_validators=[
            ...         LengthValidator(tolerance_percent=5.0, tolerance_seconds=30.0)
            ...     ]
            ... )

        Example with partial analysis (duplicates mode):
            >>> # Only analyze first 60 seconds for duplicate detection
            >>> pipeline = Pipeline(
            ...     steps=[...],
            ...     analyze_duration=60.0,  # Analyze first 60 seconds only
            ...     analyze_from_start=True
            ... )
        """
        self.steps = steps
        self.storage = storage or StorageManager()
        self.global_threshold = global_threshold
        self.early_termination = early_termination
        self.early_termination_margin = early_termination_margin
        self.show_progress = show_progress
        self.validation_mode = validation_mode
        self.analyze_duration = analyze_duration
        self.analyze_from_start = analyze_from_start

        # Convert validator dicts to instances if needed
        self.pre_validators = self._initialize_validators(pre_validators or [])
        self.post_validators = self._initialize_validators(post_validators or [])

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

    def _initialize_validators(self, validators: List) -> List[Validator]:
        """
        Initialize validators from list of dicts or instances.

        Args:
            validators: List of Validator instances or dicts with 'type' and 'config'

        Returns:
            List of Validator instances
        """
        initialized = []

        for validator in validators:
            # If already a Validator instance, use it directly
            if isinstance(validator, Validator):
                initialized.append(validator)
            # If dict with 'type' and 'config', instantiate
            elif isinstance(validator, dict):
                validator_type = validator.get('type')
                validator_config = validator.get('config', {})

                if not validator_type:
                    raise ValueError("Validator dict must have 'type' field")

                # Import and instantiate the validator class
                if validator_type == 'LengthValidator':
                    from duplicateflow.sdk.validator import LengthValidator
                    initialized.append(LengthValidator(**validator_config))
                else:
                    raise ValueError(f"Unknown validator type: {validator_type}")
            else:
                raise TypeError(f"Validator must be Validator instance or dict, got {type(validator)}")

        return initialized

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

    def _run_validators(
        self,
        validators: List[Validator],
        video1: str,
        video2: str,
        result: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, List[Dict[str, Any]]]:
        """
        Run a list of validators.

        Args:
            validators: List of Validator instances
            video1: Path to first video
            video2: Path to second video
            result: Optional comparison result (for post-validators)

        Returns:
            Tuple of (all_valid, metadata_list):
            - all_valid: True if validation passed according to validation_mode
            - metadata_list: List of metadata dicts from each validator
        """
        if not validators:
            return True, []

        validation_results = []
        metadata_list = []

        for validator in validators:
            try:
                is_valid, metadata = validator.validate(video1, video2, result)
                validation_results.append(is_valid)
                metadata_list.append({
                    'validator': validator.__class__.__name__,
                    'passed': is_valid,
                    'metadata': metadata
                })
                logger.debug(f"Validator {validator.__class__.__name__}: {'PASS' if is_valid else 'FAIL'}")
            except Exception as e:
                logger.error(f"Validator {validator.__class__.__name__} failed: {e}")
                validation_results.append(False)
                metadata_list.append({
                    'validator': validator.__class__.__name__,
                    'passed': False,
                    'metadata': {'error': str(e)}
                })

        # Apply validation mode logic
        if self.validation_mode == 'all':
            all_valid = all(validation_results)
        elif self.validation_mode == 'any':
            all_valid = any(validation_results)
        else:
            raise ValueError(f"Invalid validation_mode: {self.validation_mode}")

        return all_valid, metadata_list

    def _compute_analysis_params(
        self,
        video_path: str,
        requested_start: Optional[float],
        requested_duration: Optional[float]
    ) -> tuple[float, Optional[float]]:
        """
        Compute effective start_time and duration based on analyze_duration setting.

        Args:
            video_path: Path to video
            requested_start: User-requested start time (or None)
            requested_duration: User-requested duration (or None)

        Returns:
            Tuple of (start_time, duration) to use for analysis
        """
        # If no analyze_duration limit, use requested params
        if self.analyze_duration is None:
            return requested_start or 0.0, requested_duration

        # Get video duration if needed
        import cv2
        cap = cv2.VideoCapture(video_path)
        try:
            if not cap.isOpened():
                # Fallback: use requested params
                return requested_start or 0.0, requested_duration

            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            video_duration = frame_count / fps if fps > 0 else None
        finally:
            cap.release()

        if video_duration is None:
            # Fallback: use requested params
            return requested_start or 0.0, requested_duration

        # Apply analyze_duration limit
        if self.analyze_from_start:
            # Analyze from start
            start_time = requested_start or 0.0
            effective_duration = min(self.analyze_duration, video_duration - start_time)
        else:
            # Analyze from end
            start_time = max(0.0, video_duration - self.analyze_duration)
            effective_duration = min(self.analyze_duration, video_duration)

        # If user requested a shorter duration, use that
        if requested_duration is not None:
            effective_duration = min(effective_duration, requested_duration)

        return start_time, effective_duration

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

        Note:
            If analyze_duration is set, the effective analysis window will be
            limited to the first (or last) N seconds of each video, overriding
            the duration parameter if necessary.
        """
        # Compute effective analysis parameters based on analyze_duration
        if self.analyze_duration is not None:
            short_start, short_duration = self._compute_analysis_params(
                short_video, 0.0, None
            )
            long_start, long_duration = self._compute_analysis_params(
                long_video, start_time, duration
            )
            # Use computed values
            start_time = long_start
            duration = long_duration
            logger.info(f"Partial analysis mode: analyzing {self.analyze_duration}s from {'start' if self.analyze_from_start else 'end'}")
            logger.debug(f"Short video: start={short_start:.1f}s, duration={short_duration}s")
            logger.debug(f"Long video: start={start_time:.1f}s, duration={duration}s")
        # Run pre-validators (before comparison)
        if self.pre_validators:
            logger.info(f"Running {len(self.pre_validators)} pre-validator(s)")
            pre_valid, pre_metadata = self._run_validators(
                self.pre_validators, short_video, long_video, None
            )
            if not pre_valid:
                logger.info("Pre-validation failed, skipping comparison")
                return {
                    'global_score': 0.0,
                    'accepted': False,
                    'individual_results': [],
                    'weights': {},
                    'metadata': {
                        'pre_validation_failed': True,
                        'pre_validation_results': pre_metadata
                    }
                }

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

        # Create initial result
        result = {
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

        # Run post-validators (after comparison)
        if self.post_validators:
            logger.info(f"Running {len(self.post_validators)} post-validator(s)")
            post_valid, post_metadata = self._run_validators(
                self.post_validators, short_video, long_video, result
            )

            # Add post-validation metadata
            result['metadata']['post_validation_results'] = post_metadata

            # If post-validation fails, mark result as not accepted
            if not post_valid:
                logger.info("Post-validation failed, rejecting result")
                result['accepted'] = False
                result['metadata']['post_validation_failed'] = True

        logger.info(f"Pipeline complete: score={global_score:.2f}, accepted={result['accepted']}")

        return result

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
            'num_algorithms': len(self.algorithms),
            'pre_validators': [v.get_metadata() for v in self.pre_validators],
            'post_validators': [v.get_metadata() for v in self.post_validators],
            'validation_mode': self.validation_mode,
            'analyze_duration': self.analyze_duration,
            'analyze_from_start': self.analyze_from_start
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
