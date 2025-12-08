#!/usr/bin/env python3
"""
Test d'intégration end-to-end pour le plugin Duplicate Finder.
Vérifie que toutes les fonctionnalités critiques fonctionnent correctement.
"""

import sys
import os
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

def test_duplicate_finder_import():
    """Test 1: Verify all imports work."""
    print("Test 1: Vérification des imports...")
    try:
        from plugins.duplicate_finder.main_window import DuplicateFinderWindow
        from plugins.duplicate_finder.managers import (
            UnifiedConfigManager,
            ProgressManager,
            SettingsManager
        )
        from plugins.duplicate_finder.ui import SettingsDialog, WidgetRegistry
        from plugins.duplicate_finder.controllers import WorkflowController
        print("✅ Tous les imports fonctionnent")
        return True
    except Exception as e:
        print(f"❌ Erreur d'import: {e}")
        return False

def test_duplicate_finder_window_creation():
    """Test 2: Verify DuplicateFinderWindow can be instantiated."""
    print("\nTest 2: Création de DuplicateFinderWindow...")
    try:
        from plugins.duplicate_finder.main_window import DuplicateFinderWindow

        # Create QApplication if needed
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        # Try to create the window
        window = DuplicateFinderWindow()
        print(f"✅ Fenêtre créée avec succès")
        print(f"   - unified_config_manager: {hasattr(window, 'unified_config_manager')}")
        print(f"   - widget_registry: {hasattr(window, 'widget_registry')}")
        print(f"   - progress_manager: {hasattr(window, 'progress_manager')}")
        print(f"   - workflow_controller: {hasattr(window, 'workflow_controller')}")

        # Clean up
        window.close()
        window.deleteLater()

        return True
    except Exception as e:
        print(f"❌ Erreur de création: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_settings_dialog():
    """Test 3: Verify SettingsDialog works."""
    print("\nTest 3: Test du SettingsDialog...")
    try:
        from plugins.duplicate_finder.managers import UnifiedConfigManager, SettingsManager
        from plugins.duplicate_finder.ui import SettingsDialog

        # Create QApplication if needed
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        # Create config manager and dialog
        settings_manager = SettingsManager()
        config_manager = UnifiedConfigManager(settings_manager)
        dialog = SettingsDialog(config_manager)

        print(f"✅ SettingsDialog créé avec succès")
        print(f"   - Nombre d'onglets: {dialog.tabs.count()}")

        # Clean up
        dialog.close()
        dialog.deleteLater()

        return True
    except Exception as e:
        print(f"❌ Erreur SettingsDialog: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_config_migration():
    """Test 4: Verify config migration works."""
    print("\nTest 4: Test de la migration de configuration...")
    try:
        from plugins.duplicate_finder.managers import UnifiedConfigManager, SettingsManager
        from PyQt6.QtCore import QSettings

        settings_manager = SettingsManager()
        config_manager = UnifiedConfigManager(settings_manager)

        # Test auto-migration
        migrated = config_manager.auto_migrate_and_save()

        print(f"✅ Migration réussie")
        print(f"   - Config retournée: {migrated is not None}")

        return True
    except Exception as e:
        print(f"❌ Erreur migration: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_abstractions():
    """Test 5: Verify abstractions work."""
    print("\nTest 5: Test des abstractions...")
    try:
        from plugins.duplicate_finder.managers import ProgressManager, get_progress_manager
        from plugins.duplicate_finder.ui.widget_registry import WidgetRegistry, get_widget_registry
        from plugins.duplicate_finder.controllers import WorkflowController, get_workflow_controller

        # Test ProgressManager
        pm = ProgressManager()
        print(f"   - ProgressManager: ✅")

        # Test WidgetRegistry
        wr = WidgetRegistry()
        print(f"   - WidgetRegistry: ✅")

        # Test WorkflowController
        wc = WorkflowController()
        print(f"   - WorkflowController: ✅")

        # Test singletons
        pm2 = get_progress_manager()
        wr2 = get_widget_registry()
        wc2 = get_workflow_controller()
        print(f"   - Singletons: ✅")

        print(f"✅ Toutes les abstractions fonctionnent")
        return True
    except Exception as e:
        print(f"❌ Erreur abstractions: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("TEST D'INTÉGRATION END-TO-END - DUPLICATE FINDER")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("Imports", test_duplicate_finder_import()))
    results.append(("Création fenêtre", test_duplicate_finder_window_creation()))
    results.append(("SettingsDialog", test_settings_dialog()))
    results.append(("Migration config", test_config_migration()))
    results.append(("Abstractions", test_abstractions()))

    # Summary
    print("\n" + "=" * 60)
    print("RÉSUMÉ DES TESTS")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name:.<40} {status}")

    print("-" * 60)
    print(f"Total: {passed}/{total} tests réussis ({passed*100//total}%)")

    if passed == total:
        print("\n🎉 TOUS LES TESTS SONT PASSÉS!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) en échec")
        return 1

if __name__ == "__main__":
    sys.exit(main())
