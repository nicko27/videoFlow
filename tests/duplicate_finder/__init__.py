"""
Test suite for DuplicateFinder plugin.

This package contains comprehensive tests for the VideoFlow DuplicateFinder plugin,
including integration tests with DuplicateFlow library.

Structure:
    - test_imports.py: Import validation tests
    - test_database.py: VideoDatabase tests
    - test_file_handler.py: FileHandler tests
    - test_hash_worker.py: ParallelHashWorker tests
    - test_subsequence_detector.py: SubsequenceDetector tests
    - test_pipeline_manager.py: PipelineManager tests
    - test_duplicateflow_integration.py: DuplicateFlow integration tests
    - test_ui_basic.py: UI tests (with mocks)
    - test_critical_errors.py: Critical error regression tests
    - conftest.py: pytest fixtures and configuration
"""

__version__ = "1.0.0"
