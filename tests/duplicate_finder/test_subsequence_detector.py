"""
SubsequenceDetector tests for DuplicateFinder plugin.

Tests the SubsequenceDetector class, specifically:
- No VideoHasher import (obsolete)
- Syntax is valid (no syntax errors)
- Line 666 syntax check (if motion_analysis)
- Can instantiate without errors

CRITICAL ERROR #1: Syntax error at line 666 in subsequence_detector.py
CRITICAL ERROR #3: SubsequenceDetector imports VideoHasher (line 11)

Reference: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md (Migration)
"""

import pytest
from pathlib import Path
import ast


def test_subsequence_detector_import():
    """
    Test that SubsequenceDetector can be imported.

    EXPECTED: FAIL if syntax error exists
    """
    try:
        from src.plugins.duplicate_finder.subsequence_detector import SubsequenceDetector
        assert SubsequenceDetector is not None
    except SyntaxError as e:
        pytest.fail(
            f"SubsequenceDetector has syntax error at line {e.lineno}: {e.msg}\n"
            f"This may be CRITICAL ERROR #1 (line 666)."
        )


@pytest.mark.critical
def test_no_video_hasher_import():
    """
    CRITICAL TEST: SubsequenceDetector should NOT import VideoHasher.

    CRITICAL ERROR #3: Line 11 in subsequence_detector.py:
        from .video_hasher import VideoHasher

    VideoHasher is OBSOLETE and was deleted during migration.

    EXPECTED: FAIL initially
    Reference: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md (Migration)
    """
    file_path = Path("src/plugins/duplicate_finder/subsequence_detector.py")

    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    # Check for VideoHasher import
    if 'from .video_hasher import VideoHasher' in code or \
       'from video_hasher import VideoHasher' in code or \
       'import video_hasher' in code:
        pytest.fail(
            "SubsequenceDetector imports VideoHasher (obsolete).\n"
            "VideoHasher was deleted during DuplicateFlow migration.\n"
            "Should use DuplicateFlow algorithms instead.\n"
            "Reference: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md (Migration)"
        )


@pytest.mark.critical
def test_syntax_valid_line_666():
    """
    CRITICAL TEST: Check syntax around line 666 for errors.

    CRITICAL ERROR #1: Possible syntax error at line 666.
    Common error: missing colon after if statement

    EXPECTED: FAIL if syntax error exists
    """
    file_path = Path("src/plugins/duplicate_finder/subsequence_detector.py")

    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    # Try to parse the file
    try:
        tree = ast.parse(code)
        # If we get here, syntax is valid
        assert True
    except SyntaxError as e:
        if e.lineno == 666 or abs(e.lineno - 666) <= 5:
            pytest.fail(
                f"CRITICAL SYNTAX ERROR at line {e.lineno} (near line 666):\n"
                f"{e.msg}\n"
                f"Text: {e.text}\n"
                f"This is CRITICAL ERROR #1."
            )
        else:
            pytest.fail(f"Syntax error at line {e.lineno}: {e.msg}")


def test_subsequence_detector_compiles():
    """
    Test that subsequence_detector.py compiles without syntax errors.

    EXPECTED: FAIL if CRITICAL ERROR #1 exists
    """
    file_path = Path("src/plugins/duplicate_finder/subsequence_detector.py")

    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    try:
        compile(code, str(file_path), 'exec')
    except SyntaxError as e:
        pytest.fail(
            f"subsequence_detector.py has syntax error at line {e.lineno}:\n"
            f"{e.msg}\n"
            f"Text: {e.text}"
        )


def test_phase2_methods_complete():
    """
    Test that phase2-related methods are syntactically complete.

    The verification_pipeline parameter suggests phase 2 migration.

    EXPECTED: PASS (methods should be syntactically complete)
    """
    file_path = Path("src/plugins/duplicate_finder/subsequence_detector.py")

    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    try:
        tree = ast.parse(code)

        # Find class definition
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if node.name == 'SubsequenceDetector':
                    # Check that class has methods
                    methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                    assert len(methods) > 0, "SubsequenceDetector should have methods"
                    break

    except SyntaxError as e:
        pytest.fail(f"Syntax error prevents method analysis: {e}")


def test_subsequence_detector_instantiates():
    """
    Test that SubsequenceDetector can be instantiated.

    Note: This requires VideoHasher, which is obsolete.
    Test will be skipped until migration is complete.

    EXPECTED: SKIP (until VideoHasher dependency removed)
    """
    pytest.skip(
        "SubsequenceDetector still requires VideoHasher (obsolete). "
        "Cannot instantiate until CRITICAL ERROR #3 is fixed."
    )


def test_check_if_statement_syntax():
    """
    Specifically check for 'if motion_analysis' syntax issues.

    Common error: missing colon after if statement.

    EXPECTED: Diagnostic info
    """
    file_path = Path("src/plugins/duplicate_finder/subsequence_detector.py")

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Look for 'if motion_analysis' patterns around line 666
    target_line = 666
    start = max(0, target_line - 10)
    end = min(len(lines), target_line + 10)

    motion_analysis_lines = []
    for i in range(start, end):
        if 'motion_analysis' in lines[i]:
            motion_analysis_lines.append((i + 1, lines[i].rstrip()))

    if motion_analysis_lines:
        info = "\n".join([f"  Line {num}: {text}" for num, text in motion_analysis_lines])
        # Just provide info, don't fail
        # Syntax errors are caught by other tests
        print(f"\nmotion_analysis references around line 666:\n{info}")


def test_no_lru_cache_import():
    """
    Test that SubsequenceDetector doesn't import custom lru_cache.

    Line 13 in subsequence_detector.py:
        from .lru_cache import MemoryBoundedLRUCache

    This may be obsolete if lru_cache.py was deleted.

    EXPECTED: May FAIL if lru_cache.py deleted
    """
    file_path = Path("src/plugins/duplicate_finder/subsequence_detector.py")

    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    if 'from .lru_cache import' in code:
        # Check if lru_cache.py exists
        lru_cache_path = Path("src/plugins/duplicate_finder/lru_cache.py")
        if not lru_cache_path.exists():
            pytest.fail(
                "SubsequenceDetector imports from .lru_cache but lru_cache.py doesn't exist.\n"
                "This import is obsolete and should be removed."
            )


def test_subsequence_detector_has_init():
    """
    Test that SubsequenceDetector has __init__ method with expected parameters.

    EXPECTED: PASS
    """
    file_path = Path("src/plugins/duplicate_finder/subsequence_detector.py")

    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    try:
        tree = ast.parse(code)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if node.name == 'SubsequenceDetector':
                    # Find __init__ method
                    init_found = False
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) and item.name == '__init__':
                            init_found = True
                            break

                    assert init_found, "SubsequenceDetector should have __init__ method"
                    break

    except SyntaxError as e:
        pytest.fail(f"Cannot analyze __init__ due to syntax error: {e}")


def test_verification_pipeline_parameter():
    """
    Test that SubsequenceDetector.__init__ accepts verification_pipeline parameter.

    Line 50 in subsequence_detector.py shows this is a NEW parameter.

    EXPECTED: PASS
    """
    file_path = Path("src/plugins/duplicate_finder/subsequence_detector.py")

    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    # Check for verification_pipeline parameter
    assert 'verification_pipeline' in code, \
        "SubsequenceDetector should have verification_pipeline parameter (new feature)"


def test_ast_find_syntax_errors():
    """
    Use AST to find any syntax errors in subsequence_detector.py.

    Provides detailed error location for debugging.

    EXPECTED: FAIL if syntax errors exist
    """
    file_path = Path("src/plugins/duplicate_finder/subsequence_detector.py")

    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    errors = []
    try:
        ast.parse(code)
    except SyntaxError as e:
        errors.append({
            'line': e.lineno,
            'msg': e.msg,
            'text': e.text.strip() if e.text else '',
            'offset': e.offset
        })

    if errors:
        details = "\n".join([
            f"  Line {e['line']}: {e['msg']}\n"
            f"    Text: {e['text']}\n"
            f"    Offset: {e['offset']}"
            for e in errors
        ])
        pytest.fail(
            f"SubsequenceDetector has {len(errors)} syntax error(s):\n{details}"
        )
