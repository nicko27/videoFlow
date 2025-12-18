"""
Main adapter for integrating duplicateFlow into duplicate_finder.

This adapter provides a clean interface between duplicate_finder's GUI
and duplicateFlow's backend, handling:
- API translation
- Result format conversion
- Progress callback bridging
- Error handling
"""

import sys
import logging
import os
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path

# Configure duplicateFlow path
def _get_duplicateflow_path() -> Path:
    """
    Get the duplicateFlow installation path.

    Tries multiple strategies:
    1. Environment variable DUPLICATEFLOW_PATH
    2. Installed package (if in PYTHONPATH)
    3. Sibling directory (development mode)

    Returns:
        Path to duplicateFlow directory
    """
    # Strategy 1: Environment variable
    if 'DUPLICATEFLOW_PATH' in os.environ:
        path = Path(os.environ['DUPLICATEFLOW_PATH'])
        if path.exists():
            return path

    # Strategy 2: Try to import directly (already in PYTHONPATH)
    try:
        import duplicateflow
        if duplicateflow.__file__:
            return Path(duplicateflow.__file__).parent.parent
    except (ImportError, AttributeError, TypeError):
        pass

    # Strategy 3: Sibling directory (development mode)
    project_root = Path(__file__).parents[4]
    duplicateflow_path = project_root / "duplicateflow"
    if duplicateflow_path.exists():
        return duplicateflow_path

    # Strategy 4: Parent directory
    parent_duplicateflow = project_root.parent / "duplicateflow"
    if parent_duplicateflow.exists():
        return parent_duplicateflow

    raise ImportError(
        f"Could not locate duplicateFlow. Tried:\n"
        f"  1. Environment variable DUPLICATEFLOW_PATH\n"
        f"  2. Python PYTHONPATH\n"
        f"  3. Project sibling: {duplicateflow_path}\n"
        f"  4. Parent directory: {parent_duplicateflow}\n"
        f"Please install duplicateFlow or set DUPLICATEFLOW_PATH"
    )

# Add duplicateFlow to Python path if needed
try:
    DUPLICATEFLOW_PATH = _get_duplicateflow_path()
    if str(DUPLICATEFLOW_PATH) not in sys.path:
        sys.path.insert(0, str(DUPLICATEFLOW_PATH))

    # Import duplicateFlow and verify version
    from duplicateflow import get_preset, list_presets, __version__ as DUPLICATEFLOW_VERSION
    # Import algorithms to trigger auto-registration
    import duplicateflow.algorithms

    DUPLICATEFLOW_AVAILABLE = True
    IMPORT_ERROR = None

    # Log successful import
    logging.getLogger('DuplicateFinder.Adapter').info(
        f"duplicateFlow loaded successfully from {DUPLICATEFLOW_PATH} (version {DUPLICATEFLOW_VERSION})"
    )

except ImportError as e:
    DUPLICATEFLOW_AVAILABLE = False
    DUPLICATEFLOW_VERSION = None
    IMPORT_ERROR = str(e)
    DUPLICATEFLOW_PATH = None

    logging.getLogger('DuplicateFinder.Adapter').warning(
        f"duplicateFlow not available: {IMPORT_ERROR}"
    )

logger = logging.getLogger('DuplicateFinder.Adapter')


class DuplicateFlowAdapter:
    """
    Adapter for using duplicateFlow from duplicate_finder GUI.

    This class provides a simplified, GUI-friendly interface to duplicateFlow's
    functionality, handling all the complexity of format conversion and
    progress tracking.

    Example:
        >>> adapter = DuplicateFlowAdapter()
        >>> result = adapter.compare_videos(
        ...     'video1.mp4',
        ...     'video2.mp4',
        ...     preset='balanced'
        ... )
        >>> print(f"Similarity: {result['similarity']:.1f}%")
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize adapter.

        Args:
            db_path: Optional path to duplicateFlow storage database.
                    If None, uses default location.

        Raises:
            ImportError: If duplicateFlow is not available
        """
        if not DUPLICATEFLOW_AVAILABLE:
            raise ImportError(
                f"duplicateFlow is not available: {IMPORT_ERROR}\n"
                f"Please ensure duplicateFlow is in PYTHONPATH:\n"
                f"  export PYTHONPATH=\"{DUPLICATEFLOW_PATH}:$PYTHONPATH\""
            )

        self.db_path = db_path
        logger.info("DuplicateFlowAdapter initialized")

    # ================================================================
    # MAIN COMPARISON METHODS
    # ================================================================

    def compare_videos_with_pipeline(
        self,
        video1: str,
        video2: str,
        pipeline_config: Dict[str, Any],
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> Dict[str, Any]:
        """
        Compare two videos using a custom pipeline configuration.

        This method allows using pipeline configurations from the database
        instead of hardcoded presets.

        Args:
            video1: Path to first video
            video2: Path to second video
            pipeline_config: Custom pipeline configuration with:
                - mode: 'filtering', 'weighting', 'hybrid', or 'staged'
                - methods: List of algorithm configs (from DB methods_json)
                - global_threshold: Global acceptance threshold (0-100)
                - confirmation: Optional confirmation config
            progress_callback: Optional callback(stage, current, total)

        Returns:
            Same format as compare_videos()

        Example:
            >>> pipeline_config = {
            ...     'mode': 'weighting',
            ...     'methods': [
            ...         {'name': 'df_audio_fingerprint', 'weight': 1.0, 'parameters': {'threshold': 200}}
            ...     ],
            ...     'global_threshold': 80.0
            ... }
            >>> result = adapter.compare_videos_with_pipeline(
            ...     'video1.mp4', 'video2.mp4', pipeline_config
            ... )
        """
        try:
            # Extract configuration
            mode = pipeline_config.get('mode', 'weighting')
            global_threshold = pipeline_config.get('global_threshold', 70.0)

            logger.info(f"Comparing {video1} vs {video2} with custom pipeline (mode={mode})")

            # Handle staged mode differently
            if mode == 'staged':
                return self._execute_staged_pipeline(
                    video1, video2, pipeline_config, progress_callback
                )

            # For other modes (filtering, weighting, hybrid), use standard pipeline
            methods = pipeline_config.get('methods', [])

            # Convert DB methods format to DuplicateFlow steps format
            steps = []
            for method in methods:
                if not method.get('enabled', True):
                    continue

                # Extract algorithm name (remove 'df_' prefix if present)
                algo_name = method.get('name', '')
                if algo_name.startswith('df_'):
                    algo_name = algo_name[3:]

                # Get weight and threshold
                weight = method.get('weight', 1.0)
                params = method.get('parameters', {}).copy()
                threshold = params.pop('threshold', 70.0)

                # Create step in DuplicateFlow format
                step = {
                    'algorithm': algo_name,
                    'weight': weight,
                    'threshold': threshold,
                    'params': params
                }
                steps.append(step)

            if not steps:
                logger.warning("No enabled algorithms in pipeline")
                return {
                    'similarity': 0.0,
                    'accepted': False,
                    'confidence': 'none',
                    'metadata': {
                        'error': 'No enabled algorithms',
                        'mode': mode
                    }
                }

            # Create Pipeline
            from duplicateflow.pipeline import Pipeline

            pipeline = Pipeline(
                steps=steps,
                global_threshold=global_threshold,
                early_termination=True,
                early_termination_margin=10.0,
                show_progress=False
            )

            # Run comparison
            # NOTE: Pass start_time=None and duration=None to compare full videos
            # DuplicateFlow algorithms will handle their own windowing internally
            result = pipeline.compare(
                short_video=video1,
                long_video=video2,
                start_time=None,
                duration=None
            )

            # Transform to GUI format
            return self._transform_result(result, f"custom_{mode}")

        except Exception as e:
            logger.error(f"Comparison failed: {e}", exc_info=True)
            return {
                'similarity': 0.0,
                'accepted': False,
                'confidence': 'none',
                'metadata': {
                    'error': str(e),
                    'mode': pipeline_config.get('mode', 'unknown')
                }
            }

    def compare_videos(
        self,
        video1: str,
        video2: str,
        preset: str = 'balanced',
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> Dict[str, Any]:
        """
        Compare two videos using duplicateFlow pipeline.

        This is the main method for 1-to-1 video comparison. It uses
        duplicateFlow's pipeline system to run multiple algorithms and
        combine their results.

        Args:
            video1: Path to first video
            video2: Path to second video
            preset: Pipeline preset name ('fast', 'balanced', 'thorough',
                   'multimodal', 'structural', 'hybrid')
            progress_callback: Optional callback(stage, current, total)

        Returns:
            {
                'similarity': float (0-100),
                'accepted': bool,
                'confidence': str ('high', 'medium', 'low', 'none'),
                'metadata': {
                    'preset': str,
                    'methods_used': list,
                    'individual_scores': dict,
                    ...
                }
            }

        Example:
            >>> result = adapter.compare_videos(
            ...     'short_scene.mp4',
            ...     'long_movie.mp4',
            ...     preset='balanced'
            ... )
            >>> if result['accepted']:
            ...     print(f"Match found! Similarity: {result['similarity']:.1f}%")
        """
        try:
            # Get pipeline preset configuration
            preset_config = get_preset(preset)

            logger.info(f"Comparing {video1} vs {video2} with preset '{preset}'")

            # Create Pipeline from config
            from duplicateflow.pipeline import Pipeline

            pipeline = Pipeline(
                steps=preset_config['steps'],
                global_threshold=preset_config.get('global_threshold', 70.0),
                early_termination=preset_config.get('early_termination', True),
                early_termination_margin=preset_config.get('early_termination_margin', 10.0),
                show_progress=False  # We handle progress via callback
            )

            # Create progress wrapper if callback provided
            def progress_wrapper(stage: str, current: int, total: int):
                if progress_callback:
                    try:
                        progress_callback(stage, current, total)
                    except Exception as e:
                        logger.warning(f"Progress callback error: {e}")

            # Run comparison
            result = pipeline.compare(
                video1,
                video2
            )

            # Transform to GUI format
            return self._transform_result(result, preset)

        except Exception as e:
            logger.error(f"Comparison failed: {e}", exc_info=True)
            return {
                'similarity': 0.0,
                'accepted': False,
                'confidence': 'none',
                'metadata': {
                    'error': str(e),
                    'preset': preset
                }
            }

    def compare_many_to_one(
        self,
        short_videos: List[str],
        long_video: str,
        preset: str = 'balanced',
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        Compare multiple short videos against one long video.

        Useful for finding which scenes appear in a movie.

        Args:
            short_videos: List of short video paths
            long_video: Path to long video
            preset: Pipeline preset
            progress_callback: Progress callback

        Returns:
            List of comparison results (one per short video)
        """
        results = []

        for i, short_video in enumerate(short_videos):
            # Progress: comparing video i of n
            if progress_callback:
                progress_callback('comparing', i, len(short_videos))

            result = self.compare_videos(
                short_video,
                long_video,
                preset=preset,
                progress_callback=None  # Don't nest callbacks
            )

            result['metadata']['short_video'] = short_video
            result['metadata']['long_video'] = long_video
            results.append(result)

        if progress_callback:
            progress_callback('completed', len(short_videos), len(short_videos))

        return results

    # ================================================================
    # STAGED PIPELINE EXECUTION
    # ================================================================

    def _execute_staged_pipeline(
        self,
        video1: str,
        video2: str,
        pipeline_config: Dict[str, Any],
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> Dict[str, Any]:
        """
        Execute a staged pipeline with windowing optimization.

        Staged pipelines have multiple stages:
        1. Localization stage: Fast algorithms find temporal offset
        2. Verification stages: Discriminant algorithms verify in narrow window
        3. Optional confirmation: pHash visual verification

        Args:
            video1: Path to first video (typically shorter)
            video2: Path to second video (typically longer)
            pipeline_config: Staged pipeline configuration
            progress_callback: Progress callback

        Returns:
            Result dictionary with global_score, accepted, metadata
        """
        from duplicateflow.core import get_algorithm

        try:
            stages = pipeline_config.get('stages', [])
            global_threshold = pipeline_config.get('global_threshold', 70.0)
            confirmation = pipeline_config.get('confirmation', {'enabled': False})

            if not stages:
                logger.warning("No stages in staged pipeline")
                return {
                    'similarity': 0.0,
                    'accepted': False,
                    'confidence': 'none',
                    'metadata': {'error': 'No stages configured'}
                }

            # Results from all stages
            all_stage_results = []
            detected_offset = None  # Time offset from localization stage
            short_duration = None

            # Execute each stage
            for stage_idx, stage in enumerate(stages):
                stage_name = stage.get('name', f'stage_{stage_idx}')
                stage_type = stage.get('type', 'localization')
                algorithms = stage.get('algorithms', [])

                logger.info(f"Executing stage '{stage_name}' (type={stage_type}, {len(algorithms)} algorithms)")

                # Determine time window for this stage
                start_time = None
                duration = None

                if stage_type == 'verification' and detected_offset is not None:
                    # Use window from previous localization stage
                    window_config = stage.get('window_config', {})
                    margin_before = window_config.get('margin_before', 30)
                    margin_after = window_config.get('margin_after', 30)

                    start_time = max(0, detected_offset - margin_before)
                    duration = (short_duration if short_duration else 60) + margin_before + margin_after

                    logger.info(
                        f"Stage '{stage_name}' using window: "
                        f"{start_time:.1f}s - {start_time + duration:.1f}s"
                    )

                # Execute algorithms in this stage
                stage_results = []
                for algo_config in algorithms:
                    if not algo_config.get('enabled', True):
                        continue

                    # Extract algorithm info
                    algo_name = algo_config.get('name', '')
                    if algo_name.startswith('df_'):
                        algo_name = algo_name[3:]

                    weight = algo_config.get('weight', 1.0)
                    params = algo_config.get('parameters', {}).copy()
                    threshold = params.pop('threshold', 70.0)

                    # Get algorithm class and create instance
                    AlgoClass = get_algorithm(algo_name)
                    algo = AlgoClass()
                    algo.configure(threshold=threshold, **params)

                    # Run comparison
                    result = algo.compare(
                        short_video=video1,
                        long_video=video2,
                        start_time=start_time,
                        duration=duration
                    )

                    # Extract offset from localization algorithms
                    if stage_type == 'localization' and detected_offset is None:
                        metadata = result.get('metadata', {})
                        if 'best_offset_seconds' in metadata:
                            detected_offset = metadata['best_offset_seconds']
                            logger.info(f"Detected offset: {detected_offset:.1f}s")

                    # Convert similarity to 0-100 scale if needed
                    similarity = result['similarity']
                    if similarity <= 1.0:
                        similarity = similarity * 100.0

                    stage_results.append({
                        'algorithm': algo_name,
                        'similarity': similarity,
                        'accepted': result['accepted'],
                        'weight': weight,
                        'metadata': result.get('metadata', {})
                    })

                all_stage_results.extend(stage_results)

            # Calculate global score (weighted average across ALL stages)
            weighted_sum = 0.0
            total_weight = 0.0

            for result in all_stage_results:
                weighted_sum += result['similarity'] * result['weight']
                total_weight += result['weight']

            global_score = weighted_sum / total_weight if total_weight > 0 else 0.0
            accepted = global_score >= global_threshold

            # Execute confirmation if enabled and score passed
            confirmation_result = None
            if confirmation.get('enabled') and accepted:
                confirmation_result = self._execute_confirmation(
                    video1, video2,
                    confirmation,
                    detected_offset
                )

                # Override acceptance if confirmation fails
                if not confirmation_result.get('accepted', True):
                    accepted = False
                    logger.info("Pipeline passed but confirmation failed")

            # Build final result
            return {
                'similarity': global_score,
                'accepted': accepted,
                'confidence': self._determine_confidence(global_score),
                'metadata': {
                    'mode': 'staged',
                    'num_stages': len(stages),
                    'detected_offset_seconds': detected_offset,
                    'individual_results': all_stage_results,
                    'confirmation': confirmation_result,
                    'global_threshold': global_threshold
                }
            }

        except Exception as e:
            logger.error(f"Staged pipeline execution failed: {e}", exc_info=True)
            return {
                'similarity': 0.0,
                'accepted': False,
                'confidence': 'none',
                'metadata': {
                    'error': str(e),
                    'mode': 'staged'
                }
            }

    def _execute_confirmation(
        self,
        video1: str,
        video2: str,
        confirmation: Dict[str, Any],
        offset: Optional[float]
    ) -> Dict[str, Any]:
        """
        Execute pHash visual confirmation.

        Args:
            video1: Short video path
            video2: Long video path
            confirmation: Confirmation configuration
            offset: Detected time offset (for windowing)

        Returns:
            Confirmation result dictionary
        """
        try:
            from ..analysis.phash_visual import PHashComparator

            params = confirmation.get('parameters', {})
            phash_threshold = params.get('phash_threshold', 10)
            frame_rate_threshold = params.get('frame_rate_threshold', 0.8)
            n_frames = params.get('n_frames', 10)
            search_window = params.get('search_window', True)

            comparator = PHashComparator(
                phash_threshold=phash_threshold,
                frame_rate_threshold=frame_rate_threshold,
                n_frames=n_frames
            )

            # Extract frames from short video (full video)
            frames1, _ = comparator.extract_frames(video1)

            # Extract frames from long video (windowed if offset available)
            window_start = None
            window_end = None

            if search_window and offset is not None:
                # Get short video duration
                import cv2
                cap = cv2.VideoCapture(video1)
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                short_duration = frame_count / fps if fps > 0 else 60
                cap.release()

                # Create window around detected offset
                margin = 30  # seconds
                window_start = max(0, offset - margin)
                window_end = offset + short_duration + margin

                logger.info(f"pHash confirmation in window: {window_start:.1f}s - {window_end:.1f}s")

            frames2, _ = comparator.extract_frames(video2, window_start, window_end)

            # Compare frames
            if not frames1 or not frames2:
                return {
                    'accepted': False,
                    'similarity': 0.0,
                    'error': 'Failed to extract frames'
                }

            # Compute pHash signatures
            hashes1 = [comparator.compute_phash(f) for f in frames1]
            hashes2 = [comparator.compute_phash(f) for f in frames2]

            # Compare all pairs and find best matches
            similar_count = 0
            for h1 in hashes1:
                best_distance = min(comparator.hamming_distance(h1, h2) for h2 in hashes2)
                if best_distance <= phash_threshold:
                    similar_count += 1

            similarity_ratio = similar_count / len(hashes1) if hashes1 else 0.0
            accepted = similarity_ratio >= frame_rate_threshold

            return {
                'accepted': accepted,
                'similarity': similarity_ratio * 100,
                'similar_frames': similar_count,
                'total_frames': len(hashes1),
                'frame_rate': similarity_ratio
            }

        except Exception as e:
            logger.error(f"Confirmation failed: {e}", exc_info=True)
            return {
                'accepted': False,
                'similarity': 0.0,
                'error': str(e)
            }

    def _determine_confidence(self, score: float) -> str:
        """Determine confidence level from score."""
        if score >= 85:
            return 'high'
        elif score >= 70:
            return 'medium'
        elif score >= 50:
            return 'low'
        else:
            return 'none'

    # ================================================================
    # PIPELINE & PRESET MANAGEMENT
    # ================================================================

    def list_presets(self) -> List[Dict[str, Any]]:
        """
        List available pipeline presets.

        Returns:
            [
                {
                    'name': 'fast',
                    'display_name': 'Fast (~30s pour 1h)',
                    'description': '3 algorithmes légers',
                    'icon': '⚡',
                    'estimated_time': 30,
                    'algorithms_count': 3
                },
                ...
            ]
        """
        preset_names = list_presets()

        # Enhanced metadata for UI
        preset_info = {
            'fast': {
                'display_name': 'Fast (~30s pour 1h)',
                'description': '3 algorithmes légers',
                'icon': '⚡',
                'estimated_time': 30,
                'use_case': 'Détection rapide de doublons exacts'
            },
            'balanced': {
                'display_name': 'Balanced (~2min pour 1h)',
                'description': '4 algorithmes équilibrés',
                'icon': '⚖️',
                'estimated_time': 120,
                'use_case': 'Bon compromis vitesse/précision'
            },
            'thorough': {
                'display_name': 'Thorough (~5min pour 1h)',
                'description': '5 algorithmes précis',
                'icon': '🔬',
                'estimated_time': 300,
                'use_case': 'Détection précise avec variations'
            },
            'multimodal': {
                'display_name': 'Multimodal (~8min pour 1h)',
                'description': 'Audio + vidéo',
                'icon': '🎵',
                'estimated_time': 480,
                'use_case': 'Matching audio ET visuel'
            },
            'structural': {
                'display_name': 'Structural',
                'description': 'Focus structures visuelles',
                'icon': '🏗️',
                'estimated_time': 240,
                'use_case': 'Scènes similaires (angles différents)'
            },
            'hybrid': {
                'display_name': 'Hybrid (sous-séquences)',
                'description': 'Détection 20min-1h',
                'icon': '🎬',
                'estimated_time': 600,
                'use_case': 'Trouver scènes longues dans films'
            }
        }

        presets = []
        for name in preset_names:
            info = preset_info.get(name, {
                'display_name': name.title(),
                'description': f'Preset {name}',
                'icon': '🔧',
                'estimated_time': 180,
                'use_case': 'Usage général'
            })

            presets.append({
                'name': name,
                **info
            })

        return presets

    def get_preset_info(self, preset_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a preset.

        Args:
            preset_name: Name of preset

        Returns:
            Preset information dict
        """
        presets = self.list_presets()
        for preset in presets:
            if preset['name'] == preset_name:
                return preset

        return {
            'name': preset_name,
            'display_name': preset_name.title(),
            'description': 'Unknown preset',
            'icon': '❓'
        }

    # ================================================================
    # UTILITIES
    # ================================================================

    def _transform_result(
        self,
        result: Dict[str, Any],
        preset: str
    ) -> Dict[str, Any]:
        """
        Transform duplicateFlow pipeline result to GUI format.

        Args:
            result: Pipeline result dict from duplicateFlow
            preset: Preset name used

        Returns:
            GUI-friendly result dict
        """
        # Extract global score
        global_score = result.get('global_score', 0.0)

        # Determine acceptance (use pipeline's accepted value)
        accepted = result.get('accepted', False)

        # Determine confidence level
        if global_score >= 85:
            confidence = 'high'
        elif global_score >= 70:
            confidence = 'medium'
        elif global_score >= 50:
            confidence = 'low'
        else:
            confidence = 'none'

        # Extract individual algorithm results
        individual_results = result.get('individual_results', [])
        method_results = {}
        methods_used = []

        for algo_result in individual_results:
            algo_name = algo_result.get('algorithm', 'unknown')
            methods_used.append(algo_name)
            method_results[algo_name] = {
                'score': algo_result.get('similarity', 0.0),
                'accepted': algo_result.get('accepted', False),
                'weight': algo_result.get('weight', 0.0),
                'metadata': algo_result.get('metadata', {})
            }

        return {
            'similarity': global_score,
            'accepted': accepted,
            'confidence': confidence,
            'metadata': {
                'preset': preset,
                'methods_used': methods_used,
                'individual_scores': method_results,
                'weights': result.get('weights', {}),
                'pipeline_metadata': result.get('metadata', {}),
                'num_algorithms': len(individual_results)
            }
        }

    def check_availability(self) -> Dict[str, Any]:
        """
        Check duplicateFlow availability and version.

        Returns:
            {
                'available': bool,
                'version': str,
                'presets': list,
                'error': str (if not available)
            }
        """
        if not DUPLICATEFLOW_AVAILABLE:
            return {
                'available': False,
                'version': None,
                'presets': [],
                'error': IMPORT_ERROR
            }

        try:
            import duplicateflow
            return {
                'available': True,
                'version': duplicateflow.__version__,
                'presets': list_presets(),
                'error': None
            }
        except Exception as e:
            return {
                'available': False,
                'version': None,
                'presets': [],
                'error': str(e)
            }

    def __repr__(self) -> str:
        """String representation."""
        status = "available" if DUPLICATEFLOW_AVAILABLE else "unavailable"
        return f"<DuplicateFlowAdapter status={status}>"


# Convenience function for quick checks
def check_duplicateflow() -> bool:
    """
    Quick check if duplicateFlow is available.

    Returns:
        True if duplicateFlow can be imported, False otherwise
    """
    return DUPLICATEFLOW_AVAILABLE


if __name__ == "__main__":
    # Quick test
    print("Testing DuplicateFlowAdapter...")
    print(f"duplicateFlow available: {DUPLICATEFLOW_AVAILABLE}")

    if DUPLICATEFLOW_AVAILABLE:
        adapter = DuplicateFlowAdapter()
        print(f"Adapter: {adapter}")

        presets = adapter.list_presets()
        print(f"\nAvailable presets: {len(presets)}")
        for preset in presets:
            print(f"  - {preset['icon']} {preset['display_name']}")
    else:
        print(f"Error: {IMPORT_ERROR}")
