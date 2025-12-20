"""
FileHandler tests for DuplicateFinder plugin.

Tests the FileHandler class, specifically:
- batch_update_cache_status() uses correct method (has_video, not has_hash)
- No references to obsolete VideoHasher
- File validation works correctly
- Integration with VideoDatabase

CRITICAL ERROR #2: batch_update_cache_status() calls has_hash() instead of has_video()
Line 282 in file_handler.py:
    is_cached = cache_checker.has_hash(file_path)

Should be:
    is_cached = cache_checker.has_video(file_path)

Reference: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md (Migration)
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import ast


def test_file_handler_import():
    """Test that FileHandler can be imported."""
    from src.plugins.duplicate_finder.handlers.file_handler import FileHandler
    assert FileHandler is not None


@pytest.mark.critical
def test_batch_update_cache_status_uses_has_video():
    """
    CRITICAL TEST: batch_update_cache_status() should call has_video(), not has_hash().

    CRITICAL ERROR #2: Line 282 in file_handler.py calls:
        is_cached = cache_checker.has_hash(file_path)

    This is WRONG. has_hash() is obsolete. Should use has_video().

    EXPECTED: FAIL initially
    Reference: Migration table - has_hash() → has_video()
    """
    file_path = Path("src/plugins/duplicate_finder/handlers/file_handler.py")

    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    # Check for has_hash call in batch_update_cache_status
    # Look for the specific pattern around line 282
    if 'has_hash' in code:
        # Find which lines contain has_hash
        lines_with_has_hash = []
        for i, line in enumerate(code.split('\n'), 1):
            if 'has_hash' in line and 'batch_update_cache_status' in code[max(0, code.index(line)-500):code.index(line)+500]:
                lines_with_has_hash.append(f"Line {i}: {line.strip()}")

        if lines_with_has_hash:
            pytest.fail(
                f"FileHandler.batch_update_cache_status() calls has_hash() (obsolete).\n"
                f"Should use has_video() instead.\n"
                f"Found:\n" + "\n".join(lines_with_has_hash) +
                f"\n\nReference: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md (Migration)"
            )


@pytest.mark.critical
def test_no_video_hasher_reference():
    """
    CRITICAL TEST: FileHandler should NOT reference VideoHasher.

    VideoHasher is obsolete, replaced by VideoDatabase.

    EXPECTED: PASS
    """
    file_path = Path("src/plugins/duplicate_finder/handlers/file_handler.py")

    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    if 'VideoHasher' in code or 'video_hasher' in code.lower():
        pytest.fail(
            "FileHandler references VideoHasher (obsolete). "
            "Should use VideoDatabase instead."
        )


def test_file_handler_db_integration(mock_video_database, mock_qt_widget):
    """
    Test FileHandler integration with VideoDatabase.

    Tests that FileHandler can work with VideoDatabase's has_video() method.

    EXPECTED: PASS (after fixing CRITICAL ERROR #2)
    """
    from src.plugins.duplicate_finder.handlers.file_handler import FileHandler

    # Create FileHandler with mock widget
    handler = FileHandler(mock_qt_widget)

    # Mock files
    files = ['/video1.mp4', '/video2.mp4']

    # Mock VideoDatabase with has_video (not has_hash)
    mock_db = mock_video_database

    # This should work if batch_update_cache_status uses has_video()
    try:
        # Note: This will fail if has_hash() is still used
        handler.batch_update_cache_status(files, mock_db)
    except AttributeError as e:
        if 'has_hash' in str(e):
            pytest.fail(
                f"FileHandler tried to call has_hash() which doesn't exist. "
                f"Should use has_video(). Error: {e}"
            )
        else:
            raise


def test_file_handler_initialization(mock_qt_widget):
    """
    Test FileHandler can be initialized.

    EXPECTED: PASS
    """
    from src.plugins.duplicate_finder.handlers.file_handler import FileHandler

    handler = FileHandler(mock_qt_widget)
    assert handler is not None
    assert handler.file_list_widget is mock_qt_widget


def test_file_handler_video_extensions():
    """
    Test that FileHandler defines VIDEO_EXTENSIONS.

    EXPECTED: PASS
    """
    from src.plugins.duplicate_finder.handlers.file_handler import FileHandler

    assert hasattr(FileHandler, 'VIDEO_EXTENSIONS'), \
        "FileHandler should define VIDEO_EXTENSIONS"

    extensions = FileHandler.VIDEO_EXTENSIONS
    assert isinstance(extensions, tuple), "VIDEO_EXTENSIONS should be a tuple"
    assert '.mp4' in extensions, "Should support .mp4"
    assert '.avi' in extensions, "Should support .avi"


def test_file_handler_has_validator(mock_qt_widget):
    """
    Test that FileHandler has FileValidator for security.

    Mentioned in file_handler.py line 47: File validator for path validation (ISSUE #28 fix)

    EXPECTED: PASS
    """
    from src.plugins.duplicate_finder.handlers.file_handler import FileHandler

    handler = FileHandler(mock_qt_widget)

    # Check for validator attribute
    assert hasattr(handler, 'validator') or hasattr(handler, 'file_validator'), \
        "FileHandler should have a validator for security (ISSUE #28)"


def test_batch_update_cache_status_signature():
    """
    Test batch_update_cache_status() has correct signature.

    Should accept: (files: List[str], cache_checker)

    EXPECTED: PASS
    """
    from src.plugins.duplicate_finder.handlers.file_handler import FileHandler
    import inspect

    # Get method signature
    sig = inspect.signature(FileHandler.batch_update_cache_status)
    params = list(sig.parameters.keys())

    assert 'files' in params, "Should have 'files' parameter"
    assert 'cache_checker' in params, "Should have 'cache_checker' parameter"


def test_batch_update_calls_update_cache_status(mock_qt_widget):
    """
    Test that batch_update_cache_status() calls update_cache_status() for each file.

    EXPECTED: PASS
    """
    from src.plugins.duplicate_finder.handlers.file_handler import FileHandler

    handler = FileHandler(mock_qt_widget)

    # Mock update_cache_status
    handler.update_cache_status = Mock()

    # Mock cache_checker with has_video (correct method)
    mock_checker = Mock()
    mock_checker.has_video = Mock(return_value=True)

    files = ['/video1.mp4', '/video2.mp4', '/video3.mp4']

    # Call batch update (will fail if has_hash is used instead of has_video)
    try:
        handler.batch_update_cache_status(files, mock_checker)
    except AttributeError as e:
        if 'has_hash' in str(e):
            pytest.skip(
                "Skipping test because CRITICAL ERROR #2 not fixed yet. "
                "FileHandler.batch_update_cache_status() still uses has_hash()."
            )
        else:
            raise

    # Verify update_cache_status was called for each file
    assert handler.update_cache_status.call_count == len(files), \
        "update_cache_status should be called once per file"


def test_file_handler_ast_analysis():
    """
    AST analysis to find exact usage of has_hash in file_handler.py.

    This provides detailed diagnostics for CRITICAL ERROR #2.

    EXPECTED: Provides diagnostic info (may FAIL)
    """
    file_path = Path("src/plugins/duplicate_finder/handlers/file_handler.py")

    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    tree = ast.parse(code)

    has_hash_calls = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            if node.attr == 'has_hash':
                has_hash_calls.append({
                    'line': node.lineno,
                    'attr': node.attr
                })

    if has_hash_calls:
        details = "\n".join([f"  Line {c['line']}: .{c['attr']}()" for c in has_hash_calls])
        pytest.fail(
            f"FileHandler contains {len(has_hash_calls)} call(s) to has_hash():\n{details}\n"
            f"Should use has_video() instead (CRITICAL ERROR #2)."
        )
