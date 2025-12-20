"""
Critical error regression tests for DuplicateFinder plugin.

This module contains specific tests for the 4 critical errors identified:

CRITICAL ERROR #1: Syntax error at line 666 in subsequence_detector.py
    Missing 'if' statement before code block

CRITICAL ERROR #2: has_hash() used instead of has_video() in file_handler.py
    Line 282: is_cached = cache_checker.has_hash(file_path)

CRITICAL ERROR #3: VideoHasher import in subsequence_detector.py
    Line 11: from .video_hasher import VideoHasher (OBSOLETE)

CRITICAL ERROR #4: video_hasher usage in hash_worker.py
    Lines 76, 101, 134, 148: References to self.video_hasher

All tests should be RED initially (failing), then GREEN after fixes.

Reference: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md (Migration section)
"""

import pytest
from pathlib import Path
import ast


@pytest.mark.critical
class TestCriticalError1:
    """CRITICAL ERROR #1: Syntax error at line 666 in subsequence_detector.py"""

    def test_subsequence_detector_line_666_syntax(self):
        """
        Test that line 666 in subsequence_detector.py has valid syntax.

        PROBLEM: Missing 'if' statement before code block
        Line 666 starts with 'verification_result = ...' without a condition

        EXPECTED BEFORE FIX: FAIL (SyntaxError)
        EXPECTED AFTER FIX: PASS
        """
        file_path = Path("src/plugins/duplicate_finder/subsequence_detector.py")

        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()

        try:
            ast.parse(code)
            # If we get here, syntax is valid
            assert True, "Syntax is valid"
        except SyntaxError as e:
            if e.lineno and abs(e.lineno - 666) <= 5:
                pytest.fail(
                    f"CRITICAL ERROR #1: Syntax error at line {e.lineno} (near 666)\n"
                    f"Error: {e.msg}\n"
                    f"Text: {e.text}\n\n"
                    f"FIX: Add 'if' statement before line 666\n"
                    f"Expected:\n"
                    f"    if self.phase2_method == 'motion_analysis':\n"
                    f"        verification_result = self._verify_motion_analysis(...)"
                )
            else:
                pytest.fail(f"Syntax error at line {e.lineno}: {e.msg}")

    def test_subsequence_detector_phase2_dispatch_complete(self):
        """
        Test that phase2 method dispatch is complete.

        The if-elif chain should cover all phase2_method options.

        EXPECTED BEFORE FIX: FAIL (missing 'if' at line 666)
        EXPECTED AFTER FIX: PASS
        """
        file_path = Path("src/plugins/duplicate_finder/subsequence_detector.py")

        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()

        # Look for phase2 method dispatch pattern
        # Should have: if ... elif ... elif ... for each method
        phase2_methods = [
            'motion_analysis',
            'dct_only',
            'frame_diff',
            'multipoint'
        ]

        for method in phase2_methods:
            pattern = f'self.phase2_method == "{method}"'
            if pattern not in code and f"self.phase2_method == '{method}'" not in code:
                pytest.fail(
                    f"Phase2 method dispatch missing for '{method}'. "
                    f"This may be related to CRITICAL ERROR #1."
                )


@pytest.mark.critical
class TestCriticalError2:
    """CRITICAL ERROR #2: has_hash() used instead of has_video()"""

    def test_file_handler_uses_has_video_not_has_hash(self):
        """
        Test that FileHandler uses has_video(), not has_hash().

        PROBLEM: Line 282 in file_handler.py:
            is_cached = cache_checker.has_hash(file_path)

        SHOULD BE:
            is_cached = cache_checker.has_video(file_path)

        EXPECTED BEFORE FIX: FAIL (has_hash found)
        EXPECTED AFTER FIX: PASS (has_video used)

        Reference: Migration table - has_hash() → has_video()
        """
        file_path = Path("src/plugins/duplicate_finder/handlers/file_handler.py")

        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()

        # Check for has_hash usage
        if 'has_hash' in code:
            lines_with_has_hash = []
            for i, line in enumerate(code.split('\n'), 1):
                if 'has_hash' in line:
                    lines_with_has_hash.append(f"    Line {i}: {line.strip()}")

            pytest.fail(
                f"CRITICAL ERROR #2: FileHandler uses has_hash() (OBSOLETE)\n"
                f"Found {len(lines_with_has_hash)} occurrence(s):\n" +
                "\n".join(lines_with_has_hash) +
                f"\n\nFIX: Replace has_hash() with has_video()\n"
                f"Reference: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md (Migration)"
            )

    def test_file_handler_batch_update_signature(self):
        """
        Test that batch_update_cache_status accepts cache_checker with has_video.

        EXPECTED AFTER FIX: PASS
        """
        from src.plugins.duplicate_finder.handlers.file_handler import FileHandler
        from unittest.mock import Mock

        handler = FileHandler(Mock())

        # Create mock with has_video (CORRECT)
        mock_checker = Mock()
        mock_checker.has_video = Mock(return_value=True)

        files = ['/test/video.mp4']

        # This should work after fix
        try:
            handler.batch_update_cache_status(files, mock_checker)
        except AttributeError as e:
            if 'has_hash' in str(e):
                pytest.fail(
                    f"CRITICAL ERROR #2 NOT FIXED: FileHandler still calls has_hash()\n"
                    f"Error: {e}"
                )
            else:
                raise


@pytest.mark.critical
class TestCriticalError3:
    """CRITICAL ERROR #3: VideoHasher import in subsequence_detector.py"""

    def test_subsequence_detector_no_videohasher_import(self):
        """
        Test that SubsequenceDetector does NOT import VideoHasher.

        PROBLEM: Line 11 in subsequence_detector.py:
            from .video_hasher import VideoHasher

        VideoHasher was DELETED during DuplicateFlow migration.
        This import will cause ImportError at runtime.

        EXPECTED BEFORE FIX: FAIL (VideoHasher import found)
        EXPECTED AFTER FIX: PASS (no VideoHasher import)

        Reference: Migration table - VideoHasher is obsolete
        """
        file_path = Path("src/plugins/duplicate_finder/subsequence_detector.py")

        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()

        videohasher_imports = []

        # Check for various import patterns
        patterns = [
            'from .video_hasher import VideoHasher',
            'from video_hasher import VideoHasher',
            'import video_hasher',
            'from .video_hasher import',
        ]

        for i, line in enumerate(code.split('\n'), 1):
            for pattern in patterns:
                if pattern in line:
                    videohasher_imports.append(f"    Line {i}: {line.strip()}")

        if videohasher_imports:
            pytest.fail(
                f"CRITICAL ERROR #3: SubsequenceDetector imports VideoHasher (OBSOLETE)\n"
                f"Found {len(videohasher_imports)} import(s):\n" +
                "\n".join(videohasher_imports) +
                f"\n\nFIX: Remove VideoHasher import\n"
                f"VideoHasher was deleted during DuplicateFlow migration.\n"
                f"Use DuplicateFlow algorithms instead.\n"
                f"Reference: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md (Migration)"
            )

    def test_subsequence_detector_can_import(self):
        """
        Test that SubsequenceDetector can be imported after fix.

        EXPECTED BEFORE FIX: FAIL (ImportError - VideoHasher not found)
        EXPECTED AFTER FIX: PASS
        """
        try:
            from src.plugins.duplicate_finder.subsequence_detector import SubsequenceDetector
            assert SubsequenceDetector is not None
        except ImportError as e:
            if 'video_hasher' in str(e).lower() or 'VideoHasher' in str(e):
                pytest.fail(
                    f"CRITICAL ERROR #3 NOT FIXED: Cannot import SubsequenceDetector\n"
                    f"Error: {e}\n"
                    f"VideoHasher import still present."
                )
            else:
                raise


@pytest.mark.critical
class TestCriticalError4:
    """CRITICAL ERROR #4: video_hasher usage in hash_worker.py"""

    def test_hash_worker_no_video_hasher_attribute(self):
        """
        Test that ParallelHashWorker does NOT use self.video_hasher.

        PROBLEM: Multiple lines in hash_worker.py reference video_hasher:
            Line 76: self.video_hasher = video_hasher
            Line 101: if self.video_hasher.has_hash(file)
            Line 134: if self.video_hasher.has_hash(file_path)
            Line 148: self.video_hasher.compute_video_hash(file_path)

        EXPECTED BEFORE FIX: FAIL (video_hasher references found)
        EXPECTED AFTER FIX: PASS (use db_manager instead)

        Reference: Migration - VideoHasher → VideoDatabase
        """
        file_path = Path("src/plugins/duplicate_finder/workers/hash_worker.py")

        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()

        video_hasher_refs = []

        for i, line in enumerate(code.split('\n'), 1):
            if 'video_hasher' in line.lower():
                video_hasher_refs.append(f"    Line {i}: {line.strip()}")

        if video_hasher_refs:
            pytest.fail(
                f"CRITICAL ERROR #4: ParallelHashWorker uses video_hasher (OBSOLETE)\n"
                f"Found {len(video_hasher_refs)} reference(s):\n" +
                "\n".join(video_hasher_refs) +
                f"\n\nFIX: Replace video_hasher with db_manager\n"
                f"- Constructor should accept db_manager, not video_hasher\n"
                f"- Use db_manager.has_video() instead of video_hasher.has_hash()\n"
                f"- Remove compute_video_hash() calls (use DuplicateFlow algorithms)\n"
                f"Reference: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md (Migration)"
            )

    def test_hash_worker_uses_has_video(self):
        """
        Test that ParallelHashWorker uses has_video(), not has_hash().

        EXPECTED BEFORE FIX: FAIL (has_hash found)
        EXPECTED AFTER FIX: PASS (has_video used)
        """
        file_path = Path("src/plugins/duplicate_finder/workers/hash_worker.py")

        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()

        if 'has_hash' in code:
            lines_with_has_hash = []
            for i, line in enumerate(code.split('\n'), 1):
                if 'has_hash' in line:
                    lines_with_has_hash.append(f"    Line {i}: {line.strip()}")

            pytest.fail(
                f"CRITICAL ERROR #4 (partial): ParallelHashWorker uses has_hash()\n"
                f"Found {len(lines_with_has_hash)} occurrence(s):\n" +
                "\n".join(lines_with_has_hash) +
                f"\n\nShould use has_video() instead."
            )

    def test_hash_worker_no_compute_video_hash(self):
        """
        Test that ParallelHashWorker does NOT call compute_video_hash().

        compute_video_hash() is a VideoHasher method (obsolete).

        EXPECTED BEFORE FIX: FAIL (compute_video_hash found)
        EXPECTED AFTER FIX: PASS (use DuplicateFlow algorithms)
        """
        file_path = Path("src/plugins/duplicate_finder/workers/hash_worker.py")

        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()

        if 'compute_video_hash' in code:
            lines = []
            for i, line in enumerate(code.split('\n'), 1):
                if 'compute_video_hash' in line:
                    lines.append(f"    Line {i}: {line.strip()}")

            pytest.fail(
                f"CRITICAL ERROR #4 (partial): ParallelHashWorker calls compute_video_hash()\n"
                f"Found {len(lines)} call(s):\n" +
                "\n".join(lines) +
                f"\n\ncompute_video_hash() is obsolete.\n"
                f"Use DuplicateFlow algorithms instead.\n"
                f"Reference: Migration table - compute_hash() → extract_features()"
            )


@pytest.mark.critical
def test_all_critical_errors_summary():
    """
    Summary test that checks all 4 critical errors at once.

    This provides a quick overview of which errors are fixed.

    EXPECTED BEFORE FIXES: FAIL with summary of all errors
    EXPECTED AFTER ALL FIXES: PASS
    """
    errors = []

    # ERROR #1: Syntax at line 666
    try:
        file_path = Path("src/plugins/duplicate_finder/subsequence_detector.py")
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        ast.parse(code)
    except SyntaxError as e:
        if e.lineno and abs(e.lineno - 666) <= 5:
            errors.append(f"ERROR #1: Syntax error at line {e.lineno} in subsequence_detector.py")

    # ERROR #2: has_hash in file_handler
    file_path = Path("src/plugins/duplicate_finder/handlers/file_handler.py")
    with open(file_path, 'r', encoding='utf-8') as f:
        if 'has_hash' in f.read():
            errors.append("ERROR #2: file_handler.py uses has_hash() instead of has_video()")

    # ERROR #3: VideoHasher import in subsequence_detector
    file_path = Path("src/plugins/duplicate_finder/subsequence_detector.py")
    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()
        if 'from .video_hasher import VideoHasher' in code or 'import video_hasher' in code:
            errors.append("ERROR #3: subsequence_detector.py imports VideoHasher (obsolete)")

    # ERROR #4: video_hasher in hash_worker
    file_path = Path("src/plugins/duplicate_finder/workers/hash_worker.py")
    with open(file_path, 'r', encoding='utf-8') as f:
        if 'video_hasher' in f.read().lower():
            errors.append("ERROR #4: hash_worker.py uses video_hasher (obsolete)")

    if errors:
        summary = "\n".join([f"  [{i+1}] {err}" for i, err in enumerate(errors)])
        pytest.fail(
            f"\n{'='*70}\n"
            f"CRITICAL ERRORS SUMMARY: {len(errors)}/4 errors found\n"
            f"{'='*70}\n"
            f"{summary}\n"
            f"{'='*70}\n"
            f"Fix these errors to make tests pass.\n"
            f"Reference: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md (Migration)\n"
            f"{'='*70}"
        )
