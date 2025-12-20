#!/usr/bin/env python3
"""
Diagnostic complet du bouton Scènes.

Vérifie tous les composants nécessaires à la détection de scènes.
"""
import sys
import os

def check_scenes_button():
    """Vérifie tous les composants du bouton Scènes."""

    print("=" * 80)
    print("DIAGNOSTIC BOUTON SCÈNES")
    print("=" * 80)
    print()

    errors = []
    warnings = []

    # ========================================================================
    # CHECK 1: Imports
    # ========================================================================
    print("1️⃣  Vérification des imports...")
    try:
        from src.plugins.duplicate_finder import DuplicateFinderWindow
        from src.plugins.duplicate_finder.database_manager import VideoDatabase
        from src.plugins.duplicate_finder.subsequence_detector import SubsequenceDetector
        from src.plugins.duplicate_finder.orchestration.pipeline_manager import PipelineManager
        print("   ✅ Tous les imports OK")
    except Exception as e:
        errors.append(f"Import failed: {e}")
        print(f"   ❌ ERREUR: {e}")
        return False

    # ========================================================================
    # CHECK 2: Création fenêtre
    # ========================================================================
    print("\n2️⃣  Vérification création fenêtre...")
    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication(sys.argv)
        window = DuplicateFinderWindow()
        print("   ✅ Fenêtre créée")

        # Vérifier les widgets scènes
        if not hasattr(window, 'scenes_pipeline_combo'):
            errors.append("Missing scenes_pipeline_combo")
            print("   ❌ ERREUR: scenes_pipeline_combo manquant")
        else:
            print(f"   ✅ scenes_pipeline_combo: {window.scenes_pipeline_combo is not None}")

        if not hasattr(window, 'scenes_edit_btn'):
            warnings.append("Missing scenes_edit_btn")
            print("   ⚠️  scenes_edit_btn manquant")
        else:
            print(f"   ✅ scenes_edit_btn: {window.scenes_edit_btn is not None}")

        if not hasattr(window, 'scenes_new_btn'):
            warnings.append("Missing scenes_new_btn")
            print("   ⚠️  scenes_new_btn manquant")
        else:
            print(f"   ✅ scenes_new_btn: {window.scenes_new_btn is not None}")

    except Exception as e:
        errors.append(f"Window creation failed: {e}")
        print(f"   ❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return False

    # ========================================================================
    # CHECK 3: start_scene_detection_mode
    # ========================================================================
    print("\n3️⃣  Vérification méthode start_scene_detection_mode...")
    try:
        if hasattr(window, 'start_scene_detection_mode'):
            print("   ✅ Méthode existe")

            # Vérifier la signature
            import inspect
            sig = inspect.signature(window.start_scene_detection_mode)
            params = list(sig.parameters.keys())
            print(f"   📝 Paramètres: {params}")

            # Vérifier le contenu
            source = inspect.getsource(window.start_scene_detection_mode)
            if 'SubsequenceDetector' in source:
                print("   ✅ Utilise SubsequenceDetector")
            else:
                warnings.append("start_scene_detection_mode doesn't use SubsequenceDetector")
                print("   ⚠️  N'utilise pas SubsequenceDetector")

            if 'db_manager=' in source:
                print("   ✅ Passe db_manager correctement")
            elif 'hasher=' in source:
                warnings.append("Uses old 'hasher=' parameter")
                print("   ⚠️  Utilise ancien paramètre 'hasher='")

        else:
            errors.append("start_scene_detection_mode method missing")
            print("   ❌ Méthode manquante!")

    except Exception as e:
        errors.append(f"Method check failed: {e}")
        print(f"   ❌ ERREUR: {e}")

    # ========================================================================
    # CHECK 4: SubsequenceDetector signature
    # ========================================================================
    print("\n4️⃣  Vérification signature SubsequenceDetector...")
    try:
        import inspect
        sig = inspect.signature(SubsequenceDetector.__init__)
        params = list(sig.parameters.keys())
        print(f"   📝 Paramètres: {params}")

        if 'db_manager' in params:
            print("   ✅ Accepte db_manager")
        else:
            errors.append("SubsequenceDetector doesn't accept db_manager")
            print("   ❌ N'accepte PAS db_manager")

        if 'hasher' in params:
            print("   ✅ Accepte hasher (backward compat)")
        else:
            warnings.append("SubsequenceDetector doesn't accept hasher")
            print("   ⚠️  N'accepte PAS hasher")

    except Exception as e:
        errors.append(f"Signature check failed: {e}")
        print(f"   ❌ ERREUR: {e}")

    # ========================================================================
    # CHECK 5: Test création SubsequenceDetector
    # ========================================================================
    print("\n5️⃣  Test création SubsequenceDetector...")
    try:
        db = VideoDatabase("test_diagnostic.db")
        sd = SubsequenceDetector(db_manager=db)
        print("   ✅ Création OK avec db_manager")

        if hasattr(sd, 'hasher'):
            print("   ✅ hasher attribute exists")
        else:
            warnings.append("hasher attribute missing")
            print("   ⚠️  hasher attribute manquant")

        if hasattr(sd, 'db'):
            print("   ✅ db attribute exists")
        else:
            errors.append("db attribute missing")
            print("   ❌ db attribute manquant")

        # Nettoyer
        os.remove("test_diagnostic.db")

    except Exception as e:
        errors.append(f"SubsequenceDetector creation failed: {e}")
        print(f"   ❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()

    # ========================================================================
    # CHECK 6: Pipeline Manager
    # ========================================================================
    print("\n6️⃣  Vérification Pipeline Manager...")
    try:
        db = VideoDatabase("test_diagnostic2.db")
        pm = PipelineManager(db)
        pipelines = pm.list_pipelines(include_defaults=True)

        # Filtrer pour scènes
        scene_keywords = ['scene', 'intro', 'credit']
        scene_pipelines = [
            p for p in pipelines
            if any(kw in p['name'].lower() for kw in scene_keywords)
        ]

        print(f"   ✅ {len(pipelines)} pipelines totaux")
        print(f"   ✅ {len(scene_pipelines)} pipelines scènes")

        if len(scene_pipelines) == 0:
            warnings.append("No scene-specific pipelines found")
            print("   ⚠️  Aucun pipeline spécifique scènes")
        else:
            print(f"   📋 Pipelines scènes:")
            for p in scene_pipelines[:3]:
                print(f"      - {p['name']}")

        # Nettoyer
        os.remove("test_diagnostic2.db")

    except Exception as e:
        errors.append(f"Pipeline manager check failed: {e}")
        print(f"   ❌ ERREUR: {e}")

    # ========================================================================
    # RÉSUMÉ
    # ========================================================================
    print("\n" + "=" * 80)
    print("📊 RÉSUMÉ")
    print("=" * 80)

    if errors:
        print(f"\n❌ ERREURS BLOQUANTES ({len(errors)}):")
        for i, err in enumerate(errors, 1):
            print(f"   {i}. {err}")

    if warnings:
        print(f"\n⚠️  AVERTISSEMENTS ({len(warnings)}):")
        for i, warn in enumerate(warnings, 1):
            print(f"   {i}. {warn}")

    if not errors and not warnings:
        print("\n✅ TOUT EST OK - Le bouton Scènes devrait fonctionner!")
        return True
    elif not errors:
        print("\n⚠️  QUELQUES AVERTISSEMENTS - Le bouton Scènes devrait fonctionner mais peut avoir des problèmes mineurs")
        return True
    else:
        print("\n❌ ERREURS CRITIQUES - Le bouton Scènes NE PEUT PAS fonctionner")
        return False

if __name__ == "__main__":
    try:
        success = check_scenes_button()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n\n❌ ERREUR FATALE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
