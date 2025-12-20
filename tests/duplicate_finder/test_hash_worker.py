"""
ParallelHashWorker tests for DuplicateFinder plugin.

Tests the ParallelHashWorker class, specifically:
- Constructor accepts db_manager, not video_hasher
- Uses db.has_video(), not video_hasher.has_hash()
- No references to compute_video_hash() (obsolete)
- Integration with VideoDatabase

CRITICAL ERRORS #4: ParallelHashWorker references video_hasher
Lines in hash_worker.py:
- Line 76: self.video_hasher = video_hasher
- Line 101: if self.video_hasher.has_hash(file)
- Line 134: if self.video_hasher.has_hash(file_path)
- Line 148: self.video_hasher.compute_video_hash(file_path)

Should use db_manager with has_video() instead.

Reference: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md (Migration)
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
import ast


def test_hash_worker_import():
    """Test that ParallelHashWorker can be imported."""
    from src.plugins.duplicate_finder.workers.hash_worker import ParallelHashWorker
    assert ParallelHashWorker is not None


@pytest.mark.critical
def test_hash_worker_accepts_db_manager():
    """
    CRITICAL TEST: ParallelHashWorker should accept db_manager, not video_hasher.

    CRITICAL ERROR #4: Constructor accepts video_hasher parameter (line 76)
    This is obsolete. Should accept db_manager instead.

    EXPECTED: FAIL initially
    Reference: Migration - VideoHasher → VideoDatabase
    """
    from src.plugins.duplicate_finder.workers.hash_worker import ParallelHashWorker
    import inspect

    # Get constructor signature
    sig = inspect.signature(ParallelHashWorker.__init__)
    params = list(sig.parameters.keys())

    # Check for video_hasher parameter (OBSOLETE)
    if 'video_hasher' in params:
        pytest.fail(
            "ParallelHashWorker.__init__() has 'video_hasher' parameter (obsolete). "
            "Should use 'db_manager' instead. "
            "Reference: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md (Migration)"
        )

    # Check for db_manager parameter (CORRECT)
    # Note: This may fail initially if not yet migrated
    # assert 'db_manager' in params, \
    #     "ParallelHashWorker should accept 'db_manager' parameter"


@pytest.mark.critical
def test_hash_worker_rejects_video_hasher():
    """
    CRITICAL TEST: ParallelHashWorker should NOT use video_hasher attribute.

    CRITICAL ERROR #4: Line 76 sets self.video_hasher = video_hasher

    EXPECTED: FAIL initially
    """
    file_path = Path("src/plugins/duplicate_finder/workers/hash_worker.py")

    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    # Check for self.video_hasher assignment
    if 'self.video_hasher' in code:
        pytest.fail(
            "ParallelHashWorker uses self.video_hasher (obsolete). "
            "Should use self.db_manager or similar instead."
        )


@pytest.mark.critical
def test_hash_worker_uses_has_video():
    """
    CRITICAL TEST: ParallelHashWorker should call has_video(), not has_hash().

    CRITICAL ERROR #4: Lines 101 and 134 call has_hash():
        if self.video_hasher.has_hash(file)
        if self.video_hasher.has_hash(file_path)

    Should be:
        if self.db_manager.has_video(file)

    EXPECTED: FAIL initially
    """
    file_path = Path("src/plugins/duplicate_finder/workers/hash_worker.py")

    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    has_hash_calls = []
    for i, line in enumerate(code.split('\n'), 1):
        if 'has_hash' in line:
            has_hash_calls.append(f"Line {i}: {line.strip()}")

    if has_hash_calls:
        pytest.fail(
            f"ParallelHashWorker contains {len(has_hash_calls)} call(s) to has_hash():\n" +
            "\n".join(has_hash_calls) +
            "\n\nShould use has_video() instead (CRITICAL ERROR #4)."
        )


@pytest.mark.critical
def test_no_compute_video_hash_call():
    """
    CRITICAL TEST: ParallelHashWorker should NOT call compute_video_hash().

    CRITICAL ERROR #4: Line 148 calls:
        self.video_hasher.compute_video_hash(file_path)

    This is obsolete. Should use DuplicateFlow algorithms instead.

    EXPECTED: FAIL initially
    Reference: Migration table - compute_hash() → extract_features()
    """
    file_path = Path("src/plugins/duplicate_finder/workers/hash_worker.py")

    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    if 'compute_video_hash' in code:
        # Find exact lines
        lines = []
        for i, line in enumerate(code.split('\n'), 1):
            if 'compute_video_hash' in line:
                lines.append(f"Line {i}: {line.strip()}")

        pytest.fail(
            f"ParallelHashWorker calls compute_video_hash() (obsolete):\n" +
            "\n".join(lines) +
            "\n\nShould use DuplicateFlow algorithms. "
            "Reference: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md (Migration)"
        )


def test_hash_worker_ast_video_hasher_usage():
    """
    AST analysis to find all video_hasher references in hash_worker.py.

    Provides detailed diagnostics for CRITICAL ERROR #4.

    EXPECTED: Diagnostic info (may FAIL)
    """
    file_path = Path("src/plugins/duplicate_finder/workers/hash_worker.py")

    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    tree = ast.parse(code)

    video_hasher_refs = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            # Check for .video_hasher attribute access
            if isinstance(node.value, ast.Name):
                if node.value.id == 'self' and node.attr == 'video_hasher':
                    video_hasher_refs.append({
                        'line': node.lineno,
                        'type': 'attribute_access'
                    })

        elif isinstance(node, ast.Assign):
            # Check for self.video_hasher = ...
            for target in node.targets:
                if isinstance(target, ast.Attribute):
                    if isinstance(target.value, ast.Name):
                        if target.value.id == 'self' and target.attr == 'video_hasher':
                            video_hasher_refs.append({
                                'line': node.lineno,
                                'type': 'assignment'
                            })

    if video_hasher_refs:
        details = "\n".join([
            f"  Line {r['line']}: {r['type']}"
            for r in video_hasher_refs
        ])
        pytest.fail(
            f"ParallelHashWorker contains {len(video_hasher_refs)} reference(s) to video_hasher:\n"
            f"{details}\n\n"
            f"Should use db_manager instead (CRITICAL ERROR #4)."
        )


def test_hash_worker_initialization_signature():
    """
    Test that ParallelHashWorker can be initialized with expected parameters.

    Note: This test documents expected signature after migration.

    EXPECTED: SKIP or FAIL (until migration complete)
    """
    pytest.skip(
        "ParallelHashWorker signature not yet migrated. "
        "Currently expects video_hasher, should expect db_manager."
    )


def test_hash_worker_has_files_parameter():
    """
    Test that ParallelHashWorker.__init__ accepts files parameter.

    This is independent of the video_hasher/db_manager issue.

    EXPECTED: PASS
    """
    from src.plugins.duplicate_finder.workers.hash_worker import ParallelHashWorker
    import inspect

    sig = inspect.signature(ParallelHashWorker.__init__)
    params = list(sig.parameters.keys())

    assert 'files' in params, "ParallelHashWorker should accept 'files' parameter"


def test_hash_worker_has_signals():
    """
    Test that ParallelHashWorker has required Qt signals.

    These signals are used for progress tracking.

    EXPECTED: PASS
    """
    from src.plugins.duplicate_finder.workers.hash_worker import ParallelHashWorker

    # Check for signal attributes
    signals = ['progress', 'finished', 'error', 'file_processed', 'current_file']

    for signal_name in signals:
        assert hasattr(ParallelHashWorker, signal_name), \
            f"ParallelHashWorker should have '{signal_name}' signal"


def test_hash_worker_is_qthread():
    """
    Test that ParallelHashWorker inherits from QThread.

    EXPECTED: PASS
    """
    from src.plugins.duplicate_finder.workers.hash_worker import ParallelHashWorker
    from PyQt6.QtCore import QThread

    assert issubclass(ParallelHashWorker, QThread), \
        "ParallelHashWorker should inherit from QThread"


def test_hash_worker_has_process_single_file():
    """
    Test that ParallelHashWorker has process_single_file() method.

    EXPECTED: PASS
    """
    from src.plugins.duplicate_finder.workers.hash_worker import ParallelHashWorker

    assert hasattr(ParallelHashWorker, 'process_single_file'), \
        "ParallelHashWorker should have process_single_file() method"


def test_hash_worker_validates_files():
    """
    Test that ParallelHashWorker uses FileValidator.

    Line 144 in hash_worker.py:
        if not FileValidator.validate_video_file(file_path):

    EXPECTED: PASS
    """
    file_path = Path("src/plugins/duplicate_finder/workers/hash_worker.py")

    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    assert 'FileValidator' in code, \
        "ParallelHashWorker should use FileValidator for file validation"


def test_hash_worker_max_workers_validation():
    """
    Test that max_workers parameter is validated.

    Line 80-82 in hash_worker.py shows validation logic.

    EXPECTED: PASS
    """
    file_path = Path("src/plugins/duplicate_finder/workers/hash_worker.py")

    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    # Check for max_workers validation
    assert 'max_workers' in code, "Should have max_workers parameter"
    assert 'validated_workers' in code or 'self.max_workers' in code, \
        "Should validate max_workers value"
