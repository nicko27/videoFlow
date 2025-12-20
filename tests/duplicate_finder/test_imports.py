"""
Import validation tests for DuplicateFinder plugin.

This test module verifies that all Python modules in the duplicate_finder plugin
can be imported without errors. It specifically checks for:
- No syntax errors in Python files
- No imports from obsolete/deleted modules (video_hasher, etc.)
- No duplicate imports (e.g., .ui.ui.*)
- All relative imports are correct

CRITICAL ERRORS TESTED:
- CRITICAL ERROR #3: SubsequenceDetector imports VideoHasher (obsolete)
- Import errors from deleted modules

Reference: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md (Migration section)
"""

import ast
import sys
from pathlib import Path
import pytest


@pytest.fixture
def duplicate_finder_files(duplicate_finder_root):
    """Get all Python files in duplicate_finder plugin."""
    return list(duplicate_finder_root.rglob("*.py"))


def test_all_python_files_compile(duplicate_finder_files):
    """
    Verify all Python files in duplicate_finder can be compiled.

    This test catches syntax errors like:
    - CRITICAL ERROR #1: SubsequenceDetector line 666 syntax error

    EXPECTED: FAIL initially due to syntax errors
    """
    errors = []

    for file_path in duplicate_finder_files:
        # Skip __pycache__
        if "__pycache__" in str(file_path):
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
                compile(code, str(file_path), 'exec')
        except SyntaxError as e:
            errors.append(f"{file_path.name}:{e.lineno} - {e.msg}")

    assert not errors, f"Syntax errors found:\n" + "\n".join(errors)


def test_no_obsolete_imports(duplicate_finder_files):
    """
    Verify no imports from obsolete/deleted modules.

    Checks for imports of:
    - video_hasher (DELETED in migration)
    - VideoHasher class (replaced by DuplicateFlow)
    - lru_cache (custom LRU, may be obsolete)
    - frame_cache (obsolete)

    CRITICAL ERROR #3: SubsequenceDetector still imports VideoHasher
    Line 11: from .video_hasher import VideoHasher

    EXPECTED: FAIL initially
    Reference: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md (Migration)
    """
    obsolete_imports = [
        'video_hasher',
        'VideoHasher',
        'lru_cache',
        'frame_cache',
    ]

    errors = []

    for file_path in duplicate_finder_files:
        if "__pycache__" in str(file_path):
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()

            # Parse AST to find imports
            try:
                tree = ast.parse(code)
            except SyntaxError:
                # Syntax errors are caught by test_all_python_files_compile
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for obsolete in obsolete_imports:
                            if obsolete in alias.name:
                                errors.append(
                                    f"{file_path.name}:{node.lineno} - "
                                    f"import {alias.name} (obsolete)"
                                )

                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        for obsolete in obsolete_imports:
                            if obsolete in node.module:
                                errors.append(
                                    f"{file_path.name}:{node.lineno} - "
                                    f"from {node.module} (obsolete module)"
                                )

                    # Check imported names
                    for alias in node.names:
                        for obsolete in obsolete_imports:
                            if obsolete == alias.name:
                                errors.append(
                                    f"{file_path.name}:{node.lineno} - "
                                    f"from ... import {alias.name} (obsolete)"
                                )

        except Exception as e:
            # Skip files that can't be processed
            continue

    assert not errors, f"Obsolete imports found:\n" + "\n".join(errors)


def test_database_manager_imports():
    """
    Test that database_manager.py imports correctly.

    VideoDatabase is the NEW replacement for VideoHasher.
    It should import without errors.

    EXPECTED: PASS (no errors in database_manager.py)
    """
    try:
        from src.plugins.duplicate_finder.database_manager import VideoDatabase
        assert VideoDatabase is not None
    except ImportError as e:
        pytest.fail(f"Failed to import VideoDatabase: {e}")


def test_handlers_imports():
    """
    Test that handlers modules import correctly.

    Handlers should NOT import VideoHasher.

    EXPECTED: PASS if no obsolete imports
    """
    try:
        from src.plugins.duplicate_finder.handlers.file_handler import FileHandler
        from src.plugins.duplicate_finder.handlers.duplicate_handler import DuplicateHandler
        from src.plugins.duplicate_finder.handlers.analysis_handler import AnalysisHandler

        assert FileHandler is not None
        assert DuplicateHandler is not None
        assert AnalysisHandler is not None
    except ImportError as e:
        pytest.fail(f"Failed to import handlers: {e}")


def test_workers_imports():
    """
    Test that workers modules import correctly.

    Workers should use database_manager, NOT video_hasher.

    CRITICAL ERROR #4: ParallelHashWorker may still use video_hasher

    EXPECTED: FAIL if workers still reference VideoHasher
    """
    try:
        from src.plugins.duplicate_finder.workers.hash_worker import ParallelHashWorker
        from src.plugins.duplicate_finder.workers.verification_worker import VerificationWorker

        assert ParallelHashWorker is not None
        assert VerificationWorker is not None
    except ImportError as e:
        pytest.fail(f"Failed to import workers: {e}")


def test_ui_imports():
    """
    Test that UI modules import correctly.

    UI modules may have Qt dependencies, but should at least parse.

    EXPECTED: PASS (UI modules have valid syntax)
    """
    # Test main UI files (without Qt initialization)
    ui_files = [
        'src.plugins.duplicate_finder.ui.panels',
        'src.plugins.duplicate_finder.ui.main_window',
        'src.plugins.duplicate_finder.ui.unified_pipeline_editor_dialog',
    ]

    errors = []
    for module_name in ui_files:
        try:
            # Try to import (may fail if Qt not available, but syntax should be valid)
            __import__(module_name)
        except ImportError as e:
            # Qt import errors are OK, but syntax errors are not
            if "PyQt" not in str(e) and "PySide" not in str(e):
                errors.append(f"{module_name}: {e}")
        except Exception as e:
            errors.append(f"{module_name}: {e}")

    assert not errors, f"UI import errors:\n" + "\n".join(errors)


def test_no_duplicate_ui_imports(duplicate_finder_files):
    """
    Test for duplicate UI imports like .ui.ui.*.

    These can occur from incorrect relative imports.

    EXPECTED: PASS
    """
    errors = []

    for file_path in duplicate_finder_files:
        if "__pycache__" in str(file_path):
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()

            # Check for patterns like .ui.ui or ..ui.ui
            if '.ui.ui' in code:
                # Find line number
                for i, line in enumerate(code.split('\n'), 1):
                    if '.ui.ui' in line:
                        errors.append(
                            f"{file_path.name}:{i} - Duplicate .ui import: {line.strip()}"
                        )

        except Exception as e:
            errors.append(f"{file_path.name}: Error reading file - {e}")

    assert not errors, f"Duplicate UI imports found:\n" + "\n".join(errors)


@pytest.mark.critical
def test_subsequence_detector_no_videohasher_import():
    """
    CRITICAL TEST: SubsequenceDetector should NOT import VideoHasher.

    CRITICAL ERROR #3: Line 11 in subsequence_detector.py:
        from .video_hasher import VideoHasher

    This is OBSOLETE. VideoHasher was deleted during migration to DuplicateFlow.

    EXPECTED: FAIL initially
    Reference: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md (Migration table)
    """
    file_path = Path("src/plugins/duplicate_finder/subsequence_detector.py")

    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    # Check for VideoHasher import
    if 'from .video_hasher import VideoHasher' in code or \
       'from video_hasher import VideoHasher' in code or \
       'import video_hasher' in code:
        pytest.fail(
            "SubsequenceDetector still imports VideoHasher (obsolete). "
            "Should use DuplicateFlow algorithms instead. "
            "See: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md (Migration)"
        )


def test_duplicateflow_integration_imports():
    """
    Test that DuplicateFlow integration modules can be imported.

    These are the NEW modules that replace VideoHasher.

    EXPECTED: PASS
    """
    try:
        from src.plugins.duplicate_finder.integration.duplicateflow_api import DuplicateFlowAPI
        assert DuplicateFlowAPI is not None
    except ImportError as e:
        pytest.fail(f"Failed to import DuplicateFlow integration: {e}")


def test_pipeline_manager_imports():
    """
    Test that PipelineManager can be imported.

    PipelineManager provides access to the 12 DuplicateFlow presets.

    EXPECTED: PASS
    Reference: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md (12 Presets)
    """
    try:
        from src.plugins.duplicate_finder.orchestration.pipeline_manager import PipelineManager
        assert PipelineManager is not None
    except ImportError as e:
        pytest.fail(f"Failed to import PipelineManager: {e}")
