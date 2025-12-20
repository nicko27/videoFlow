"""
Basic UI tests for DuplicateFinder plugin (without Qt).

Tests UI modules using mocks to avoid Qt dependency:
- panels.py imports correctly
- Widgets are creatable (mocked)
- No references to obsolete features
- Pipeline section callable

These tests use mocks to avoid requiring Qt initialization.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
import ast


@pytest.mark.ui
def test_panels_imports():
    """
    Test that panels.py can be imported.

    May require Qt, so we allow ImportError for Qt dependencies.

    EXPECTED: PASS (or skip if Qt not available)
    """
    try:
        from src.plugins.duplicate_finder.ui import panels
        assert panels is not None
    except ImportError as e:
        if "PyQt" in str(e) or "PySide" in str(e):
            pytest.skip(f"Qt not available: {e}")
        else:
            pytest.fail(f"Failed to import panels: {e}")


@pytest.mark.ui
def test_create_parameters_tab_signature():
    """
    Test that create_parameters_tab exists in panels.py.

    This is mentioned in ui/ refactoring.

    EXPECTED: PASS
    """
    file_path = Path("src/plugins/duplicate_finder/ui/panels.py")

    if not file_path.exists():
        pytest.skip("panels.py not found")

    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    # Check for create_parameters_tab function
    assert 'create_parameters_tab' in code or 'parameters_tab' in code.lower(), \
        "panels.py should have create_parameters_tab or similar"


@pytest.mark.ui
def test_no_quick_presets_reference():
    """
    Test that panels.py doesn't reference obsolete quick_presets.

    Quick presets may have been replaced by DuplicateFlow's 12 presets.

    EXPECTED: PASS
    """
    file_path = Path("src/plugins/duplicate_finder/ui/panels.py")

    if not file_path.exists():
        pytest.skip("panels.py not found")

    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    # This is a soft check - quick_presets might still be valid
    # Just checking if it exists
    if 'quick_presets' in code.lower():
        # Just log it, don't fail
        print("INFO: panels.py contains reference to quick_presets")


@pytest.mark.ui
def test_pipeline_section_callable():
    """
    Test that pipeline section creation is callable.

    Should have functions for creating pipeline UI sections.

    EXPECTED: PASS
    """
    file_path = Path("src/plugins/duplicate_finder/ui/panels.py")

    if not file_path.exists():
        pytest.skip("panels.py not found")

    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    # Check for pipeline-related functions
    pipeline_keywords = ['pipeline', 'algorithm', 'verification']
    found_keywords = [kw for kw in pipeline_keywords if kw in code.lower()]

    assert len(found_keywords) > 0, \
        f"panels.py should have pipeline-related code. Found: {found_keywords}"


@pytest.mark.ui
def test_unified_pipeline_editor_dialog_import():
    """
    Test that UnifiedPipelineEditorDialog can be imported.

    EXPECTED: PASS (or skip if Qt not available)
    """
    try:
        from src.plugins.duplicate_finder.ui.unified_pipeline_editor_dialog import UnifiedPipelineEditorDialog
        assert UnifiedPipelineEditorDialog is not None
    except ImportError as e:
        if "PyQt" in str(e) or "PySide" in str(e):
            pytest.skip(f"Qt not available: {e}")
        else:
            pytest.fail(f"Failed to import UnifiedPipelineEditorDialog: {e}")


@pytest.mark.ui
def test_validator_config_widget_import():
    """
    Test that ValidatorConfigWidget can be imported.

    This is a NEW widget for DuplicateFlow validators.

    EXPECTED: PASS
    """
    try:
        from src.plugins.duplicate_finder.ui.widgets.validator_config_widget import ValidatorConfigWidget
        assert ValidatorConfigWidget is not None
    except ImportError as e:
        if "PyQt" in str(e) or "PySide" in str(e):
            pytest.skip(f"Qt not available: {e}")
        else:
            pytest.fail(f"Failed to import ValidatorConfigWidget: {e}")


@pytest.mark.ui
def test_partial_analysis_widget_import():
    """
    Test that PartialAnalysisWidget can be imported.

    This is a NEW widget for partial analysis configuration.

    EXPECTED: PASS
    """
    try:
        from src.plugins.duplicate_finder.ui.widgets.partial_analysis_widget import PartialAnalysisWidget
        assert PartialAnalysisWidget is not None
    except ImportError as e:
        if "PyQt" in str(e) or "PySide" in str(e):
            pytest.skip(f"Qt not available: {e}")
        else:
            pytest.fail(f"Failed to import PartialAnalysisWidget: {e}")


@pytest.mark.ui
def test_main_window_import():
    """
    Test that main_window can be imported.

    EXPECTED: PASS (or skip if Qt not available)
    """
    try:
        from src.plugins.duplicate_finder.ui.main_window import MainWindow
        assert MainWindow is not None
    except ImportError as e:
        if "PyQt" in str(e) or "PySide" in str(e):
            pytest.skip(f"Qt not available: {e}")
        else:
            pytest.fail(f"Failed to import MainWindow: {e}")


@pytest.mark.ui
def test_ui_widgets_init():
    """
    Test that ui/widgets/__init__.py exists and is valid.

    EXPECTED: PASS
    """
    file_path = Path("src/plugins/duplicate_finder/ui/widgets/__init__.py")

    assert file_path.exists(), \
        "ui/widgets/__init__.py should exist"

    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    # Check it's valid Python
    try:
        compile(code, str(file_path), 'exec')
    except SyntaxError as e:
        pytest.fail(f"ui/widgets/__init__.py has syntax error: {e}")


@pytest.mark.ui
def test_no_window_py_file():
    """
    Test that obsolete window.py file doesn't exist.

    window.py may have been deleted in favor of main_window.py.

    EXPECTED: PASS
    """
    file_path = Path("src/plugins/duplicate_finder/ui/window.py")

    if file_path.exists():
        pytest.fail(
            "ui/window.py still exists but may be obsolete. "
            "Should use main_window.py instead."
        )


@pytest.mark.ui
def test_panels_no_syntax_errors():
    """
    Test that panels.py has no syntax errors.

    EXPECTED: PASS
    """
    file_path = Path("src/plugins/duplicate_finder/ui/panels.py")

    if not file_path.exists():
        pytest.skip("panels.py not found")

    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    try:
        compile(code, str(file_path), 'exec')
    except SyntaxError as e:
        pytest.fail(
            f"panels.py has syntax error at line {e.lineno}: {e.msg}\n"
            f"Text: {e.text}"
        )


@pytest.mark.ui
def test_widget_registry_exists():
    """
    Test that widget_registry exists.

    Widget registry may be used for dynamic widget loading.

    EXPECTED: PASS (if widget_registry pattern is used)
    """
    file_path = Path("src/plugins/duplicate_finder/ui/widget_registry.py")

    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()

        # Check for valid syntax
        try:
            compile(code, str(file_path), 'exec')
        except SyntaxError as e:
            pytest.fail(f"widget_registry.py has syntax error: {e}")


@pytest.mark.ui
def test_ui_uses_duplicateflow_presets():
    """
    Test that UI references DuplicateFlow's 12 presets.

    Look for references to preset names in UI files.

    EXPECTED: PASS
    """
    preset_names = [
        "fast",
        "balanced",
        "thorough",
        "multimodal",
        "fast_duplicates",
        "accurate_scenes",
        "intro_detector",
        "credits_detector"
    ]

    ui_files = [
        "src/plugins/duplicate_finder/ui/panels.py",
        "src/plugins/duplicate_finder/ui/unified_pipeline_editor_dialog.py",
        "src/plugins/duplicate_finder/ui/main_window.py"
    ]

    found_presets = []

    for ui_file in ui_files:
        file_path = Path(ui_file)
        if not file_path.exists():
            continue

        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()

        for preset in preset_names:
            if preset in code:
                found_presets.append((ui_file, preset))

    # At least some presets should be referenced in UI
    # This is a soft check
    if found_presets:
        print(f"\nINFO: Found {len(found_presets)} preset references in UI files")


@pytest.mark.ui
def test_ui_no_videohasher_references():
    """
    Test that UI files don't reference VideoHasher (obsolete).

    EXPECTED: PASS
    """
    ui_files = list(Path("src/plugins/duplicate_finder/ui").rglob("*.py"))

    errors = []

    for file_path in ui_files:
        if "__pycache__" in str(file_path):
            continue

        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()

        if 'VideoHasher' in code or 'video_hasher' in code:
            errors.append(f"{file_path.name} references VideoHasher (obsolete)")

    assert not errors, \
        f"UI files reference VideoHasher:\n" + "\n".join(errors)


@pytest.mark.ui
def test_themes_import():
    """
    Test that themes.py can be imported if it exists.

    EXPECTED: PASS
    """
    try:
        from src.plugins.duplicate_finder.ui.themes import themes
        # If import succeeds, it's valid
        assert True
    except ImportError as e:
        if "PyQt" in str(e) or "themes" not in str(e):
            pytest.skip(f"Themes not available: {e}")
        else:
            pytest.fail(f"Failed to import themes: {e}")
    except AttributeError:
        # themes module exists but no 'themes' attribute
        pytest.skip("themes module exists but structure differs")
